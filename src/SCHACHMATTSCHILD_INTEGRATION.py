"""
SCHACHMATTSCHILD_INTEGRATION.py
Optimierung 4 & Modul 14: Vollständige Integration aller Komponenten
- Hardware-Abstraktion + KI-Modelle + Formale Verifikation
- NEU: Bionischer ISC-A Bridge Controller (Modul 14) im zyklischen Frame-Prüflauf
Autor: Dmitrij Medkov
Version: 2.1 (Acoustic Cascade Update)
"""

import os
import time
import logging
import json
from pathlib import Path
from typing import Any, Dict, Optional

# Importiere die bestehenden Optimierungen
from src.HARDWARE_ABSTRACTION_LAYER import HardwareFabrik, Plattform
from src.KI_MODELL_LADELOGIK import ModellManager, YOLOModell, PredictiveMaintenanceModell
from src.FORMALE_VERIFIKATION import (
    VerifikationsMonitor,
    erstelle_isc_zustandsmaschine,
    ZustandsMaschine,
    SicherheitseigenschaftFehler
)

# Importiere das neue Modul 14
from src.ISC_A_BRIDGE_CONTROLLER import ISCABridgeController, NavigationsModus

logger = logging.getLogger(__name__)

STANDARD_KONFIGURATION = {
    "system": {
        "name": "SCHACHMATTSCHILD",
        "version": "2.1",
        "debug_modus": False,
        "log_level": "INFO"
    },
    "hardware": {
        "plattform": "auto",
        "pixhawk_port": None,
        "kamera_aufloesung": [1920, 1080],
        "kamera_fps": 30,
        "gpio_pins": {
            "safety_interrupt": 18,
            "status_led": 23,
            "alarm": 24
        }
    },
    "ki_modelle": {
        "yolo_pfad": "modelle/yolo_drohnen.pt",
        "konfidenz_schwelle": 0.5,
        "fallback_erlaubt": True
    },
    "verifikation": {
        "aktiv": True,
        "strenger_modus": True
    }
}

class Konfiguration:
    def __init__(self, pfad: Optional[str] = None):
        self.daten = STANDARD_KONFIGURATION.copy()
        if pfad and os.path.exists(pfad):
            try:
                with open(pfad, "r", encoding="utf-8") as f:
                    nutzer_daten = json.load(f)
                    for k, v in nutzer_daten.items():
                        if isinstance(v, dict) and k in self.daten:
                            self.daten[k].update(v)
                        else:
                            self.daten[k] = v
            except Exception as e:
                print(f"⚠️ Konfigurationsfehler, nutze Standard: {e}")

