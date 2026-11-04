"""Rakományadatok és validáció. Minden méret centiméterben, tömeg kilogrammban."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

EPS = 1e-9

# Szabványos raklapok: (hosszúság cm, szélesség cm). None = szabadon megadható.
RAKLAP_TIPUSOK: dict[str, Optional[tuple[float, float]]] = {
    "EUR-raklap (120 × 80 cm)": (120.0, 80.0),
    "Ipari raklap (120 × 100 cm)": (120.0, 100.0),
    "Félraklap (80 × 60 cm)": (80.0, 60.0),
    "Egyedi méret": None,
}


def hu(x: float, tizedes: int = 2, elojel: bool = False) -> str:
    """Magyar számformátum üzenetekhez: tizedesvessző, szóköz ezres elválasztó."""
    s = f"{x:{'+' if elojel else ''},.{tizedes}f}"
    return s.replace(",", " ").replace(".", ",")


@dataclass
class Uzenet:
    szint: str  # "hiba" | "figyelmeztetes" | "info" | "ok"
    szoveg: str


@dataclass
class RakomanyCsoport:
    """Azonos méretű és kezelésű rakományegységek csoportja."""

    nev: str
    hossz_cm: float
    szelesseg_cm: float
    magassag_cm: float
    darab: int
    suly_kg: float  # egy egység tömege
    max_szint: int = 1  # legfeljebb ennyi egység helyezhető egymásra (1 = nem halmozható)
    forgathato: bool = True  # alapterületen 90°-kal elforgatható
    valtakozo_tajolas: bool = False  # a halomban eltérő (felváltva forgatott) tájolás megengedett
    raterheles_kg: Optional[float] = None  # alsó egység megengedett felső terhelése; None = nem ismert
    tipus: str = ""
    raklap_meret_cm: Optional[tuple[float, float]] = None  # alap raklap (túlnyúlás-ellenőrzéshez)

    @property
    def alapterulet_cm2(self) -> float:
        return self.hossz_cm * self.szelesseg_cm

    @property
    def ossz_suly_kg(self) -> float:
        return self.darab * self.suly_kg

    @property
    def tulnyulas_cm(self) -> float:
        """Legnagyobb túlnyúlás a raklapon túl (0, ha nincs vagy nem ismert a raklap)."""
        if not self.raklap_meret_cm:
            return 0.0
        rh, rsz = self.raklap_meret_cm
        return max(0.0, self.hossz_cm - rh, self.szelesseg_cm - rsz)


def egysegsuly(ossz_suly_kg: float, darab: int) -> float:
    if darab < 1:
        raise ValueError("A darabszám legalább 1 legyen.")
    return ossz_suly_kg / darab


def validal_csoport(cs: RakomanyCsoport) -> list[str]:
    hibak = []
    if cs.hossz_cm <= 0 or cs.szelesseg_cm <= 0 or cs.magassag_cm <= 0:
        hibak.append("A hosszúság, szélesség és magasság legyen nagyobb 0-nál.")
    if cs.darab < 1 or int(cs.darab) != cs.darab:
        hibak.append("A darabszám legalább 1 egész szám legyen.")
    if cs.suly_kg <= 0:
        hibak.append("A tömeg legyen nagyobb 0-nál.")
    if cs.max_szint < 1 or int(cs.max_szint) != cs.max_szint:
        hibak.append("A halmozási szintszám legalább 1 egész szám legyen.")
    if cs.raterheles_kg is not None and cs.raterheles_kg < 0:
        hibak.append("A megengedett felső terhelés nem lehet negatív.")
    return hibak
