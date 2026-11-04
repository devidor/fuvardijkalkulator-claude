"""Geometriai elhelyezés: méretek, forgatás, átfedés, határok, referenciapéldák."""

import math

import pytest

from packing_optimizer import (
    MODSZER_KOZELITO,
    Elhelyezes,
    Tetel,
    ellenoriz_elhelyezest,
    elfer_egyseg,
    optimalizal,
    szabad_teglalapok,
)

W, L = 245, 1360


def ervenyes(e, szelesseg=W):
    """Átfedésmentes, a sávon belüli elrendezés, és minden egység a megadott méretű."""
    assert ellenoriz_elhelyezest(e.elhelyezesek, e.hasznalt_hossz_cm, szelesseg) == []
    assert max(x.x2_cm for x in e.elhelyezesek) == pytest.approx(e.hasznalt_hossz_cm)


def test_a_pelda_4_raklap_140x100_240_cm_en():
    e = optimalizal([Tetel(0, 140, 100, True, 4)], L, W)
    assert e.hasznalt_hossz_cm == 240
    assert e.bizonyitott
    assert len(e.elhelyezesek) == 4
    ervenyes(e)
    for x in e.elhelyezesek:  # minden raklap 140 × 100, valamelyik tájolásban
        assert sorted((x.hossz_cm, x.szelesseg_cm)) == [100, 140]
        assert x.forgatott == (x.hossz_cm == 100)
    assert any(x.forgatott for x in e.elhelyezesek) and not all(x.forgatott for x in e.elhelyezesek)


def test_b_pelda_7_raklap_70x100_210_cm_en():
    e = optimalizal([Tetel(0, 70, 100, True, 7)], L, W)
    assert e.hasznalt_hossz_cm == 210
    assert e.bizonyitott
    assert len(e.elhelyezesek) == 7
    ervenyes(e)


def test_b_pelda_200_cm_bizonyitottan_nem_eleg():
    # Területben pont 200 cm lenne, de 70/100 cm-es méretekből a 245 cm-ből csak 240 tölthető ki.
    e = optimalizal([Tetel(0, 70, 100, True, 7)], L, W)
    assert e.also_korlat_cm == 210


def test_a_pelda_szabad_teruletek():
    e = optimalizal([Tetel(0, 140, 100, True, 4)], L, W)
    osszes = sum(s.terulet_cm2 for s in e.szabad_teruletek)
    assert osszes == pytest.approx(240 * 245 - 4 * 140 * 100)  # 2800 cm²
    assert e.sav_kihasznaltsag_pct == pytest.approx(56000 / 58800 * 100)
    meretek = sorted((s.hossz_cm, s.szelesseg_cm) for s in e.szabad_teruletek)
    assert (40, 40) in meretek  # a „szélkerék” közepe
    assert (240, 5) in meretek  # a 245 cm-ből kimaradó 5 cm-es csík


def test_eur_raklapok_ismert_elrendezesei():
    assert optimalizal([Tetel(0, 120, 80, True, 5)], L, W).hasznalt_hossz_cm == 200
    assert optimalizal([Tetel(0, 120, 80, True, 33)], L, W).hasznalt_hossz_cm == 1320
    assert optimalizal([Tetel(0, 120, 100, True, 26)], L, W).hasznalt_hossz_cm == 1300


def test_forgatas_tiltasa_hosszabb_elrendezest_ad():
    forg = optimalizal([Tetel(0, 120, 80, True, 4)], L, W)
    tilt = optimalizal([Tetel(0, 120, 80, False, 4)], L, W)
    assert forg.hasznalt_hossz_cm == 160
    assert tilt.hasznalt_hossz_cm == 240
    assert not any(x.forgatott for x in tilt.elhelyezesek)
    ervenyes(tilt)


def test_vegyes_meretek_kombinacioja():
    e = optimalizal([Tetel(0, 120, 80, True, 4), Tetel(1, 120, 100, True, 3), Tetel(2, 80, 60, True, 5)], L, W)
    ervenyes(e)
    assert {x.csoport for x in e.elhelyezesek} == {0, 1, 2}
    assert len(e.elhelyezesek) == 12
    terulet = 4 * 120 * 80 + 3 * 120 * 100 + 5 * 80 * 60
    assert e.hasznalt_hossz_cm >= terulet / W


def test_pontos_kereses_idokorlat_eseten_kozelitokent_jelol():
    e = optimalizal([Tetel(0, 120, 100, True, 27)], L, W, idokorlat_s=0.3)
    ervenyes(e)
    if not e.bizonyitott:
        assert e.modszer == MODSZER_KOZELITO
        assert e.also_korlat_cm <= e.hasznalt_hossz_cm


def test_nem_fero_rakomany_tullepi_a_hosszt():
    e = optimalizal([Tetel(0, 120, 80, True, 40)], L, W)
    assert not e.belefer
    ervenyes(e)


def test_szelesseg_tullepes_hibat_ad():
    assert not elfer_egyseg(250, 250, True, L, W)
    assert elfer_egyseg(300, 240, True, L, W)
    assert not elfer_egyseg(240, 300, False, L, W)
    with pytest.raises(ValueError):
        optimalizal([Tetel(0, 250, 250, True, 1)], L, W)


def test_ellenorzo_kimutatja_az_atfedest_es_a_kilogast():
    atfedo = [Elhelyezes(1, 0, 0, 0, 120, 80, False), Elhelyezes(2, 0, 100, 40, 120, 80, False)]
    assert any("átfedi" in h for h in ellenoriz_elhelyezest(atfedo, 300, W))
    kilogo = [Elhelyezes(1, 0, 0, 200, 120, 80, False)]
    assert any("kilóg" in h for h in ellenoriz_elhelyezest(kilogo, 300, W))
    erinto = [Elhelyezes(1, 0, 0, 0, 120, 80, False), Elhelyezes(2, 0, 120, 0, 120, 80, False)]
    assert ellenoriz_elhelyezest(erinto, 240, W) == []


def test_szabad_teglalapok_lefedik_a_maradekot():
    elh = [Elhelyezes(1, 0, 0, 0, 120, 80, False)]
    szabad = szabad_teglalapok(elh, 120, W)
    assert sum(s.terulet_cm2 for s in szabad) == pytest.approx(120 * (W - 80))


@pytest.mark.parametrize("darab", range(1, 13))
def test_veletlenszeru_mennyisegek_ervenyesek(darab):
    e = optimalizal([Tetel(0, 130, 90, True, darab), Tetel(1, 80, 60, False, darab // 2)], L, W, idokorlat_s=0.5)
    ervenyes(e)
    assert e.hasznalt_hossz_cm >= math.ceil((darab * 130 * 90 + (darab // 2) * 80 * 60) / W)
