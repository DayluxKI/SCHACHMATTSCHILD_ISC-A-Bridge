"""
HARDWARE_ABSTRACTION_LAYER.py
SCHACHMATTSCHILD – ISC Sicherheitsplattform
Optimierung 1: Vollständige Hardware-Abstraktion
- Raspberry Pi GPIO (echte Hardware)
- NVIDIA Jetson
- Pixhawk/ArduPilot Integration
- x86 Simulation
Autor: Dmitrij Medkov
"""

import time
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# PLATTFORM-ERKENNUNG
# =============================================================================

class Plattform(Enum):
    RASPBERRY_PI = "raspberry_pi"
    NVIDIA_JETSON = "nvidia_jetson"
    X86_SIMULATION = "x86_simulation"
    PIXHAWK = "pixhawk"


def erkenne_plattform() -> Plattform:
    """Automatische Plattformerkennung"""
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        if 'Raspberry Pi' in cpuinfo or 'BCM' in cpuinfo:
            return Plattform.RASPBERRY_PI
        if 'NVIDIA Tegra' in cpuinfo or 'Jetson' in cpuinfo:
            return Plattform.NVIDIA_JETSON
    except Exception:
        pass
    return Plattform.X86_SIMULATION


# =============================================================================
# ABSTRAKTE BASIS-KLASSEN
# =============================================================================

class GPIOSteuerung(ABC):
    """Abstrakte Basisklasse für GPIO-Steuerung"""

    @abstractmethod
    def pin_als_ausgang(self, pin: int) -> None:
        pass

    @abstractmethod
    def pin_als_eingang(self, pin: int, pull_up: bool = True) -> None:
        pass

    @abstractmethod
    def setze_pin(self, pin: int, wert: bool) -> None:
        pass

    @abstractmethod
    def lese_pin(self, pin: int) -> bool:
        pass

    @abstractmethod
    def pwm_starten(self, pin: int, frequenz: float, duty_cycle: float) -> None:
        pass

    @abstractmethod
    def pwm_stoppen(self, pin: int) -> None:
        pass

    @abstractmethod
    def aufraumen(self) -> None:
        pass


class KameraHardware(ABC):
    """Abstrakte Basisklasse für Kamera-Hardware"""

    @abstractmethod
    def initialisieren(self) -> bool:
        pass

    @abstractmethod
    def frame_aufnehmen(self) -> Optional[Any]:
        pass

    @abstractmethod
    def freigeben(self) -> None:
        pass


class AudioHardware(ABC):
    """Abstrakte Basisklasse für Audio-Hardware"""

    @abstractmethod
    def aufnehmen(self, dauer_sekunden: float) -> Optional[bytes]:
        pass

    @abstractmethod
    def abspielen(self, audio_daten: bytes) -> None:
        pass


