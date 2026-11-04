"""Rakodási terv összeállítása: halmozás → elhelyezés → LDM-ek → figyelmeztetések."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from billing_config import ElszamolasiKonfig
from cargo_models import RakomanyCsoport, Uzenet, hu, validal_csoport
from ldm_calculator import ElszamolasEredmeny, elmeleti_ldm, elszamolasi_ldm, fizikai_ldm
from packing_optimizer import PakolasEredmeny, Tetel, elfer_egyseg, optimalizal
from stacking_validator import NEM_RAKHATO, HalmozasEredmeny, ellenoriz_halmozast
from trailer_config import Potkocsi, validal_potkocsi

Pakolo = Callable[[list[Tetel], float, float, float], PakolasEredmeny]


@dataclass
class CsoportTerv:
    index: int
    csoport: RakomanyCsoport
    halmozas: HalmozasEredmeny
    elmeleti_ldm_nelkul: float
    elmeleti_ldm: float
    berakhato: bool
    uzenetek: list[Uzenet] = field(default_factory=list)


@dataclass
class RakodasiTerv:
    potkocsi: Potkocsi
    csoportok: list[CsoportTerv]
    pakolas: PakolasEredmeny
    elszamolas: ElszamolasEredmeny
    halmok: dict[int, int]  # elhelyezés sorszáma → egymásra helyezett egységek száma
    berakhato: bool
    uzenetek: list[Uzenet] = field(default_factory=list)
    feltetelezesek: list[str] = field(default_factory=list)

    @property
    def darab(self) -> int:
        return sum(c.csoport.darab for c in self.csoportok)

    @property
    def ossz_suly_kg(self) -> float:
        return sum(c.csoport.ossz_suly_kg for c in self.csoportok)

    @property
    def helyek(self) -> int:
        return sum(c.halmozas.helyek for c in self.csoportok)

    @property
    def elmeleti_ldm_nelkul(self) -> float:
        return sum(c.elmeleti_ldm_nelkul for c in self.csoportok)

    @property
    def elmeleti_ldm(self) -> float:
        return sum(c.elmeleti_ldm for c in self.csoportok)

    @property
    def fizikai_ldm(self) -> float:
        return self.elszamolas.fizikai_ldm

    @property
    def megtakaritott_ldm(self) -> float:
        return self.elmeleti_ldm_nelkul - self.elmeleti_ldm

    @property
    def megtakaritas_pct(self) -> float:
        return self.megtakaritott_ldm / self.elmeleti_ldm_nelkul * 100 if self.elmeleti_ldm_nelkul else 0.0

    @property
    def hossz_kihasznaltsag_pct(self) -> float:
        return self.pakolas.hasznalt_hossz_cm / self.potkocsi.rakter_hossz_cm * 100

    @property
    def suly_kihasznaltsag_pct(self) -> float:
        return self.ossz_suly_kg / self.potkocsi.teherbiras_kg * 100


def tervez(
    csoportok: list[RakomanyCsoport],
    pk: Potkocsi,
    cfg: ElszamolasiKonfig = ElszamolasiKonfig(),
    idokorlat_s: float = 2.0,
    pakolo: Optional[Pakolo] = None,
) -> RakodasiTerv:
    hibak = validal_potkocsi(pk) + [h for cs in csoportok for h in validal_csoport(cs)]
    if hibak:
        raise ValueError(" ".join(hibak))
    pakolo = pakolo or optimalizal

    tervek: list[CsoportTerv] = []
    tetelek: list[Tetel] = []
    feltetelezesek: list[str] = []
    for i, cs in enumerate(csoportok):
        halm = ellenoriz_halmozast(cs, pk.rakter_magassag_cm)
        uzenetek = list(halm.uzenetek)
        berakhato = halm.statusz != NEM_RAKHATO
        if not elfer_egyseg(cs.hossz_cm, cs.szelesseg_cm, cs.forgathato, pk.rakter_hossz_cm, pk.rakter_szelesseg_cm):
            berakhato = False
            forg = "" if cs.forgathato else " (forgatás nélkül)"
            uzenetek.append(Uzenet(
                "hiba",
                f"Az egység alapterülete ({cs.hossz_cm:g} × {cs.szelesseg_cm:g} cm) nem fér el a "
                f"{pk.rakter_hossz_cm:g} × {pk.rakter_szelesseg_cm:g} cm-es rakodótéren{forg}.",
            ))
        if berakhato:
            tetelek.append(Tetel(i, cs.hossz_cm, cs.szelesseg_cm, cs.forgathato, halm.helyek))
        else:
            uzenetek.append(Uzenet("hiba", "Ez a csoport kimaradt a rakodási tervből."))
        feltetelezesek += halm.feltetelezesek
        tervek.append(CsoportTerv(
            index=i,
            csoport=cs,
            halmozas=halm,
            elmeleti_ldm_nelkul=elmeleti_ldm(cs.darab, cs.hossz_cm, cs.szelesseg_cm, pk.szelesseg_cm),
            elmeleti_ldm=elmeleti_ldm(halm.helyek, cs.hossz_cm, cs.szelesseg_cm, pk.szelesseg_cm),
            berakhato=berakhato,
            uzenetek=uzenetek,
        ))

    pakolas = pakolo(tetelek, pk.rakter_hossz_cm, pk.rakter_szelesseg_cm, idokorlat_s)

    halmok: dict[int, int] = {}
    for t in tervek:
        sajat = [e for e in pakolas.elhelyezesek if e.csoport == t.index]
        for e, db in zip(sajat, t.halmozas.egysegek_helyenkent(t.csoport.darab)):
            halmok[e.sorszam] = db

    ossz_suly = sum(cs.ossz_suly_kg for cs in csoportok)
    elszamolas = elszamolasi_ldm(fizikai_ldm(pakolas.hasznalt_hossz_cm), ossz_suly, cfg)
    elmeleti = sum(t.elmeleti_ldm for t in tervek if t.berakhato)

    uzenetek: list[Uzenet] = []
    berakhato = all(t.berakhato for t in tervek)
    if ossz_suly > pk.teherbiras_kg:
        berakhato = False
        uzenetek.append(Uzenet(
            "hiba",
            f"A rakomány tömege ({hu(ossz_suly, 0)} kg) túllépi a megadott hasznos teherbírást "
            f"({hu(pk.teherbiras_kg, 0)} kg).",
        ))
    if not pakolas.belefer:
        berakhato = False
        uzenetek.append(Uzenet(
            "hiba",
            f"A rakodási terv {pakolas.hasznalt_hossz_cm:g} cm hosszt igényel, a rakodótér csak "
            f"{pk.rakter_hossz_cm:g} cm – a rakomány nem fér el.",
        ))
    if not pakolas.bizonyitott:
        uzenetek.append(Uzenet(
            "figyelmeztetes",
            f"Az elrendezés közelítő megoldás: {pakolas.hasznalt_hossz_cm:g} cm. Az igazolt alsó korlát "
            f"{pakolas.also_korlat_cm:g} cm, tehát a fizikai LDM legfeljebb "
            f"{hu((pakolas.hasznalt_hossz_cm - pakolas.also_korlat_cm) / 100)}-dal lehet kisebb. "
            "Ez nem bizonyított optimum.",
        ))
    if pakolas.elhelyezesek and elszamolas.fizikai_ldm - elmeleti > 0.005:
        uzenetek.append(Uzenet(
            "info",
            f"Az elméleti {hu(elmeleti)} LDM csak területalapú alsó becslés; a fizikailag megvalósítható "
            f"elrendezés {hu(elszamolas.fizikai_ldm)} LDM-et igényel.",
        ))
    if elszamolas.meghatarozo == "tömeg":
        uzenetek.append(Uzenet(
            "info",
            f"Az elszámolási LDM-et a tömeg határozza meg ({hu(ossz_suly, 0)} kg ÷ {cfg.kg_per_ldm:g} kg/LDM = "
            f"{hu(elszamolas.tomegalapu_ldm)} LDM > {hu(elszamolas.fizikai_ldm)} fizikai LDM).",
        ))

    alap = [
        f"Rakodótér: {pk.rakter_hossz_cm:g} × {pk.rakter_szelesseg_cm:g} × {pk.rakter_magassag_cm:g} cm "
        f"({pk.tipus}{', a névlegestől eltérő szabad méretekkel' if pk.eltero_szabad_rakter else ''}); "
        "feltételezés, hogy ez a terület akadálymentesen használható.",
        "Az egységek tengelyekkel párhuzamosan, legfeljebb 90°-kal elforgatva, átfedés nélkül állnak; "
        "a koordináták a homlokfaltól (x) és a bal oldalfaltól (y) értendők.",
        "A tengelyterhelés, a rakományrögzítés és a rakodási sorrend nincs modellezve.",
        "A szabad területek nem feltétlenül alkalmasak más rakomány fogadására (alak, hozzáférhetőség).",
        "Egyetlen megbízó rakománya; más megbízók árujának együttes elhelyezése nincs vizsgálva.",
        f"Elszámolási index: 1 LDM = {cfg.kg_per_ldm:g} kg (díjszámítási tömegegyenérték, nem a jármű "
        f"terhelhetősége); kerekítés: {cfg.kerekites.lower()}.",
    ]

    return RakodasiTerv(
        potkocsi=pk,
        csoportok=tervek,
        pakolas=pakolas,
        elszamolas=elszamolas,
        halmok=halmok,
        berakhato=berakhato,
        uzenetek=uzenetek,
        feltetelezesek=alap + feltetelezesek,
    )
