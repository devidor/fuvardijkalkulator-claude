"""Az e-mailből kinyert fuvarigény adatszerkezete.

Minden mezőt egy (érték, bizonyosság, megjegyzés) hármasként tárolunk, hogy a
felület külön tudja jelezni, mi egyértelmű, mi bizonytalan, és mi hiányzik.
A modul Streamlit- és AI-független: csak az adatszerkezetet és az abból
levezethető ellenőrzéseket tartalmazza.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Union

Ertek = Union[str, float, int, bool, None]


class Bizonyossag(str, Enum):
    BIZTOS = "biztos"
    BIZONYTALAN = "bizonytalan"
    HIANYZIK = "hianyzik"


BIZONYOSSAG_CIMKE = {
    Bizonyossag.BIZTOS: "felismert",
    Bizonyossag.BIZONYTALAN: "bizonytalan",
    Bizonyossag.HIANYZIK: "hiányzik",
}


@dataclass
class KinyertMezo:
    """Egy kinyert adat: érték, megbízhatóság és (ha van) indoklás/megjegyzés."""

    ertek: Ertek = None
    bizonyossag: Bizonyossag = Bizonyossag.HIANYZIK
    megjegyzes: str = ""

    @property
    def ismert(self) -> bool:
        return self.bizonyossag != Bizonyossag.HIANYZIK and self.ertek is not None

    @classmethod
    def ures(cls) -> "KinyertMezo":
        return cls(None, Bizonyossag.HIANYZIK, "")

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "KinyertMezo":
        if not d:
            return cls.ures()
        try:
            bizonyossag = Bizonyossag(d.get("bizonyossag", "hianyzik"))
        except ValueError:
            bizonyossag = Bizonyossag.HIANYZIK
        ertek = d.get("ertek")
        if ertek is None:
            bizonyossag = Bizonyossag.HIANYZIK
        return cls(ertek=ertek, bizonyossag=bizonyossag, megjegyzes=(d.get("megjegyzes") or "").strip())


@dataclass
class RakomanyTetelAdat:
    """Egy rakománytétel: darabszám, méretek (cm), tömeg (kg), halmozhatóság."""

    nev: KinyertMezo = field(default_factory=KinyertMezo.ures)
    darab: KinyertMezo = field(default_factory=KinyertMezo.ures)
    hossz_cm: KinyertMezo = field(default_factory=KinyertMezo.ures)
    szelesseg_cm: KinyertMezo = field(default_factory=KinyertMezo.ures)
    magassag_cm: KinyertMezo = field(default_factory=KinyertMezo.ures)
    suly_kg: KinyertMezo = field(default_factory=KinyertMezo.ures)
    halmozhato: KinyertMezo = field(default_factory=KinyertMezo.ures)
    halmozasi_szint: KinyertMezo = field(default_factory=KinyertMezo.ures)

    @property
    def alapadatok_ismertek(self) -> bool:
        """A kalkulátorhoz feltétlenül szükséges mezők (darab, méret, súly) megvannak-e."""
        return all(m.ismert for m in (self.darab, self.hossz_cm, self.szelesseg_cm, self.magassag_cm, self.suly_kg))

    @property
    def ossztomeg_kg(self) -> Optional[float]:
        if self.darab.ismert and self.suly_kg.ismert:
            try:
                return float(self.darab.ertek) * float(self.suly_kg.ertek)
            except (TypeError, ValueError):
                return None
        return None

    @classmethod
    def from_dict(cls, d: dict) -> "RakomanyTetelAdat":
        return cls(
            nev=KinyertMezo.from_dict(d.get("nev")),
            darab=KinyertMezo.from_dict(d.get("darab")),
            hossz_cm=KinyertMezo.from_dict(d.get("hossz_cm")),
            szelesseg_cm=KinyertMezo.from_dict(d.get("szelesseg_cm")),
            magassag_cm=KinyertMezo.from_dict(d.get("magassag_cm")),
            suly_kg=KinyertMezo.from_dict(d.get("suly_kg")),
            halmozhato=KinyertMezo.from_dict(d.get("halmozhato")),
            halmozasi_szint=KinyertMezo.from_dict(d.get("halmozasi_szint")),
        )


@dataclass
class FuvarIgenyAdat:
    """Egy e-mailből kinyert teljes fuvarigény."""

    felrakas_hely: KinyertMezo = field(default_factory=KinyertMezo.ures)
    felrakas_cim: KinyertMezo = field(default_factory=KinyertMezo.ures)
    felrakas_datum: KinyertMezo = field(default_factory=KinyertMezo.ures)
    lerakas_hely: KinyertMezo = field(default_factory=KinyertMezo.ures)
    lerakas_cim: KinyertMezo = field(default_factory=KinyertMezo.ures)
    lerakas_datum: KinyertMezo = field(default_factory=KinyertMezo.ures)
    rakomany_megnevezese: KinyertMezo = field(default_factory=KinyertMezo.ures)
    jarmuigeny: KinyertMezo = field(default_factory=KinyertMezo.ures)
    tetelek: list[RakomanyTetelAdat] = field(default_factory=list)
    altalanos_megjegyzesek: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "FuvarIgenyAdat":
        return cls(
            felrakas_hely=KinyertMezo.from_dict(d.get("felrakas_hely")),
            felrakas_cim=KinyertMezo.from_dict(d.get("felrakas_cim")),
            felrakas_datum=KinyertMezo.from_dict(d.get("felrakas_datum")),
            lerakas_hely=KinyertMezo.from_dict(d.get("lerakas_hely")),
            lerakas_cim=KinyertMezo.from_dict(d.get("lerakas_cim")),
            lerakas_datum=KinyertMezo.from_dict(d.get("lerakas_datum")),
            rakomany_megnevezese=KinyertMezo.from_dict(d.get("rakomany_megnevezese")),
            jarmuigeny=KinyertMezo.from_dict(d.get("jarmuigeny")),
            tetelek=[RakomanyTetelAdat.from_dict(t) for t in d.get("tetelek") or []],
            altalanos_megjegyzesek=[str(x).strip() for x in d.get("altalanos_megjegyzesek") or [] if str(x).strip()],
        )


# A fuvarozási (nem rakomány-) mezők felirata, a hiányzó/bizonytalan lista összeállításához.
_FUVAR_MEZO_CIMKE = {
    "felrakas_hely": "felrakási hely",
    "felrakas_cim": "felrakási cím",
    "felrakas_datum": "felrakási időpont",
    "lerakas_hely": "lerakási hely",
    "lerakas_cim": "lerakási cím",
    "lerakas_datum": "lerakási időpont",
    "rakomany_megnevezese": "rakomány megnevezése",
    "jarmuigeny": "jármúigény",
}
_TETEL_MEZO_CIMKE = {
    "darab": "darabszám", "hossz_cm": "hosszúság", "szelesseg_cm": "szélesség",
    "magassag_cm": "magasság", "suly_kg": "tömeg", "halmozhato": "halmozhatóság",
}


def hianyzo_es_bizonytalan_mezok(adat: FuvarIgenyAdat) -> tuple[list[str], list[str]]:
    """(hiányzó mezők, bizonytalan mezők) emberi olvasható feliratokkal."""
    hianyzik, bizonytalan = [], []
    for nev, cimke in _FUVAR_MEZO_CIMKE.items():
        mezo: KinyertMezo = getattr(adat, nev)
        if mezo.bizonyossag == Bizonyossag.HIANYZIK:
            hianyzik.append(cimke)
        elif mezo.bizonyossag == Bizonyossag.BIZONYTALAN:
            bizonytalan.append(cimke + (f" ({mezo.megjegyzes})" if mezo.megjegyzes else ""))
    if not adat.tetelek:
        hianyzik.append("rakománytételek")
    for i, t in enumerate(adat.tetelek, start=1):
        elotag = f"{i}. tétel" if len(adat.tetelek) > 1 else "rakomány"
        for nev, cimke in _TETEL_MEZO_CIMKE.items():
            mezo: KinyertMezo = getattr(t, nev)
            if mezo.bizonyossag == Bizonyossag.HIANYZIK:
                hianyzik.append(f"{elotag}: {cimke}")
            elif mezo.bizonyossag == Bizonyossag.BIZONYTALAN:
                bizonytalan.append(f"{elotag}: {cimke}" + (f" ({mezo.megjegyzes})" if mezo.megjegyzes else ""))
    return hianyzik, bizonytalan
