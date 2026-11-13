"""Az „AI e-mail-feldolgozás” fül végponttól végpontig (Streamlit AppTest, API-kulcs nélkül)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from email_samples import BUDAPEST_MUNCHEN

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def indit(monkeypatch) -> AppTest:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def kattint(at: AppTest, felirat: str) -> AppTest:
    at.button[[b.label for b in at.button].index(felirat)].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_minta_betoltese_es_kinyeres_teszt_uzemmodban(monkeypatch):
    at = indit(monkeypatch)
    at.selectbox(key="ai_minta_valasztott").set_value(BUDAPEST_MUNCHEN.cim)
    at = kattint(at, "Minta beillesztése")
    assert at.text_area(key="ai_level_szoveg").value == BUDAPEST_MUNCHEN.szoveg

    at = kattint(at, "🔍 Fuvaradatok kinyerése")
    s = " ".join(m.value for m in at.markdown)
    assert "Teszt üzemmód" in s and BUDAPEST_MUNCHEN.cim in s
    assert at.text_input(key="ai_f_hely").value == "Budapest"
    assert at.text_input(key="ai_l_hely").value == "München"
    assert at.text_input(key="ai_f_datum").value == "2026-11-18"
    assert at.number_input(key="ai_t_0_darab").value == 6
    assert at.number_input(key="ai_t_0_hossz_cm").value == 120
    assert at.number_input(key="ai_t_0_szelesseg_cm").value == 80
    assert at.number_input(key="ai_t_0_magassag_cm").value == 150
    assert at.number_input(key="ai_t_0_suly_kg").value == 500
    assert at.checkbox(key="ai_t_0_halmozhato").value is False
    assert "Hiányzó adat: felrakási cím" in s


def test_atadas_uj_csoportot_hoz_letre_a_rakomany_fulon(monkeypatch):
    at = indit(monkeypatch)
    eredeti_csoportszam = len(at.session_state["csoport_idk"])
    at.selectbox(key="ai_minta_valasztott").set_value(BUDAPEST_MUNCHEN.cim)
    at = kattint(at, "Minta beillesztése")
    at = kattint(at, "🔍 Fuvaradatok kinyerése")
    at = kattint(at, "➕ Átadás a FuvarDíj kalkulátornak")

    assert len(at.session_state["csoport_idk"]) == eredeti_csoportszam + 1
    uj_gid = at.session_state["csoport_idk"][-1]
    assert at.session_state[f"darab_{uj_gid}"] == 6
    assert at.session_state[f"hossz_{uj_gid}"] == 120
    assert at.session_state[f"szel_{uj_gid}"] == 80
    assert at.session_state[f"mag_{uj_gid}"] == 150
    assert at.session_state[f"suly_{uj_gid}"] == 500
    assert at.session_state[f"szint_opcio_{uj_gid}"] == "Nem halmozható"
    assert at.session_state["viszonylat"] == "Budapest – München"
    s = " ".join(m.value for m in at.markdown)
    assert "1 rakománytétel átadva" in s


def test_ismeretlen_szoveg_api_kulcs_nelkul_hibat_jelez(monkeypatch):
    at = indit(monkeypatch)
    at.text_area(key="ai_level_szoveg").set_value("Ez egy teljesen kitalált, ismeretlen fuvarigény szövege.")
    at.run()
    at = kattint(at, "🔍 Fuvaradatok kinyerése")
    assert at.error
    assert "Teszt üzemmódban" in at.error[0].value
