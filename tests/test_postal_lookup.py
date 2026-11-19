"""Irányítószám → település keresés (hálózat nélkül, mockolt válaszokkal) és a felület kitöltése."""

import io
import json
import urllib.error
import urllib.parse
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import postal_lookup as pl

APP = str(Path(__file__).resolve().parent.parent / "app.py")


class _Valasz(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def hamis_halozat(valaszok: dict, hivasok: list | None = None):
    """URL-részlet → JSON válasz; ami nincs a listában, arra 404."""

    def urlopen(keres, timeout):
        url = urllib.parse.unquote(keres.full_url)
        if hivasok is not None:
            hivasok.append(url)
        for minta, adat in valaszok.items():
            if minta in url:
                return _Valasz(json.dumps(adat).encode())
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b"{}"))

    return urlopen


def zip_valasz(irsz, *helyek):
    return {"post code": irsz, "places": [{"place name": h} for h in helyek]}


@pytest.mark.parametrize("orszag, irsz, elso", [
    ("CZ", "11000", "110 00"), ("SK", "01001", "010 01"), ("PL", "00001", "00-001"),
    ("PT", "1000001", "1000-001"), ("LU", "1009", "L-1009"), ("LU", "L-1009", "L-1009"), ("HU", " 8000 ", "8000"),
])
def test_irsz_valtozatok_orszagonkent(orszag, irsz, elso):
    assert pl.irsz_valtozatok(orszag, irsz)[0] == elso


def test_zippopotam_talalat_es_formazott_irsz():
    hivasok = []
    net = hamis_halozat({"/pl/00-001": zip_valasz("00-001", "Warszawa")}, hivasok)
    t = pl.telepules_keresese("PL", "00001", _urlopen=net)
    assert t.elso == "Warszawa" and t.irsz == "00-001" and t.forras == "zippopotam"
    assert "api.zippopotam.us/pl/00-001" in hivasok[0]


def test_tobb_telepules_duplikatum_nelkul():
    net = hamis_halozat({"/sk/010 01": zip_valasz("010 01", "Žilina", "Strážov", "Žilina")})
    assert pl.telepules_keresese("SK", "01001", _urlopen=net).telepulesek == ("Žilina", "Strážov")


def test_haromjegyu_orszagkod_iso2_re_valt():
    hivasok = []
    net = hamis_halozat({"/rs/11000": zip_valasz("11000", "Beograd")}, hivasok)
    assert pl.telepules_keresese("SRB", "11000", _urlopen=net).elso == "Beograd"


def test_google_tartalek_csak_kulccsal():
    google = {"status": "OK", "results": [{"address_components": [
        {"long_name": "010011", "types": ["postal_code"]},
        {"long_name": "București", "types": ["locality", "political"]},
    ]}]}
    hivasok = []
    net = hamis_halozat({"geocode/json": google}, hivasok)
    assert pl.telepules_keresese("RO", "010011", _urlopen=net) is None  # kulcs nélkül nincs Google
    t = pl.telepules_keresese("RO", "010011", google_kulcs="k", _urlopen=net)
    assert t.elso == "București" and t.forras == "google"
    assert any("components=postal_code:010011|country:RO" in h for h in hivasok)


def test_halozati_hiba_eseten_none():
    def nincs_net(keres, timeout):
        raise urllib.error.URLError("offline")

    assert pl.telepules_keresese("HU", "8000", _urlopen=nincs_net) is None
    assert pl.telepules_keresese("HU", "", _urlopen=nincs_net) is None


# --- Felület ------------------------------------------------------------------------------

def indit(monkeypatch, talalatok: dict) -> AppTest:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)

    def hamis_kereses(orszag, irsz, google_kulcs=None, _urlopen=None):
        nevek = talalatok.get((orszag, irsz.strip()))
        return pl.Talalat(tuple(nevek), "zippopotam", irsz.strip()) if nevek else None

    monkeypatch.setattr(pl, "telepules_keresese", hamis_kereses)
    st.cache_data.clear()  # a keresés gyorsítótárazott – tesztenként tiszta lap
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_irsz_beirasa_kitolti_a_telepulest(monkeypatch):
    at = indit(monkeypatch, {("HU", "8000"): ["Székesfehérvár"], ("AT", "1230"): ["Wien"]})
    at.text_input(key="fd_f_irsz").set_value("8000")
    at.text_input(key="fd_l_irsz").set_value("1230")
    at.run()
    assert not at.exception
    assert at.text_input(key="fd_f_telepules").value == "Székesfehérvár"
    assert at.text_input(key="fd_l_telepules").value == "Wien"


def test_tobb_talalatnal_valaszthato(monkeypatch):
    at = indit(monkeypatch, {("AT", "1230"): ["Wien", "Liesing"]})
    at.text_input(key="fd_l_irsz").set_value("1230")
    at.run()
    assert at.text_input(key="fd_l_telepules").value == ""  # többértelmű → választást kér
    at.selectbox(key="fd_l_telep_valaszto").set_value(1)
    at.run()
    assert at.text_input(key="fd_l_telepules").value == "Liesing"


def test_ismeretlen_irsz_kezi_bevitelt_ker(monkeypatch):
    at = indit(monkeypatch, {})
    at.text_input(key="fd_f_irsz").set_value("9999")
    at.run()
    assert at.text_input(key="fd_f_telepules").value == ""
    assert any("nem található település" in c.value for c in at.caption)


def test_orszagvaltas_ujrakeresi_a_telepulest(monkeypatch):
    at = indit(monkeypatch, {("AT", "1230"): ["Wien"], ("DE", "1230"): []})
    at.text_input(key="fd_l_irsz").set_value("1230")
    at.run()
    assert at.text_input(key="fd_l_telepules").value == "Wien"
    at.selectbox(key="fd_l_orszag").set_value("CH")
    at.run()
    assert any("nem található település" in c.value for c in at.caption)
