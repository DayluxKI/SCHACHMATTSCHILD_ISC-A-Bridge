"""
FORMALE_VERIFIKATION.py
SCHACHMATTSCHILD – ISC Sicherheitsplattform
Optimierung 3: Formale Verifikation mit Pre/Post-Conditions und Assertions
- Design-by-Contract (Vor- und Nachbedingungen)
- Invarianten-Prüfung
- Zustandsmaschinen-Verifikation
- Sicherheitseigenschaften mathematisch prüfbar
Autor: Dmitrij Medkov
"""

import time
import logging
import functools
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


# =============================================================================
# VERIFIKATIONS-FEHLER
# =============================================================================

class VorbedingungFehler(AssertionError):
    """Ausgelöst wenn eine Vorbedingung verletzt wird"""
    pass


class NachbedingungFehler(AssertionError):
    """Ausgelöst wenn eine Nachbedingung verletzt wird"""
    pass


class InvariantenFehler(AssertionError):
    """Ausgelöst wenn eine Invariante verletzt wird"""
    pass


class SicherheitseigenschaftFehler(Exception):
    """Ausgelöst wenn eine Sicherheitseigenschaft verletzt wird"""
    pass


# =============================================================================
# DEKORATOREN FÜR DESIGN-BY-CONTRACT
# =============================================================================

def vorbedingung(bedingung: Callable[..., bool], nachricht: str = ""):
    """
    Dekorator für Vorbedingungen (Preconditions).
    Wirft VorbedingungFehler wenn Bedingung nicht erfüllt.
    """
    def dekorator(funktion: F) -> F:
        @functools.wraps(funktion)
        def wrapper(*args, **kwargs):
            if not bedingung(*args, **kwargs):
                fehler_msg = nachricht or f"Vorbedingung verletzt in {funktion.__name__}"
                logger.error(f"❌ VORBEDINGUNG: {fehler_msg}")
                raise VorbedingungFehler(fehler_msg)
            return funktion(*args, **kwargs)
        return wrapper
    return dekorator


def nachbedingung(bedingung: Callable[..., bool], nachricht: str = ""):
    """
    Dekorator für Nachbedingungen (Postconditions).
    Wirft NachbedingungFehler wenn Bedingung nach Ausführung nicht erfüllt.
    """
    def dekorator(funktion: F) -> F:
        @functools.wraps(funktion)
        def wrapper(*args, **kwargs):
            ergebnis = funktion(*args, **kwargs)
            if not bedingung(ergebnis):
                fehler_msg = nachricht or f"Nachbedingung verletzt in {funktion.__name__}"
                logger.error(f"❌ NACHBEDINGUNG: {fehler_msg}")
                raise NachbedingungFehler(fehler_msg)
            return ergebnis
        return wrapper
    return dekorator


def invariante(pruefer: Callable[['Any'], bool], nachricht: str = ""):
    """
    Dekorator für Klassen-Invarianten.
    Prüft Invariante vor und nach jeder Methode.
    """
    def dekorator(funktion: F) -> F:
        @functools.wraps(funktion)
        def wrapper(self, *args, **kwargs):
            # Vor-Prüfung
            if not pruefer(self):
                raise InvariantenFehler(
                    f"Invariante VOR {funktion.__name__} verletzt: {nachricht}"
                )
            ergebnis = funktion(self, *args, **kwargs)
            # Nach-Prüfung
            if not pruefer(self):
                raise InvariantenFehler(
                    f"Invariante NACH {funktion.__name__} verletzt: {nachricht}"
                )
            return ergebnis
        return wrapper
    return dekorator


# =============================================================================
# SICHERHEITSEIGENSCHAFTEN
# =============================================================================