class DrohnenSteuerung(ABC):
    """Abstrakte Basisklasse für Drohnen-Steuerung (Pixhawk/ArduPilot)"""

    @abstractmethod
    def verbinden(self, verbindungs_string: str) -> bool:
        pass

    @abstractmethod
    def arm(self) -> bool:
        pass

    @abstractmethod
    def disarm(self) -> bool:
        pass

    @abstractmethod
    def takeoff(self, hoehe_meter: float) -> bool:
        pass

    @abstractmethod
    def land(self) -> bool:
        pass

    @abstractmethod
    def setze_position(self, lat: float, lon: float, alt: float) -> bool:
        pass

    @abstractmethod
    def setze_geschwindigkeit(self, vx: float, vy: float, vz: float) -> bool:
        pass

    @abstractmethod
    def lese_telemetrie(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def notfall_stop(self) -> bool:
        pass


# =============================================================================
# RASPBERRY PI IMPLEMENTIERUNG
# =============================================================================

class RaspberryPiGPIO(GPIOSteuerung):
    """Echte GPIO-Implementierung für Raspberry Pi"""

    def __init__(self):
        self._gpio = None
        self._pwm_instanzen: Dict[int, Any] = {}
        self._initialisiert = False
        self._initialisieren()

    def _initialisieren(self) -> None:
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            self._gpio.setmode(GPIO.BCM)
            self._gpio.setwarnings(False)
            self._initialisiert = True
            logger.info("✅ Raspberry Pi GPIO initialisiert (BCM-Modus)")
        except ImportError:
            logger.warning("⚠️ RPi.GPIO nicht verfügbar – Fallback auf Simulation")
            self._gpio = SimulierteGPIO()
            self._initialisiert = True

    def pin_als_ausgang(self, pin: int) -> None:
        if self._initialisiert:
            try:
                self._gpio.setup(pin, self._gpio.OUT)
            except Exception:
                self._gpio.setup(pin, 'OUT')

    def pin_als_eingang(self, pin: int, pull_up: bool = True) -> None:
        if self._initialisiert:
            try:
                pud = self._gpio.PUD_UP if pull_up else self._gpio.PUD_DOWN
                self._gpio.setup(pin, self._gpio.IN, pull_up_down=pud)
            except Exception:
                self._gpio.setup(pin, 'IN')

    def setze_pin(self, pin: int, wert: bool) -> None:
        if self._initialisiert:
            try:
                self._gpio.output(pin, self._gpio.HIGH if wert else self._gpio.LOW)
            except Exception:
                self._gpio.output(pin, wert)

    def lese_pin(self, pin: int) -> bool:
        if self._initialisiert:
            try:
                return bool(self._gpio.input(pin))
            except Exception:
                return False
        return False

    def pwm_starten(self, pin: int, frequenz: float, duty_cycle: float) -> None:
        if self._initialisiert:
            try:
                self.pin_als_ausgang(pin)
                pwm = self._gpio.PWM(pin, frequenz)
                pwm.start(duty_cycle)
                self._pwm_instanzen[pin] = pwm
                logger.info(f"PWM gestartet – Pin {pin}, {frequenz}Hz, {duty_cycle}%")
            except Exception as e:
                logger.error(f"PWM Fehler: {e}")

    def pwm_stoppen(self, pin: int) -> None:
        if pin in self._pwm_instanzen:
            self._pwm_instanzen[pin].stop()
            del self._pwm_instanzen[pin]

    def aufraumen(self) -> None:
        for pin in list(self._pwm_instanzen.keys()):
            self.pwm_stoppen(pin)
        try:
            self._gpio.cleanup()
        except Exception:
            pass
        logger.info("GPIO aufgeräumt")


class RaspberryPiKamera(KameraHardware):
    """Kamera-Implementierung für Raspberry Pi"""

    def __init__(self, aufloesung=(1920, 1080), fps=30):
        self._aufloesung = aufloesung
        self._fps = fps
        self._kamera = None
        self._cv2 = None

    def initialisieren(self) -> bool:
        try:
            import cv2
            self._cv2 = cv2
            # Versuche PiCamera
            try:
                from picamera2 import Picamera2
                self._kamera = Picamera2()
                config = self._kamera.create_preview_configuration(
                    main={"size": self._aufloesung}
                )
                self._kamera.configure(config)
                self._kamera.start()
                logger.info("✅ PiCamera2 initialisiert")
                return True
            except ImportError:
                pass
            # Fallback: USB Kamera
            self._kamera = cv2.VideoCapture(0)
            self._kamera.set(cv2.CAP_PROP_FRAME_WIDTH, self._aufloesung[0])
            self._kamera.set(cv2.CAP_PROP_FRAME_HEIGHT, self._aufloesung[1])
            self._kamera.set(cv2.CAP_PROP_FPS, self._fps)
            if self._kamera.isOpened():
                logger.info("✅ USB-Kamera initialisiert")
                return True
        except Exception as e:
            logger.error(f"Kamera-Fehler: {e}")
        return False

    def frame_aufnehmen(self) -> Optional[Any]:
        try:
            from picamera2 import Picamera2
            if isinstance(self._kamera, Picamera2):
                return self._kamera.capture_array()
        except ImportError:
            pass
        if self._kamera and self._cv2:
            ret, frame = self._kamera.read()
            return frame if ret else None
        return None

    def freigeben(self) -> None:
        if self._kamera:
            try:
                self._kamera.stop()
            except Exception:
                try:
                    self._kamera.release()
                except Exception:
                    pass


class RaspberryPiAudio(AudioHardware):
    """Audio-Implementierung für Raspberry Pi"""

    def __init__(self, samplerate=44100, kanaele=1):
        self._samplerate = samplerate
        self._kanaele = kanaele

    def aufnehmen(self, dauer_sekunden: float) -> Optional[bytes]:
        try:
            import sounddevice as sd
            import numpy as np
            frames = int(dauer_sekunden * self._samplerate)
            aufnahme = sd.rec(frames, samplerate=self._samplerate,
                              channels=self._kanaele, dtype='int16')
            sd.wait()
            return aufnahme.tobytes()
        except Exception as e:
            logger.error(f"Audio-Aufnahme-Fehler: {e}")
            return None

    def abspielen(self, audio_daten: bytes) -> None:
        try:
            import sounddevice as sd
            import numpy as np
            audio_array = np.frombuffer(audio_daten, dtype='int16')
            sd.play(audio_array, self._samplerate)
            sd.wait()
        except Exception as e:
            logger.error(f"Audio-Wiedergabe-Fehler: {e}")


# =============================================================================
# PIXHAWK / ARDUPILOT IMPLEMENTIERUNG (NEU)
# =============================================================================

class PixhawkSteuerung(DrohnenSteuerung):
    """
    Echte Pixhawk/ArduPilot Integration über MAVLink.
    Unterstützt: Pixhawk 4, Pixhawk 6C, Cube Orange, ArduPilot
    """

    def __init__(self):
        self._fahrzeug = None
        self._verbunden = False
        self._letzte_telemetrie: Dict[str, Any] = {}

    def verbinden(self, verbindungs_string: str = 'udp:127.0.0.1:14550') -> bool:
        """
        Verbindet mit Pixhawk über MAVLink.
        Verbindungsstrings:
          - USB:    '/dev/ttyUSB0'  oder  '/dev/ttyACM0'
          - UDP:    'udp:127.0.0.1:14550'
          - TCP:    'tcp:127.0.0.1:5760'
        """
        try:
            from dronekit import connect, VehicleMode
            logger.info(f"🔌 Verbinde mit Pixhawk: {verbindungs_string}")
            self._fahrzeug = connect(
                verbindungs_string,
                wait_ready=True,
                timeout=30,
                heartbeat_timeout=30
            )
            self._verbunden = True
            logger.info(f"✅ Pixhawk verbunden")
            logger.info(f"   Firmware: {self._fahrzeug.version}")
            logger.info(f"   GPS: {self._fahrzeug.gps_0}")
            logger.info(f"   Batterie: {self._fahrzeug.battery}")
            return True
        except ImportError:
            logger.error("❌ DroneKit nicht installiert: pip install dronekit")
            return False
        except Exception as e:
            logger.error(f"❌ Verbindungsfehler: {e}")
            return False

    def arm(self) -> bool:
        """Armt die Drohne (aktiviert Motoren)"""
        if not self._verbunden or not self._fahrzeug:
            return False
        try:
            from dronekit import VehicleMode
            # Prüfe ob armierbar
            if not self._fahrzeug.is_armable:
                logger.warning("⚠️ Drohne noch nicht armierbar – warte...")
                timeout = 30
                while not self._fahrzeug.is_armable and timeout > 0:
                    time.sleep(1)
                    timeout -= 1
            self._fahrzeug.mode = VehicleMode("GUIDED")
            self._fahrzeug.armed = True
            # Warte auf Bestätigung
            timeout = 10
            while not self._fahrzeug.armed and timeout > 0:
                time.sleep(0.5)
                timeout -= 1
            if self._fahrzeug.armed:
                logger.info("✅ Drohne armiert")
                return True
            logger.error("❌ Armierung fehlgeschlagen")
            return False
        except Exception as e:
            logger.error(f"❌ Arm-Fehler: {e}")
            return False

    def disarm(self) -> bool:
        """Disarmt die Drohne"""
        if not self._verbunden or not self._fahrzeug:
            return False
        try:
            self._fahrzeug.armed = False
            logger.info("✅ Drohne disarmiert")
            return True
        except Exception as e:
            logger.error(f"❌ Disarm-Fehler: {e}")
            return False

    def takeoff(self, hoehe_meter: float) -> bool:
        """Startet und steigt auf definierte Höhe"""
        if not self._verbunden or not self._fahrzeug:
            return False
        try:
            logger.info(f"🚀 Takeoff auf {hoehe_meter}m")
            self._fahrzeug.simple_takeoff(hoehe_meter)
            # Warte bis Zielhöhe erreicht
            while True:
                aktuelle_hoehe = self._fahrzeug.location.global_relative_frame.alt
                if aktuelle_hoehe >= hoehe_meter * 0.95:
                    logger.info(f"✅ Zielhöhe {hoehe_meter}m erreicht")
                    return True
                time.sleep(0.5)
        except Exception as e:
            logger.error(f"❌ Takeoff-Fehler: {e}")
            return False

    def land(self) -> bool:
        """Landet die Drohne"""
        if not self._verbunden or not self._fahrzeug:
            return False
        try:
            from dronekit import VehicleMode
            self._fahrzeug.mode = VehicleMode("LAND")
            logger.info("🛬 Landung eingeleitet")
            return True
        except Exception as e:
            logger.error(f"❌ Lande-Fehler: {e}")
            return False

    def setze_position(self, lat: float, lon: float, alt: float) -> bool:
        """Fliegt zu GPS-Position"""
        if not self._verbunden or not self._fahrzeug:
            return False
        try:
            from dronekit import LocationGlobalRelative
            ziel = LocationGlobalRelative(lat, lon, alt)
            self._fahrzeug.simple_goto(ziel)
            logger.info(f"📍 Fliege zu: {lat}, {lon}, {alt}m")
            return True
        except Exception as e:
            logger.error(f"❌ Positions-Fehler: {e}")
            return False

    def setze_geschwindigkeit(self, vx: float, vy: float, vz: float) -> bool:
        """Setzt Geschwindigkeit in m/s (NED-Koordinaten)"""
        if not self._verbunden or not self._fahrzeug:
            return False
        try:
            from pymavlink import mavutil
            msg = self._fahrzeug.message_factory.set_position_target_local_ned_encode(
                0, 0, 0,
                mavutil.mavlink.MAV_FRAME_LOCAL_NED,
                0b0000111111000111,
                0, 0, 0,
                vx, vy, vz,
                0, 0, 0,
                0, 0
            )
            self._fahrzeug.send_mavlink(msg)
            return True
        except Exception as e:
            logger.error(f"❌ Geschwindigkeits-Fehler: {e}")
            return False

    def lese_telemetrie(self) -> Dict[str, Any]:
        """Liest aktuelle Telemetriedaten"""
        if not self._verbunden or not self._fahrzeug:
            return {}
        try:
            loc = self._fahrzeug.location.global_relative_frame
            self._letzte_telemetrie = {
                'latitude': loc.lat,
                'longitude': loc.lon,
                'altitude': loc.alt,
                'heading': self._fahrzeug.heading,
                'groundspeed': self._fahrzeug.groundspeed,
                'airspeed': self._fahrzeug.airspeed,
                'battery_voltage': self._fahrzeug.battery.voltage,
                'battery_level': self._fahrzeug.battery.level,
                'gps_fix': self._fahrzeug.gps_0.fix_type,
                'armed': self._fahrzeug.armed,
                'mode': self._fahrzeug.mode.name,
                'timestamp': time.time()
            }
            return self._letzte_telemetrie
        except Exception as e:
            logger.error(f"❌ Telemetrie-Fehler: {e}")
            return self._letzte_telemetrie

    def notfall_stop(self) -> bool:
        """NOTFALL: Sofortiger Motorstopp"""
        if not self._verbunden or not self._fahrzeug:
            return False
        try:
            from dronekit import VehicleMode
            logger.critical("🚨 NOTFALL-STOP AKTIVIERT!")
            self._fahrzeug.mode = VehicleMode("LAND")
            self._fahrzeug.armed = False
            return True
        except Exception as e:
            logger.critical(f"KRITISCH – Notfall-Stop fehlgeschlagen: {e}")
            return False


# =============================================================================
# NVIDIA JETSON IMPLEMENTIERUNGEN
# =============================================================================

class NVIDIAJetsonKamera(KameraHardware):
    """Kamera-Implementierung für NVIDIA Jetson mit GStreamer"""

    def __init__(self, sensor_id=0, aufloesung=(1920, 1080), fps=30):
        self._sensor_id = sensor_id
        self._aufloesung = aufloesung
        self._fps = fps
        self._kamera = None
        self._cv2 = None

    def _gstreamer_pipeline(self) -> str:
        return (
            f"nvarguscamerasrc sensor-id={self._sensor_id} ! "
            f"video/x-raw(memory:NVMM), width={self._aufloesung[0]}, "
            f"height={self._aufloesung[1]}, framerate={self._fps}/1 ! "
            f"nvvidconv ! video/x-raw, format=BGRx ! "
            f"videoconvert ! video/x-raw, format=BGR ! appsink"
        )

    def initialisieren(self) -> bool:
        try:
            import cv2
            self._cv2 = cv2
            self._kamera = cv2.VideoCapture(
                self._gstreamer_pipeline(), cv2.CAP_GSTREAMER
            )
            if self._kamera.isOpened():
                logger.info("✅ NVIDIA Jetson Kamera initialisiert")
                return True
            # Fallback USB
            self._kamera = cv2.VideoCapture(0)
            return self._kamera.isOpened()
        except Exception as e:
            logger.error(f"Jetson Kamera Fehler: {e}")
            return False

    def frame_aufnehmen(self) -> Optional[Any]:
        if self._kamera and self._cv2:
            ret, frame = self._kamera.read()
            return frame if ret else None
        return None

    def freigeben(self) -> None:
        if self._kamera:
            self._kamera.release()


class NVIDIAAudio(AudioHardware):
    """Audio-Implementierung für NVIDIA Jetson"""

    def aufnehmen(self, dauer_sekunden: float) -> Optional[bytes]:
        try:
            import sounddevice as sd
            import numpy as np
            aufnahme = sd.rec(
                int(dauer_sekunden * 44100),
                samplerate=44100, channels=1, dtype='int16'
            )
            sd.wait()
            return aufnahme.tobytes()
        except Exception as e:
            logger.error(f"Jetson Audio Fehler: {e}")
            return None

    def abspielen(self, audio_daten: bytes) -> None:
        try:
            import sounddevice as sd
            import numpy as np
            sd.play(np.frombuffer(audio_daten, dtype='int16'), 44100)
            sd.wait()
        except Exception as e:
            logger.error(f"Audio Wiedergabe Fehler: {e}")


# =============================================================================
# SIMULATION (x86 / Entwicklung)
# =============================================================================

class SimulierteGPIO:
    """Simulierte GPIO für Entwicklung ohne Hardware"""
    OUT = 'OUT'
    IN = 'IN'
    HIGH = True
    LOW = False
    PUD_UP = 'PUD_UP'
    PUD_DOWN = 'PUD_DOWN'
    BCM = 'BCM'

    def __init__(self):
        self._pins: Dict[int, bool] = {}
        logger.info("🖥️ Simulierte GPIO aktiv (kein echtes Hardware)")

    def setmode(self, modus): pass
    def setwarnings(self, wert): pass
    def setup(self, pin, modus, pull_up_down=None):
        self._pins[pin] = False
    def output(self, pin, wert):
        self._pins[pin] = bool(wert)
    def input(self, pin) -> bool:
        return self._pins.get(pin, False)
    def PWM(self, pin, frequenz):
        return SimuliertePWM(pin, frequenz)
    def cleanup(self): pass


class SimuliertePWM:
    def __init__(self, pin, frequenz):
        self._pin = pin
        self._frequenz = frequenz
    def start(self, duty_cycle):
        logger.debug(f"PWM-Simulation: Pin {self._pin}, {self._frequenz}Hz, {duty_cycle}%")
    def stop(self): pass
    def ChangeDutyCycle(self, duty_cycle): pass


class SimulierteDrohnenSteuerung(DrohnenSteuerung):
    """Simulierte Drohnensteuerung für Entwicklung ohne Pixhawk"""

    def __init__(self):
        self._position = {'lat': 52.0, 'lon': 8.5, 'alt': 0.0}
        self._armed = False
        self._verbunden = False

    def verbinden(self, verbindungs_string: str) -> bool:
        self._verbunden = True
        logger.info("🖥️ Simulierte Drohnensteuerung verbunden")
        return True

    def arm(self) -> bool:
        self._armed = True
        logger.info("✅ [SIM] Drohne armiert")
        return True

    def disarm(self) -> bool:
        self._armed = False
        logger.info("✅ [SIM] Drohne disarmiert")
        return True

    def takeoff(self, hoehe_meter: float) -> bool:
        self._position['alt'] = hoehe_meter
        logger.info(f"🚀 [SIM] Takeoff auf {hoehe_meter}m")
        return True

    def land(self) -> bool:
        self._position['alt'] = 0.0
        logger.info("🛬 [SIM] Landung")
        return True

    def setze_position(self, lat: float, lon: float, alt: float) -> bool:
        self._position = {'lat': lat, 'lon': lon, 'alt': alt}
        return True

    def setze_geschwindigkeit(self, vx: float, vy: float, vz: float) -> bool:
        return True

    def lese_telemetrie(self) -> Dict[str, Any]:
        return {
            'latitude': self._position['lat'],
            'longitude': self._position['lon'],
            'altitude': self._position['alt'],
            'heading': 0.0,
            'groundspeed': 0.0,
            'battery_voltage': 12.6,
            'battery_level': 95,
            'armed': self._armed,
            'mode': 'GUIDED',
            'timestamp': time.time()
        }

    def notfall_stop(self) -> bool:
        self._armed = False
        logger.critical("🚨 [SIM] NOTFALL-STOP")
        return True


class X86Kamera(KameraHardware):
    """Kamera für x86 Entwicklungsrechner"""

    def __init__(self):
        self._kamera = None
        self._cv2 = None

    def initialisieren(self) -> bool:
        try:
            import cv2
            self._cv2 = cv2
            self._kamera = cv2.VideoCapture(0)
            if self._kamera.isOpened():
                logger.info("✅ x86 USB-Kamera initialisiert")
                return True
        except Exception as e:
            logger.error(f"x86 Kamera Fehler: {e}")
        return False

    def frame_aufnehmen(self) -> Optional[Any]:
        if self._kamera and self._cv2:
            ret, frame = self._kamera.read()
            return frame if ret else None
        return None

    def freigeben(self) -> None:
        if self._kamera:
            self._kamera.release()


class X86Audio(AudioHardware):
    """Audio für x86 Entwicklungsrechner"""

    def aufnehmen(self, dauer_sekunden: float) -> Optional[bytes]:
        try:
            import sounddevice as sd
            import numpy as np
            aufnahme = sd.rec(
                int(dauer_sekunden * 44100),
                samplerate=44100, channels=1, dtype='int16'
            )
            sd.wait()
            return aufnahme.tobytes()
        except Exception as e:
            logger.error(f"x86 Audio Fehler: {e}")
            return None

    def abspielen(self, audio_daten: bytes) -> None:
        try:
            import sounddevice as sd
            import numpy as np
            sd.play(np.frombuffer(audio_daten, dtype='int16'), 44100)
            sd.wait()
        except Exception as e:
            logger.error(f"x86 Wiedergabe Fehler: {e}")


# =============================================================================
# HARDWARE-FABRIK (Singleton)
# =============================================================================

class HardwareFabrik:
    """
    Zentrale Hardware-Fabrik.
    Erkennt Plattform automatisch und gibt die richtige Implementierung zurück.
    """
    _instanz: Optional['HardwareFabrik'] = None

    def __new__(cls):
        if cls._instanz is None:
            cls._instanz = super().__new__(cls)
            cls._instanz._initialisiert = False
        return cls._instanz

    def __init__(self):
        if not self._initialisiert:
            self._plattform = erkenne_plattform()
            self._hardware_instanzen: Dict[str, Any] = {}
            self._initialisiert = True
            logger.info(f"🔧 Hardware-Fabrik initialisiert: {self._plattform.value}")

    @property
    def plattform(self) -> Plattform:
        return self._plattform

    def gpio(self) -> GPIOSteuerung:
        key = 'gpio'
        if key not in self._hardware_instanzen:
            if self._plattform == Plattform.RASPBERRY_PI:
                self._hardware_instanzen[key] = RaspberryPiGPIO()
            else:
                self._hardware_instanzen[key] = RaspberryPiGPIO()  # Fallback auf Sim
        return self._hardware_instanzen[key]

    def kamera(self) -> KameraHardware:
        key = 'kamera'
        if key not in self._hardware_instanzen:
            if self._plattform == Plattform.RASPBERRY_PI:
                self._hardware_instanzen[key] = RaspberryPiKamera()
            elif self._plattform == Plattform.NVIDIA_JETSON:
                self._hardware_instanzen[key] = NVIDIAJetsonKamera()
            else:
                self._hardware_instanzen[key] = X86Kamera()
        return self._hardware_instanzen[key]

    def audio(self) -> AudioHardware:
        key = 'audio'
        if key not in self._hardware_instanzen:
            if self._plattform == Plattform.RASPBERRY_PI:
                self._hardware_instanzen[key] = RaspberryPiAudio()
            elif self._plattform == Plattform.NVIDIA_JETSON:
                self._hardware_instanzen[key] = NVIDIAAudio()
            else:
                self._hardware_instanzen[key] = X86Audio()
        return self._hardware_instanzen[key]

    def drohne(self, verbindungs_string: Optional[str] = None) -> DrohnenSteuerung:
        """
        Gibt Drohnensteuerung zurück.
        Bei verbindungs_string=None wird Simulation verwendet.
        Beispiel: fabrik.drohne('/dev/ttyUSB0')  # Pixhawk über USB
        """
        key = 'drohne'
        if key not in self._hardware_instanzen:
            if verbindungs_string:
                steuerung = PixhawkSteuerung()
                if steuerung.verbinden(verbindungs_string):
                    self._hardware_instanzen[key] = steuerung
                else:
                    logger.warning("Pixhawk nicht erreichbar – Simulation aktiv")
                    sim = SimulierteDrohnenSteuerung()
                    sim.verbinden('')
                    self._hardware_instanzen[key] = sim
            else:
                sim = SimulierteDrohnenSteuerung()
                sim.verbinden('')
                self._hardware_instanzen[key] = sim
        return self._hardware_instanzen[key]

    def aufraumen(self) -> None:
        """Räumt alle Hardware-Ressourcen auf"""
        for key, instanz in self._hardware_instanzen.items():
            try:
                if hasattr(instanz, 'aufraumen'):
                    instanz.aufraumen()
                elif hasattr(instanz, 'freigeben'):
                    instanz.freigeben()
            except Exception as e:
                logger.error(f"Aufräum-Fehler für {key}: {e}")
        self._hardware_instanzen.clear()
        logger.info("✅ Alle Hardware-Ressourcen freigegeben")


# =============================================================================
# HAUPTPROGRAMM – TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("SCHACHMATTSCHILD – Hardware-Abstraktion Test")
    print("=" * 60)

    fabrik = HardwareFabrik()
    print(f"Erkannte Plattform: {fabrik.plattform.value}")

    # GPIO Test
    gpio = fabrik.gpio()
    gpio.pin_als_ausgang(18)
    gpio.setze_pin(18, True)
    print(f"GPIO Pin 18: {gpio.lese_pin(18)}")

    # Kamera Test
    kamera = fabrik.kamera()
    if kamera.initialisieren():
        frame = kamera.frame_aufnehmen()
        print(f"Kamera: {'Frame erhalten' if frame is not None else 'Kein Frame'}")
        kamera.freigeben()

    # Drohne Test (Simulation)
    drohne = fabrik.drohne()  # Ohne Verbindungsstring = Simulation
    telemetrie = drohne.lese_telemetrie()
    print(f"Drohne Telemetrie: {telemetrie}")

    fabrik.aufraumen()
    print("✅ Hardware-Abstraktion Test abgeschlossen")
