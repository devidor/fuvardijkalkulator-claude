"""python benchmark.py: közös geometriák, eredeti algoritmusok, külső időkorlát."""
import csv, json, signal, time, importlib.util, sys
from pathlib import Path
from benchmark_cases import cases, SEED
from cargo_models import RakomanyCsoport
from stacking_validator import ellenoriz_halmozast
from packing_optimizer import Tetel, optimalizal, ellenoriz_elhelyezest

ROOT=Path(__file__).parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
old=module('old_claude',ROOT/'baselines/claude/packing_optimizer.py')
gpt=module('old_gpt',ROOT/'baselines/chatgpt/packing_optimizer.py')
class Budget(Exception):pass

def timeout(*args):raise Budget()

def main():
    rows=[]
    signal.signal(signal.SIGALRM,timeout)
    data=cases()
    for case in data:
        groups=[RakomanyCsoport(**g) for g in case['groups']]
        for name in ('ChatGPT 3','Claude eredeti','FuvarDíj 4'):
            row=dict(eset=case['id'],kategoria=case['kind'],algoritmus=name,allapot='',ldm='',also_korlat='',bizonyitott=False,ervenyes=False,futasido_s=0,ismert_optimum_ldm=case['optimum']/100 if case['optimum'] else '',optimum_elteres_ldm='')
            if case['invalid']:
                row['allapot']='közös bemenetellenőrzés elutasítja';rows.append(row);continue
            items=[Tetel(i,g.hossz_cm,g.szelesseg_cm,g.forgathato,ellenoriz_halmozast(g,case['height']).helyek) for i,g in enumerate(groups)]
            start=time.perf_counter()
            try:
                signal.setitimer(signal.ITIMER_REAL,.5)
                if name=='ChatGPT 3':
                    # All generated cases have uniform rotation policy. Axis mapping: old x=width, new x=length.
                    its=[gpt.Item(str(t.csoport),t.szelesseg_cm,t.hossz_cm) for t in items for _ in range(t.darab)]
                    r=gpt.pack(its,case['width'],case['length'],allow_rotate=all(t.forgathato for t in items))
                    row['allapot']='érvényes terv' if r.valid else ('darabszámkorlát' if len(its)>120 else 'nem talált tervet')
                    row['ervenyes']=r.valid and len(r.placements)==len(its) and gpt.validate(r.placements,case['width'],case['length'])
                    if r.valid:row['ldm']=r.used_length/100
                else:
                    mod=old if name=='Claude eredeti' else sys.modules['packing_optimizer']
                    ts=[mod.Tetel(t.csoport,t.hossz_cm,t.szelesseg_cm,t.forgathato,t.darab) for t in items]
                    r=mod.optimalizal(ts,case['length'],case['width'],.02)
                    row.update(ldm=r.hasznalt_hossz_cm/100,also_korlat=r.also_korlat_cm/100,bizonyitott=r.bizonyitott)
                    row['ervenyes']=len(r.elhelyezesek)==sum(t.darab for t in items) and not ellenoriz_elhelyezest(r.elhelyezesek,case['length'],case['width'])
                    row['allapot']='érvényes terv' if row['ervenyes'] else ('alsó korlát szerint nem fér' if r.also_korlat_cm>case['length'] else 'nem talált raktérbe férő tervet')
                if row['ldm']!='' and row['ismert_optimum_ldm']!='':row['optimum_elteres_ldm']=row['ldm']-row['ismert_optimum_ldm']
            except Budget:row['allapot']='külső 0,5 s időkorlát'
            except Exception as exc:row['allapot']=f'hiba: {type(exc).__name__}: {exc}'
            finally:signal.setitimer(signal.ITIMER_REAL,0)
            row['futasido_s']=round(time.perf_counter()-start,6);rows.append(row)
        if int(case['id'])%100==0:print(case['id'],flush=True)
    (ROOT/'reports').mkdir(exist_ok=True)
    with (ROOT/'reports/comparison.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
    (ROOT/'reports/cases.json').write_text(json.dumps(dict(seed=SEED,cases=data),ensure_ascii=False,indent=2))
    summary={n:{'cases':sum(r['algoritmus']==n for r in rows),'valid':sum(r['algoritmus']==n and r['ervenyes'] for r in rows),'timeouts':sum(r['algoritmus']==n and 'időkorlát' in r['allapot'] for r in rows),'proven':sum(r['algoritmus']==n and r['bizonyitott'] for r in rows)} for n in ('ChatGPT 3','Claude eredeti','FuvarDíj 4')}
    (ROOT/'reports/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    print(summary)
if __name__=='__main__':main()
