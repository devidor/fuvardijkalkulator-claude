from cargo_models import RakomanyCsoport
from trailer_config import Potkocsi
from load_planner import tervez
from visualization_3d import terv_3d

def test_individual_stack_layers_and_real_scale():
    t=tervez([RakomanyCsoport('Halom',120,80,100,5,100,max_szint=2,raterheles_kg=200)],Potkocsi())
    f=terv_3d(t)
    mesh=f.data[0]
    assert len(mesh.x)==5*8
    assert max(mesh.z)==200
    assert len(mesh.i)==5*12
    assert f.layout.scene.aspectmode=='data'
    assert 'plotly.js' in f.to_html(include_plotlyjs=True)

def test_rotation_matches_plan():
    t=tervez([RakomanyCsoport('Forgatott',140,100,100,4,100)],Potkocsi())
    f=terv_3d(t)
    assert max(f.data[0].x)==t.pakolas.hasznalt_hossz_cm
