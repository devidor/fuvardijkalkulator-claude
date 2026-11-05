"""Elszámolási beállítások: tömeg–LDM index és kerekítési szabály.

Az itt megadott alapértékek a felületen felülírhatók.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

ALAP_KG_PER_LDM = 1750.0

# Felirat → (mód, lépésköz LDM-ben). Mód: "fel" = felfelé, "kerekit" = matematikai kerekítés.
KEREKITESI_SZABALYOK: dict[str, Optional[tuple[str, float]]] = {
    "Nincs kerekítés": None,
    "Felfelé 0,01 LDM-re": ("fel", 0.01),
    "Felfelé 0,1 LDM-re": ("fel", 0.1),
    "Felfelé 0,25 LDM-re": ("fel", 0.25),
    "Felfelé 0,5 LDM-re": ("fel", 0.5),
    "Matematikai kerekítés 0,1 LDM-re": ("kerekit", 0.1),
}
ALAP_KEREKITES = "Nincs kerekítés"


@dataclass(frozen=True)
class ElszamolasiKonfig:
    kg_per_ldm: float = ALAP_KG_PER_LDM
    kerekites: str = ALAP_KEREKITES

    szabaly: str = "maximum"

    def __post_init__(self):
        if self.szabaly not in ("maximum", "fizikai", "tömeg"):
            raise ValueError("Ismeretlen elszámolási szabály.")
        if not math.isfinite(self.kg_per_ldm) or self.kg_per_ldm <= 0:
            raise ValueError("Az elszámolási index (kg/LDM) legyen nagyobb 0-nál.")
        if self.kerekites not in KEREKITESI_SZABALYOK:
            raise ValueError(f"Ismeretlen kerekítési szabály: {self.kerekites}")
