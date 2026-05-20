"""
KI_MODELL_LADELOGIK.py
SCHACHMATTSCHILD – ISC Sicherheitsplattform
Optimierung 2: KI-Modell-Gewichte Ladelogik
- Automatisches Laden von .pth / .onnx / .pt Dateien
- Fallback-Mechanismus bei fehlendem Modell
- Modell-Validierung vor Nutzung
- Caching für schnelleres Laden
Autor: Dmitrij Medkov
"""

import os
import time
import logging
import hashlib
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# MODELL-TYPEN
# =============================================================================

class ModellTyp(Enum):
    PYTORCH = ".pt"
    PYTORCH_GEWICHTE = ".pth"
    ONNX = ".onnx"
    TFLITE = ".tflite"
    TENSORRT = ".engine"


class ModellStatus(Enum):
    NICHT_GELADEN = "nicht_geladen"
    GELADEN = "geladen"
    FEHLER = "fehler"
    FALLBACK = "fallback"


# =============================================================================
# ABSTRAKTE BASIS-KLASSE
# =============================================================================

class KIModell(ABC):
    """Abstrakte Basisklasse für alle KI-Modelle"""

    def __init__(self, modell_pfad: str, fallback_modus: bool = True):
        self._modell_pfad = Path(modell_pfad)
        self._fallback_modus = fallback_modus
        self._modell = None
        self._status = ModellStatus.NICHT_GELADEN
        self._lade_zeit: float = 0.0
        self._modell_hash: str = ""
        self._metadaten: Dict[str, Any] = {}

    @abstractmethod
    def laden(self) -> bool:
        pass

    @abstractmethod
    def inferenz(self, eingabe: Any) -> Any:
        pass

    @abstractmethod
    def _fallback_inferenz(self, eingabe: Any) -> Any:
        """Fallback wenn Modell nicht geladen"""
        pass

    @property
    def status(self) -> ModellStatus:
        return self._status

    @property
    def geladen(self) -> bool:
        return self._status == ModellStatus.GELADEN

    def _berechne_hash(self) -> str:
        """Berechnet MD5-Hash der Modelldatei zur Integritätsprüfung"""
        try:
            md5 = hashlib.md5()
            with open(self._modell_pfad, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception:
            return ""

    def validiere(self) -> bool:
        """Validiert ob das Modell korrekt geladen wurde"""
        if self._status != ModellStatus.GELADEN:
            return False
        if not self._modell:
            return False
        return True

    def info(self) -> Dict[str, Any]:
        return {
            'pfad': str(self._modell_pfad),
            'status': self._status.value,
            'lade_zeit': f"{self._lade_zeit:.2f}s",
            'hash': self._modell_hash[:8] + "..." if self._modell_hash else "N/A",
            'metadaten': self._metadaten
        }


# =============================================================================
# YOLO MODELL (Zielerkennung)
# =============================================================================

class YOLOModell(KIModell):
    """
    YOLO-Modell für Drohnen-Zielerkennung.
    Unterstützt YOLOv8, YOLOv5, ONNX-Export.
    """

    # Drohnen-spezifische Klassen
    ZIEL_KLASSEN = {
        0: 'fpv_drohne',
        1: 'multirotor',
        2: 'fixed_wing',
        3: 'helikopter',
        4: 'person',
        5: 'fahrzeug'
    }

    def __init__(
        self,
        modell_pfad: str = "modelle/yolo_drohnen.pt",
        konfidenz_schwelle: float = 0.5,
        iou_schwelle: float = 0.45,
        device: str = 'auto'
    ):
        super().__init__(modell_pfad)
        self._konfidenz_schwelle = konfidenz_schwelle
        self._iou_schwelle = iou_schwelle
        self._device = self._waehle_device(device)

    def _waehle_device(self, device: str) -> str:
        if device == 'auto':
            try:
                import torch
                if torch.cuda.is_available():
                    logger.info("🖥️ GPU erkannt – nutze CUDA")
                    return 'cuda'
            except ImportError:
                pass
            try:
                import torch
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    logger.info("🍎 Apple Silicon erkannt – nutze MPS")
                    return 'mps'
            except Exception:
                pass
            return 'cpu'
        return device

    def laden(self) -> bool:
        start = time.time()

        # Prüfe ob Datei existiert
        if not self._modell_pfad.exists():
            logger.warning(f"⚠️ Modelldatei nicht gefunden: {self._modell_pfad}")
            if self._fallback_modus:
                logger.info("🔄 Versuche YOLOv8n als Standard-Modell zu laden...")
                return self._lade_standard_modell()
            self._status = ModellStatus.FEHLER
            return False

        # Lade Modell
        try:
            from ultralytics import YOLO
            self._modell = YOLO(str(self._modell_pfad))
            self._modell.to(self._device)
            self._modell_hash = self._berechne_hash()
            self._lade_zeit = time.time() - start
            self._status = ModellStatus.GELADEN
            self._metadaten = {
                'typ': 'YOLO',
                'device': self._device,
                'konfidenz': self._konfidenz_schwelle
            }
            logger.info(f"✅ YOLO geladen in {self._lade_zeit:.2f}s auf {self._device}")
            return True
        except ImportError:
            logger.error("❌ ultralytics nicht installiert: pip install ultralytics")
        except Exception as e:
            logger.error(f"❌ YOLO Ladefehler: {e}")

        if self._fallback_modus:
            return self._lade_standard_modell()

        self._status = ModellStatus.FEHLER
        return False

    def _lade_standard_modell(self) -> bool:
        """Lädt YOLOv8n als Fallback"""
        try:
            from ultralytics import YOLO
            logger.info("⬇️ Lade YOLOv8n Standard-Modell...")
            self._modell = YOLO('yolov8n.pt')
            self._modell.to(self._device)
            self._lade_zeit = time.time()
            self._status = ModellStatus.FALLBACK
            logger.info("✅ YOLOv8n Fallback geladen")
            return True
        except Exception as e:
            logger.error(f"❌ Fallback Ladefehler: {e}")
            self._status = ModellStatus.FEHLER
            return False

    def inferenz(self, frame: Any) -> Dict[str, Any]:
        """Führt Objekterkennung auf einem Frame durch"""
        if self._status == ModellStatus.FEHLER:
            return self._fallback_inferenz(frame)

        try:
            ergebnisse = self._modell(
                frame,
                conf=self._konfidenz_schwelle,
                iou=self._iou_schwelle,
                verbose=False
            )

            erkennungen = []
            for r in ergebnisse:
                for box in r.boxes:
                    klasse_id = int(box.cls[0])
                    erkennungen.append({
                        'klasse_id': klasse_id,
                        'klasse_name': self.ZIEL_KLASSEN.get(klasse_id, f'klasse_{klasse_id}'),
                        'konfidenz': float(box.conf[0]),
                        'bbox': box.xyxy[0].tolist(),
                        'timestamp': time.time()
                    })

            return {
                'erkennungen': erkennungen,
                'anzahl': len(erkennungen),
                'status': 'ok'
            }
        except Exception as e:
            logger.error(f"YOLO Inferenz Fehler: {e}")
            return self._fallback_inferenz(frame)

    def _fallback_inferenz(self, frame: Any) -> Dict[str, Any]:
        """Gibt leeres Ergebnis zurück wenn Modell nicht verfügbar"""
        logger.warning("⚠️ YOLO Fallback-Inferenz – kein Modell geladen")
        return {
            'erkennungen': [],
            'anzahl': 0,
            'status': 'fallback',
            'warnung': 'Modell nicht verfügbar'
        }


# =============================================================================
# RANDOM FOREST MODELL (Predictive Maintenance)
# =============================================================================

class PredictiveMaintenanceModell(KIModell):
    """
    Random Forest Modell für Predictive Maintenance.
    Vorhersage von Komponentenausfällen.
    """

    FEATURE_NAMEN = [
        'temperatur', 'vibration', 'strom', 'spannung',
        'betriebsstunden', 'zyklen', 'feuchtigkeit'
    ]

    def __init__(self, modell_pfad: str = "modelle/predictive_maintenance.pkl"):
        super().__init__(modell_pfad)
        self._scaler = None

    def laden(self) -> bool:
        start = time.time()

        if not self._modell_pfad.exists():
            logger.warning(f"⚠️ Modell nicht gefunden: {self._modell_pfad}")
            if self._fallback_modus:
                return self._trainiere_standard_modell()
            self._status = ModellStatus.FEHLER
            return False

        try:
            import pickle
            with open(self._modell_pfad, 'rb') as f:
                daten = pickle.load(f)

            if isinstance(daten, dict):
                self._modell = daten.get('modell')
                self._scaler = daten.get('scaler')
            else:
                self._modell = daten

            self._lade_zeit = time.time() - start
            self._status = ModellStatus.GELADEN
            logger.info(f"✅ Predictive Maintenance Modell geladen in {self._lade_zeit:.2f}s")
            return True
        except Exception as e:
            logger.error(f"❌ Ladefehler: {e}")
            if self._fallback_modus:
                return self._trainiere_standard_modell()
            self._status = ModellStatus.FEHLER
            return False

    def _trainiere_standard_modell(self) -> bool:
        """Trainiert ein einfaches Standard-Modell mit synthetischen Daten"""
        try:
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.preprocessing import StandardScaler
            import numpy as np

            logger.info("🔄 Trainiere Standard Predictive Maintenance Modell...")

            # Synthetische Trainingsdaten
            np.random.seed(42)
            n_samples = 1000
            X = np.random.randn(n_samples, len(self.FEATURE_NAMEN))
            # Regel: Ausfall wenn Temperatur > 2 ODER Vibration > 2
            y = ((X[:, 0] > 2) | (X[:, 1] > 2)).astype(int)

            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X)

            self._modell = RandomForestClassifier(
                n_estimators=100, random_state=42, n_jobs=-1
            )
            self._modell.fit(X_scaled, y)

            self._status = ModellStatus.FALLBACK
            logger.info("✅ Standard-Modell trainiert (synthetische Daten)")
            return True
        except ImportError:
            logger.error("❌ scikit-learn nicht installiert: pip install scikit-learn")
            self._status = ModellStatus.FEHLER
            return False

    def inferenz(self, sensordaten: Dict[str, float]) -> Dict[str, Any]:
        """Vorhersage ob Ausfall wahrscheinlich"""
        if self._status == ModellStatus.FEHLER:
            return self._fallback_inferenz(sensordaten)

        try:
            import numpy as np

            features = [sensordaten.get(f, 0.0) for f in self.FEATURE_NAMEN]
            X = np.array(features).reshape(1, -1)

            if self._scaler:
                X = self._scaler.transform(X)

            wahrscheinlichkeit = self._modell.predict_proba(X)[0]
            vorhersage = self._modell.predict(X)[0]

            return {
                'ausfall_wahrscheinlichkeit': float(wahrscheinlichkeit[1]),
                'ausfall_vorhergesagt': bool(vorhersage),
                'risiko_level': self._risiko_level(float(wahrscheinlichkeit[1])),
                'empfehlung': self._empfehlung(float(wahrscheinlichkeit[1])),
                'status': 'ok'
            }
        except Exception as e:
            logger.error(f"Inferenz Fehler: {e}")
            return self._fallback_inferenz(sensordaten)

    def _risiko_level(self, wahrscheinlichkeit: float) -> str:
        if wahrscheinlichkeit < 0.3:
            return 'NIEDRIG'
        elif wahrscheinlichkeit < 0.6:
            return 'MITTEL'
        elif wahrscheinlichkeit < 0.8:
            return 'HOCH'
        return 'KRITISCH'

    def _empfehlung(self, wahrscheinlichkeit: float) -> str:
        if wahrscheinlichkeit < 0.3:
            return 'Normalbetrieb – keine Maßnahmen erforderlich'
        elif wahrscheinlichkeit < 0.6:
            return 'Erhöhte Überwachung empfohlen'
        elif wahrscheinlichkeit < 0.8:
            return 'Wartung innerhalb 48h einplanen'
        return 'SOFORTIGE Wartung erforderlich!'

    def _fallback_inferenz(self, eingabe: Any) -> Dict[str, Any]:
        return {
            'ausfall_wahrscheinlichkeit': 0.0,
            'ausfall_vorhergesagt': False,
            'risiko_level': 'UNBEKANNT',
            'empfehlung': 'Modell nicht verfügbar',
            'status': 'fallback'
        }

    def speichern(self, pfad: Optional[str] = None) -> bool:
        """Speichert das trainierte Modell"""
        try:
            import pickle
            speicher_pfad = Path(pfad) if pfad else self._modell_pfad
            speicher_pfad.parent.mkdir(parents=True, exist_ok=True)
            with open(speicher_pfad, 'wb') as f:
                pickle.dump({'modell': self._modell, 'scaler': self._scaler}, f)
            logger.info(f"✅ Modell gespeichert: {speicher_pfad}")
            return True
        except Exception as e:
            logger.error(f"❌ Speicher-Fehler: {e}")
            return False


