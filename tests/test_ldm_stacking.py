"""LDM-számítás, tömegalapú elszámolás, halmozási korlátok, pótkocsitípusok, követés, díj."""

import pytest

from billing_config import ElszamolasiKonfig
from cargo_models import RakomanyCsoport, validal_csoport
from ldm_calculator import elmeleti_ldm, elszamolasi_ldm, kerekit
from ldm_tracking import ELUTASITVA, NINCS_ELKULDVE, VISSZAIGAZOLVA, LdmKovetes, elemzes
from load_planner import tervez
from pricing import DijParameterek, szamol_dij
from stacking_validator import ELLENORZOTT, NEM_HALMOZOTT, NEM_IGAZOLT, NEM_RAKHATO, ellenoriz_halmozast
from trailer_config import POTKOCSI_TIPUSOK, Potkocsi, validal_potkocsi

PK = Potkocsi.tipusbol("Normál")


def eur(darab, mag=220, suly=600.0, szint=1, raterheles=None, **kw):
    return RakomanyCsoport("EUR", 120, 80, mag, darab, suly, max_szint=szint, raterheles_kg=raterheles, **kw)


# --- Pótkocsi -----------------------------------------------------------------

def test_potkocsitipusok_meretei_cm_ben():
    assert [(t.hossz_cm, t.szelesseg_cm, t.magassag_cm) for t in POTKOCSI_TIPUSOK.values()] == [
        (1360, 245, 270), (1360, 245, 285), (1360, 245, 300),
    ]
    mega = Potkocsi.tipusbol("Mega")
    assert mega.rakter_magassag_cm == 300 and not mega.eltero_szabad_rakter


def test_szabad_rakter_felulirja_a_nevlegest():
    pk = Potkocsi.tipusbol("Normál")
    pk.szabad_hossz_cm = 1300
    assert pk.rakter_hossz_cm == 1300 and pk.eltero_szabad_rakter
    pk.szabad_szelesseg_cm = 260
    assert validal_potkocsi(pk)


# --- LDM ----------------------------------------------------------------------

def test_elmeleti_ldm_kepletek():
    assert elmeleti_ldm(4, 140, 100) == pytest.approx(2.2857, abs=1e-4)
    assert elmeleti_ldm(7, 70, 100) == pytest.approx(2.0)
    assert elmeleti_ldm(1, 120, 80) == pytest.approx(9600 / 24500)


@pytest.mark.parametrize("suly, varhato_ldm, varhato_kg", [(3000, 2.00, 3500), (7000, 4.00, 7000)])
def test_dijpeldak_5_eur_raklap(suly, varhato_ldm, varhato_kg):
    t = tervez([eur(5, suly=suly / 5)], PK)
    assert t.fizikai_ldm == pytest.approx(2.00)
    assert t.elszamolas.elszamolasi_ldm == pytest.approx(varhato_ldm)
    assert t.elszamolas.tomegegyenertek_kg == pytest.approx(varhato_kg)


def test_tomegalapu_ldm_es_meghatarozo():
    e = elszamolasi_ldm(2.0, 7000, ElszamolasiKonfig())
    assert e.tomegalapu_ldm == pytest.approx(4.0) and e.meghatarozo == "tömeg"
    e = elszamolasi_ldm(2.0, 3000, ElszamolasiKonfig())
    assert e.meghatarozo == "fizikai"


def test_modosithato_index_es_kerekites():
    e = elszamolasi_ldm(1.0, 3000, ElszamolasiKonfig(kg_per_ldm=1500))
    assert e.elszamolasi_ldm == pytest.approx(2.0)
    assert kerekit(2.2857, "Felfelé 0,1 LDM-re") == pytest.approx(2.3)
    assert kerekit(2.0000000001, "Felfelé 0,1 LDM-re") == pytest.approx(2.0)
    assert kerekit(2.21, "Felfelé 0,25 LDM-re") == pytest.approx(2.25)
    assert kerekit(2.24, "Matematikai kerekítés 0,1 LDM-re") == pytest.approx(2.2)
    assert kerekit(2.2857, "Nincs kerekítés") == pytest.approx(2.2857)
    with pytest.raises(ValueError):
        ElszamolasiKonfig(kg_per_ldm=0)


def test_a_pelda_tervben():
    t = tervez([RakomanyCsoport("A", 140, 100, 200, 4, 500)], PK)
    assert t.elmeleti_ldm == pytest.approx(2.2857, abs=1e-4)
    assert t.fizikai_ldm == pytest.approx(2.40)
    assert t.elszamolas.tomegalapu_ldm == pytest.approx(2000 / 1750)
    assert t.elszamolas.elszamolasi_ldm == pytest.approx(2.40)
    assert t.berakhato


def test_b_pelda_tervben():
    t = tervez([RakomanyCsoport("B", 70, 100, 120, 7, 350)], PK)
    assert t.elmeleti_ldm == pytest.approx(2.0)
    assert t.fizikai_ldm == pytest.approx(2.10)


