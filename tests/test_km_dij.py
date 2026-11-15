"""Km-alapú FTL/LTL díj, díjtáblák, fix profit és Google-távolság (hálózat nélkül)."""

import io
import json
import urllib.error

import pytest

import distance as tav
import freight_pricing as fp
import rate_tables as rt
from pricing import DijParameterek, szamol_dij


# --- Km-kerekítés (Daniel: 216 km → 300 km) --------------------------------------------

@pytest.mark.parametrize("km, vart", [(216, 300), (201, 300), (300, 300), (300.4, 400), (40, 100), (1, 100), (1234, 1300)])
def test_km_felfele_kerekul_100_ra(km, vart):
    assert fp.kerekitett_km(km) == vart


def test_nulla_km_hiba():
    with pytest.raises(ValueError):
        fp.kerekitett_km(0)


# --- Viszonylat és €/km javaslat --------------------------------------------------------

@pytest.mark.parametrize("fel, le, vart", [
    ("HU", "AT", 2.0), ("SK", "HU", 2.0), ("HU", "PL", 1.5), ("PL", "HU", 2.0),
    ("HU", "DE", 1.6), ("IT", "HU", 1.8), ("HU", "FR", 1.8), ("FR", "HU", 1.6),
    ("HU", "PT", 1.3), ("EE", "HU", 1.3),
])
def test_javasolt_eur_per_km_daniel_tablaja(fel, le, vart):
    assert rt.javasolt_eur_per_km(rt.viszonylat(fel, le)) == vart


@pytest.mark.parametrize("fel, le, irany", [("HU", "HU", rt.BELFOLD), ("AT", "DE", rt.HARMADIK)])
def test_nincs_tablas_dij_belfoldre_es_harmadik_orszagra(fel, le, irany):
    v = rt.viszonylat(fel, le)
    assert v.irany == irany and rt.javasolt_eur_per_km(v) is None


def test_egyedi_dijas_es_tiltott_orszagok():
    for kod in ("GB", "IE", "CH", "DK", "SE", "NO", "FI", "GR", "MD", "AL", "BIH", "SRB", "MNE", "UA", "TR", "GE", "AZ", "AM"):
        v = rt.viszonylat("HU", kod)
        assert v.egyedi and rt.javasolt_eur_per_km(v) is None, kod
    assert rt.viszonylat("HU", "RU").tiltott and rt.viszonylat("BY", "HU").tiltott
    with pytest.raises(fp.KmDijHiba, match="szankciók"):
        fp.szamol_km_dij("HU", "RU", km=1000, eur_per_km=2.0)


def test_orszagkod_normalizalas():
    assert rt.normalizal_orszagkod("de") == "DE"
    assert rt.normalizal_orszagkod("RS") == "SRB"
    assert rt.normalizal_orszagkod("UK") == "GB"
    assert rt.normalizal_orszagkod("XX") is None and rt.normalizal_orszagkod(None) is None


# --- LTL-szorzótábla --------------------------------------------------------------------

def test_szorzotabla_teljes_es_12_1_ldm_tol_1():
    assert sorted(rt.LTL_SZORZOK) == list(range(1, 137))
    assert rt.LTL_SZORZOK[1] == (0.195, 0.13, 0.117, 0.104)
    assert rt.LTL_SZORZOK[20] == (0.45, 0.3, 0.27, 0.24)
    assert rt.LTL_SZORZOK[120] == (0.9915, 0.9915, 0.981585, 0.9766275)
    assert all(rt.LTL_SZORZOK[t] == (1.0, 1.0, 1.0, 1.0) for t in range(121, 137))


@pytest.mark.parametrize("ldm, vart", [(2.33, 2.4), (2.0, 2.0), (2.04, 2.1), (0.01, 0.1), (1.71, 1.8)])
def test_dijszamitasi_ldm_felfele_0_1_re(ldm, vart):
    assert rt.dijszamitasi_ldm(ldm) == vart


def test_ltl_csoportok():
    assert rt.ltl_csoport(rt.viszonylat("HU", "AT")) == 0
    assert rt.ltl_csoport(rt.viszonylat("PL", "HU")) == 1
    assert rt.ltl_csoport(rt.viszonylat("HU", "FR")) == 1
    assert rt.ltl_csoport(rt.viszonylat("HU", "LV")) == 2
    assert rt.ltl_csoport(rt.viszonylat("HU", "PT")) == 3
    assert rt.ltl_csoport(rt.viszonylat("HU", "HU")) is None


def test_gyanus_szorzok_jelzik_a_nem_novekvo_ertekeket():
    gyanus = {(ldm, cs) for ldm, cs, _, _ in rt.gyanus_szorzok()}
    assert (7.2, 0) in gyanus and (8.8, 0) in gyanus and (11.5, 0) in gyanus
    assert (1.3, 3) in gyanus  # 1,2 és 1,3 ldm egyaránt 0,18
    assert all(cs != 1 for _, cs in gyanus)  # a 2. csoport monoton


# --- Km-alapú díj -------------------------------------------------------------------------

def test_ftl_dij_216_km_ausztriaba():
    e = fp.szamol_km_dij("HU", "AT", km=216, eur_per_km=2.0, szolgaltatas=fp.SZOLG_FTL)
    assert e.km_kerekitett == 300 and e.ftl_dij == 600 and e.alapdij == 600 and e.szorzo is None


