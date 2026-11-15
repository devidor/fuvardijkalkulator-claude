"""Fuvardíj-becslés: alapdíj, felárak, beszerzési költség, ajánlati ár, fedezet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


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
    arazas_mod: str = "haszonkulcs"  # "haszonkulcs" | "arres" | "fix"
    szazalek: float = 0.0
    fix_profit: float = 0.0  # "fix" módban: ár = költség + fix összeg
    # Ha meg van adva (pl. km-alapú FTL/LTL-díj), ez az alapdíj az LDM × díj/LDM helyett.
    kulso_alapdij: Optional[float] = None


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
    - Fix: kézzel megadott profit → ár = költség + fix összeg.
    """
    for nev, ertek in (
        ("LDM", p.ldm), ("díj/LDM", p.dij_per_ldm), ("minimum díj", p.minimum_dij),
        ("útdíj", p.utdij), ("üzemanyag-pótdíj", p.uzemanyag_pct),
        ("várakozási idő", p.varakozas_ora), ("várakozási óradíj", p.varakozas_oradij),
        ("egyéb felár", p.egyeb_felar), ("százalék", p.szazalek), ("fix profit", p.fix_profit),
        ("alapdíj", p.kulso_alapdij or 0.0),
    ):
        if ertek < 0:
            raise ValueError(f"A(z) {nev} nem lehet negatív.")
    if p.arazas_mod not in ("haszonkulcs", "arres", "fix"):
        raise ValueError("Ismeretlen árazási mód.")
    if p.arazas_mod == "arres" and p.szazalek >= 100:
        raise ValueError("Az árrés 100% alatt kell legyen (az árrés az eladási ár része).")

    ldm_dij = p.kulso_alapdij if p.kulso_alapdij is not None else p.ldm * p.dij_per_ldm
    alapdij = max(ldm_dij, p.minimum_dij)
    uzemanyag = alapdij * p.uzemanyag_pct / 100
    varakozas = p.varakozas_ora * p.varakozas_oradij
    felarak = uzemanyag + p.utdij + varakozas + p.egyeb_felar
    koltseg = alapdij + felarak

    if p.arazas_mod == "haszonkulcs":
        ar = koltseg * (1 + p.szazalek / 100)
    elif p.arazas_mod == "fix":
        ar = koltseg + p.fix_profit
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
