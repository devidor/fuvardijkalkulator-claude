"""A számítási logika tesztjei. Futtatás: python tests/test_kalkulacio.py (vagy pytest)."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kalkulacio import (  # noqa: E402
    DijParameterek,
    Potkocsi,
    RakomanyCsoport,
    osszesit,
    szamol_csoport,
    szamol_dij,
    tervez_elrendezes,
)

PK = Potkocsi()


def eur(darab, szint=1, mag=100.0, suly=300.0, raterheles=0.0, forgathato=True):
    return RakomanyCsoport("EUR", 120, 80, mag, darab, suly, szint, raterheles, forgathato)


def kozel(a, b):
    return math.isclose(a, b, abs_tol=1e-9)


def test_10_eur_2_szint():
    e = szamol_csoport(eur(10, szint=2), PK)
    assert e.helyek == 5
    assert kozel(e.ldm, 2.0)
    assert kozel(e.ldm_halmozas_nelkul, 4.0)


def test_vegyes_halmozas_3_2_ldm():
    e = [szamol_csoport(eur(8, szint=2), PK), szamol_csoport(eur(4), PK)]
    o = osszesit(e, PK)
    assert kozel(e[0].ldm, 1.6) and kozel(e[1].ldm, 1.6)
    assert kozel(o.ldm, 3.2)
    assert kozel(o.ldm_halmozas_nelkul, 4.8)
    assert kozel(o.megtakaritott_ldm, 1.6)
    assert math.isclose(o.megtakaritas_pct, 100 / 3)


def test_paratlan_darab_felfele_kerekit():
    assert szamol_csoport(eur(9, szint=2), PK).helyek == 5


def test_magassag_korlatozza_a_halmozast():
    e = szamol_csoport(eur(10, szint=2, mag=150), PK)  # 2 × 150 > 270 cm
    assert e.alkalmazott_szint == 1
    assert e.helyek == 10
    assert any(u.szint == "figyelmeztetes" for u in e.uzenetek)


def test_raterheles_korlatozza_a_halmozast():
    e = szamol_csoport(eur(9, szint=3, mag=80, suly=500, raterheles=600), PK)  # 1 + 600//500 = 2
    assert e.alkalmazott_szint == 2
    assert e.helyek == 5


def test_tul_magas_egyseg():
    e = szamol_csoport(eur(1, mag=300), PK)
    assert not e.berakhato
    assert any(u.szint == "hiba" for u in e.uzenetek)


def test_nem_fer_el():
    e = szamol_csoport(RakomanyCsoport("Gép", 300, 260, 100, 1, 1000), PK)
    assert e.elrendezes is None and not e.berakhato


def test_elrendezes_33_eur_es_26_ipari():
    assert kozel(tervez_elrendezes(120, 80, 33, PK).hossz_m, 13.2)
    assert kozel(tervez_elrendezes(120, 100, 26, PK).hossz_m, 13.0)


def test_elrendezes_forgatas_nelkul_hosszabb():
    assert kozel(tervez_elrendezes(120, 80, 4, PK, forgathato=True).hossz_m, 1.6)
    assert kozel(tervez_elrendezes(120, 80, 4, PK, forgathato=False).hossz_m, 2.4)


def test_teherbiras_tullepes():
    o = osszesit([szamol_csoport(eur(30, suly=1000), PK)], PK)
    assert not o.berakhato
    assert any("teherbírás" in u.szoveg for u in o.uzenetek)


def test_elmeleti_befer_de_elrendezes_nem():
    # 27 ipari raklap: 13,5 LDM elméletben befér, de soronként csak 2 fér el → 14 sor × 1,0 m.
    ipari = RakomanyCsoport("Ipari", 120, 100, 100, 27, 100)
    o = osszesit([szamol_csoport(ipari, PK)], PK)
    assert kozel(o.ldm, 13.5)
    assert kozel(o.elrendezes_hossz_m, 14.0)
    assert not o.berakhato


def test_haszonkulcs_es_arres():
    hk = szamol_dij(DijParameterek(ldm=2, dij_per_ldm=500, arazas_mod="haszonkulcs", szazalek=25))
    assert kozel(hk.beszerzesi_koltseg, 1000) and kozel(hk.ajanlott_ar, 1250)
    assert kozel(hk.fedezeti_hanyad_pct, 20) and kozel(hk.haszonkulcs_pct, 25)
    ar = szamol_dij(DijParameterek(ldm=2, dij_per_ldm=500, arazas_mod="arres", szazalek=20))
    assert kozel(ar.ajanlott_ar, 1250) and kozel(ar.fedezeti_hanyad_pct, 20)


def test_felarak_es_minimumdij():
    d = szamol_dij(DijParameterek(
        ldm=1, dij_per_ldm=300, minimum_dij=500, utdij=50, uzemanyag_pct=10,
        varakozas_ora=2, varakozas_oradij=25, egyeb_felar=10,
    ))
    assert d.minimum_alkalmazva and kozel(d.alapdij, 500)
    assert kozel(d.felarak_osszesen, 50 + 50 + 50 + 10)
    assert kozel(d.beszerzesi_koltseg, 660)


def test_hibas_adatok():
    for rossz in (eur(0), eur(1, suly=0), eur(1, szint=0)):
        try:
            szamol_csoport(rossz, PK)
        except ValueError:
            continue
        raise AssertionError("ValueError várt")
    try:
        szamol_dij(DijParameterek(ldm=1, dij_per_ldm=1, arazas_mod="arres", szazalek=100))
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError várt")


if __name__ == "__main__":
    tesztek = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for t in tesztek:
        t()
        print(f"OK  {t.__name__}")
    print(f"\n{len(tesztek)} teszt sikeres.")
