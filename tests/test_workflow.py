from pathlib import Path
from streamlit.testing.v1 import AppTest
from ldm_tracking import VISSZAIGAZOLVA,NINCS_ELKULDVE
APP=str(Path(__file__).resolve().parents[1]/'app.py')

def test_weight_pricing_and_stale_confirmation():
    at=AppTest.from_file(APP,default_timeout=30).run()
    assert not at.exception
    at.selectbox(key='allapot').set_value(VISSZAIGAZOLVA).run()
    at.text_input(key='visszaig_hiv').set_value('mail-123').run()
    at.text_area(key='ajanlat_feltetelek').set_value('Fuvarozói nettó ár visszaigazolva.').run()
    at.checkbox(key='ajanlat_jovahagyva').check().run()
    assert at.checkbox(key='ajanlat_jovahagyva').value
    at.number_input(key='darab_1').set_value(6).run()
    assert not at.exception
    assert at.selectbox(key='allapot').value==NINCS_ELKULDVE
    assert not at.checkbox(key='ajanlat_jovahagyva').value
    pricing=next(x for x in at.selectbox if x.label=='Fuvarozói díjazás')
    pricing.set_value('kg').run()
    assert not at.exception
    at.radio(key='penznem').set_value('HUF').run()
    assert not at.exception
    pricing=next(x for x in at.selectbox if x.label=='Fuvarozói díjazás')
    pricing.set_value('ftl').run()
    assert not at.exception

def test_add_remove_and_input_order():
    at=AppTest.from_file(APP,default_timeout=30).run()
    keys=[x.key for x in at.number_input if x.key and x.key.endswith('_1')]
    assert keys[:5]==['darab_1','hossz_1','szel_1','mag_1','suly_1']
    next(b for b in at.button if 'Új rakománycsoport' in b.label).click().run()
    assert at.number_input(key='darab_3').value==1
    at.button(key='torol_3').click().run()
    assert not at.exception
    assert not any(x.key=='darab_3' for x in at.number_input)

def test_quote_suppressed_on_oversize():
    at=AppTest.from_file(APP,default_timeout=30).run()
    at.number_input(key='mag_1').set_value(400).run()
    assert not at.exception
    assert not any(x.key=='ajanlat_jovahagyva' for x in at.checkbox)
