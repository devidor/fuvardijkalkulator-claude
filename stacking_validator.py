"""Halmozási korlátok: halommagasság, ráterhelés, alátámasztás, túlnyúlás, váltott tájolás."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from cargo_models import EPS, RakomanyCsoport, Uzenet

NEM_HALMOZOTT = "Nem halmozott"
ELLENORZOTT = "Ellenőrzött"
NEM_IGAZOLT = "Nem igazolt"
NEM_RAKHATO = "Nem rakható"


@dataclass
class ValtakozoElemzes:
    """Két egymásra helyezett egység, amelyek közül a felső 90°-kal el van forgatva (középre igazítva)."""

    befoglalo_hossz_cm: float
    befoglalo_szelesseg_cm: float
    alatamasztas_pct: float  # a felső egység alapterületének ekkora része fekszik fel az alsóra
    tulnyulas_cm: float  # oldalanként
    terulet_novekedes_pct: float  # a halom befoglaló alapterülete az egységhez képest

    @property
    def negyzetes(self) -> bool:
        return self.tulnyulas_cm <= EPS


@dataclass
class HalmozasEredmeny:
    kert_szint: int
    alkalmazott_szint: int
    max_szint_magassag: int
    max_szint_terheles: Optional[int]
    halom_magassag_cm: float
    helyek: int  # szükséges alapterületi helyek (halmok) száma
    statusz: str
    uzenetek: list[Uzenet] = field(default_factory=list)
    feltetelezesek: list[str] = field(default_factory=list)
    valtakozo: Optional[ValtakozoElemzes] = None

    def egysegek_helyenkent(self, darab: int) -> list[int]:
        s = self.alkalmazott_szint
        return [min(s, darab - i * s) for i in range(self.helyek)]


def valtakozo_elemzes(hossz_cm: float, szelesseg_cm: float) -> ValtakozoElemzes:
    nagy, kicsi = max(hossz_cm, szelesseg_cm), min(hossz_cm, szelesseg_cm)
    return ValtakozoElemzes(
        befoglalo_hossz_cm=nagy,
        befoglalo_szelesseg_cm=nagy,
        alatamasztas_pct=kicsi * kicsi / (nagy * kicsi) * 100,
        tulnyulas_cm=(nagy - kicsi) / 2,
        terulet_novekedes_pct=(nagy * nagy / (nagy * kicsi) - 1) * 100,
    )


def ellenoriz_halmozast(cs: RakomanyCsoport, rakter_magassag_cm: float) -> HalmozasEredmeny:
    uzenetek: list[Uzenet] = []
    feltetelezesek: list[str] = []
    kert = int(cs.max_szint)
    igeny = min(kert, cs.darab)  # a legmagasabb ténylegesen kialakuló halom

    max_mag = math.floor(rakter_magassag_cm / cs.magassag_cm + EPS)
    max_ter = None
    if cs.raterheles_kg is not None:
        max_ter = 1 + math.floor(cs.raterheles_kg / cs.suly_kg + EPS)

    if max_mag < 1:
        uzenetek.append(Uzenet(
            "hiba",
            f"Egy egység magassága ({cs.magassag_cm:g} cm) meghaladja a rakodótér "
            f"{rakter_magassag_cm:g} cm-es belmagasságát – a rakomány túl magas a pótkocsihoz.",
        ))
        return HalmozasEredmeny(kert, 1, 0, max_ter, cs.magassag_cm, cs.darab, NEM_RAKHATO, uzenetek)

    alkalmazott = max(1, min(kert, max_mag, max_ter if max_ter is not None else kert))

    if igeny > max_mag:
        uzenetek.append(Uzenet(
            "figyelmeztetes",
            f"A kért {kert} szintes halom {igeny * cs.magassag_cm:g} cm magas lenne, ami meghaladja "
            f"a {rakter_magassag_cm:g} cm belmagasságot – legfeljebb {max_mag} szint fér el.",
        ))
    if max_ter is not None and igeny > max_ter:
        uzenetek.append(Uzenet(
            "figyelmeztetes",
            f"A halmozás nem megengedett: {igeny} szintnél a legalsó egységre "
            f"{(igeny - 1) * cs.suly_kg:g} kg nehezedne, a megengedett felső terhelés "
            f"{cs.raterheles_kg:g} kg – legfeljebb {max_ter} szint biztonságos.",
        ))
    if alkalmazott < igeny:
        uzenetek.append(Uzenet(
            "figyelmeztetes",
            f"A kért {kert} szint nem valósítható meg – a terv {alkalmazott} szinttel számol.",
        ))

    halmozott = alkalmazott > 1 and cs.darab > 1
    valtakozo = None
    statusz = NEM_HALMOZOTT
    if halmozott:
        statusz = ELLENORZOTT
        feltetelezesek.append(
            f"{cs.nev}: azonos tájolású, élben egymásra illeszkedő halmozás, legfeljebb {alkalmazott} szint; "
            "csak a csoport saját egységei kerülnek egymásra."
        )
        if max_ter is None:
            statusz = NEM_IGAZOLT
            uzenetek.append(Uzenet(
                "figyelmeztetes",
                "Az alsó egység megengedett felső terhelése nem ismert, ezért a halmozás biztonsága "
                f"nem igazolt. A terv a kért {alkalmazott} szintes halmozást feltételezi – ezt a "
                "feladóval és a fuvarozóval egyeztetni kell.",
            ))
        if cs.tulnyulas_cm > EPS:
            statusz = NEM_IGAZOLT
            uzenetek.append(Uzenet(
                "figyelmeztetes",
                f"A rakomány legfeljebb {cs.tulnyulas_cm:g} cm-rel túlnyúlik a raklapon. Halmozásnál a "
                "felső raklap a túlnyúló árura is támaszkodhat – az alátámasztás és a túlnyúló rész "
                "terhelhetősége nem ellenőrizhető.",
            ))
        if cs.valtakozo_tajolas:
            valtakozo = valtakozo_elemzes(cs.hossz_cm, cs.szelesseg_cm)
            if valtakozo.negyzetes:
                uzenetek.append(Uzenet(
                    "info",
                    "Négyzetes alapterületnél a felváltva forgatott halmozás nem változtat a helyigényen; "
                    "a stabilitást ettől függetlenül ellenőrizni kell.",
                ))
            else:
                uzenetek.append(Uzenet(
                    "figyelmeztetes",
                    f"Felváltva forgatott halmozásnál a felső egység alapterületének csak "
                    f"{valtakozo.alatamasztas_pct:.0f}%-a fekszik fel az alsóra, oldalanként "
                    f"{valtakozo.tulnyulas_cm:g} cm túlnyúlással; a halom befoglaló alapterülete "
                    f"{valtakozo.befoglalo_hossz_cm:g} × {valtakozo.befoglalo_szelesseg_cm:g} cm "
                    f"(+{valtakozo.terulet_novekedes_pct:.0f}%). Ez nem helytakarékos és nem tekinthető "
                    "automatikusan biztonságosnak – a terv azonos tájolású halmozással számol.",
                ))

    return HalmozasEredmeny(
        kert_szint=kert,
        alkalmazott_szint=alkalmazott,
        max_szint_magassag=max_mag,
        max_szint_terheles=max_ter,
        halom_magassag_cm=min(alkalmazott, cs.darab) * cs.magassag_cm,
        helyek=math.ceil(cs.darab / alkalmazott),
        statusz=statusz,
        uzenetek=uzenetek,
        feltetelezesek=feltetelezesek,
        valtakozo=valtakozo,
    )