def test_vegyes_halmozas_ket_csoporttal():
    t = tervez([eur(8, mag=120, suly=350, szint=2, raterheles=800), eur(4, mag=180)], PK)
    assert [c.halmozas.helyek for c in t.csoportok] == [4, 4]
    assert t.elmeleti_ldm == pytest.approx(8 * 9600 / 24500)
    assert t.fizikai_ldm == pytest.approx(3.2)
    assert sorted(t.halmok.values()) == [1, 1, 1, 1, 2, 2, 2, 2]


def test_teherbiras_tullepese():
    t = tervez([eur(20, suly=1500)], PK)
    assert not t.berakhato
    assert any("teherbírást" in u.szoveg for u in t.uzenetek)


# --- Halmozás -----------------------------------------------------------------

def test_halommagassag_korlatozza_a_szintet():
    h = ellenoriz_halmozast(eur(10, mag=150, szint=2, raterheles=1000), 270)
    assert h.alkalmazott_szint == 1 and h.helyek == 10
    assert ellenoriz_halmozast(eur(10, mag=150, szint=2, raterheles=1000), 300).alkalmazott_szint == 2


def test_raterheles_korlatozza_a_szintet():
    h = ellenoriz_halmozast(eur(9, mag=80, suly=500, szint=3, raterheles=600), 270)
    assert h.alkalmazott_szint == 2 and h.helyek == 5 and h.statusz == ELLENORZOTT


def test_hianyzo_terhelhetoseg_nem_igazolt():
    h = ellenoriz_halmozast(eur(10, mag=120, szint=2), 270)
    assert h.statusz == NEM_IGAZOLT and h.helyek == 5
    assert any(u.szint == "figyelmeztetes" and "nem igazolt" in u.szoveg for u in h.uzenetek)


def test_nem_halmozhato_es_tul_magas():
    assert ellenoriz_halmozast(eur(3), 270).statusz == NEM_HALMOZOTT
    h = ellenoriz_halmozast(eur(1, mag=290), 270)
    assert h.statusz == NEM_RAKHATO and any(u.szint == "hiba" for u in h.uzenetek)
    assert ellenoriz_halmozast(eur(1, mag=290), 300).statusz == NEM_HALMOZOTT


def test_tulnyulas_mellett_a_halmozas_nem_igazolt():
    cs = RakomanyCsoport("Túl", 130, 80, 100, 4, 300, max_szint=2, raterheles_kg=1000, raklap_meret_cm=(120, 80))
    h = ellenoriz_halmozast(cs, 270)
    assert cs.tulnyulas_cm == 10 and h.statusz == NEM_IGAZOLT


def test_valtakozo_tajolas_nem_helytakarekos_es_nem_automatikusan_biztonsagos():
    h = ellenoriz_halmozast(eur(4, mag=100, szint=2, raterheles=1000, valtakozo_tajolas=True), 270)
    v = h.valtakozo
    assert v.alatamasztas_pct == pytest.approx(80 * 80 / (120 * 80) * 100)
    assert v.tulnyulas_cm == 20 and v.terulet_novekedes_pct == pytest.approx(50)
    assert any("nem tekinthető automatikusan biztonságosnak" in u.szoveg for u in h.uzenetek)
    negyzet = RakomanyCsoport("N", 100, 100, 100, 4, 300, max_szint=2, raterheles_kg=1000, valtakozo_tajolas=True)
    assert ellenoriz_halmozast(negyzet, 270).valtakozo.negyzetes


def test_hibas_bemenetek():
    assert validal_csoport(eur(0))
    assert validal_csoport(eur(1, suly=0))
    assert validal_csoport(eur(1, szint=0))
    with pytest.raises(ValueError):
        tervez([eur(0)], PK)


# --- Tervezett / visszaigazolt / tényleges --------------------------------------

def test_tervezett_ldm_nem_garantalt_es_a_tenyleges_nem_irja_felul_a_dijat():
    k = LdmKovetes(2.4, 2.4, allapot=NINCS_ELKULDVE, tenyleges_ldm=2.8, elteres_indoka="Rögzítés miatt")
    assert k.elszamolasi_alap[0] == 2.4
    szovegek = " ".join(u.szoveg for u in elemzes(k))
    assert "nem garantált" in szovegek and "nem módosul automatikusan" in szovegek and "Rögzítés" in szovegek
    v = LdmKovetes(2.4, 2.4, allapot=VISSZAIGAZOLVA, visszaigazolt_ldm=2.5, tenyleges_ldm=2.8)
    assert v.elszamolasi_alap == (2.5, "fuvarozó által visszaigazolt LDM")
    assert v.visszaigazolt_elteres == pytest.approx(0.1)
    assert v.tenyleges_elteres == pytest.approx(0.3)
    assert any(u.szint == "hiba" for u in elemzes(LdmKovetes(2.4, 2.4, allapot=ELUTASITVA)))


# --- Díj (változatlan funkció) ---------------------------------------------------

def test_haszonkulcs_es_arres():
    hk = szamol_dij(DijParameterek(ldm=2, dij_per_ldm=500, arazas_mod="haszonkulcs", szazalek=25))
    assert hk.ajanlott_ar == pytest.approx(1250) and hk.fedezeti_hanyad_pct == pytest.approx(20)
    ar = szamol_dij(DijParameterek(ldm=2, dij_per_ldm=500, arazas_mod="arres", szazalek=20))
    assert ar.ajanlott_ar == pytest.approx(1250)
