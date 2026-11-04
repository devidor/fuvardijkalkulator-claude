"""A Streamlit felület futtatása (AppTest): az eredmények helyes megjelenítése."""

from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def futtat(pelda=None):
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    if pelda:
        at.selectbox(key="pelda").set_value(pelda)
        at.button[[b.label for b in at.button].index("Betöltés")].click()
        at.run()
    assert not at.exception, [e.value for e in at.exception]
    return at


def html_szoveg(at) -> str:
    return " ".join(m.value for m in at.markdown)


def test_alapallapot_hiba_nelkul_fut():
    at = futtat()
    s = html_szoveg(at)
    for cimke in ("1 · Elméleti LDM", "2 · Fizikai LDM", "3 · Tömegalapú LDM", "4 · Elszámolási LDM",
                  "5 · Rakodótér kihasználtsága", "6 · Szabad rakodóterület", "7 · Rakodási terv",
                  "8 · Figyelmeztetések"):
        assert cimke in s, cimke
    assert "<svg" in s


def test_a_pelda_megjelenitese():
    s = html_szoveg(futtat("A példa – 4 raklap 140 × 100 cm, 2000 kg"))
    assert "2,29" in s  # elméleti LDM
    assert "rakodási hossz 240 cm" in s
    assert '<div class="ertek">2,40</div>' in s  # fizikai és elszámolási LDM
    assert "bizonyított optimum" in s
    assert "nincs átfedés" in s


def test_b_pelda_megjelenitese():
    s = html_szoveg(futtat("B példa – 7 raklap 70 × 100 cm, 2450 kg"))
    assert '<div class="ertek">2,00</div>' in s  # elméleti
    assert "rakodási hossz 210 cm" in s
    assert '<div class="ertek">2,10</div>' in s


def test_2_dijpelda_tomeg_hatarozza_meg():
    s = html_szoveg(futtat("2. díjpélda – 5 EUR-raklap, 7000 kg"))
    assert '<div class="ertek">4,00</div>' in s
    assert "tömeg alapján" in s
    assert "7 000 kg" in s


def test_potkocsitipus_valtas_betolti_a_meretet():
    at = futtat()
    at.selectbox(key="pk_tipus").set_value("Mega")
    at.run()
    assert at.number_input(key="pk_mag").value == 300
    assert at.number_input(key="pk_hossz").value == 1360
    assert at.number_input(key="pk_szel").value == 245
