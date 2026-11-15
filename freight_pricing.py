"""Km-alapú alapfuvardíj (FTL és LTL) a Finian-féle díjtáblák szerint.

- FTL-díj = kerekített km × €/km. A km felfelé kerekül a következő egész 100-ra (216 → 300).
- LTL-díj = FTL-díj × szorzó, ahol a szorzó a díjszámítási ldm (0,1-re felkerekítve) és a
  nem magyar fél országcsoportja szerint a szorzótáblából jön. 12,1 ldm-től a szorzó 1.

Feltételezések (Daniel Finian megerősítésére vár): az LTL-képlet (km × €/km × szorzó),
a 0,1-es felkerekítés, és hogy pontos százas km nem kerekül feljebb. A felület mindegyiket
kiírja, így ellenőrizhető. Streamlit-független modul.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

import rate_tables as rt

KM_LEPES = 100

SZOLG_AUTO = "auto"  # LTL, ha az ldm 12,1 alatt van, egyébként FTL
SZOLG_FTL = "FTL"
SZOLG_LTL = "LTL"


def _tized(x: float) -> str:
    return f"{x:.1f}".replace(".", ",")


def kerekitett_km(km: float, lepes: int = KM_LEPES) -> int:
    """Felfelé kerekítés a következő egész `lepes`-re; legalább egy lépés (pl. 40 km → 100 km)."""
    if km <= 0:
        raise ValueError("A távolság legyen nagyobb 0 km-nél.")
    return max(1, math.ceil(round(km, 6) / lepes)) * lepes


@dataclass
class KmDijEredmeny:
    viszonylat: rt.Viszonylat
    km: float
    km_kerekitett: int
    eur_per_km: float
    ftl_dij: float
    szolgaltatas: str  # SZOLG_FTL | SZOLG_LTL
    ldm: Optional[float] = None
    dijszamitasi_ldm: Optional[float] = None
    csoport: Optional[int] = None
    szorzo: Optional[float] = None
    alapdij: float = 0.0
    megjegyzesek: list[str] = field(default_factory=list)


class KmDijHiba(ValueError):
    """A km-alapú díj nem számolható (tiltott ország, hiányzó adat stb.)."""


def szamol_km_dij(
    felrako: str,
    lerako: str,
    km: float,
    eur_per_km: float,
    ldm: Optional[float] = None,
    szolgaltatas: str = SZOLG_AUTO,
    csoport_felulir: Optional[int] = None,
) -> KmDijEredmeny:
    v = rt.viszonylat(felrako, lerako)
    if v.tiltott:
        raise KmDijHiba("BY és RU irányba a jelenlegi szankciók miatt nem biztosítunk szállítási szolgáltatást.")
    if eur_per_km <= 0:
        raise KmDijHiba("Adja meg a km-díjat (€/km).")
    km_k = kerekitett_km(km)
    ftl = km_k * eur_per_km
    e = KmDijEredmeny(viszonylat=v, km=km, km_kerekitett=km_k, eur_per_km=eur_per_km, ftl_dij=ftl,
                      szolgaltatas=SZOLG_FTL, ldm=ldm, alapdij=ftl)

    if szolgaltatas == SZOLG_FTL:
        return e
    if szolgaltatas not in (SZOLG_AUTO, SZOLG_LTL):
        raise KmDijHiba(f"Ismeretlen szolgáltatás: {szolgaltatas}")
    if ldm is None or ldm <= 0:
        if szolgaltatas == SZOLG_LTL:
            raise KmDijHiba("Az LTL-díjhoz ldm szükséges (Rakomány fül vagy kézi megadás).")
        e.megjegyzesek.append("Nincs ldm-adat – komplett (FTL) díj számolva.")
        return e

    dldm = rt.dijszamitasi_ldm(ldm)
    e.dijszamitasi_ldm = dldm
    if szolgaltatas == SZOLG_AUTO and dldm >= rt.FTL_HATAR_LDM:
        e.megjegyzesek.append(f"{_tized(rt.FTL_HATAR_LDM)} ldm-től a szorzó 1 – komplett (FTL) díj.")
        return e

    cs = csoport_felulir if csoport_felulir is not None else rt.ltl_csoport(v)
    if cs is None:
        raise KmDijHiba(
            "Ehhez a viszonylathoz nincs LTL-szorzócsoport a táblában – válasszon csoportot kézzel, "
            "vagy számoljon FTL-díjat."
        )
    if dldm > rt.MAX_LDM:
        e.megjegyzesek.append(f"Az ldm meghaladja a {_tized(rt.MAX_LDM)} ldm-t – egy pótkocsiba nem fér, "
                              "a díj egy komplett kocsira szól.")
    e.szolgaltatas = SZOLG_LTL
    e.csoport = cs
    e.szorzo = rt.ltl_szorzo(dldm, cs)
    e.alapdij = ftl * e.szorzo
    return e
