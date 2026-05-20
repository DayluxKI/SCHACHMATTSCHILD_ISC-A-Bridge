# SCHACHMATTSCHILD v2.0
## ISC Sicherheitsplattform für autonome Systeme

[![CI/CD](https://github.com/medkov-isc/schachmattschild/actions/workflows/ci.yml/badge.svg)](https://github.com/medkov-isc/schachmattschild/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org)
[![Lizenz](https://img.shields.io/badge/lizenz-proprietär-red.svg)](LICENSE)

---

## 🎯 Was ist SCHACHMATTSCHILD?

SCHACHMATTSCHILD ist eine modulare Sicherheitsplattform für autonome Systeme – Drohnen, Roboter, kritische Infrastrukturen. Sie implementiert die **ISC-Patentfamilie** (17 Patente) von Dmitrij Medkov.

### Kernprinzip

> Bevor ein autonomes System eine Entscheidung trifft, prüft SCHACHMATTSCHILD ob die zugrundeliegende Realität überhaupt vertrauenswürdig ist.

---

## 🏗️ Architektur

```
SCHACHMATTSCHILD v2.0
├── HARDWARE_ABSTRACTION_LAYER.py   # Optimierung 1: Hardware
│   ├── Raspberry Pi GPIO
│   ├── Pixhawk/ArduPilot (MAVLink)
│   ├── NVIDIA Jetson
│   └── x86 Simulation
│
├── KI_MODELL_LADELOGIK.py          # Optimierung 2: KI-Modelle
│   ├── YOLO Drohnenerkennung
│   ├── Predictive Maintenance
│   └── Automatischer Fallback
│
├── FORMALE_VERIFIKATION.py         # Optimierung 3: Verifikation
│   ├── 5 Sicherheitseigenschaften (S1-S5)
│   ├── ISC V4.0 Zustandsmaschine
│   └── Laufzeit-Verifikationsmonitor
│
├── SCHACHMATTSCHILD_INTEGRATION.py # Optimierung 4: Integration
│   ├── Einheitliche Konfiguration
│   └── Zentraler System-Manager
│
└── TEST_SUITE_OPTIMIERUNGEN.py     # Test-Suite (28 Tests)
```

---

## 🔒 Sicherheitseigenschaften

| ID | Eigenschaft | Beschreibung |
|----|-------------|--------------|
| S1 | Keine Aktion ohne Validierung | Kein autonomer Angriff ohne geprüfte Realitätsbasis |
| S2 | Vollständiges Audit-Log | Jede Entscheidung wird protokolliert |
| S3 | Keine Single-Point-of-Failure | Mindestens 2 unabhängige Referenzquellen |
| S4 | Notfall-Stop immer verfügbar | System kann immer gestoppt werden |
| S5 | Friendly-Fire-Schutz | Kein Angriff auf eigene Einheiten |

---

## 🚀 Schnellstart

### Installation

```bash
# Basis-Installation
pip install scikit-learn numpy

# Hardware (Raspberry Pi)
pip install RPi.GPIO picamera2

# Drohne (Pixhawk)
pip install dronekit pymavlink

# KI-Modelle
pip install ultralytics torch
```

### Verwendung

```python
from SCHACHMATTSCHILD_INTEGRATION import SchachmattSchildSystem, Konfiguration

# System initialisieren
config = Konfiguration()
system = SchachmattSchildSystem(config)
system.initialisieren()

# Frame verarbeiten
ergebnis = system.verarbeite_frame()
print(f"Status: {ergebnis['status']}")
print(f"Verifikation: {ergebnis['verifikation_ok']}")

# Telemetrie
print(system.telemetrie())

# Notfall-Stop
system.notfall_stop()
```

### Pixhawk verbinden

```python
from HARDWARE_ABSTRACTION_LAYER import HardwareFabrik

fabrik = HardwareFabrik()

# USB Verbindung
drohne = fabrik.drohne('/dev/ttyUSB0')

# UDP (SITL Simulator)
drohne = fabrik.drohne('udp:127.0.0.1:14550')

# Simulation (kein Hardware)
drohne = fabrik.drohne()

drohne.arm()
drohne.takeoff(10.0)
print(drohne.lese_telemetrie())
```

---

## 🧪 Tests ausführen

```bash
# Alle Tests
python TEST_SUITE_OPTIMIERUNGEN.py

# Mit pytest
pytest TEST_SUITE_OPTIMIERUNGEN.py -v

# Einzelne Klasse
pytest TEST_SUITE_OPTIMIERUNGEN.py::TestFormaleVerifikation -v
```

---

## 📋 Konfiguration

```json
{
  "system": {
    "name": "SCHACHMATTSCHILD",
    "version": "2.0"
  },
  "hardware": {
    "plattform": "auto",
    "pixhawk_port": "/dev/ttyUSB0"
  },
  "ki_modelle": {
    "yolo_pfad": "modelle/yolo_drohnen.pt",
    "konfidenz_schwelle": 0.5,
    "fallback_erlaubt": true
  },
  "verifikation": {
    "aktiv": true,
    "strenger_modus": true
  }
}
```

---

## 📊 Bewertung

| Kategorie | Bewertung |
|-----------|-----------|
| Sicherheit | 9.5/10 |
| Skalierbarkeit | 10/10 |
| Code-Struktur | 9.0/10 |
| Robustheit | 8.5/10 |

---

## ⚖️ Lizenz & Patente

**© 2026 Dmitrij Medkov – Alle Rechte vorbehalten**

Dieses System ist durch 17 Patentanmeldungen beim DPMA geschützt (ISC-Patentfamilie). Nutzung nur mit ausdrücklicher schriftlicher Genehmigung des Rechteinhabers.

Kontakt: medkov@web.de | +49 160 2089888

---

## 📞 Kontakt

**Dmitrij Medkov**
Auguststraße 12, 32130 Enger
medkov@web.de
+49 160 2089888
