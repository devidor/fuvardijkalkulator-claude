"""3D rakodási nézet: minden egység megjelenik, a halmok egymáson állnak, a rakodótéren belül."""

import pytest

from cargo_models import RakomanyCsoport
from load_planner import tervez
from trailer_config import Potkocsi
from visualization_3d import dobozok, rakodasi_3d_abra

PK = Potkocsi.tipusbol("Normál")


def vegyes_terv():
    return tervez([
        RakomanyCsoport("Halmozott", 120, 80, 120, 9, 350, max_szint=2, raterheles_kg=800),
        RakomanyCsoport("Magas", 140, 100, 200, 4, 500),
    ], PK)


def test_minden_egyseg_egy_doboz_es_a_halmok_egymason_allnak():
    terv = vegyes_terv()
    db = dobozok(terv)
    assert len(db) == 9 + 4
    for d in db:
        assert 0 <= d.x0 < d.x1 <= PK.rakter_hossz_cm
        assert 0 <= d.y0 < d.y1 <= PK.rakter_szelesseg_cm
        assert 0 <= d.z0 < d.z1 <= PK.rakter_magassag_cm
    halmozott = [d for d in db if d.csoport == 0]
    assert max(d.szint for d in halmozott) == 2
    for d in halmozott:
        assert d.z0 == pytest.approx((d.szint - 1) * 120)
    # egy helyen álló egységek alapterülete azonos
    for d in halmozott:
        alatta = [a for a in halmozott if a.sorszam == d.sorszam and a.szint == d.szint - 1]
        if d.szint > 1:
            assert (alatta[0].x0, alatta[0].y0, alatta[0].x1, alatta[0].y1) == (d.x0, d.y0, d.x1, d.y1)


def test_abra_csoportonkent_egy_test_8_csuccsal_dobozonkent():
    terv = vegyes_terv()
    fig = rakodasi_3d_abra(terv)
    testek = [t for t in fig.data if t.type == "mesh3d" and t.name in ("Halmozott", "Magas")]
    assert [t.name for t in testek] == ["Halmozott", "Magas"]
    assert len(testek[0].x) == 9 * 8 and len(testek[0].i) == 9 * 12
    assert len(testek[1].x) == 4 * 8
    assert fig.layout.scene.zaxis.range == (0, 270)


def test_csak_sav_nezet():
    fig = rakodasi_3d_abra(vegyes_terv(), csak_sav=True)
    assert fig.layout.scene.xaxis.range[1] < 1360
