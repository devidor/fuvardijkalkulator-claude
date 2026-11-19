"""Ország + település felismerése irányítószámból (Google Geocoding, mockolt) és a felület."""

import io
import json
import urllib.parse
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import country_detect as cd
import postal_lookup as pl

APP = str(Path(__file__).resolve().parent.parent / "app.py")


class _Valasz(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def geo(*talalatok, status="OK"):
    """Google Geocoding-válasz: talalatok = (ISO2, országnév, település, irsz) vagy (…, [települések])."""
    results = []
    for iso, nev, telep, irsz in talalatok:
        r = {"address_components": [
            {"long_name": irsz, "short_name": irsz, "types": ["postal_code"]},
            {"long_name": nev, "short_name": iso, "types": ["country", "political"]},
        ]}
        if isinstance(telep, list):
            r["postcode_localities"] = telep
        else:
            r["address_components"].insert(0, {"long_name": telep, "short_name": telep, "types": ["locality"]})
        results.append(r)
    return {"status": status if results or status != "OK" else "ZERO_RESULTS", "results": results}


def halozat(valasz: dict, hivasok: list | None = None):
    def urlopen(keres, timeout):
        if hivasok is not None:
            hivasok.append(urllib.parse.unquote(keres.full_url))
        return _Valasz(json.dumps(valasz).encode())
    return urlopen


# --- Modul ----------------------------------------------------------------------------------

def test_egy_talalat_orszag_es_telepules_ugyanabbol():
    hivasok = []
    j = cd.orszag_felismerese("1230", "k", elonyben="HU", _urlopen=halozat(geo(("AT", "Ausztria", "Bécs", "1230")), hivasok))
    assert j == [cd.Jelolt("AT", "Ausztria", "Bécs", "1230")]
    assert "components=postal_code:1230" in hivasok[0] and "region=hu" in hivasok[0] and "country:" not in hivasok[0]


def test_tobb_talalat_a_valasztott_orszag_elol():
    valasz = geo(("AT", "Ausztria", "Bécs", "1230"), ("HU", "Magyarország", "Kunszentmiklós", "1230"))
    j = cd.orszag_felismerese("1230", "k", elonyben="HU", _urlopen=halozat(valasz))
    assert [x.orszag for x in j] == ["HU", "AT"]


def test_postcode_localities_tobb_telepules():
    j = cd.orszag_felismerese("01001", "k", _urlopen=halozat(geo(("SK", "Szlovákia", ["Žilina", "Strážov"], "010 01"))))
    assert [x.telepules for x in j] == ["Žilina", "Strážov"] and j[0].irsz == "010 01"


def test_europan_kivuli_talalat_kiesik_haromjegyu_kod_atvalt():
    valasz = geo(("US", "Egyesült Államok", "Springfield", "11000"), ("RS", "Szerbia", "Belgrád", "11000"))
    assert cd.orszag_felismerese("11000", "k", _urlopen=halozat(valasz)) == [cd.Jelolt("SRB", "Szerbia", "Belgrád", "11000")]


def test_elutasitott_keres_hibat_ad_ures_valasz_nem():
    with pytest.raises(cd.GeocodeHiba, match="REQUEST_DENIED.*not authorized"):
        cd.orszag_felismerese("1230", "k", _urlopen=halozat(
            {"status": "REQUEST_DENIED", "error_message": "This API project is not authorized", "results": []}))
    assert cd.orszag_felismerese("0000", "k", _urlopen=halozat(geo())) == []


@pytest.mark.parametrize("be, ki", [("AT-1230", ("AT", "1230")), ("de 80331", ("DE", "80331")),
                                     ("1230", (None, "1230")), ("XX-1230", (None, "XX-1230"))])
def test_orszag_elotag(be, ki):
    assert cd.orszag_elotag(be) == ki


# --- Felület --------------------------------------------------------------------------------

def indit(monkeypatch, google: dict | None = None, zip_: dict | None = None, embed: bool = True) -> AppTest:
    """google: irsz → Jelolt-lista (None: nincs Google-kulcs); zip_: (ország, irsz) → települések."""
    monkeypatch.setenv("GOOGLE_MAPS_EMBED_API_KEY", "embed-teszt") if embed else monkeypatch.delenv(
        "GOOGLE_MAPS_EMBED_API_KEY", raising=False)
    if google is None:
        monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    else:
        monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "teszt-kulcs")

    def hamis_felismeres(irsz, kulcs, elonyben=None, _urlopen=None):
        ertek = (google or {}).get(irsz, [])
        if isinstance(ertek, Exception):
            raise ertek
        return sorted(ertek, key=lambda j: j.orszag != elonyben) if elonyben else list(ertek)

    def hamis_zip(orszag, irsz, google_kulcs=None, _urlopen=None):
        nevek = (zip_ or {}).get((orszag, irsz))
        return pl.Talalat(tuple(nevek), "zippopotam", irsz) if nevek else None

    monkeypatch.setattr(cd, "orszag_felismerese", hamis_felismeres)
    monkeypatch.setattr(pl, "telepules_keresese", hamis_zip)
    st.cache_data.clear()
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def futtat(at):
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def terkep_latszik(at) -> bool:
    return any("google.com/maps/embed" in str(getattr(e, "proto", "")) for e in at.get("iframe"))


