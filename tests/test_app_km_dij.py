"""A Fuvardíj fül km-alapú díjszámítása a felületen (Streamlit AppTest, hálózat nélkül)."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from email_samples import BUDAPEST_MUNCHEN

APP = str(Path(__file__).resolve().parent.parent / "app.py")
NB = "\xa0"  # a pénzformátum nem törhető szóközt használ


def ertek(szoveg: str) -> str:
    return f'<div class="ertek">{szoveg.replace(" ", NB)}</div>'


def indit(monkeypatch) -> AppTest:
    monkeypatch.delenv("GOOGLE_MAPS_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def futtat(at: AppTest) -> str:
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    return " ".join(m.value for m in at.markdown)


def test_alapallapot_km_nelkul_kering_tavolsagot(monkeypatch):
    at = indit(monkeypatch)
    s = futtat(at)
    assert "Adja meg a távolságot" in s
    assert "Nincs Google Maps API-kulcs" in s and "google.com/maps/dir" in s
    assert at.number_input(key="fd_eur_per_km").value == 2.0  # HU → AT javaslat


def test_ftl_dij_216_km_es_fix_profit(monkeypatch):
    at = indit(monkeypatch)
    at.number_input(key="fd_km").set_value(216)
    at.radio(key="fd_szolg").set_value("FTL")
    at.radio(key="arazas").set_value("Fix összeg (kézi megadás)")
    futtat(at)
    at.number_input(key="fix_profit_EUR").set_value(150)
    s = futtat(at)
    assert '<div class="ertek">300 km</div>' in s
    assert "300 km × 2,00 €/km" in s
    assert ertek("600,00 €") in s  # FTL-díj és alapdíj
    assert ertek("750,00 €") in s  # total díj


def test_orszagvaltas_betolti_a_javaslatot_es_ltl_szorzot_szamol(monkeypatch):
    at = indit(monkeypatch)
    at.selectbox(key="fd_l_orszag").set_value("PL")
    futtat(at)
    assert at.number_input(key="fd_eur_per_km").value == 1.5
    at.selectbox(key="fd_f_orszag").set_value("PL")
    at.selectbox(key="fd_l_orszag").set_value("HU")
    futtat(at)
    assert at.number_input(key="fd_eur_per_km").value == 2.0  # PL import
    at.number_input(key="fd_km").set_value(700)
    s = futtat(at)
    assert "LTL-alapdíj" in s and "PL, DE, IT, BE, NL, LU, FR" in s


def test_tiltott_es_egyedi_orszag(monkeypatch):
    at = indit(monkeypatch)
    at.selectbox(key="fd_l_orszag").set_value("RU")
    s = futtat(at)
    assert "szankciók" in s and "Total díj</div>" not in s
    at.selectbox(key="fd_l_orszag").set_value("GB")
    s = futtat(at)
    assert "Egyedi díjas ország" in s
    at.number_input(key="fd_alvallalkozo").set_value(1000)
    s = futtat(at)
    assert "alvállalkozói díj" in s and ertek("1 000,00 €") in s


def test_ldm_alapu_mod_tovabbra_is_mukodik(monkeypatch):
    at = indit(monkeypatch)
    at.radio(key="fd_dijalap").set_value("LDM-alapú (díj / LDM)")
    s = futtat(at)
    assert "LDM ×" in s and "Total díj</div>" in s


def test_ai_atadas_kitolti_a_viszonylatot(monkeypatch):
    at = indit(monkeypatch)
    at.selectbox(key="ai_minta_valasztott").set_value(BUDAPEST_MUNCHEN.cim)
    at.button[[b.label for b in at.button].index("Minta beillesztése")].click()
    futtat(at)
    at.button[[b.label for b in at.button].index("🔍 Fuvaradatok kinyerése")].click()
    futtat(at)
    assert at.selectbox(key="ai_f_orszag").value == "HU"
    assert at.selectbox(key="ai_l_orszag").value == "DE"
    at.button[[b.label for b in at.button].index("➕ Átadás a FuvarDíj kalkulátornak")].click()
    s = futtat(at)
    assert at.selectbox(key="fd_f_orszag").value == "HU"
    assert at.selectbox(key="fd_l_orszag").value == "DE"
    assert at.text_input(key="fd_f_telepules").value == "Budapest"
    assert at.text_input(key="fd_l_telepules").value == "München"
    assert at.number_input(key="fd_eur_per_km").value == 1.6  # DE export
    assert "átkerült a 💶 Fuvardíj fülre" in s
