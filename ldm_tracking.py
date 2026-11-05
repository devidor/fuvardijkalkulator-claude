"""Tervezett, fuvarozó által visszaigazolt és tényleges LDM elkülönített kezelése."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Optional

from cargo_models import Uzenet, hu

NINCS_ELKULDVE = "Nincs elküldve"
VALASZRA_VAR = "Elküldve – visszaigazolásra vár"
VISSZAIGAZOLVA = "Visszaigazolva"
MODOSITASSAL = "Módosítással visszaigazolva"
ELUTASITVA = "Elutasítva"
ALLAPOTOK = [NINCS_ELKULDVE, VALASZRA_VAR, VISSZAIGAZOLVA, MODOSITASSAL, ELUTASITVA]
VISSZAIGAZOLT_ALLAPOTOK = {VISSZAIGAZOLVA, MODOSITASSAL}

TURES_LDM = 0.005


@dataclass
class LdmKovetes:
    tervezett_fizikai_ldm: float  # A – a kalkulátor számítása
    tervezett_elszamolasi_ldm: float
    allapot: str = NINCS_ELKULDVE
    visszaigazolt_ldm: Optional[float] = None  # B – a fuvarozó írásos visszaigazolása
    visszaigazolas_datuma: Optional[date] = None
    visszaigazolas_hivatkozas: str = ""
    tenyleges_ldm: Optional[float] = None  # C – rakodás utáni visszajelzés
    elteres_indoka: str = ""

    @property
    def visszaigazolt(self) -> bool:
        return (self.allapot in VISSZAIGAZOLT_ALLAPOTOK and self.visszaigazolt_ldm is not None
                and math.isfinite(self.visszaigazolt_ldm) and self.visszaigazolt_ldm > 0)

    @property
    def elszamolasi_alap(self) -> tuple[float, str]:
        """A díjszámítás LDM-alapja és forrása. A tényleges LDM sosem írja felül automatikusan."""
        if self.visszaigazolt:
            return self.visszaigazolt_ldm, "fuvarozó által visszaigazolt LDM"
        return self.tervezett_elszamolasi_ldm, "tervezett elszámolási LDM (nem visszaigazolt)"

    @property
    def visszaigazolt_elteres(self) -> Optional[float]:
        if self.visszaigazolt_ldm is None:
            return None
        return self.visszaigazolt_ldm - self.tervezett_fizikai_ldm

    @property
    def tenyleges_elteres(self) -> Optional[float]:
        """Tényleges LDM eltérése a visszaigazolttól (ha van), különben a tervezettől."""
        if self.tenyleges_ldm is None:
            return None
        viszonyitas = self.visszaigazolt_ldm if self.visszaigazolt else self.tervezett_fizikai_ldm
        return self.tenyleges_ldm - viszonyitas


def elemzes(k: LdmKovetes) -> list[Uzenet]:
    u: list[Uzenet] = []
    if k.allapot == ELUTASITVA:
        u.append(Uzenet("hiba", "A fuvarozó elutasította a rakodási tervet – új terv vagy egyeztetés szükséges."))
    elif k.allapot in VISSZAIGAZOLT_ALLAPOTOK and k.visszaigazolt_ldm is None:
        u.append(Uzenet("figyelmeztetes", "A visszaigazolt állapothoz adja meg a fuvarozó által elfogadott LDM-et."))
    elif not k.visszaigazolt:
        u.append(Uzenet(
            "figyelmeztetes",
            "A tervezett LDM nem garantált, amíg a fuvarozó írásban vissza nem igazolja.",
        ))
    if k.visszaigazolt:
        if not k.visszaigazolas_hivatkozas.strip():
            u.append(Uzenet("info", "Rögzítse a visszaigazolás hivatkozását (pl. e-mail tárgya, dokumentumszám)."))
        elteres = k.visszaigazolt_elteres
        if elteres is not None and abs(elteres) > TURES_LDM:
            u.append(Uzenet(
                "figyelmeztetes",
                f"A visszaigazolt LDM {hu(elteres, elojel=True)}-dal eltér a tervezett fizikai LDM-től "
                f"({hu(k.visszaigazolt_ldm)} vs. {hu(k.tervezett_fizikai_ldm)}).",
            ))
    if k.tenyleges_ldm is not None:
        elteres = k.tenyleges_elteres
        alap = "visszaigazolt" if k.visszaigazolt else "tervezett"
        if abs(elteres) > TURES_LDM:
            indok = f" Indok: {k.elteres_indoka.strip()}" if k.elteres_indoka.strip() else " Az eltérés indoka nincs megadva."
            u.append(Uzenet(
                "figyelmeztetes",
                f"A tényleges rakodási LDM {hu(elteres, elojel=True)}-dal eltér a {alap} értéktől "
                f"({hu(k.tenyleges_ldm)} LDM).{indok}",
            ))
        else:
            u.append(Uzenet("ok", f"A tényleges rakodás megegyezik a {alap} LDM-mel."))
    u.append(Uzenet(
        "info",
        "A fuvardíj nem módosul automatikusan a rakodás után megadott tényleges LDM alapján; az "
        "elszámolást a visszaigazolt ajánlat és a szerződéses feltételek határozzák meg.",
    ))
    return u