AT_BECS = cd.Jelolt("AT", "Ausztria", "Bécs", "1230")
HU_KUNSZ = cd.Jelolt("HU", "Magyarország", "Kunszentmiklós", "1230")
HU_SZFV = cd.Jelolt("HU", "Magyarország", "Székesfehérvár", "8000")
DE_MUC = cd.Jelolt("DE", "Németország", "München", "80331")


def test_irsz_kitolti_az_orszagot_es_a_telepulest(monkeypatch):
    at = indit(monkeypatch, google={"80331": [DE_MUC]})
    at.text_input(key="fd_l_irsz").set_value("80331")
    futtat(at)
    assert at.selectbox(key="fd_l_orszag").value == "DE"
    assert at.text_input(key="fd_l_telepules").value == "München"
    assert at.number_input(key="fd_eur_per_km").value == 1.6  # HU → DE export javaslat
    assert any("Felismerve (Google): Németország (DE) – München" in c.value for c in at.caption)


def test_tobbertelmu_irsz_valasztast_ker(monkeypatch):
    at = indit(monkeypatch, google={"1230": [AT_BECS, HU_KUNSZ]})
    at.text_input(key="fd_l_irsz").set_value("1230")
    futtat(at)
    assert at.text_input(key="fd_l_telepules").value == ""
    assert at.selectbox(key="fd_l_orszag").value == "AT"  # változatlan, amíg nem választ
    assert "többértelmű (2 találat)" in " ".join(m.value for m in at.markdown)
    valaszto = at.selectbox(key="fd_l_telep_valaszto")
    assert valaszto.value is None and len(valaszto.options) == 2
    valaszto.set_value(1)  # HU – Kunszentmiklós
    futtat(at)
    assert at.selectbox(key="fd_l_orszag").value == "HU"
    assert at.text_input(key="fd_l_telepules").value == "Kunszentmiklós"


def test_orszag_es_telepules_kezzel_modosithato(monkeypatch):
    at = indit(monkeypatch, google={"80331": [DE_MUC]}, zip_={("AT", "80331"): None})
    at.text_input(key="fd_l_irsz").set_value("80331")
    futtat(at)
    at.text_input(key="fd_l_telepules").set_value("München-Altstadt")
    futtat(at)
    assert at.text_input(key="fd_l_telepules").value == "München-Altstadt"
    at.selectbox(key="fd_l_orszag").set_value("AT")  # kézi ország: az automatika nem írja vissza DE-re
    futtat(at)
    assert at.selectbox(key="fd_l_orszag").value == "AT"


def test_orszag_elotag_kulcs_nelkul_is(monkeypatch):
    at = indit(monkeypatch, google=None, zip_={("DE", "80331"): ["München"]})
    at.text_input(key="fd_l_irsz").set_value("DE-80331")
    futtat(at)
    assert at.selectbox(key="fd_l_orszag").value == "DE"
    assert at.text_input(key="fd_l_irsz").value == "80331"
    assert at.text_input(key="fd_l_telepules").value == "München"


def test_kulcs_nelkul_a_valasztott_orszagban_keres_es_jelzi(monkeypatch):
    at = indit(monkeypatch, google=None, zip_={("HU", "8000"): ["Székesfehérvár"]})
    at.text_input(key="fd_f_irsz").set_value("8000")
    futtat(at)
    assert at.text_input(key="fd_f_telepules").value == "Székesfehérvár"
    assert any("Google-kulcs (Geocoding API) szükséges" in c.value for c in at.caption)


def test_elutasitott_google_eseten_tartalek_kereses(monkeypatch):
    at = indit(monkeypatch, google={"8000": cd.GeocodeHiba("Google Geocoding API: REQUEST_DENIED")},
               zip_={("HU", "8000"): ["Székesfehérvár"]})
    at.text_input(key="fd_f_irsz").set_value("8000")
    futtat(at)
    assert at.text_input(key="fd_f_telepules").value == "Székesfehérvár"
    assert any("REQUEST_DENIED" in c.value and "Geocoding API" in c.value for c in at.caption)


def test_terkep_orszagvaltaskor_is_megmarad(monkeypatch):
    at = indit(monkeypatch, google={"8000": [HU_SZFV], "1230": [AT_BECS]},
               zip_={("DE", "1230"): None, ("CH", "1230"): None})
    at.text_input(key="fd_f_irsz").set_value("8000")
    at.text_input(key="fd_l_irsz").set_value("1230")
    futtat(at)
    assert terkep_latszik(at)
    for orszag in ("DE", "CH", "AT"):  # kézi országváltás, a település nem található / megtalálható
        at.selectbox(key="fd_l_orszag").set_value(orszag)
        futtat(at)
        assert terkep_latszik(at), orszag
    at.selectbox(key="fd_f_orszag").set_value("SK")
    futtat(at)
    assert terkep_latszik(at)


def test_terkep_tobbertelmu_talalatnal_is_megmarad(monkeypatch):
    at = indit(monkeypatch, google={"8000": [HU_SZFV], "1230": [AT_BECS, HU_KUNSZ]})
    at.text_input(key="fd_f_irsz").set_value("8000")
    at.text_input(key="fd_l_irsz").set_value("1230")
    futtat(at)
    assert terkep_latszik(at)
