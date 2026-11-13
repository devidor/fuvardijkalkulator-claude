"""E-mail-feldolgozás: séma, mintalevelek, AI-hívás (mockolva), teszt üzemmód, gyorsítótár."""

import pytest

import email_extraction as ee
from email_schema import Bizonyossag, FuvarIgenyAdat, KinyertMezo, hianyzo_es_bizonytalan_mezok
from email_samples import BUDAPEST_MUNCHEN, GYOR_HAMBURG, minta_adat, talalt_minta


# --- séma ---------------------------------------------------------------------

def test_kinyert_mezo_hianyzo_es_ismert():
    assert KinyertMezo.ures().ismert is False
    assert KinyertMezo.from_dict(None).bizonyossag == Bizonyossag.HIANYZIK
    assert KinyertMezo.from_dict({"ertek": None, "bizonyossag": "biztos"}).bizonyossag == Bizonyossag.HIANYZIK
    m = KinyertMezo.from_dict({"ertek": "Budapest", "bizonyossag": "biztos"})
    assert m.ismert and m.ertek == "Budapest"
    # ismeretlen bizonyossag-érték -> biztonságosan hiányzóként kezeljük
    assert KinyertMezo.from_dict({"ertek": "x", "bizonyossag": "???"}).bizonyossag == Bizonyossag.HIANYZIK


def test_tetel_ossztomeg_es_alapadatok():
    t = minta_adat(BUDAPEST_MUNCHEN).tetelek[0]
    assert t.alapadatok_ismertek
    assert t.ossztomeg_kg == pytest.approx(3000)
    ures = FuvarIgenyAdat.from_dict({}).tetelek
    assert ures == []


# --- mintalevelek ---------------------------------------------------------------

def test_budapest_muncheni_pelda_megfelel_a_prompt_elvarasainak():
    adat = minta_adat(BUDAPEST_MUNCHEN)
    t = adat.tetelek
    assert len(t) == 1
    assert (t[0].darab.ertek, t[0].hossz_cm.ertek, t[0].szelesseg_cm.ertek,
            t[0].magassag_cm.ertek, t[0].suly_kg.ertek) == (6, 120, 80, 150, 500)
    assert t[0].ossztomeg_kg == pytest.approx(3000)
    assert t[0].halmozhato.ertek is False
    assert adat.felrakas_hely.ertek == "Budapest"
    assert adat.lerakas_hely.ertek == "München"
    assert adat.felrakas_datum.ertek == "2026-11-18"

    hianyzik, _ = hianyzo_es_bizonytalan_mezok(adat)
    for cimke in ("felrakási cím", "lerakási cím", "lerakási időpont"):
        assert any(cimke in h for h in hianyzik), cimke


def test_gyor_hamburg_pelda_ket_tetel_es_osszsulybol_szamolt_egysegsuly():
    adat = minta_adat(GYOR_HAMBURG)
    assert len(adat.tetelek) == 2
    doboz = adat.tetelek[1]
    assert doboz.darab.ertek == 3 and doboz.suly_kg.ertek == pytest.approx(600)
    assert doboz.ossztomeg_kg == pytest.approx(1800)
    assert adat.felrakas_datum.bizonyossag == Bizonyossag.BIZONYTALAN


def test_talalt_minta_pontos_es_whitespace_toleralo_egyezes():
    assert talalt_minta(BUDAPEST_MUNCHEN.szoveg) is BUDAPEST_MUNCHEN
    assert talalt_minta("  " + BUDAPEST_MUNCHEN.szoveg.replace("\n\n", "\n") + "  ") is BUDAPEST_MUNCHEN
    assert talalt_minta("Ez egy teljesen más levél, Szegedről Pécsre.") is None


# --- séma a Claude eszközhíváshoz -----------------------------------------------

