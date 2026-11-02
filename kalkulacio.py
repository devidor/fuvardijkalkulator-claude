"""Számítási logika a fuvar- és rakománykalkulátorhoz.

A modul nem függ a Streamlittől, így önállóan tesztelhető és más felületről
(pl. API, parancssor) is újrahasznosítható.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

EPS = 1e-9

# Szabványos raklapok: (hosszúság cm, szélesség cm). None = szabadon megadható.
RAKLAP_TIPUSOK: dict[str, Optional[tuple[float, float]]] = {
    "EUR-raklap (120 × 80 cm)": (120.0, 80.0),
    "Ipari raklap (120 × 100 cm)": (120.0, 100.0),
    "Félraklap (80 × 60 cm)": (80.0, 60.0),
    "Egyedi méret": None,
}


# ---------------------------------------------------------------------------
# Adatszerkezetek
# ---------------------------------------------------------------------------

@dataclass
class Potkocsi:
    belso_hossz_m: float = 13.6
    belso_szelesseg_m: float = 2.4  # az LDM-számítás alapja is
    belso_magassag_m: float = 2.7
    teherbiras_kg: float = 24000.0


@dataclass
class RakomanyCsoport:
    nev: str
    hossz_cm: float
    szelesseg_cm: float
    magassag_cm: float
    darab: int
    suly_kg: float  # egy darab tömege
    szint: int = 1  # kért halmozási szint (1 = nem halmozható)
    max_raterheles_kg: float = 0.0  # egy egységre helyezhető max. tömeg; 0 = nincs megadva
    forgathato: bool = True  # 90°-kal elforgatva is rakható
    tipus: str = ""


@dataclass
class Uzenet:
    szint: str  # "hiba" | "figyelmeztetes" | "info"
    szoveg: str


@dataclass
class Sor:
    """Egy keresztirányú sor a pótkocsi rakfelületén."""

    helyek: int  # alapterületi helyek száma a sorban
    keresztben_cm: float  # egy egység mérete a pótkocsi szélessége mentén
    melyseg_cm: float  # a sor hossza a pótkocsi hossza mentén
    forgatott: bool


@dataclass
class Elrendezes:
    sorok: list[Sor]

    @property
    def hossz_m(self) -> float:
        return sum(s.melyseg_cm for s in self.sorok) / 100

    @property
    def leiras(self) -> str:
        if not self.sorok:
            return "–"
        reszek = []
        for forgatott in (False, True):
            sorok = [s for s in self.sorok if s.forgatott == forgatott]
            if sorok:
                irany = "keresztben" if forgatott else "hosszirányban"
                max_db = max(s.helyek for s in sorok)
                reszek.append(f"{len(sorok)} sor {irany} (max. {max_db} hely/sor)")
        return " + ".join(reszek)


@dataclass
class CsoportEredmeny:
    csoport: RakomanyCsoport
    alapterulet_m2: float
    ossz_suly_kg: float
    kert_szint: int
    alkalmazott_szint: int
    helyek: int
    ldm_halmozas_nelkul: float
    ldm: float
    halom_magassag_cm: float
    elrendezes: Optional[Elrendezes]
    berakhato: bool
    uzenetek: list[Uzenet] = field(default_factory=list)

    @property
    def elrendezes_hossz_m(self) -> Optional[float]:
        return self.elrendezes.hossz_m if self.elrendezes else None

    def egysegek_helyenkent(self) -> list[int]:
        """Hány egység áll az egyes alapterületi helyeken (alulról felfelé halmozva)."""
        d, s = self.csoport.darab, self.alkalmazott_szint
        return [min(s, d - i * s) for i in range(self.helyek)]


@dataclass
class Osszesites:
    darab: int
    ossz_suly_kg: float
    helyek: int
    ldm_halmozas_nelkul: float
    ldm: float
    elrendezes_hossz_m: float
    megtakaritott_ldm: float
    megtakaritas_pct: float
    hossz_kihasznaltsag_pct: float
    suly_kihasznaltsag_pct: float
    berakhato: bool
    uzenetek: list[Uzenet] = field(default_factory=list)


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


# ---------------------------------------------------------------------------
# Ellenőrzés
# ---------------------------------------------------------------------------

def validal_potkocsi(pk: Potkocsi) -> list[str]:
    hibak = []
    if pk.belso_hossz_m <= 0:
        hibak.append("A pótkocsi belső hossza legyen nagyobb 0-nál.")
    if pk.belso_szelesseg_m <= 0:
        hibak.append("A pótkocsi belső szélessége legyen nagyobb 0-nál.")
    if pk.belso_magassag_m <= 0:
        hibak.append("A pótkocsi belső magassága legyen nagyobb 0-nál.")
    if pk.teherbiras_kg <= 0:
        hibak.append("A hasznos teherbírás legyen nagyobb 0-nál.")
    return hibak


def validal_csoport(cs: RakomanyCsoport) -> list[str]:
    hibak = []
    if cs.hossz_cm <= 0 or cs.szelesseg_cm <= 0 or cs.magassag_cm <= 0:
        hibak.append("A hosszúság, szélesség és magasság legyen nagyobb 0-nál.")
    if cs.darab < 1 or int(cs.darab) != cs.darab:
        hibak.append("A darabszám legalább 1 egész szám legyen.")
    if cs.suly_kg <= 0:
        hibak.append("Az egy darabra eső tömeg legyen nagyobb 0-nál.")
    if cs.szint < 1 or int(cs.szint) != cs.szint:
        hibak.append("A halmozási szintszám legalább 1 egész szám legyen.")
    if cs.max_raterheles_kg < 0:
        hibak.append("A ráterhelhetőség nem lehet negatív.")
    return hibak


# ---------------------------------------------------------------------------
# Rakodási elrendezés
# ---------------------------------------------------------------------------

def tervez_elrendezes(
    hossz_cm: float, szelesseg_cm: float, helyek: int, pk: Potkocsi, forgathato: bool = True
) -> Optional[Elrendezes]:
    """Soros rakodási terv: az egységek keresztirányú sorokban állnak.

    Két irányt vizsgál (hosszirányban / 90°-kal elforgatva), és a kettő
    keverésével a legrövidebb rakfelület-hosszt keresi. None, ha az egység
    semmilyen irányban nem fér el a pótkocsiban.
    """
    w = pk.belso_szelesseg_m * 100
    lt = pk.belso_hossz_m * 100

    iranyok = [(szelesseg_cm, hossz_cm, False)]
    if forgathato and abs(hossz_cm - szelesseg_cm) > EPS:
        iranyok.append((hossz_cm, szelesseg_cm, True))

    ervenyes = []
    for keresztben, melyseg, forgatott in iranyok:
        soronkent = math.floor(w / keresztben + EPS)
        if soronkent >= 1 and melyseg <= lt + EPS:
            ervenyes.append((keresztben, melyseg, forgatott, soronkent))
    if not ervenyes:
        return None
    if helyek <= 0:
        return Elrendezes([])

    a = ervenyes[0]
    b = ervenyes[1] if len(ervenyes) > 1 else None
    legjobb = None  # (hossz, sorok száma, a_sorok, b_sorok)
    max_a = math.ceil(helyek / a[3])
    for a_sor in range(max_a + 1):
        maradek = max(0, helyek - a_sor * a[3])
        if b is None:
            if maradek > 0:
                continue
            b_sor = 0
        else:
            b_sor = math.ceil(maradek / b[3])
        hossz = a_sor * a[1] + (b_sor * b[1] if b else 0)
        kulcs = (round(hossz, 6), a_sor + b_sor)
        if legjobb is None or kulcs < legjobb[:2]:
            legjobb = (*kulcs, a_sor, b_sor)

    _, _, a_sor, b_sor = legjobb
    sorok: list[Sor] = []
    maradek = helyek
    for irany, db in ((a, a_sor), (b, b_sor)):
        for _ in range(db):
            n = min(irany[3], maradek)
            maradek -= n
            sorok.append(Sor(n, irany[0], irany[1], irany[2]))
    return Elrendezes(sorok)


# ---------------------------------------------------------------------------
# Rakománycsoport és összesítés
# ---------------------------------------------------------------------------

def szamol_csoport(cs: RakomanyCsoport, pk: Potkocsi) -> CsoportEredmeny:
    hibak = validal_csoport(cs) + validal_potkocsi(pk)
    if hibak:
        raise ValueError(" ".join(hibak))

    uzenetek: list[Uzenet] = []
    berakhato = True
    alapterulet = cs.hossz_cm * cs.szelesseg_cm / 10_000
    belmagassag_cm = pk.belso_magassag_m * 100

    # Halmozási korlátok
    kert = int(cs.szint)
    igeny = min(kert, cs.darab)  # a legmagasabb ténylegesen kialakuló halom
    max_magassag = math.floor(belmagassag_cm / cs.magassag_cm + EPS)
    max_terheles = None
    if cs.max_raterheles_kg > 0:
        max_terheles = 1 + math.floor(cs.max_raterheles_kg / cs.suly_kg + EPS)

    alkalmazott = min(kert, max_magassag, max_terheles if max_terheles else kert)
    alkalmazott = max(1, alkalmazott)

    if max_magassag < 1:
        berakhato = False
        uzenetek.append(Uzenet(
            "hiba",
            f"Egy egység magassága ({cs.magassag_cm:g} cm) meghaladja a pótkocsi "
            f"belmagasságát ({belmagassag_cm:g} cm) – a rakomány túl magas a pótkocsihoz.",
        ))
    elif igeny > max_magassag:
        uzenetek.append(Uzenet(
            "figyelmeztetes",
            f"A kért {kert} szintes halmozás {igeny * cs.magassag_cm:g} cm magas lenne, "
            f"ami meghaladja a {belmagassag_cm:g} cm belmagasságot – legfeljebb "
            f"{max_magassag} szint fér el.",
        ))

    if max_terheles is not None and igeny > max_terheles:
        uzenetek.append(Uzenet(
            "figyelmeztetes",
            f"A halmozás nem megengedett: {igeny} szint esetén a legalsó egységre "
            f"{(igeny - 1) * cs.suly_kg:g} kg nehezedne, de a megengedett ráterhelés "
            f"csak {cs.max_raterheles_kg:g} kg – legfeljebb {max_terheles} szint biztonságos.",
        ))
    elif max_terheles is None and igeny > 1:
        uzenetek.append(Uzenet(
            "info",
            "A ráterhelhetőség nincs megadva, ezért a halmozás biztonsága tömeg "
            "szempontjából nem ellenőrzött.",
        ))

    if berakhato and alkalmazott < igeny:
        uzenetek.append(Uzenet(
            "figyelmeztetes",
            f"A kért {kert} szint nem valósítható meg biztonságosan – a számítás "
            f"{alkalmazott} szinttel készült.",
        ))

    helyek = math.ceil(cs.darab / alkalmazott)
    ldm_nelkul = cs.darab * alapterulet / pk.belso_szelesseg_m
    ldm = helyek * alapterulet / pk.belso_szelesseg_m

    elrendezes = tervez_elrendezes(cs.hossz_cm, cs.szelesseg_cm, helyek, pk, cs.forgathato)
    if elrendezes is None:
        berakhato = False
        forg = "" if cs.forgathato else " (forgatás nélkül)"
        uzenetek.append(Uzenet(
            "hiba",
            f"A rakomány alapterülete ({cs.hossz_cm:g} × {cs.szelesseg_cm:g} cm) nem fér el "
            f"a {pk.belso_hossz_m:g} × {pk.belso_szelesseg_m:g} m-es rakfelületen{forg}.",
        ))

    return CsoportEredmeny(
        csoport=cs,
        alapterulet_m2=alapterulet,
        ossz_suly_kg=cs.darab * cs.suly_kg,
        kert_szint=kert,
        alkalmazott_szint=alkalmazott,
        helyek=helyek,
        ldm_halmozas_nelkul=ldm_nelkul,
        ldm=ldm,
        halom_magassag_cm=min(alkalmazott, cs.darab) * cs.magassag_cm,
        elrendezes=elrendezes,
        berakhato=berakhato,
        uzenetek=uzenetek,
    )


def osszesit(eredmenyek: list[CsoportEredmeny], pk: Potkocsi) -> Osszesites:
    darab = sum(e.csoport.darab for e in eredmenyek)
    suly = sum(e.ossz_suly_kg for e in eredmenyek)
    helyek = sum(e.helyek for e in eredmenyek)
    ldm_nelkul = sum(e.ldm_halmozas_nelkul for e in eredmenyek)
    ldm = sum(e.ldm for e in eredmenyek)
    elr_hossz = sum(e.elrendezes_hossz_m or 0 for e in eredmenyek)
    megtakaritott = ldm_nelkul - ldm
    pct = megtakaritott / ldm_nelkul * 100 if ldm_nelkul > 0 else 0.0

    uzenetek: list[Uzenet] = []
    berakhato = all(e.berakhato for e in eredmenyek)

    if suly > pk.teherbiras_kg + EPS:
        berakhato = False
        uzenetek.append(Uzenet(
            "hiba",
            f"A rakomány tömege ({suly:,.0f} kg) túllépi a megadott hasznos teherbírást "
            f"({pk.teherbiras_kg:,.0f} kg).".replace(",", " "),
        ))
    if ldm > pk.belso_hossz_m + EPS:
        berakhato = False
        uzenetek.append(Uzenet(
            "hiba",
            f"Már az elméleti helyigény ({ldm:.2f} LDM) is meghaladja a pótkocsi "
            f"{pk.belso_hossz_m:g} m-es belső hosszát.",
        ))
    elif elr_hossz > pk.belso_hossz_m + EPS:
        berakhato = False
        uzenetek.append(Uzenet(
            "figyelmeztetes",
            f"Az elméleti {ldm:.2f} LDM alapján a rakomány beférne, de a soros rakodási "
            f"elrendezés {elr_hossz:.2f} m hosszt igényel – a tényleges berakhatóság "
            "nem igazolható, egyedi rakodási terv szükséges.",
        ))
    if eredmenyek and elr_hossz > ldm + 0.01 and elr_hossz <= pk.belso_hossz_m + EPS:
        uzenetek.append(Uzenet(
            "info",
            f"A rakodási elrendezés {elr_hossz - ldm:.2f} m-rel hosszabb az elméleti LDM-nél "
            "(nem teljes sorok, keresztirányú hézagok). Vegyes rakásnál a hiányos sorok "
            "esetenként összevonhatók.",
        ))

    return Osszesites(
        darab=darab,
        ossz_suly_kg=suly,
        helyek=helyek,
        ldm_halmozas_nelkul=ldm_nelkul,
        ldm=ldm,
        elrendezes_hossz_m=elr_hossz,
        megtakaritott_ldm=megtakaritott,
        megtakaritas_pct=pct,
        hossz_kihasznaltsag_pct=ldm / pk.belso_hossz_m * 100,
        suly_kihasznaltsag_pct=suly / pk.teherbiras_kg * 100,
        berakhato=berakhato,
        uzenetek=uzenetek,
    )


# ---------------------------------------------------------------------------
# Fuvardíj
# ---------------------------------------------------------------------------

def szamol_dij(p: DijParameterek) -> DijEredmeny:
    """Becsült fuvardíj és ajánlati ár.

    - Haszonkulcs: a beszerzési költségre vetített felár → ár = költség × (1 + h).
    - Árrés: az eladási árra vetített fedezet → ár = költség ÷ (1 − a).
    """
    for nev, ertek in (
        ("LDM", p.ldm), ("díj/LDM", p.dij_per_ldm), ("minimum díj", p.minimum_dij),
        ("útdíj", p.utdij), ("üzemanyag-pótdíj", p.uzemanyag_pct),
        ("várakozási idő", p.varakozas_ora), ("várakozási óradíj", p.varakozas_oradij),
        ("egyéb felár", p.egyeb_felar), ("százalék", p.szazalek),
    ):
        if ertek < 0:
            raise ValueError(f"A(z) {nev} nem lehet negatív.")
    if p.arazas_mod not in ("haszonkulcs", "arres"):
        raise ValueError("Ismeretlen árazási mód.")
    if p.arazas_mod == "arres" and p.szazalek >= 100:
        raise ValueError("Az árrés 100% alatt kell legyen (az árrés az eladási ár része).")

    ldm_dij = p.ldm * p.dij_per_ldm
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
