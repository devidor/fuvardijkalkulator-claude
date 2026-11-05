import json, math, random
from io import BytesIO
import pytest
from packing_optimizer import Tetel, Elhelyezes, optimalizal, ellenoriz_elhelyezest, PakolasEredmeny
from cargo_models import RakomanyCsoport, validal_csoport
from trailer_config import Potkocsi
from load_planner import tervez
from pricing import DijParameterek, szamol_dij
from billing_config import ElszamolasiKonfig
from ldm_calculator import elszamolasi_ldm
from ldm_tracking import LdmKovetes
from tracking_history import uj_bejegyzes, beolvas_naplo
from pdf_export import ajanlat_pdf
from load_plan_export import TervFejlec

@pytest.mark.parametrize('bad',[float('nan'),float('inf'),-1,0,10.04])
def test_bad_dimensions_rejected(bad):
    with pytest.raises(ValueError):optimalizal([Tetel(0,bad,80,True,1)],1360,245)

def test_raw_geometry_does_not_hide_small_overlap():
    assert ellenoriz_elhelyezest([Elhelyezes(1,0,0,0,120,80,False),Elhelyezes(2,0,119.99,0,120,80,False)],300,245)

def test_invalid_numbers():
    assert validal_csoport(RakomanyCsoport('a',120,80,100,float('nan'),100))
    with pytest.raises(ValueError):ElszamolasiKonfig(kg_per_ldm=float('nan'))
    with pytest.raises(ValueError):szamol_dij(DijParameterek(2,float('inf')))

def test_use_usable_width():
    t=tervez([RakomanyCsoport('a',120,80,100,1,100)],Potkocsi(szabad_szelesseg_cm=240))
    assert t.elmeleti_ldm==.4

def test_no_solution_is_not_impossible():
    def heuristic(*args):return PakolasEredmeny([],1400,1000,False,'közelítő',1360,245)
    t=tervez([RakomanyCsoport('a',120,80,100,1,100)],Potkocsi(),pakolo=heuristic)
    assert any('lehetetlenség nem bizonyított' in u.szoveg for u in t.uzenetek)

@pytest.mark.parametrize('mode,kwargs,expected',[('kg',dict(ossz_kg=3000,dij_per_kg=.2),600),('ftl',dict(teljes_kocsi_dij=2000),2000),('ldm',{},200)])
def test_pricing_modes(mode,kwargs,expected):
    r=szamol_dij(DijParameterek(2,100,dij_mod=mode,szazalek=20,arazas_mod='arres',**kwargs))
    assert r.beszerzesi_koltseg==expected
    assert r.ajanlott_ar==expected/.8

@pytest.mark.parametrize('rule,expected',[('maximum',4),('fizikai',2),('tömeg',4)])
def test_contract_rule(rule,expected):
    assert elszamolasi_ldm(2,7000,ElszamolasiKonfig(szabaly=rule)).elszamolasi_ldm==expected

def test_journal_roundtrip():
    k=LdmKovetes(2,3,tenyleges_ldm=2.5)
    rows=[uj_bejegyzes('hash','F-1',k)]
    assert beolvas_naplo(json.dumps(rows).encode())==rows
    with pytest.raises(ValueError):beolvas_naplo(b'[{"schema":1}]')

def test_pdf_unicode_and_carrier_privacy():
    from pypdf import PdfReader
    t=tervez([RakomanyCsoport('Árvíztűrő tükörfúrógép',120,80,100,5,100)],Potkocsi())
    pdf=ajanlat_pdf(t,TervFejlec('F-1','Győr - Róma','Árvíztűrő'),LdmKovetes(t.fizikai_ldm,2),szamol_dij(DijParameterek(2,100,szazalek=33)))
    text=''.join(p.extract_text() for p in PdfReader(BytesIO(pdf)).pages)
    assert 'Árvíztűrő' in text and 'ELŐZETES TERV' in text
    assert '266.00' not in text # internal selling price does not go to carrier

# Independent exhaustive integer-grid oracle: no normal-pattern or lower-bound code shared.
def oracle(rects,width):
    def fits(length):
        occupied=set()
        def rec(i):
            if i==len(rects):return True
            a,b,rot=rects[i]
            for l,w in {(a,b),(b,a)} if rot else {(a,b)}:
                for x in range(length-l+1):
                    for y in range(width-w+1):
                        cells={(u,v) for u in range(x,x+l) for v in range(y,y+w)}
                        if cells & occupied:continue
                        occupied.update(cells)
                        if rec(i+1):return True
                        occupied.difference_update(cells)
            return False
        return rec(0)
    for length in range(math.ceil(sum(a*b for a,b,_ in rects)/width),sum(a for a,b,_ in rects)+1):
        if fits(length):return length

@pytest.mark.parametrize('seed',range(32))
def test_exact_against_independent_oracle(seed):
    rng=random.Random(seed)
    rects=[(rng.randint(1,4),rng.randint(1,4),bool(seed%2)) for _ in range(3)]
    optimum=oracle(rects,5)
    r=optimalizal([Tetel(i,a,b,rot,1) for i,(a,b,rot) in enumerate(rects)],30,5,1)
    assert r.also_korlat_cm <= optimum <= r.hasznalt_hossz_cm
    if r.bizonyitott:assert r.hasznalt_hossz_cm==optimum