def test_eszkoz_sema_tetel_mezosorrendje():
    kotelezo = ee._TETEL_SEMA["required"]
    assert kotelezo == ["nev", "darab", "hossz_cm", "szelesseg_cm", "magassag_cm", "suly_kg", "halmozhato", "halmozasi_szint"]
    assert "tetelek" in ee.FUVARIGENY_ESZKOZ["input_schema"]["properties"]


# --- api_kulcs_elerheto ---------------------------------------------------------

def test_api_kulcs_elerheto_sorrendje(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert ee.api_kulcs_elerheto() is None
    assert ee.api_kulcs_elerheto("explicit-kulcs") == "explicit-kulcs"
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-kulcs")
    assert ee.api_kulcs_elerheto() == "env-kulcs"
    assert ee.api_kulcs_elerheto("explicit-kulcs") == "explicit-kulcs"  # explicit elsőbbséget élvez


# --- fuvarigeny_kinyerese --------------------------------------------------------

def test_kulcs_nelkul_ismert_mintara_mukodik_es_teszt_modot_jelez(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    eredmeny = ee.fuvarigeny_kinyerese(GYOR_HAMBURG.szoveg)
    assert eredmeny.mod == "minta"
    assert eredmeny.adat.felrakas_hely.ertek == "Győr"


def test_kulcs_nelkul_ismeretlen_szovegre_hibat_ad(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ee.KinyerasiHiba):
        ee.fuvarigeny_kinyerese("Egy teljesen ismeretlen, kitalált fuvarigény szövege.")


def test_ures_szovegre_hibat_ad():
    with pytest.raises(ee.KinyerasiHiba):
        ee.fuvarigeny_kinyerese("   ")


def test_ai_hivas_mockolva_es_gyorsitotarazva(monkeypatch):
    hivasok = {"n": 0}

    def hamis_hivas(szoveg, api_kulcs, modell):
        hivasok["n"] += 1
        return {
            "felrakas_hely": {"ertek": "Szeged", "bizonyossag": "biztos", "megjegyzes": ""},
            "felrakas_cim": {"ertek": None, "bizonyossag": "hianyzik", "megjegyzes": ""},
            "felrakas_datum": {"ertek": None, "bizonyossag": "hianyzik", "megjegyzes": ""},
            "lerakas_hely": {"ertek": "Pécs", "bizonyossag": "biztos", "megjegyzes": ""},
            "lerakas_cim": {"ertek": None, "bizonyossag": "hianyzik", "megjegyzes": ""},
            "lerakas_datum": {"ertek": None, "bizonyossag": "hianyzik", "megjegyzes": ""},
            "rakomany_megnevezese": {"ertek": None, "bizonyossag": "hianyzik", "megjegyzes": ""},
            "jarmuigeny": {"ertek": None, "bizonyossag": "hianyzik", "megjegyzes": ""},
            "tetelek": [],
            "altalanos_megjegyzesek": [],
        }

    monkeypatch.setattr(ee, "_hivja_a_modellt", hamis_hivas)
    ee._GYORSITOTAR.clear()
    eredmeny = ee.fuvarigeny_kinyerese("Szeged -> Pécs, teszt szöveg.", api_kulcs="hamis-kulcs")
    assert eredmeny.mod == "ai" and eredmeny.adat.felrakas_hely.ertek == "Szeged"
    assert hivasok["n"] == 1
    ee.fuvarigeny_kinyerese("Szeged -> Pécs, teszt szöveg.", api_kulcs="hamis-kulcs")
    assert hivasok["n"] == 1  # ugyanarra a szövegre nem hív újra


def test_hianyos_valasz_eszkoz_nelkul_hibat_ad(monkeypatch):
    def hamis_hivas(szoveg, api_kulcs, modell):
        raise ee.KinyerasiHiba("A modell nem adott vissza strukturált adatot.")

    monkeypatch.setattr(ee, "_hivja_a_modellt", hamis_hivas)
    with pytest.raises(ee.KinyerasiHiba):
        ee.fuvarigeny_kinyerese("Bármilyen szöveg.", api_kulcs="hamis-kulcs")