def test_ltl_dij_2_ldm_ausztriaba():
    e = fp.szamol_km_dij("HU", "AT", km=216, eur_per_km=2.0, ldm=2.0)
    assert e.szolgaltatas == fp.SZOLG_LTL and e.szorzo == 0.45
    assert e.alapdij == pytest.approx(270.0)


def test_ltl_suly_alapu_4_ldm_nemetorszagba():
    # Daniel 2. példája: 7000 kg → 4 ldm (díjszámítási alapindex)
    e = fp.szamol_km_dij("HU", "DE", km=850, eur_per_km=1.6, ldm=7000 / 1750)
    assert e.km_kerekitett == 900 and e.dijszamitasi_ldm == 4.0 and e.szorzo == 0.466
    assert e.alapdij == pytest.approx(900 * 1.6 * 0.466)


def test_automatikus_mod_12_1_ldm_felett_ftl():
    e = fp.szamol_km_dij("HU", "AT", km=300, eur_per_km=2.0, ldm=12.5)
    assert e.szolgaltatas == fp.SZOLG_FTL and e.alapdij == 600 and e.megjegyzesek


def test_ltl_csoport_nelkul_hiba_de_kezzel_valaszthato():
    with pytest.raises(fp.KmDijHiba, match="szorzócsoport"):
        fp.szamol_km_dij("AT", "DE", km=500, eur_per_km=1.8, ldm=2.0)
    e = fp.szamol_km_dij("AT", "DE", km=500, eur_per_km=1.8, ldm=2.0, csoport_felulir=1)
    assert e.szorzo == 0.3 and e.alapdij == pytest.approx(500 * 1.8 * 0.3)


def test_ldm_nelkul_auto_ftl_ltl_hiba():
    assert fp.szamol_km_dij("HU", "AT", km=216, eur_per_km=2.0).szolgaltatas == fp.SZOLG_FTL
    with pytest.raises(fp.KmDijHiba):
        fp.szamol_km_dij("HU", "AT", km=216, eur_per_km=2.0, szolgaltatas=fp.SZOLG_LTL)


# --- Profit és total díj --------------------------------------------------------------------

def test_fix_profit_es_kulso_alapdij():
    d = szamol_dij(DijParameterek(ldm=0, dij_per_ldm=0, kulso_alapdij=600, arazas_mod="fix", fix_profit=150))
    assert d.alapdij == 600 and d.beszerzesi_koltseg == 600 and d.ajanlott_ar == 750 and d.fedezet == 150


def test_kulso_alapdij_minimummal_es_haszonkulccsal():
    d = szamol_dij(DijParameterek(ldm=0, dij_per_ldm=0, kulso_alapdij=270, minimum_dij=300,
                                  arazas_mod="haszonkulcs", szazalek=20))
    assert d.minimum_alkalmazva and d.alapdij == 300 and d.ajanlott_ar == pytest.approx(360)


def test_regi_ldm_alapu_szamitas_valtozatlan():
    d = szamol_dij(DijParameterek(ldm=2.0, dij_per_ldm=450, arazas_mod="arres", szazalek=20))
    assert d.alapdij == 900 and d.ajanlott_ar == pytest.approx(1125)


# --- Google-távolság (hálózat nélkül, mockolt válasszal) -------------------------------------

class _Valasz(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_google_tavolsag_feldolgozasa():
    kuldott = {}

    def urlopen(keres, timeout):
        kuldott["fejlec"] = dict(keres.header_items())
        kuldott["torzs"] = json.loads(keres.data)
        return _Valasz(json.dumps({"routes": [{"distanceMeters": 216400, "duration": "8100s"}]}).encode())

    t = tav.google_tavolsag("8000 Székesfehérvár, Magyarország", "1230 Bécs, Ausztria", "teszt-kulcs", _urlopen=urlopen)
    assert t.km == pytest.approx(216.4) and t.ido_perc == pytest.approx(135)
    assert kuldott["torzs"]["origin"]["address"].startswith("8000")
    assert kuldott["fejlec"]["X-goog-api-key"] == "teszt-kulcs"


def test_google_hiba_es_ures_valasz():
    def ures(keres, timeout):
        return _Valasz(b"{}")

    with pytest.raises(tav.TavolsagHiba, match="nem talált"):
        tav.google_tavolsag("a", "b", "k", _urlopen=ures)

    def http_hiba(keres, timeout):
        raise urllib.error.HTTPError(keres.full_url, 403, "Forbidden", {},
                                     io.BytesIO(b'{"error": {"message": "API key not valid"}}'))

    with pytest.raises(tav.TavolsagHiba, match="403.*API key not valid"):
        tav.google_tavolsag("a", "b", "k", _urlopen=http_hiba)


def test_cim_es_link():
    assert tav.cim_szoveg("HU", "8000", "Székesfehérvár") == "8000 Székesfehérvár, Magyarország"
    assert tav.cim_szoveg("AT") == "Ausztria"
    assert tav.utvonal_link("a b", "c").startswith("https://www.google.com/maps/dir/?api=1&origin=a+b")
