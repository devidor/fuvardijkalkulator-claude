"""1024 reprodukálható szintetikus/örökölt bemenet, rögzített maggal."""
import random
from dataclasses import asdict
from cargo_models import RakomanyCsoport
from legacy_examples import PELDÁK

SEED = 20261105

def cases():
    rng=random.Random(SEED)
    out=[]
    def add(kind, groups, width=245, length=1360, height=300, invalid=False, optimum=None):
        out.append(dict(id=f"{len(out)+1:04}",kind=kind,groups=[asdict(g) for g in groups],width=width,length=length,height=height,invalid=invalid,optimum=optimum))
    for i in range(200):
        # Full-width items: pairwise cannot share the width; sum lengths is an independent proof.
        width=200+i/10
        groups=[RakomanyCsoport(f"Bizonyított {j}",rng.randint(10,100),width,100,1,50,forgathato=False) for j in range(1+i%5)]
        add("bizonyított optimum",groups,width,optimum=sum(g.hossz_cm for g in groups))
    for i in range(200):
        add("EUR",[RakomanyCsoport("EUR",120,80,100,1+i%40,100+i,forgathato=bool(i%2))],width=240+(i//40))
    for i in range(350):
        groups=[RakomanyCsoport(f"Vegyes {j}",rng.randint(3,18)*10,rng.randint(3,12)*10,80,1+rng.randrange(2),100+i,forgathato=bool(i%2)) for j in range(1+i%4)]
        add("vegyes geometria",groups,width=240+(i%6),length=100 if i%9==0 else 1360)
    for i in range(100):
        add("halmozás",[RakomanyCsoport("Halom",120,80,70+i%80,3+i%27,80+i,max_szint=2+i%3,raterheles_kg=None if i%3==0 else 100+i*3,valtakozo_tajolas=bool(i%2),raklap_meret_cm=(100,80) if i%7==0 else None)])
    for i in range(100):
        g=RakomanyCsoport("Hibás",120,80,100,1,100+i)
        if i%4==0:g.hossz_cm=-1-i
        elif i%4==1:g.darab=0
        elif i%4==2:g.max_szint=0
        else:g.suly_kg=-1-i
        add("hibás bemenet",[g],invalid=True)
    for i in range(50):
        add("nagy darabszám",[RakomanyCsoport("Sok egység",10+i,10,30,121+i*3,1,forgathato=False)])
    for i,e in enumerate(PELDÁK):
        groups=[RakomanyCsoport(name,l,w,e['magassag'],n,100,max_szint=2 if e['halmozhato'] else 1,raterheles_kg=100) for name,l,w,n in [("EUR",120,80,e['eur']),("Angol",120,100,e['angol']),("US",120,120,e['us'])] if n]
        add("24 örökölt referencia",groups,height=300)
    assert len(out)==1024
    return out