class Sicherheitseigenschaft(ABC):
    """Abstrakte Basis für formale Sicherheitseigenschaften"""

    @abstractmethod
    def pruefen(self, zustand: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def beschreibung(self) -> str:
        pass

    def verletzung_melden(self, zustand: Dict[str, Any]) -> None:
        logger.critical(
            f"🚨 SICHERHEITSEIGENSCHAFT VERLETZT: {self.beschreibung()}"
            f"\nZustand: {zustand}"
        )
        raise SicherheitseigenschaftFehler(
            f"Sicherheitseigenschaft verletzt: {self.beschreibung()}"
        )


class NiemalsFeindlicheAktion(Sicherheitseigenschaft):
    """
    Sicherheitseigenschaft S1:
    Das System darf NIEMALS eine feindliche Aktion ohne
    vorherige Realitätsvalidierung ausführen.
    """

    def pruefen(self, zustand: Dict[str, Any]) -> bool:
        aktion_aktiv = zustand.get('aktion_aktiv', False)
        realitaet_validiert = zustand.get('realitaet_validiert', False)

        # Wenn Aktion aktiv, MUSS Realität validiert sein
        if aktion_aktiv and not realitaet_validiert:
            return False
        return True

    def beschreibung(self) -> str:
        return "S1: Keine Aktion ohne validierte Realität"


class ImmerAuditLog(Sicherheitseigenschaft):
    """
    Sicherheitseigenschaft S2:
    JEDE sicherheitskritische Entscheidung MUSS im Audit-Log stehen.
    """

    def pruefen(self, zustand: Dict[str, Any]) -> bool:
        entscheidungen = zustand.get('entscheidungen_gesamt', 0)
        log_eintraege = zustand.get('log_eintraege', 0)
        return log_eintraege >= entscheidungen

    def beschreibung(self) -> str:
        return "S2: Jede Entscheidung muss protokolliert sein"


class KeineSinglePointOfFailure(Sicherheitseigenschaft):
    """
    Sicherheitseigenschaft S3:
    Das System darf NIEMALS auf einer einzelnen Datenquelle basieren.
    """

    def pruefen(self, zustand: Dict[str, Any]) -> bool:
        aktive_quellen = zustand.get('aktive_referenzquellen', 0)
        return aktive_quellen >= 2

    def beschreibung(self) -> str:
        return "S3: Mindestens 2 unabhängige Referenzquellen erforderlich"


class NotfallStopImmerMoeglich(Sicherheitseigenschaft):
    """
    Sicherheitseigenschaft S4:
    Der Notfall-Stop MUSS immer ausführbar sein.
    """

    def pruefen(self, zustand: Dict[str, Any]) -> bool:
        return zustand.get('notfall_stop_verfuegbar', True)

    def beschreibung(self) -> str:
        return "S4: Notfall-Stop muss immer verfügbar sein"


class FriendlyFireVerhinderung(Sicherheitseigenschaft):
    """
    Sicherheitseigenschaft S5:
    Das System darf NIEMALS auf ein als Freund identifiziertes Objekt feuern.
    """

    def pruefen(self, zustand: Dict[str, Any]) -> bool:
        ziel_ist_freund = zustand.get('ziel_ist_freund', False)
        waffe_aktiv = zustand.get('waffe_aktiv', False)
        if ziel_ist_freund and waffe_aktiv:
            return False
        return True

    def beschreibung(self) -> str:
        return "S5: Kein Angriff auf Freund-Objekte (Friendly Fire)"


# =============================================================================
# ZUSTANDSMASCHINEN-VERIFIKATION
# =============================================================================

class ZustandsMaschine:
    """
    Formale Zustandsmaschine mit Verifikation.
    Stellt sicher dass nur gültige Zustandsübergänge möglich sind.
    """

    def __init__(self, name: str, zustaende: List[str],
                 erlaubte_uebergaenge: Dict[str, List[str]],
                 start_zustand: str):

        # Vorbedingungen prüfen
        assert name, "Name darf nicht leer sein"
        assert zustaende, "Zustandsliste darf nicht leer sein"
        assert start_zustand in zustaende, \
            f"Startzustand '{start_zustand}' muss in Zustandsliste sein"

        self._name = name
        self._zustaende = set(zustaende)
        self._uebergaenge = erlaubte_uebergaenge
        self._aktueller_zustand = start_zustand
        self._zustandshistorie: List[Tuple[str, str, float]] = []
        self._sicherheitseigenschaften: List[Sicherheitseigenschaft] = []

        # Invariante: Zustand immer gültig
        assert self._zustand_gueltig(), "Initialzustand ungültig"
        logger.info(f"✅ Zustandsmaschine '{name}' initialisiert: {start_zustand}")

    def _zustand_gueltig(self) -> bool:
        return self._aktueller_zustand in self._zustaende

    def uebergang(self, neuer_zustand: str,
                  kontext: Optional[Dict[str, Any]] = None) -> bool:
        """
        Führt Zustandsübergang durch.
        Prüft Vorbedingungen, Invarianten und Nachbedingungen.
        """
        # VORBEDINGUNG: Neuer Zustand muss existieren
        if neuer_zustand not in self._zustaende:
            raise VorbedingungFehler(
                f"Zustand '{neuer_zustand}' existiert nicht"
            )

        # VORBEDINGUNG: Übergang muss erlaubt sein
        erlaubt = self._uebergaenge.get(self._aktueller_zustand, [])
        if neuer_zustand not in erlaubt:
            raise VorbedingungFehler(
                f"Übergang '{self._aktueller_zustand}' → '{neuer_zustand}' "
                f"ist NICHT erlaubt! Erlaubt: {erlaubt}"
            )

        # INVARIANTE: Aktueller Zustand muss gültig sein
        assert self._zustand_gueltig(), "Invariante verletzt vor Übergang"

        # Sicherheitseigenschaften prüfen
        if kontext:
            self._pruefe_sicherheitseigenschaften(kontext)

        # Übergang durchführen
        alter_zustand = self._aktueller_zustand
        self._aktueller_zustand = neuer_zustand
        self._zustandshistorie.append(
            (alter_zustand, neuer_zustand, time.time())
        )

        # INVARIANTE: Neuer Zustand muss gültig sein
        assert self._zustand_gueltig(), "Invariante verletzt nach Übergang"

        # NACHBEDINGUNG: Zustand hat sich geändert
        assert self._aktueller_zustand == neuer_zustand, \
            "Nachbedingung: Zustand wurde nicht korrekt gesetzt"

        logger.info(f"🔄 [{self._name}] {alter_zustand} → {neuer_zustand}")
        return True

    def _pruefe_sicherheitseigenschaften(
            self, zustand: Dict[str, Any]) -> None:
        for eigenschaft in self._sicherheitseigenschaften:
            if not eigenschaft.pruefen(zustand):
                eigenschaft.verletzung_melden(zustand)

    def registriere_sicherheitseigenschaft(
            self, eigenschaft: Sicherheitseigenschaft) -> None:
        self._sicherheitseigenschaften.append(eigenschaft)
        logger.info(f"🔒 Sicherheitseigenschaft registriert: "
                    f"{eigenschaft.beschreibung()}")

    @property
    def zustand(self) -> str:
        return self._aktueller_zustand

    @property
    def historie(self) -> List[Tuple[str, str, float]]:
        return list(self._zustandshistorie)

    def ist_in_zustand(self, zustand: str) -> bool:
        return self._aktueller_zustand == zustand


# =============================================================================
# ISC V4.0 ZUSTANDSMASCHINE (Formal verifiziert)
# =============================================================================

def erstelle_isc_zustandsmaschine() -> ZustandsMaschine:
    """
    Erstellt die formal verifizierte ISC V4.0 Zustandsmaschine.
    Definiert alle erlaubten Zustandsübergänge.
    """
    zustaende = [
        'INAKTIV',
        'INITIALISIERUNG',
        'NORMALBETRIEB',
        'VALIDIERUNG',
        'REALITAET_UNSICHER',
        'DEGRADIERT_GELB',
        'DEGRADIERT_ORANGE',
        'SAFE_LOCK',
        'NOTFALL_STOP',
        'FEHLER'
    ]

    # Nur explizit erlaubte Übergänge sind möglich
    erlaubte_uebergaenge = {
        'INAKTIV': ['INITIALISIERUNG'],
        'INITIALISIERUNG': ['NORMALBETRIEB', 'FEHLER'],
        'NORMALBETRIEB': ['VALIDIERUNG', 'DEGRADIERT_GELB', 'NOTFALL_STOP'],
        'VALIDIERUNG': ['NORMALBETRIEB', 'REALITAET_UNSICHER', 'NOTFALL_STOP'],
        'REALITAET_UNSICHER': ['NORMALBETRIEB', 'DEGRADIERT_GELB', 'NOTFALL_STOP'],
        'DEGRADIERT_GELB': ['NORMALBETRIEB', 'DEGRADIERT_ORANGE', 'NOTFALL_STOP'],
        'DEGRADIERT_ORANGE': ['DEGRADIERT_GELB', 'SAFE_LOCK', 'NOTFALL_STOP'],
        'SAFE_LOCK': ['NOTFALL_STOP'],
        'NOTFALL_STOP': [],  # Kein Übergang aus Notfall möglich!
        'FEHLER': ['INAKTIV']
    }

    maschine = ZustandsMaschine(
        name="ISC-V4.0",
        zustaende=zustaende,
        erlaubte_uebergaenge=erlaubte_uebergaenge,
        start_zustand='INAKTIV'
    )

    # Sicherheitseigenschaften registrieren
    maschine.registriere_sicherheitseigenschaft(NiemalsFeindlicheAktion())
    maschine.registriere_sicherheitseigenschaft(ImmerAuditLog())
    maschine.registriere_sicherheitseigenschaft(KeineSinglePointOfFailure())
    maschine.registriere_sicherheitseigenschaft(NotfallStopImmerMoeglich())
    maschine.registriere_sicherheitseigenschaft(FriendlyFireVerhinderung())

    return maschine


# =============================================================================
# VERIFIKATIONS-MONITOR
# =============================================================================

class VerifikationsMonitor:
    """
    Laufzeit-Monitor der alle Sicherheitseigenschaften überwacht.
    Wird in jeden Zyklus eingebunden.
    """

    def __init__(self):
        self._eigenschaften: List[Sicherheitseigenschaft] = [
            NiemalsFeindlicheAktion(),
            ImmerAuditLog(),
            KeineSinglePointOfFailure(),
            NotfallStopImmerMoeglich(),
            FriendlyFireVerhinderung(),
        ]
        self._verletzungen: List[Dict[str, Any]] = []
        self._pruefungen_gesamt: int = 0

    def pruefe_zustand(self, system_zustand: Dict[str, Any]) -> bool:
        """
        Prüft alle Sicherheitseigenschaften.
        Gibt True zurück wenn alle erfüllt, False bei Verletzung.
        """
        self._pruefungen_gesamt += 1
        alle_ok = True

        for eigenschaft in self._eigenschaften:
            try:
                if not eigenschaft.pruefen(system_zustand):
                    verletzung = {
                        'eigenschaft': eigenschaft.beschreibung(),
                        'zustand': system_zustand.copy(),
                        'timestamp': time.time()
                    }
                    self._verletzungen.append(verletzung)
                    logger.critical(
                        f"🚨 VERLETZUNG: {eigenschaft.beschreibung()}"
                    )
                    alle_ok = False
            except Exception as e:
                logger.error(f"Verifikationsfehler: {e}")
                alle_ok = False

        return alle_ok

    @property
    def verletzungen(self) -> List[Dict[str, Any]]:
        return list(self._verletzungen)

    @property
    def statistik(self) -> Dict[str, Any]:
        return {
            'pruefungen_gesamt': self._pruefungen_gesamt,
            'verletzungen_gesamt': len(self._verletzungen),
            'verletzungsrate': (
                len(self._verletzungen) / self._pruefungen_gesamt
                if self._pruefungen_gesamt > 0 else 0
            )
        }


# =============================================================================
# HAUPTPROGRAMM – TEST
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    print("=" * 60)
    print("SCHACHMATTSCHILD – Formale Verifikation Test")
    print("=" * 60)

    # Test 1: Zustandsmaschine
    print("\n📊 Test 1: ISC V4.0 Zustandsmaschine")
    maschine = erstelle_isc_zustandsmaschine()

    maschine.uebergang('INITIALISIERUNG')
    maschine.uebergang('NORMALBETRIEB')
    maschine.uebergang('VALIDIERUNG')
    maschine.uebergang('NORMALBETRIEB')
    print(f"✅ Zustand: {maschine.zustand}")

    # Test 2: Ungültiger Übergang
    print("\n📊 Test 2: Ungültiger Übergang")
    try:
        maschine.uebergang('SAFE_LOCK')  # Nicht erlaubt!
        print("❌ Fehler: Hätte Ausnahme werfen müssen!")
    except VorbedingungFehler as e:
        print(f"✅ Korrekt abgefangen: {e}")

    # Test 3: Verifikations-Monitor
    print("\n📊 Test 3: Verifikations-Monitor")
    monitor = VerifikationsMonitor()

    # Gültiger Zustand
    gueltiger_zustand = {
        'aktion_aktiv': True,
        'realitaet_validiert': True,
        'entscheidungen_gesamt': 10,
        'log_eintraege': 10,
        'aktive_referenzquellen': 3,
        'notfall_stop_verfuegbar': True,
        'ziel_ist_freund': False,
        'waffe_aktiv': False
    }
    ergebnis = monitor.pruefe_zustand(gueltiger_zustand)
    print(f"✅ Gültiger Zustand: {ergebnis}")

    # Verletzender Zustand (Aktion ohne Validierung)
    ungueltig = gueltiger_zustand.copy()
    ungueltig['realitaet_validiert'] = False
    ergebnis = monitor.pruefe_zustand(ungueltig)
    print(f"Verletzender Zustand erkannt: {not ergebnis}")
    print(f"Statistik: {monitor.statistik}")

    print("\n✅ Formale Verifikation Test abgeschlossen!")
