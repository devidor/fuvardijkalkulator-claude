"""Fuvardíj-becslés: alapdíj, felárak, beszerzési költség, ajánlati ár, fedezet."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class DijParameterek:
    ldm: float
    dij_per_ldm: float
    penznem: str = "EUR"
    minimum_dij: float = 0.0
    utdij: float = 0.0
    uzemanyag_pct: float = 0.0  # az alapdíj százalékában
    varakozas_ora: float = 0.0
    varakozas_oradij: float = 0.0
    egyeb_felar: float = 0.0
    arazas_mod: str = "haszonkulcs"  # "haszonkulcs" | "arres"
    szazalek: float = 0.0
    dij_mod: str = "ldm"
    ossz_kg: float = 0.0
    dij_per_kg: float = 0.0
    teljes_kocsi_dij: float = 0.0


@dataclass
class DijEredmeny:
    penznem: str
    ldm: float
    alapdij: float
    minimum_alkalmazva: bool
    uzemanyag_potdij: float
    utdij: float
    varakozasi_dij: float
    egyeb_felar: float
    felarak_osszesen: float
    beszerzesi_koltseg: float
    ajanlott_ar: float
    fedezet: float
    fedezeti_hanyad_pct: float  # = árrés: fedezet / eladási ár
    haszonkulcs_pct: float  # fedezet / beszerzési költség


def szamol_dij(p: DijParameterek) -> DijEredmeny:
    """Becsült fuvardíj és ajánlati ár.

    - Haszonkulcs: a beszerzési költségre vetített felár → ár = költség × (1 + h).
    - Árrés: az eladási árra vetített fedezet → ár = költség ÷ (1 − a).
    """
    for nev, ertek in (
        ("kg", p.ossz_kg), ("díj/kg", p.dij_per_kg), ("teljes kocsi díj", p.teljes_kocsi_dij),
        ("LDM", p.ldm), ("díj/LDM", p.dij_per_ldm), ("minimum díj", p.minimum_dij),
        ("útdíj", p.utdij), ("üzemanyag-pótdíj", p.uzemanyag_pct),
        ("várakozási idő", p.varakozas_ora), ("várakozási óradíj", p.varakozas_oradij),
        ("egyéb felár", p.egyeb_felar), ("százalék", p.szazalek),
    ):
        if not math.isfinite(ertek) or ertek < 0:
            raise ValueError(f"A(z) {nev} nem lehet negatív.")
    if p.arazas_mod not in ("haszonkulcs", "arres"):
        raise ValueError("Ismeretlen árazási mód.")
    if p.arazas_mod == "arres" and p.szazalek >= 100:
        raise ValueError("Az árrés 100% alatt kell legyen (az árrés az eladási ár része).")

    if p.dij_mod not in ("ldm", "kg", "ftl") or p.penznem not in ("EUR", "HUF"):
        raise ValueError("Ismeretlen díjazás vagy pénznem.")
    ldm_dij = {"ldm": p.ldm * p.dij_per_ldm, "kg": p.ossz_kg * p.dij_per_kg, "ftl": p.teljes_kocsi_dij}[p.dij_mod]
    alapdij = max(ldm_dij, p.minimum_dij)
    uzemanyag = alapdij * p.uzemanyag_pct / 100
    varakozas = p.varakozas_ora * p.varakozas_oradij
    felarak = uzemanyag + p.utdij + varakozas + p.egyeb_felar
    koltseg = alapdij + felarak

    if p.arazas_mod == "haszonkulcs":
        ar = koltseg * (1 + p.szazalek / 100)
    else:
        ar = koltseg / (1 - p.szazalek / 100)
    fedezet = ar - koltseg

    return DijEredmeny(
        penznem=p.penznem,
        ldm=p.ldm,
        alapdij=alapdij,
        minimum_alkalmazva=p.minimum_dij > ldm_dij,
        uzemanyag_potdij=uzemanyag,
        utdij=p.utdij,
        varakozasi_dij=varakozas,
        egyeb_felar=p.egyeb_felar,
        felarak_osszesen=felarak,
        beszerzesi_koltseg=koltseg,
        ajanlott_ar=ar,
        fedezet=fedezet,
        fedezeti_hanyad_pct=fedezet / ar * 100 if ar > 0 else 0.0,
        haszonkulcs_pct=fedezet / koltseg * 100 if koltseg > 0 else 0.0,
    )
