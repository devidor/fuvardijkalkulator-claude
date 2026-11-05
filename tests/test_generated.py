import math
import pytest
from benchmark_cases import cases
from cargo_models import RakomanyCsoport
from trailer_config import Potkocsi
from load_planner import tervez
from packing_optimizer import ellenoriz_elhelyezest

@pytest.mark.parametrize('case',cases(),ids=lambda c:c['id']+' '+c['kind'])
def test_generated(case):
    groups=[RakomanyCsoport(**g) for g in case['groups']]
    pk=Potkocsi(hossz_cm=case['length'],szelesseg_cm=case['width'],magassag_cm=case['height'])
    if case['invalid']:
        with pytest.raises(ValueError):tervez(groups,pk,idokorlat_s=.01)
        return
    t=tervez(groups,pk,idokorlat_s=.01)
    r=t.pakolas
    assert not ellenoriz_elhelyezest(r.elhelyezesek,r.hasznalt_hossz_cm,case['width'])
    assert sum(t.halmok.values())==sum(c.csoport.darab for c in t.csoportok if c.berakhato)
    assert r.also_korlat_cm<=r.hasznalt_hossz_cm+1e-8
    assert r.sav_szabad_terulet_cm2 == pytest.approx(sum(s.terulet_cm2 for s in r.szabad_teruletek))
    for e in r.elhelyezesek:
        g=groups[e.csoport]
        assert (e.hossz_cm,e.szelesseg_cm)==((g.szelesseg_cm,g.hossz_cm) if e.forgatott else (g.hossz_cm,g.szelesseg_cm))
        assert not e.forgatott or g.forgathato
    if case['optimum'] is not None:
        assert r.hasznalt_hossz_cm==pytest.approx(case['optimum'])
        assert r.bizonyitott
    assert t.elszamolas.elszamolasi_ldm==pytest.approx(max(r.hasznalt_hossz_cm/100,sum(g.darab*g.suly_kg for g in groups)/1750))
    if t.berakhato:
        assert not ellenoriz_elhelyezest(r.elhelyezesek,pk.rakter_hossz_cm,pk.rakter_szelesseg_cm)
        assert t.ossz_suly_kg<=pk.teherbiras_kg
