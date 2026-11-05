"""Pótkocsitípusok és a rakodótér méretei. Minden méret centiméterben."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class PotkocsiTipus:
    nev: str
    hossz_cm: float
    szelesseg_cm: float
    magassag_cm: float


POTKOCSI_TIPUSOK: dict[str, PotkocsiTipus] = {
    "Normál": PotkocsiTipus("Normál", 1360, 245, 270),
    "Semi-mega": PotkocsiTipus("Semi-mega", 1360, 245, 285),
    "Mega": PotkocsiTipus("Mega", 1360, 245, 300),
}
EGYEDI_TIPUS = "Egyedi méret"
ALAP_TIPUS = "Normál"
ALAP_TEHERBIRAS_KG = 24000.0


@dataclass
class Potkocsi:
    """Pótkocsi névleges méretei és – ha eltér – a ténylegesen szabad rakodótér.

    A névleges méret nem jelenti automatikusan, hogy a teljes tér akadálymentesen
    használható (pl. kerékdob, rakományrögzítő sín, ajtókeret). A szabad méretek
    megadásakor a rakodási terv azokkal számol.
    """

    tipus: str = ALAP_TIPUS
    hossz_cm: float = 1360.0
    szelesseg_cm: float = 245.0
    magassag_cm: float = 270.0
    teherbiras_kg: float = ALAP_TEHERBIRAS_KG
    szabad_hossz_cm: Optional[float] = None
    szabad_szelesseg_cm: Optional[float] = None
    szabad_magassag_cm: Optional[float] = None

    @classmethod
    def tipusbol(cls, nev: str, teherbiras_kg: float = ALAP_TEHERBIRAS_KG) -> "Potkocsi":
        t = POTKOCSI_TIPUSOK[nev]
        return cls(nev, t.hossz_cm, t.szelesseg_cm, t.magassag_cm, teherbiras_kg)

    @property
    def rakter_hossz_cm(self) -> float:
        return self.szabad_hossz_cm if self.szabad_hossz_cm else self.hossz_cm

    @property
    def rakter_szelesseg_cm(self) -> float:
        return self.szabad_szelesseg_cm if self.szabad_szelesseg_cm else self.szelesseg_cm

    @property
    def rakter_magassag_cm(self) -> float:
        return self.szabad_magassag_cm if self.szabad_magassag_cm else self.magassag_cm

    @property
    def eltero_szabad_rakter(self) -> bool:
        return (
            self.rakter_hossz_cm != self.hossz_cm
            or self.rakter_szelesseg_cm != self.szelesseg_cm
            or self.rakter_magassag_cm != self.magassag_cm
        )


def validal_potkocsi(pk: Potkocsi) -> list[str]:
    hibak = []
    for nev, ertek in (
        ("belső hossz", pk.hossz_cm), ("belső szélesség", pk.szelesseg_cm),
        ("belső magasság", pk.magassag_cm), ("hasznos teherbírás", pk.teherbiras_kg),
    ):
        if not math.isfinite(ertek) or ertek <= 0:
            hibak.append(f"A pótkocsi {nev} értéke legyen nagyobb 0-nál.")
    for nev, szabad, nevleges in (
        ("hossz", pk.szabad_hossz_cm, pk.hossz_cm),
        ("szélesség", pk.szabad_szelesseg_cm, pk.szelesseg_cm),
        ("magasság", pk.szabad_magassag_cm, pk.magassag_cm),
    ):
        if szabad is not None and not 0 < szabad <= nevleges:
            hibak.append(f"A szabad rakodási {nev} 0 és a névleges {nevleges:g} cm között legyen.")
    for v in (pk.hossz_cm, pk.szelesseg_cm, pk.magassag_cm, pk.szabad_hossz_cm, pk.szabad_szelesseg_cm, pk.szabad_magassag_cm):
        if v is not None and math.isfinite(v) and abs(v*10-round(v*10)) > 1e-6:
            hibak.append("A raktérméret legfeljebb 0,1 cm pontosságú legyen.")
    return hibak