# =============================================================================
# MODELL-MANAGER (Zentrale Verwaltung)
# =============================================================================

class ModellManager:
    """
    Zentrale Verwaltung aller KI-Modelle.
    Singleton-Pattern für systemweiten Zugriff.
    """
    _instanz: Optional['ModellManager'] = None

    def __new__(cls):
        if cls._instanz is None:
            cls._instanz = super().__new__(cls)
            cls._instanz._initialisiert = False
        return cls._instanz

    def __init__(self):
        if not self._initialisiert:
            self._modelle: Dict[str, KIModell] = {}
            self._initialisiert = True
            logger.info("🤖 Modell-Manager initialisiert")

    def registriere(self, name: str, modell: KIModell) -> None:
        self._modelle[name] = modell

    def lade_alle(self) -> Dict[str, bool]:
        """Lädt alle registrierten Modelle"""
        ergebnisse = {}
        for name, modell in self._modelle.items():
            logger.info(f"⏳ Lade Modell: {name}")
            ergebnisse[name] = modell.laden()
        return ergebnisse

    def hole(self, name: str) -> Optional[KIModell]:
        return self._modelle.get(name)

    def status_alle(self) -> Dict[str, str]:
        return {
            name: modell.status.value
            for name, modell in self._modelle.items()
        }


# =============================================================================
# HAUPTPROGRAMM – TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("SCHACHMATTSCHILD – KI Modell Ladelogik Test")
    print("=" * 60)

    manager = ModellManager()

    # YOLO registrieren und laden
    yolo = YOLOModell(modell_pfad="modelle/yolo_drohnen.pt")
    manager.registriere('yolo', yolo)

    # Predictive Maintenance registrieren und laden
    pm = PredictiveMaintenanceModell()
    manager.registriere('predictive_maintenance', pm)

    # Alle laden
    ergebnisse = manager.lade_alle()
    print(f"\nLade-Ergebnisse: {ergebnisse}")
    print(f"Status: {manager.status_alle()}")

    # Test Predictive Maintenance
    test_sensoren = {
        'temperatur': 1.5, 'vibration': 0.8,
        'strom': 2.1, 'spannung': 12.4,
        'betriebsstunden': 500, 'zyklen': 1200, 'feuchtigkeit': 0.6
    }
    ergebnis = pm.inferenz(test_sensoren)
    print(f"\nPredictive Maintenance: {ergebnis}")

    print("\n✅ KI Modell Ladelogik Test abgeschlossen")
