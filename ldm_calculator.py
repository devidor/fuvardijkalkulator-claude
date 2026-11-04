"""Elméleti, fizikai, tömegalapú és elszámolási LDM."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from billing_config import KEREKITESI_SZABALYOK, ElszamolasiKonfig


def elmeleti_ldm(darab: int, hossz_cm: float, szelesseg_cm: float, ref_szelesseg_cm: float = 245.0) -> float:
    """Területalapú alsó becslés: (darab × hossz × szélesség) ÷ (pótkocsi-szélesség × 100)."""
    return darab * hossz_cm * szelesseg_cm / (ref_szelesseg_cm * 100)


def fizikai_ldm(hasznalt_hossz_cm: float) -> float:
    """A rakodási tervben ténylegesen lefoglalt rakodótér-hossz méterben."""
    return hasznalt_hossz_cm / 100


def tomegalapu_ldm(ossz_suly_kg: float, kg_per_ldm: float) -> float:
    return ossz_suly_kg / kg_per_ldm


def kerekit(ertek: float, szabaly: str) -> float:
    beallitas = KEREKITESI_SZABALYOK[szabaly]
    if beallitas is None:
        return ertek
    mod, lepes = beallitas
    # Decimal + 9 tizedesre vágás: a lebegőpontos zaj (pl. 2,0000000001) ne kerekítsen felfelé.
    d = Decimal(repr(ertek)).quantize(Decimal("1e-9"))
    l = Decimal(repr(lepes))
    irany = ROUND_CEILING if mod == "fel" else ROUND_HALF_UP
    return float((d / l).quantize(Decimal(1), rounding=irany) * l)


@dataclass
class ElszamolasEredmeny:
    fizikai_ldm: float
    tomegalapu_ldm: float
    elszamolasi_ldm: float  # kerekítés után
    meghatarozo: str  # "fizikai" | "tömeg"
    kg_per_ldm: float
    kerekites: str

    @property
    def tomegegyenertek_kg(self) -> float:
        return self.elszamolasi_ldm * self.kg_per_ldm


def elszamolasi_ldm(fizikai: float, ossz_suly_kg: float, cfg: ElszamolasiKonfig) -> ElszamolasEredmeny:
    """Elszámolási LDM = MAX(fizikai LDM, össztömeg ÷ index), majd a beállított kerekítés.

    Az index díjszámítási tömegegyenérték, nem azonos a jármű terhelhetőségével.
    """
    tomeg = tomegalapu_ldm(ossz_suly_kg, cfg.kg_per_ldm)
    nyers = max(fizikai, tomeg)
    return ElszamolasEredmeny(
        fizikai_ldm=fizikai,
        tomegalapu_ldm=tomeg,
        elszamolasi_ldm=kerekit(nyers, cfg.kerekites),
        meghatarozo="tömeg" if tomeg > fizikai else "fizikai",
        kg_per_ldm=cfg.kg_per_ldm,
        kerekites=cfg.kerekites,
    )