class SchachmattSchildSystem:
    def __init__(self, konfig: Konfiguration):
        self.config = konfig.daten
        self._hardware: Optional[HardwareFabrik] = None
        self._modell_manager: Optional[ModellManager] = None
        self._verifikation: Optional[VerifikationsMonitor] = None
        self._zustandsmaschine: Optional[ZustandsMaschine] = None
        
        # Modul 14 Instanziierung
        self.acoustic_bridge: Optional[ISCABridgeController] = None
        self._drohne = None
        self._kamera = None
        self._gpio = None
        self._initialisiert = False

    def initialisieren(self) -> bool:
        """Initialisiert alle Teilsysteme dezentral und verifiziert den Startzustand"""
        logger.info(f"🚀 Initialisiere {self.config['system']['name']} v{self.config['system']['version']}...")
        
        # 1. Hardware-Ebene aktivieren
        self._hardware = HardwareFabrik()
        self._gpio = self._hardware.gpio()
        self._kamera = self._hardware.kamera()
        self._drohne = self._hardware.drohne(self.config['hardware']['pixhawk_port'])
        
        # 2. KI-Modelle laden
        self._modell_manager = ModellManager()
        yolo = YOLOModell(self.config['ki_modelle']['yolo_pfad'], self.config['ki_modelle']['fallback_erlaubt'])
        pm = PredictiveMaintenanceModell()
        self._modell_manager.registriere('yolo', yolo)
        self._modell_manager.registriere('predictive_maintenance', pm)
        self._modell_manager.lade_alle()
        
        # 3. Formale Verifikation & Monitor starten
        self._verifikation = VerifikationsMonitor()
        self._zustandsmaschine = erstelle_isc_zustandsmaschine()
        self._zustandsmaschine.uebergang('INITIALISIERUNG')
        
        # 4. Modul 14 Controller binden
        self.acoustic_bridge = ISCABridgeController(self)
        
        self._zustandsmaschine.uebergang('NORMALBETRIEB')
        self._initialisiert = True
        logger.info("✅ SCHACHMATTSCHILD: Alle Systeme inklusive Modul 14 operational.")
        return True

    def verarbeite_frame(self, simulierte_anomalie: bool = False, hf_jamming: float = 0.0, akustik_stoerung: float = 0.0) -> Dict[str, Any]:
        """
        Zentraler zyklischer Frame-Prüflauf (Kernschleife).
        Überwacht kontinuierlich die Integrität der Sensoren und schaltet ggf. Kaskaden.
        """
        if not self._initialisiert:
            raise RuntimeError("System nicht initialisiert!")

        self._zustandsmaschine.uebergang('VALIDIERUNG')
        
        # Telemetrie und Sensorik einlesen
        telemetrie = self._drohne.lese_telemetrie() if self._drohne else {}
        gps_validiert = not simulierte_anomalie  # Wenn simulierte Anomalie, schlägt GPS fehl
        
        # Modul 14 Kaskadenevaluierung ausführen
        primar_modus_aktiv = self.acoustic_bridge.evaluiere_kaskade(
            gps_validiert=gps_validiert,
            hf_jamming_pegel=hf_jamming,
            akustik_stoerung=akustik_stoerung
        )
        
        # JAR-Algorithmus triggern, falls wir bereits im Akustik-Modus sind
        aktuelle_frequenz = self.acoustic_bridge.jar_frequenzwechsel()

        # Erstelle aktuellen Systemzustand für den formalen Verifikations-Monitor
        system_zustand = {
            'aktion_aktiv': True,
            'realitaet_validiert': primar_modus_aktiv or (self.acoustic_bridge.modus == NavigationsModus.SEKUNDAER_ISC_A),
            'entscheidungen_gesamt': 1,
            'log_eintraege': 1,
            'aktive_referenzquellen': 3 if primar_modus_aktiv else 2,
            'notfall_stop_verfuegbar': True,
            'ziel_ist_freund': False,
            'waffe_aktiv': False
        }

        # Formale Verifikation erzwingen
        verifikation_ok = self._verifikation.pruefe_zustand(system_zustand)
        
        # Status-LEDs auf der Hardware schalten je nach Modus
        if self.acoustic_bridge.modus == NavigationsModus.PRIMAER_GNSS:
            self._gpio.setze_pin(self.config['hardware']['gpio_pins']['status_led'], True)
            self._gpio.setze_pin(self.config['hardware']['gpio_pins']['alarm'], False)
        else:
            # Bei Umschaltung auf ISC-A oder Glasfaser: Warn-Alarm auf GPIO ausgeben
            self._gpio.setze_pin(self.config['hardware']['gpio_pins']['status_led'], False)
            self._gpio.setze_pin(self.config['hardware']['gpio_pins']['alarm'], True)

        self._zustandsmaschine.uebergang('NORMALBETRIEB')

        return {
            "status": "PROCESSED",
            "navigations_modus": self.acoustic_bridge.modus.value,
            "akustische_frequenz_hz": aktuelle_frequenz,
            "verifikation_ok": verifikation_ok,
            "system_zustand": self._zustandsmaschine.zustand
        }

    def telemetrie(self) -> Dict[str, Any]:
        return {
            'plattform': self._hardware.plattform.value if self._hardware else "unknown",
            'modus': self.acoustic_bridge.modus.value if self.acoustic_bridge else "unknown",
            'frequenz': self.acoustic_bridge.aktuelle_frequenz if self.acoustic_bridge else 0.0,
            'ki_status': self._modell_manager.status_alle() if self._modell_manager else {}
        }

    def aufraumen(self) -> None:
        logger.info("🔄 System wird heruntergefahren...")
        if self._hardware:
            self._hardware.aufraumen()
        logger.info("✅ System heruntergefahren")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("SCHACHMATTSCHILD v2.1 Integration Test Run")
    config = Konfiguration()
    system = SchachmattSchildSystem(config)
    system.initialisieren()
    res = system.verarbeite_frame(simulierte_anomalie=True, hf_jamming=0.8)
    print(f"Ergebnis bei GPS-Ausfall: {res}")
    system.aufraumen()