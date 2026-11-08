"""Intelligens fuvar- és rakománykalkulátor – Streamlit alkalmazás.

Indítás:  streamlit run app.py
"""

from __future__ import annotations

import html
from datetime import date, datetime

import pandas as pd
import streamlit as st

from billing_config import ALAP_KEREKITES, ALAP_KG_PER_LDM, KEREKITESI_SZABALYOK, ElszamolasiKonfig
from cargo_models import RAKLAP_TIPUSOK, RakomanyCsoport, Uzenet, validal_csoport
from ldm_tracking import ALLAPOTOK, VISSZAIGAZOLT_ALLAPOTOK, LdmKovetes, elemzes
from load_plan_export import TervFejlec, elhelyezes_sorok, rakodasi_terv_html
from load_planner import RakodasiTerv, tervez
from packing_optimizer import PakolasEredmeny, Tetel, ellenoriz_elhelyezest, optimalizal
from pricing import DijEredmeny, DijParameterek, szamol_dij
from trailer_config import (
    ALAP_TEHERBIRAS_KG, ALAP_TIPUS, EGYEDI_TIPUS, POTKOCSI_TIPUSOK, Potkocsi, validal_potkocsi,
)
from visualization import rakodasi_svg, szin
from visualization_3d import rakodasi_3d_abra

st.set_page_config(
    page_title="Fuvar- és rakománykalkulátor",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="auto",
)

# ---------------------------------------------------------------------------
# Állandók
# ---------------------------------------------------------------------------

MOD_SZABVANYOS = "Szabványos raklap"
MOD_EGYEDI = "Egyedi rakományméret"
MODOK = [MOD_SZABVANYOS, MOD_EGYEDI]

SULY_EGYSEG = "Egy egység tömege"
SULY_OSSZES = "Teljes tömeg"

SZINT_OPCIOK = {
    "Nem halmozható": 1,
    "2 szintig halmozható": 2,
    "3 szintig halmozható": 3,
    "4 szintig halmozható": 4,
    "Egyedi szintszám": None,
}

LDM_ALAP_ELSZAMOLASI = "Elszámolási LDM (tervezett)"
LDM_ALAP_VISSZAIGAZOLT = "Fuvarozó által visszaigazolt LDM"
LDM_ALAP_FIZIKAI = "Fizikai LDM"
LDM_ALAP_ELMELETI = "Elméleti LDM"
LDM_ALAP_KEZI = "Kézi megadás"

ARAZAS_HASZONKULCS = "Haszonkulcs (beszerzési költségre vetítve)"
ARAZAS_ARRES = "Árrés (eladási árra vetítve)"

CSOPORT_ALAP = {
    "nev": "Rakomány",
    "mod": MOD_SZABVANYOS,
    "tipus": "EUR-raklap (120 × 80 cm)",
    "hossz": 120.0,
    "szel": 80.0,
    "mag": 120.0,
    "darab": 1,
    "suly_mod": SULY_EGYSEG,
    "suly": 300.0,
    "ossz_suly": 300.0,
    "szint_opcio": "Nem halmozható",
    "szint_egyedi": 5,
    "raterheles_ismert": False,
    "raterheles": 0.0,
    "forgathato": True,
    "valtakozo": False,
}

EUR = "EUR-raklap (120 × 80 cm)"
PELDAK = {
    "A példa – 4 raklap 140 × 100 cm, 2000 kg": [dict(
        nev="Raklap 140×100", mod=MOD_EGYEDI, hossz=140.0, szel=100.0, mag=200.0, darab=4,
        suly_mod=SULY_OSSZES, ossz_suly=2000.0)],
    "B példa – 7 raklap 70 × 100 cm, 2450 kg": [dict(
        nev="Raklap 70×100", mod=MOD_EGYEDI, hossz=70.0, szel=100.0, mag=120.0, darab=7,
        suly_mod=SULY_OSSZES, ossz_suly=2450.0)],
    "1. díjpélda – 5 EUR-raklap, 3000 kg": [dict(
        nev="EUR-raklap", tipus=EUR, mag=220.0, darab=5, suly_mod=SULY_OSSZES, ossz_suly=3000.0)],
    "2. díjpélda – 5 EUR-raklap, 7000 kg": [dict(
        nev="EUR-raklap", tipus=EUR, mag=220.0, darab=5, suly_mod=SULY_OSSZES, ossz_suly=7000.0)],
    "Vegyes halmozás – 8 + 4 EUR-raklap": [
        dict(nev="EUR-raklap, halmozható", tipus=EUR, darab=8, mag=120.0, suly=350.0,
             szint_opcio="2 szintig halmozható", raterheles_ismert=True, raterheles=800.0),
        dict(nev="EUR-raklap, nem halmozható", tipus=EUR, darab=4, mag=180.0, suly=600.0),
    ],
}

# ---------------------------------------------------------------------------
# Megjelenés
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1300px;}
.app-fejlec {
  background: linear-gradient(135deg, #0B2545 0%, #13315C 55%, #1E88E5 100%);
  color: #fff; border-radius: 16px; padding: 1.1rem 1.4rem; margin-bottom: 1rem;
  box-shadow: 0 4px 14px rgba(11,37,69,.18);
}
.app-fejlec h1 {color: #fff; font-size: 1.65rem; margin: 0; padding: 0; line-height: 1.25;}
.app-fejlec p {color: #CFE3F7; margin: .35rem 0 0 0; font-size: .95rem;}
.kartya-racs {display: grid; grid-template-columns: repeat(auto-fit, minmax(175px, 1fr)); gap: .75rem; margin: .4rem 0 1rem;}
.kartya {
  background: #fff; border-radius: 14px; padding: .8rem 1rem; border-left: 6px solid #1E88E5;
  box-shadow: 0 1px 5px rgba(11,37,69,.09);
}
.kartya.zold {border-left-color: #2E7D32; background: #F1F8F2;}
.kartya.narancs {border-left-color: #F57C00; background: #FFF6EC;}
.kartya.sotet {border-left-color: #0B2545;}
.kartya .cimke {font-size: .76rem; color: #4A6380; text-transform: uppercase; letter-spacing: .03em; font-weight: 600;}
.kartya .ertek {font-size: 1.45rem; font-weight: 700; color: #0B2545; line-height: 1.3; margin-top: .15rem;}
.kartya.zold .ertek {color: #2E7D32;}
.kartya.narancs .ertek {color: #E65100;}
.kartya .al {font-size: .8rem; color: #5C7590; margin-top: .1rem;}
.uzenet {border-radius: 10px; padding: .55rem .85rem; margin: .35rem 0; font-size: .92rem; line-height: 1.4;}
.uzenet.hiba {background: #FDECEA; border-left: 5px solid #C62828; color: #7F1D1D;}
.uzenet.figyelmeztetes {background: #FFF3E0; border-left: 5px solid #F57C00; color: #7A3E00;}
.uzenet.info {background: #E3F2FD; border-left: 5px solid #1E88E5; color: #0B2545;}
.uzenet.ok {background: #E8F5E9; border-left: 5px solid #2E7D32; color: #1B5E20;}
.csik {display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: .8rem;}
.csik span {
  background: #E3EEF9; color: #0B2545; border-radius: 999px; padding: .3rem .8rem;
  font-size: .88rem; font-weight: 600;
}
.csik span.zold {background: #E8F5E9; color: #1B5E20;}
.csik span.narancs {background: #FFF3E0; color: #7A3E00;}
.csik span.piros {background: #FDECEA; color: #7F1D1D;}
.mini {font-size: .88rem; color: #13315C; background: #F4F8FC; border-radius: 10px; padding: .5rem .8rem; margin-top: .3rem;}
.abra-keret {background: #fff; border: 1px solid #D5E3F2; border-radius: 12px; padding: .6rem; margin: .3rem 0 .6rem;}
.jelmagyarazat {display: flex; flex-wrap: wrap; gap: .8rem; font-size: .85rem; margin-top: .4rem;}
.jelmagyarazat i {display: inline-block; width: .9rem; height: .9rem; border-radius: 3px; margin-right: .3rem; vertical-align: -2px;}
.panel-cim {font-size: 1.15rem; font-weight: 700; color: #0B2545; margin: .2rem 0 .3rem;}
.jelveny {display: inline-block; border-radius: 999px; padding: .15rem .65rem; font-size: .8rem; font-weight: 700;}
.jelveny.zold {background: #E8F5E9; color: #1B5E20;} .jelveny.narancs {background: #FFF3E0; color: #7A3E00;}
div[data-testid="stTabs"] button p {font-size: 1rem; font-weight: 600;}
@media (max-width: 640px) {
  .app-fejlec h1 {font-size: 1.3rem;}
  .kartya .ertek {font-size: 1.2rem;}
  .kartya-racs {grid-template-columns: repeat(2, minmax(0, 1fr));}
}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Formázás
# ---------------------------------------------------------------------------


def szam(x: float, tizedes: int = 2) -> str:
    """Magyar számformátum: szóköz ezres elválasztó, tizedesvessző."""
    return f"{x:,.{tizedes}f}".replace(",", " ").replace(".", ",")


def penz(x: float, penznem: str) -> str:
    return f"{szam(x, 0 if penznem == 'HUF' else 2)} {'Ft' if penznem == 'HUF' else '€'}"


def kartya(cimke: str, ertek: str, al: str = "", stilus: str = "") -> str:
    al_html = f'<div class="al">{al}</div>' if al else ""
    return (
        f'<div class="kartya {stilus}"><div class="cimke">{cimke}</div>'
        f'<div class="ertek">{ertek}</div>{al_html}</div>'
    )


def uzenet_html(u: Uzenet, elotag: str = "") -> str:
    ikon = {"hiba": "⛔", "figyelmeztetes": "⚠️", "info": "ℹ️", "ok": "✅"}[u.szint]
    return f'<div class="uzenet {u.szint}">{ikon} {html.escape(elotag)}{html.escape(u.szoveg)}</div>'


def uzenetek_megjelenitese(uzenetek: list[Uzenet]) -> None:
    if uzenetek:
        st.markdown("".join(uzenet_html(u) for u in uzenetek), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Munkamenet-állapot
# ---------------------------------------------------------------------------


def k(nev: str, gid: int) -> str:
    return f"{nev}_{gid}"


def csoport_hozzaad(**ertekek) -> None:
    gid = st.session_state.kovetkezo_id
    st.session_state.kovetkezo_id += 1
    adatok = {**CSOPORT_ALAP, "nev": f"Rakomány {len(st.session_state.csoport_idk) + 1}", **ertekek}
    meret = RAKLAP_TIPUSOK.get(adatok["tipus"]) if adatok["mod"] == MOD_SZABVANYOS else None
    if meret and "hossz" not in ertekek:
        adatok["hossz"], adatok["szel"] = meret
    for nev, ertek in adatok.items():
        st.session_state[k(nev, gid)] = ertek
    st.session_state.csoport_idk.append(gid)


def csoport_torol(gid: int) -> None:
    st.session_state.csoport_idk.remove(gid)
    for nev in CSOPORT_ALAP:
        st.session_state.pop(k(nev, gid), None)


def tipus_valtozott(gid: int) -> None:
    meret = RAKLAP_TIPUSOK.get(st.session_state[k("tipus", gid)])
    if meret:
        st.session_state[k("hossz", gid)], st.session_state[k("szel", gid)] = meret


def mod_valtozott(gid: int) -> None:
    if st.session_state[k("mod", gid)] == MOD_SZABVANYOS:
        st.session_state.setdefault(k("tipus", gid), CSOPORT_ALAP["tipus"])
        tipus_valtozott(gid)


def pelda_betoltese() -> None:
    nev = st.session_state.get("pelda")
    if nev not in PELDAK:
        return
    for gid in list(st.session_state.csoport_idk):
        csoport_torol(gid)
    for adatok in PELDAK[nev]:
        csoport_hozzaad(**adatok)


def potkocsi_tipus_valtozott() -> None:
    t = POTKOCSI_TIPUSOK.get(st.session_state.pk_tipus)
    if t:
        st.session_state.pk_hossz = float(t.hossz_cm)
        st.session_state.pk_szel = float(t.szelesseg_cm)
        st.session_state.pk_mag = float(t.magassag_cm)


def alaphelyzet() -> None:
    for kulcs in list(st.session_state.keys()):
        del st.session_state[kulcs]


def allapot_init() -> None:
    alap_pk = POTKOCSI_TIPUSOK[ALAP_TIPUS]
    for kulcs, ertek in {
        "pk_tipus": ALAP_TIPUS, "pk_hossz": float(alap_pk.hossz_cm), "pk_szel": float(alap_pk.szelesseg_cm),
        "pk_mag": float(alap_pk.magassag_cm), "pk_teherbiras": ALAP_TEHERBIRAS_KG, "pk_szabad": False,
        "kg_per_ldm": ALAP_KG_PER_LDM, "kerekites": ALAP_KEREKITES, "idokorlat": 3.0,
    }.items():
        st.session_state.setdefault(kulcs, ertek)
    for kulcs, forras in (("pk_szabad_hossz", "pk_hossz"), ("pk_szabad_szel", "pk_szel"), ("pk_szabad_mag", "pk_mag")):
        st.session_state.setdefault(kulcs, st.session_state[forras])

    if "csoport_idk" in st.session_state:
        # A feltételesen megjelenő mezők értéke elveszhet, amíg rejtve vannak.
        for gid in st.session_state.csoport_idk:
            for nev, ertek in CSOPORT_ALAP.items():
                st.session_state.setdefault(k(nev, gid), ertek)
        return
    st.session_state.csoport_idk = []
    st.session_state.kovetkezo_id = 1
    for adatok in PELDAK["Vegyes halmozás – 8 + 4 EUR-raklap"]:
        csoport_hozzaad(**adatok)


allapot_init()


@st.cache_data(show_spinner="Rakodási elrendezés optimalizálása…", max_entries=64)
def optimalizal_gyorsitotarral(
    tetelek: tuple[Tetel, ...], hossz_cm: float, szelesseg_cm: float, idokorlat_s: float,
) -> PakolasEredmeny:
    return optimalizal(list(tetelek), hossz_cm, szelesseg_cm, idokorlat_s)


def pakolo(tetelek, hossz_cm, szelesseg_cm, idokorlat_s):
    return optimalizal_gyorsitotarral(tuple(tetelek), hossz_cm, szelesseg_cm, idokorlat_s)


# ---------------------------------------------------------------------------
# Fejléc és oldalsáv
# ---------------------------------------------------------------------------

st.markdown(
    """
<div class="app-fejlec">
  <h1>🚚 Intelligens fuvar- és rakománykalkulátor</h1>
  <p>Elméleti, fizikai, tömegalapú és elszámolási LDM · optimalizált raklapelrendezés · rakodási terv a fuvarozónak.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("🚛 Pótkocsi")
    st.selectbox(
        "Pótkocsitípus", list(POTKOCSI_TIPUSOK) + [EGYEDI_TIPUS], key="pk_tipus",
        on_change=potkocsi_tipus_valtozott,
        help="A típus kiválasztásakor a névleges belső méretek automatikusan betöltődnek.",
    )
    egyedi_pk = st.session_state.pk_tipus == EGYEDI_TIPUS
    st.number_input("Belső hossz (cm)", min_value=100.0, max_value=2500.0, step=10.0, format="%.0f",
                    key="pk_hossz", disabled=not egyedi_pk)
    st.number_input("Belső szélesség (cm)", min_value=100.0, max_value=350.0, step=1.0, format="%.0f",
                    key="pk_szel", disabled=not egyedi_pk,
                    help="Az elméleti LDM osztója (szélesség × 100) és az elhelyezés szélességi korlátja.")
    st.number_input("Belső magasság (cm)", min_value=50.0, max_value=450.0, step=5.0, format="%.0f",
                    key="pk_mag", disabled=not egyedi_pk)
    st.number_input("Hasznos teherbírás (kg)", min_value=100.0, max_value=60000.0, step=500.0, format="%.0f",
                    key="pk_teherbiras")
    st.checkbox(
        "A szabad rakodótér eltér a névlegestől", key="pk_szabad",
        help="Pl. kerékdob, rögzítősín, ajtókeret miatt. A rakodási terv a szabad méretekkel számol.",
    )
    if st.session_state.pk_szabad:
        st.number_input("Szabad hossz (cm)", min_value=1.0, max_value=2500.0, step=5.0, format="%.0f", key="pk_szabad_hossz")
        st.number_input("Szabad szélesség (cm)", min_value=1.0, max_value=350.0, step=1.0, format="%.0f", key="pk_szabad_szel")
        st.number_input("Szabad magasság (cm)", min_value=1.0, max_value=450.0, step=5.0, format="%.0f", key="pk_szabad_mag")

    with st.expander("⚖️ Elszámolási beállítások"):
        st.number_input(
            "Elszámolási index (kg / LDM)", min_value=1.0, max_value=10000.0, step=50.0, format="%.0f",
            key="kg_per_ldm",
            help="Díjszámítási tömegegyenérték: tömegalapú LDM = össztömeg ÷ index. Nem azonos a jármű terhelhetőségével.",
        )
        st.selectbox("Elszámolási LDM kerekítése", list(KEREKITESI_SZABALYOK), key="kerekites")
    with st.expander("⚙️ Optimalizálás"):
        st.slider(
            "Időkeret a pontos kereséshez (s)", min_value=1.0, max_value=15.0, step=1.0, key="idokorlat",
            help="Ha a keresés ennyi idő alatt nem zárul le, a program a legjobb talált elrendezést "
            "közelítő megoldásként jelöli.",
        )
    st.divider()
    st.button("↺ Alapértékek visszaállítása", on_click=alaphelyzet, width="stretch")
    st.caption("Az eredmények tervezési becslések, nem helyettesítik a fuvarozói visszaigazolást.")

ss = st.session_state
pk = Potkocsi(
    tipus=ss.pk_tipus,
    hossz_cm=float(ss.pk_hossz),
    szelesseg_cm=float(ss.pk_szel),
    magassag_cm=float(ss.pk_mag),
    teherbiras_kg=float(ss.pk_teherbiras),
    szabad_hossz_cm=float(ss.pk_szabad_hossz) if ss.pk_szabad else None,
    szabad_szelesseg_cm=float(ss.pk_szabad_szel) if ss.pk_szabad else None,
    szabad_magassag_cm=float(ss.pk_szabad_mag) if ss.pk_szabad else None,
)
pk_hibak = validal_potkocsi(pk)
if pk_hibak:
    for h in pk_hibak:
        st.error(h)
    st.stop()
cfg = ElszamolasiKonfig(kg_per_ldm=float(ss.kg_per_ldm), kerekites=ss.kerekites)

osszegzo_hely = st.container()
tab_rakomany, tab_visszaig, tab_dij, tab_eredmeny, tab_sugo = st.tabs(
    ["📦 Rakomány", "✅ Visszaigazolás", "💶 Fuvardíj", "📊 Összesítő", "ℹ️ Útmutató"]
)

# ---------------------------------------------------------------------------
# Rakomány fül – bemenet
# ---------------------------------------------------------------------------


def csoport_urlap(gid: int, sorszam: int) -> tuple[RakomanyCsoport | None, st.delta_generator.DeltaGenerator]:
    with st.container(border=True):
        fej, torles = st.columns([4, 1], vertical_alignment="center")
        fej.markdown(f"##### {sorszam}. rakománycsoport")
        torles.button("🗑️ Törlés", key=k("torol", gid), on_click=csoport_torol, args=(gid,), width="stretch")

        c1, c2 = st.columns(2)
        c1.text_input("Megnevezés", key=k("nev", gid), max_chars=60)
        c2.radio("Megadás módja", MODOK, key=k("mod", gid), horizontal=True, on_change=mod_valtozott, args=(gid,))

        szabvany = None
        if ss[k("mod", gid)] == MOD_SZABVANYOS:
            st.selectbox(
                "Raklaptípus", list(RAKLAP_TIPUSOK), key=k("tipus", gid), on_change=tipus_valtozott, args=(gid,),
                help="A hosszúság és szélesség automatikusan kitöltődik; a tényleges rakományméret "
                "(pl. túllógás) módosítható.",
            )
            szabvany = RAKLAP_TIPUSOK.get(ss[k("tipus", gid)])

        # Sorrend: darabszám, hosszúság, szélesség, magasság, tömeg, halmozhatóság.
        m0, m1 = st.columns(2)
        m2, m3 = st.columns(2)
        m0.number_input("Darabszám", min_value=1, max_value=10000, step=1, key=k("darab", gid))
        m1.number_input("Hosszúság (cm)", min_value=1.0, max_value=2000.0, step=1.0, format="%.0f", key=k("hossz", gid))
        m2.number_input("Szélesség (cm)", min_value=1.0, max_value=500.0, step=1.0, format="%.0f", key=k("szel", gid))
        m3.number_input("Magasság (cm)", min_value=1.0, max_value=500.0, step=1.0, format="%.0f", key=k("mag", gid),
                        help="Egy rakományegység teljes magassága (raklappal együtt).")

        darab = int(ss[k("darab", gid)])
        d1, d2 = st.columns(2)
        d1.radio("Tömeg megadása", [SULY_EGYSEG, SULY_OSSZES], key=k("suly_mod", gid), horizontal=True)
        if ss[k("suly_mod", gid)] == SULY_EGYSEG:
            d2.number_input("Egy egység tömege (kg)", min_value=0.1, max_value=50000.0, step=10.0, format="%.1f",
                            key=k("suly", gid))
            suly = float(ss[k("suly", gid)])
            d2.caption(f"Össztömeg: {szam(suly * darab, 0)} kg")
        else:
            d2.number_input("A csoport teljes tömege (kg)", min_value=0.1, max_value=500000.0, step=50.0,
                            format="%.1f", key=k("ossz_suly", gid))
            suly = float(ss[k("ossz_suly", gid)]) / darab
            d2.caption(f"Egységenként: {szam(suly, 1)} kg")

        h1, h2 = st.columns(2)
        h1.selectbox("Halmozhatóság", list(SZINT_OPCIOK), key=k("szint_opcio", gid))
        szint = SZINT_OPCIOK[ss[k("szint_opcio", gid)]]
        if szint is None:
            h1.number_input("Maximális szintszám", min_value=1, max_value=20, step=1, key=k("szint_egyedi", gid))
            szint = int(ss[k("szint_egyedi", gid)])
        h2.checkbox("90°-kal elforgatható (alapterületen)", key=k("forgathato", gid))
        raterheles = None
        if szint > 1:
            h2.checkbox("Halomban eltérő tájolás megengedett", key=k("valtakozo", gid),
                        help="Felváltva 90°-kal forgatott egységek a halomban. A program kiértékeli, "
                        "de nem tekinti automatikusan biztonságosnak.")
            h2.checkbox("Alsó egység felső terhelhetősége ismert", key=k("raterheles_ismert", gid))
            if ss[k("raterheles_ismert", gid)]:
                h2.number_input("Megengedett felső terhelés (kg)", min_value=0.0, max_value=100000.0, step=50.0,
                                format="%.0f", key=k("raterheles", gid))
                raterheles = float(ss[k("raterheles", gid)])

        tipus = ss[k("tipus", gid)] if ss[k("mod", gid)] == MOD_SZABVANYOS else "Egyedi rakomány"
        cs = RakomanyCsoport(
            nev=ss[k("nev", gid)].strip() or f"{sorszam}. csoport",
            hossz_cm=float(ss[k("hossz", gid)]),
            szelesseg_cm=float(ss[k("szel", gid)]),
            magassag_cm=float(ss[k("mag", gid)]),
            darab=darab,
            suly_kg=suly,
            max_szint=szint,
            forgathato=bool(ss[k("forgathato", gid)]),
            valtakozo_tajolas=bool(ss[k("valtakozo", gid)]) and szint > 1,
            raterheles_kg=raterheles,
            tipus=tipus,
            raklap_meret_cm=szabvany,
        )
        hibak = validal_csoport(cs)
        for h in hibak:
            st.error(h)
        if szabvany and cs.tulnyulas_cm > 0:
            st.markdown(uzenet_html(Uzenet(
                "info", f"A rakomány legfeljebb {cs.tulnyulas_cm:g} cm-rel túlnyúlik a raklapon – "
                "az elhelyezés a megadott tényleges méretekkel készül.")), unsafe_allow_html=True)
        eredmeny_hely = st.container()
    return (None if hibak else cs), eredmeny_hely


terv: RakodasiTerv | None = None
terv_hiba: str | None = None
hibas_csoportok = 0

with tab_rakomany:
    p1, p2 = st.columns([3, 1], vertical_alignment="bottom")
    p1.selectbox("Példa betöltése (a jelenlegi csoportokat lecseréli)", list(PELDAK), key="pelda")
    p2.button("Betöltés", on_click=pelda_betoltese, width="stretch")

    bal, jobb = st.columns([1.1, 1], gap="large")
    with bal:
        st.markdown('<div class="panel-cim">Bemenet – rakománycsoportok</div>', unsafe_allow_html=True)
        csoportok: list[RakomanyCsoport] = []
        helyek = []
        for sorszam, gid in enumerate(list(ss.csoport_idk), start=1):
            cs, hely = csoport_urlap(gid, sorszam)
            if cs is None:
                hibas_csoportok += 1
                continue
            csoportok.append(cs)
            helyek.append(hely)
        if not ss.csoport_idk:
            st.info("Nincs rakománycsoport. Adjon hozzá legalább egyet a számításhoz.")
        st.button("➕ Új rakománycsoport hozzáadása", on_click=csoport_hozzaad, type="primary", width="stretch")

    if csoportok:
        try:
            terv = tervez(csoportok, pk, cfg, float(ss.idokorlat), pakolo=pakolo)
        except ValueError as exc:
            terv_hiba = str(exc)

    if terv:
        for hely, c in zip(helyek, terv.csoportok):
            h = c.halmozas
            with hely:
                st.markdown(
                    f'<div class="mini">📐 <b>{h.helyek}</b> alapterületi hely · elméleti <b>{szam(c.elmeleti_ldm)}</b> LDM '
                    f"(halmozás nélkül {szam(c.elmeleti_ldm_nelkul)}) · {szam(c.csoport.ossz_suly_kg, 0)} kg · "
                    f"{h.alkalmazott_szint} szint, halommagasság {szam(h.halom_magassag_cm, 0)} cm · "
                    f"halmozás: <b>{h.statusz}</b></div>",
                    unsafe_allow_html=True,
                )
                uzenetek_megjelenitese(c.uzenetek)

    with jobb:
        st.markdown('<div class="panel-cim">Eredmények</div>', unsafe_allow_html=True)
        if terv_hiba:
            st.error(terv_hiba)
        elif not terv:
            st.info("Adjon meg legalább egy érvényes rakománycsoportot.")
        else:
            p, el = terv.pakolas, terv.elszamolas
            if hibas_csoportok:
                st.markdown(uzenet_html(Uzenet(
                    "hiba", f"{hibas_csoportok} rakománycsoport hibás adatok miatt kimaradt.")), unsafe_allow_html=True)
            jelveny = (
                '<span class="jelveny zold">bizonyított optimum</span>' if p.bizonyitott
                else '<span class="jelveny narancs">közelítő megoldás</span>'
            )
            st.markdown(
                '<div class="kartya-racs">'
                + kartya("1 · Elméleti LDM", szam(terv.elmeleti_ldm), f"területalapú alsó becslés · halmozás nélkül {szam(terv.elmeleti_ldm_nelkul)}")
                + kartya("2 · Fizikai LDM", szam(el.fizikai_ldm), f"rakodási hossz {szam(p.hasznalt_hossz_cm, 0)} cm · {jelveny}",
                         "narancs" if not p.belefer else "sotet")
                + kartya("3 · Tömegalapú LDM", szam(el.tomegalapu_ldm), f"{szam(terv.ossz_suly_kg, 0)} kg ÷ {szam(el.kg_per_ldm, 0)} kg/LDM")
                + kartya("4 · Elszámolási LDM", szam(el.elszamolasi_ldm),
                         f"{'tömeg' if el.meghatarozo == 'tömeg' else 'fizikai'} alapján · ≈ {szam(el.tomegegyenertek_kg, 0)} kg", "zold")
                + kartya("5 · Rakodótér kihasználtsága", f"{szam(p.sav_kihasznaltsag_pct, 1)} %",
                         f"a felhasznált sávon belül · pótkocsi hossza: {szam(terv.hossz_kihasznaltsag_pct, 1)} %")
                + kartya("6 · Szabad rakodóterület", f"{szam(p.sav_szabad_terulet_cm2 / 10000)} m²",
                         f"a sávon belül · a sávon túl: {szam(p.maradek_rakter_cm2 / 10000)} m²")
                + "</div>",
                unsafe_allow_html=True,
            )
            st.markdown("**8 · Figyelmeztetések és ellenőrzések**")
            osszes = list(terv.uzenetek)
            for c in terv.csoportok:
                osszes += [Uzenet(u.szint, f"{c.csoport.nev}: {u.szoveg}") for u in c.uzenetek if u.szint != "info"]
            if terv.berakhato and not any(u.szint in ("hiba", "figyelmeztetes") for u in osszes):
                osszes.insert(0, Uzenet("ok", "A megadott méretek, tömeg és halmozás alapján a rakomány a tervezett "
                                              "elrendezésben elhelyezhető."))
            uzenetek_megjelenitese(osszes)

    # Rakodási terv – teljes szélességben
    if terv and terv.pakolas.elhelyezesek:
        p = terv.pakolas
        st.markdown("#### 7 · Rakodási terv (felülnézet, méretarányos)")
        st.caption(
            f"Módszer: {p.modszer} · futásidő {szam(p.futasido_s, 2)} s · alsó korlát {szam(p.also_korlat_cm, 0)} cm. "
            "x: távolság a homlokfaltól, y: a bal oldalfaltól. Zöld szaggatott keret: felhasznált rakodósáv; "
            "narancs sraffozás: szabad terület a sávon belül; „×2”: egymásra helyezett egységek."
        )
        st.markdown(f'<div class="abra-keret">{rakodasi_svg(p, pk, terv.halmok, azonosito="teljes")}</div>',
                    unsafe_allow_html=True)
        st.markdown(
            '<div class="jelmagyarazat">'
            + "".join(f'<span><i style="background:{szin(c.index)}"></i>{html.escape(c.csoport.nev)}</span>'
                      for c in terv.csoportok if c.berakhato)
            + '<span><i style="background:#FFE0B2;border:1px solid #F57C00"></i>szabad terület</span></div>',
            unsafe_allow_html=True,
        )
        st.markdown("#### Rakodási terv három dimenzióban")
        nezet_3d = st.radio("3D nézet", ["Teljes rakodótér", "Csak a felhasznált sáv"], horizontal=True,
                            key="nezet_3d", label_visibility="collapsed")
        st.caption("Forgatás: húzás egérrel/ujjal · nagyítás: görgő/csippentés · egy egységre mutatva "
                   "látszik a helye és a szintje. Az egységek közötti 1 cm-es rés csak a jobb láthatóságot szolgálja.")
        st.plotly_chart(rakodasi_3d_abra(terv, csak_sav=nezet_3d == "Csak a felhasznált sáv"),
                        width="stretch", theme=None, key="abra_3d")
        geo_hibak = ellenoriz_elhelyezest(p.elhelyezesek, max(p.hasznalt_hossz_cm, 0.0), pk.rakter_szelesseg_cm)
        uzenetek_megjelenitese(
            [Uzenet("hiba", h) for h in geo_hibak] if geo_hibak
            else [Uzenet("ok", f"Geometriai ellenőrzés: {len(p.elhelyezesek)} alapterületi hely, nincs átfedés, "
                               f"minden egység a {szam(pk.rakter_szelesseg_cm, 0)} cm széles rakodótéren belül.")]
        )
        t1, t2 = st.columns([1.4, 1])
        with t1:
            st.markdown("**Elhelyezési koordináták (cm)**")
            st.dataframe(pd.DataFrame(elhelyezes_sorok(terv)), hide_index=True, width="stretch", height=260)
        with t2:
            st.markdown("**Szabad területek a felhasznált sávon belül**")
            if p.szabad_teruletek:
                st.dataframe(pd.DataFrame([
                    {"x (cm)": s.x_cm, "y (cm)": s.y_cm, "Hossz (cm)": s.hossz_cm, "Szélesség (cm)": s.szelesseg_cm,
                     "Terület (m²)": round(s.terulet_cm2 / 10000, 3)} for s in p.szabad_teruletek
                ]), hide_index=True, width="stretch", height=260)
            else:
                st.caption("A felhasznált sáv teljesen ki van töltve.")
            st.caption("A szabad területek nem feltétlenül alkalmasak más rakomány fogadására "
                       "(alak, hozzáférhetőség, rögzítés).")

# ---------------------------------------------------------------------------
# Visszaigazolás fül – tervezett / visszaigazolt / tényleges LDM
# ---------------------------------------------------------------------------

kovetes: LdmKovetes | None = None

with tab_visszaig:
    if not terv:
        st.info("Előbb adja meg a rakományt a **Rakomány** fülön.")
    else:
        st.markdown(
            "A tervezett LDM **nem garantált**: a fuvarozó írásos visszaigazolása és a rakodás utáni "
            "visszajelzés külön adatként szerepel."
        )
        f1, f2 = st.columns(2)
        fejlec = TervFejlec(
            hivatkozas=f1.text_input("Hivatkozás / ajánlatszám", key="hivatkozas"),
            viszonylat=f2.text_input("Viszonylat (felrakás – lerakás)", key="viszonylat"),
            fuvarozo=f1.text_input("Fuvarozó", key="fuvarozo"),
            keszitette=f2.text_input("Készítette", key="keszitette"),
        )

        st.markdown("##### B · Fuvarozói visszaigazolás")
        v1, v2, v3 = st.columns(3)
        allapot = v1.selectbox("Visszaigazolás állapota", ALLAPOTOK, key="allapot")
        visszaig_ldm = None
        datum = None
        if allapot in VISSZAIGAZOLT_ALLAPOTOK:
            ss.setdefault("visszaig_ldm", round(terv.fizikai_ldm, 2))
            visszaig_ldm = v2.number_input("Visszaigazolt LDM", min_value=0.0, max_value=100.0, step=0.1,
                                           format="%.2f", key="visszaig_ldm")
            datum = v3.date_input("Visszaigazolás dátuma", value=date.today(), key="visszaig_datum",
                                  format="YYYY.MM.DD")
        hivatkozas = st.text_input("Visszaigazolás hivatkozása (e-mail tárgya, dokumentumszám)", key="visszaig_hiv")

        st.markdown("##### C · Tényleges rakodás")
        tenyleges = None
        if st.checkbox("A rakodás megtörtént, van visszajelzés", key="rakodas_kesz"):
            ss.setdefault("tenyleges_ldm", round(terv.fizikai_ldm, 2))
            r1, r2 = st.columns([1, 2])
            tenyleges = r1.number_input("Tényleges rakodási LDM", min_value=0.0, max_value=100.0, step=0.1,
                                        format="%.2f", key="tenyleges_ldm")
            r2.text_area("Eltérés indoka (ha ismert)", key="elteres_indoka", height=80)

        kovetes = LdmKovetes(
            tervezett_fizikai_ldm=terv.fizikai_ldm,
            tervezett_elszamolasi_ldm=terv.elszamolas.elszamolasi_ldm,
            allapot=allapot,
            visszaigazolt_ldm=visszaig_ldm,
            visszaigazolas_datuma=datum,
            visszaigazolas_hivatkozas=hivatkozas,
            tenyleges_ldm=tenyleges,
            elteres_indoka=ss.get("elteres_indoka", "") if tenyleges is not None else "",
        )
        ve = kovetes.visszaigazolt_elteres
        te = kovetes.tenyleges_elteres
        st.markdown(
            '<div class="kartya-racs">'
            + kartya("A · Tervezett fizikai LDM", szam(terv.fizikai_ldm),
                     f"elszámolási: {szam(terv.elszamolas.elszamolasi_ldm)} · kalkulátor")
            + kartya("B · Visszaigazolt LDM", szam(visszaig_ldm) if visszaig_ldm is not None else "–",
                     allapot + (f" · eltérés {ve:+.2f}".replace(".", ",") if ve is not None else ""),
                     "zold" if kovetes.visszaigazolt else "narancs")
            + kartya("C · Tényleges rakodási LDM", szam(tenyleges) if tenyleges is not None else "–",
                     f"eltérés {te:+.2f}".replace(".", ",") if te is not None else "rakodás után rögzítendő")
            + kartya("Díjszámítás alapja", szam(kovetes.elszamolasi_alap[0]), kovetes.elszamolasi_alap[1], "sotet")
            + "</div>",
            unsafe_allow_html=True,
        )
        uzenetek_megjelenitese(elemzes(kovetes))

        with st.expander("Alkalmazott feltételezések", expanded=False):
            st.markdown("\n".join(f"- {f}" for f in terv.feltetelezesek))

        st.markdown("##### Rakodási terv a fuvarozónak")
        st.caption("A HTML-fájl böngészőben megnyitható, nyomtatható vagy PDF-be menthető, és tartalmazza "
                   "a fuvarozói visszaigazolás mezőit.")
        idobelyeg = datetime.now().strftime("%Y%m%d_%H%M")
        x1, x2 = st.columns(2)
        x1.download_button(
            "⬇️ Rakodási terv (HTML, nyomtatható)", rakodasi_terv_html(terv, fejlec).encode("utf-8"),
            file_name=f"rakodasi_terv_{idobelyeg}.html", mime="text/html", width="stretch", type="primary",
        )
        x2.download_button(
            "⬇️ Elhelyezési koordináták (CSV)",
            pd.DataFrame(elhelyezes_sorok(terv)).to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
            file_name=f"rakodasi_koordinatak_{idobelyeg}.csv", mime="text/csv", width="stretch",
        )

# ---------------------------------------------------------------------------
# Fuvardíj fül
# ---------------------------------------------------------------------------

dij: DijEredmeny | None = None

with tab_dij:
    st.markdown(
        uzenet_html(Uzenet(
            "info",
            "A díjszámítás becslés. Nem minden fuvarozó áraz LDM alapján – gyakori a "
            "viszonylatonkénti teljes kocsi ár, a tömeg- vagy térfogatalapú (kg, m³) díjazás, "
            "illetve a minimumdíj. Az eredményt a fuvarozói ajánlattal mindig vesse össze.",
        )),
        unsafe_allow_html=True,
    )

    p1, p2, p3 = st.columns(3)
    penznem = p1.radio("Pénznem", ["EUR", "HUF"], horizontal=True, key="penznem")
    egyseg = "€" if penznem == "EUR" else "Ft"
    dij_per_ldm = p2.number_input(
        f"Fuvardíj ({egyseg}/LDM)", min_value=0.0, step=10.0 if penznem == "EUR" else 1000.0,
        value=450.0 if penznem == "EUR" else 180000.0, format="%.2f" if penznem == "EUR" else "%.0f",
        key=f"dij_per_ldm_{penznem}",
    )
    minimum_dij = p3.number_input(
        f"Minimum fuvardíj ({egyseg})", min_value=0.0, step=10.0 if penznem == "EUR" else 1000.0,
        value=0.0, format="%.2f" if penznem == "EUR" else "%.0f", key=f"minimum_{penznem}",
        help="Ha az LDM-alapú díj ennél kevesebb, a minimumdíj érvényes. 0 = nincs.",
    )

    l1, l2 = st.columns([2, 1])
    ldm_alap = l1.radio(
        "Díjszámítás LDM-alapja",
        [LDM_ALAP_ELSZAMOLASI, LDM_ALAP_VISSZAIGAZOLT, LDM_ALAP_FIZIKAI, LDM_ALAP_ELMELETI, LDM_ALAP_KEZI],
        key="ldm_alap",
        help="Elszámolási LDM = MAX(fizikai LDM, össztömeg ÷ index). A rakodás után megadott tényleges LDM "
        "nem módosítja automatikusan a díjat.",
    )
    if ldm_alap == LDM_ALAP_KEZI:
        dij_ldm = l2.number_input(
            "Rakomány teljes LDM-értéke", min_value=0.0, max_value=100.0, step=0.1,
            value=round(terv.elszamolas.elszamolasi_ldm, 2) if terv else 0.0, format="%.2f", key="kezi_ldm",
        )
    else:
        if not terv:
            dij_ldm = 0.0
        elif ldm_alap == LDM_ALAP_VISSZAIGAZOLT:
            if kovetes and kovetes.visszaigazolt:
                dij_ldm = kovetes.visszaigazolt_ldm
            else:
                dij_ldm = terv.elszamolas.elszamolasi_ldm
                st.markdown(uzenet_html(Uzenet(
                    "figyelmeztetes", "Nincs fuvarozói visszaigazolás – a számítás a tervezett elszámolási "
                    "LDM-mel készül.")), unsafe_allow_html=True)
        elif ldm_alap == LDM_ALAP_FIZIKAI:
            dij_ldm = terv.fizikai_ldm
        elif ldm_alap == LDM_ALAP_ELMELETI:
            dij_ldm = terv.elmeleti_ldm
        else:
            dij_ldm = terv.elszamolas.elszamolasi_ldm
        l2.metric("Számítási alap", f"{szam(dij_ldm)} LDM")

    st.markdown("###### Felárak")
    f1, f2, f3, f4, f5 = st.columns(5)
    utdij = f1.number_input(f"Útdíj ({egyseg})", min_value=0.0, step=10.0, value=0.0, key=f"utdij_{penznem}")
    uzemanyag_pct = f2.number_input(
        "Üzemanyag-pótdíj (%)", min_value=0.0, max_value=100.0, step=0.5, value=0.0, key="uzemanyag_pct",
        help="Az alapdíj százalékában.",
    )
    varakozas_ora = f3.number_input("Várakozás (óra)", min_value=0.0, max_value=240.0, step=0.5, value=0.0, key="varakozas_ora")
    varakozas_oradij = f4.number_input(
        f"Várakozási díj ({egyseg}/óra)", min_value=0.0, step=5.0, value=0.0, key=f"varakozas_oradij_{penznem}",
    )
    egyeb_felar = f5.number_input(f"Egyéb felár ({egyseg})", min_value=0.0, step=10.0, value=0.0, key=f"egyeb_{penznem}")

    st.markdown("###### Fuvarszervezői árképzés")
    a1, a2 = st.columns([2, 1])
    arazas = a1.radio(
        "Árképzés módja", [ARAZAS_HASZONKULCS, ARAZAS_ARRES], key="arazas",
        help="Haszonkulcs: ár = költség × (1 + h). Árrés: ár = költség ÷ (1 − a). "
        "Ugyanaz a százalék a két módszerrel eltérő árat ad!",
    )
    szazalek = a2.number_input(
        "Haszonkulcs (%)" if arazas == ARAZAS_HASZONKULCS else "Árrés (%)",
        min_value=0.0, max_value=1000.0 if arazas == ARAZAS_HASZONKULCS else 99.9,
        step=1.0, value=15.0, key=f"szazalek_{arazas}",
    )

    try:
        dij = szamol_dij(DijParameterek(
            ldm=dij_ldm, dij_per_ldm=dij_per_ldm, penznem=penznem, minimum_dij=minimum_dij,
            utdij=utdij, uzemanyag_pct=uzemanyag_pct, varakozas_ora=varakozas_ora,
            varakozas_oradij=varakozas_oradij, egyeb_felar=egyeb_felar,
            arazas_mod="haszonkulcs" if arazas == ARAZAS_HASZONKULCS else "arres", szazalek=szazalek,
        ))
    except ValueError as exc:
        st.error(str(exc))

    if dij:
        alap_al = "minimumdíj alkalmazva" if dij.minimum_alkalmazva else f"{szam(dij.ldm)} LDM × {penz(dij_per_ldm, penznem)}"
        st.markdown(
            '<div class="kartya-racs">'
            + kartya("Alapfuvardíj", penz(dij.alapdij, penznem), alap_al)
            + kartya("Felárak összesen", penz(dij.felarak_osszesen, penznem))
            + kartya("Teljes beszerzési költség", penz(dij.beszerzesi_koltseg, penznem), "fuvarozói díj + felárak", "sotet")
            + kartya("Ügyfélnek ajánlott ár", penz(dij.ajanlott_ar, penznem), "nettó, ÁFA nélkül", "zold")
            + kartya("Várható bruttó fedezet", penz(dij.fedezet, penznem), "ajánlott ár − beszerzési költség", "zold")
            + kartya(
                "Fedezeti hányad (árrés)", f"{szam(dij.fedezeti_hanyad_pct, 1)} %",
                f"haszonkulcs: {szam(dij.haszonkulcs_pct, 1)} %", "zold",
            )
            + "</div>",
            unsafe_allow_html=True,
        )
        bontas = pd.DataFrame(
            [
                ("Alapfuvardíj", dij.alapdij),
                (f"Üzemanyag-pótdíj ({szam(uzemanyag_pct, 1)} %)", dij.uzemanyag_potdij),
                ("Útdíj", dij.utdij),
                (f"Várakozási díj ({szam(varakozas_ora, 1)} óra)", dij.varakozasi_dij),
                ("Egyéb felár", dij.egyeb_felar),
                ("Teljes beszerzési költség", dij.beszerzesi_koltseg),
                ("Fuvarszervezői fedezet", dij.fedezet),
                ("Ügyfélnek ajánlott ár", dij.ajanlott_ar),
            ],
            columns=["Tétel", "Összeg"],
        )
        bontas["Összeg"] = bontas["Összeg"].map(lambda x: penz(x, penznem))
        st.dataframe(bontas, hide_index=True, width="stretch")

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def csoportok_df(terv: RakodasiTerv) -> pd.DataFrame:
    sorok = []
    for c in terv.csoportok:
        cs, h = c.csoport, c.halmozas
        sorok.append({
            "Megnevezés": cs.nev,
            "Típus": cs.tipus,
            "Hosszúság (cm)": cs.hossz_cm,
            "Szélesség (cm)": cs.szelesseg_cm,
            "Magasság (cm)": cs.magassag_cm,
            "Darabszám": cs.darab,
            "Tömeg/db (kg)": round(cs.suly_kg, 2),
            "Össztömeg (kg)": round(cs.ossz_suly_kg, 2),
            "Max. szint": h.kert_szint,
            "Alkalmazott szint": h.alkalmazott_szint,
            "Halmozás állapota": h.statusz,
            "Forgatható": "igen" if cs.forgathato else "nem",
            "Alapterületi helyek": h.helyek,
            "Elméleti LDM halmozás nélkül": round(c.elmeleti_ldm_nelkul, 3),
            "Elméleti LDM": round(c.elmeleti_ldm, 3),
            "Berakható": "igen" if c.berakhato else "nem",
            "Megjegyzések": " | ".join(u.szoveg for u in c.uzenetek),
        })
    return pd.DataFrame(sorok)


def osszesito_df(terv: RakodasiTerv, dij: DijEredmeny | None, kovetes: LdmKovetes | None) -> pd.DataFrame:
    pk, p, el = terv.potkocsi, terv.pakolas, terv.elszamolas
    sorok = [
        ("Pótkocsi", f"{pk.tipus}: {pk.hossz_cm:g} × {pk.szelesseg_cm:g} × {pk.magassag_cm:g}", "cm"),
        ("Rakodótér (tervezéshez)", f"{pk.rakter_hossz_cm:g} × {pk.rakter_szelesseg_cm:g} × {pk.rakter_magassag_cm:g}", "cm"),
        ("Hasznos teherbírás", pk.teherbiras_kg, "kg"),
        ("Teljes darabszám", terv.darab, "db"),
        ("Alapterületi helyek", terv.helyek, "db"),
        ("Rakomány teljes tömege", round(terv.ossz_suly_kg, 1), "kg"),
        ("Elméleti LDM halmozás nélkül", round(terv.elmeleti_ldm_nelkul, 3), "LDM"),
        ("Elméleti LDM", round(terv.elmeleti_ldm, 3), "LDM"),
        ("Felhasznált rakodótér-hossz", p.hasznalt_hossz_cm, "cm"),
        ("Fizikai LDM", round(el.fizikai_ldm, 3), "LDM"),
        ("Elrendezés módszere", p.modszer, ""),
        ("Tömegalapú LDM", round(el.tomegalapu_ldm, 3), "LDM"),
        ("Elszámolási index", el.kg_per_ldm, "kg/LDM"),
        ("Elszámolási LDM", round(el.elszamolasi_ldm, 3), "LDM"),
        ("Tömegegyenérték", round(el.tomegegyenertek_kg, 1), "kg"),
        ("Rakodósáv kihasználtsága", round(p.sav_kihasznaltsag_pct, 1), "%"),
        ("Szabad terület a sávon belül", round(p.sav_szabad_terulet_cm2 / 10000, 3), "m²"),
        ("Megtakarított elméleti LDM (halmozás)", round(terv.megtakaritott_ldm, 3), "LDM"),
        ("Berakható", "igen" if terv.berakhato else "nem / nem igazolható", ""),
    ]
    if kovetes:
        sorok += [
            ("Visszaigazolás állapota", kovetes.allapot, ""),
            ("Visszaigazolt LDM", kovetes.visszaigazolt_ldm if kovetes.visszaigazolt_ldm is not None else "", "LDM"),
            ("Tényleges rakodási LDM", kovetes.tenyleges_ldm if kovetes.tenyleges_ldm is not None else "", "LDM"),
        ]
    if dij:
        pn = dij.penznem
        sorok += [
            ("Díjszámítás LDM-alapja", round(dij.ldm, 3), "LDM"),
            ("Alapfuvardíj", round(dij.alapdij, 2), pn),
            ("Felárak összesen", round(dij.felarak_osszesen, 2), pn),
            ("Teljes beszerzési költség", round(dij.beszerzesi_koltseg, 2), pn),
            ("Ügyfélnek ajánlott ár", round(dij.ajanlott_ar, 2), pn),
            ("Várható bruttó fedezet", round(dij.fedezet, 2), pn),
            ("Fedezeti hányad (árrés)", round(dij.fedezeti_hanyad_pct, 2), "%"),
            ("Haszonkulcs", round(dij.haszonkulcs_pct, 2), "%"),
        ]
    for u in terv.uzenetek:
        sorok.append(("Figyelmeztetés", u.szoveg, ""))
    return pd.DataFrame(sorok, columns=["Mutató", "Érték", "Egység"])


def csv_bajtok(df: pd.DataFrame) -> bytes:
    # Pontosvessző + tizedesvessző + BOM: a magyar Excel közvetlenül megnyitja.
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Összesítő fül
# ---------------------------------------------------------------------------

with tab_eredmeny:
    if not terv:
        st.info("Nincs érvényes rakománycsoport – adjon meg adatokat a **Rakomány** fülön.")
    else:
        el = terv.elszamolas
        dij_ertek = penz(dij.ajanlott_ar, dij.penznem) if dij else "–"
        fedezet_ertek = penz(dij.fedezet, dij.penznem) if dij else "–"
        st.markdown(
            '<div class="kartya-racs">'
            + kartya("Teljes raklap-/darabszám", f"{terv.darab} db", f"{terv.helyek} alapterületi hely")
            + kartya(
                "Rakomány teljes tömege", f"{szam(terv.ossz_suly_kg, 0)} kg",
                f"{szam(terv.suly_kihasznaltsag_pct, 0)} % a teherbírásból",
                "narancs" if terv.ossz_suly_kg > pk.teherbiras_kg else "",
            )
            + kartya("Elméleti LDM halmozás nélkül", szam(terv.elmeleti_ldm_nelkul), "területalapú")
            + kartya("Elméleti LDM halmozással", szam(terv.elmeleti_ldm), "területalapú")
            + kartya("Fizikai LDM", szam(el.fizikai_ldm), f"{szam(terv.pakolas.hasznalt_hossz_cm, 0)} cm rakodási hossz",
                     "narancs" if not terv.pakolas.belefer else "sotet")
            + kartya("Elszámolási LDM", szam(el.elszamolasi_ldm), f"tömegalapú: {szam(el.tomegalapu_ldm)}", "zold")
            + kartya("Megtakarított LDM", szam(terv.megtakaritott_ldm), f"halmozással · {szam(terv.megtakaritas_pct, 1)} %", "zold")
            + kartya("Becsült fuvardíj (ajánlott ár)", dij_ertek, "becslés, nettó", "zold")
            + kartya("Várható bruttó fedezet", fedezet_ertek,
                     f"fedezeti hányad: {szam(dij.fedezeti_hanyad_pct, 1)} %" if dij else "", "zold")
            + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### Kihasználtság")
        k1, k2 = st.columns(2)
        with k1:
            st.progress(min(terv.hossz_kihasznaltsag_pct, 100) / 100,
                        text=f"Rakodótér hossza (fizikai): {szam(terv.hossz_kihasznaltsag_pct, 1)} %")
            st.progress(min(terv.pakolas.sav_kihasznaltsag_pct, 100) / 100,
                        text=f"Felhasznált sáv területe: {szam(terv.pakolas.sav_kihasznaltsag_pct, 1)} %")
        with k2:
            st.progress(min(terv.suly_kihasznaltsag_pct, 100) / 100,
                        text=f"Teherbírás: {szam(terv.suly_kihasznaltsag_pct, 1)} %")

        st.markdown("#### Rakománycsoportok részletesen")
        df_cs = csoportok_df(terv)
        st.dataframe(
            df_cs.drop(columns=["Megjegyzések"]), hide_index=True, width="stretch",
            column_config={
                "Elméleti LDM halmozás nélkül": st.column_config.NumberColumn(format="%.2f"),
                "Elméleti LDM": st.column_config.NumberColumn(format="%.2f"),
            },
        )

        st.markdown("#### Letöltés")
        idobelyeg = datetime.now().strftime("%Y%m%d_%H%M")
        e1, e2 = st.columns(2)
        e1.download_button(
            "⬇️ Összesítő és díjkalkuláció (CSV)", csv_bajtok(osszesito_df(terv, dij, kovetes)),
            file_name=f"fuvarkalkulacio_osszesito_{idobelyeg}.csv", mime="text/csv", width="stretch",
        )
        e2.download_button(
            "⬇️ Rakománycsoportok (CSV)", csv_bajtok(df_cs),
            file_name=f"fuvarkalkulacio_csoportok_{idobelyeg}.csv", mime="text/csv", width="stretch",
        )

# ---------------------------------------------------------------------------
# Útmutató fül
# ---------------------------------------------------------------------------

with tab_sugo:
    st.markdown(
        r"""
### Használati útmutató

1. **Pótkocsi** (oldalsáv): válassza ki a típust (Normál 1360 × 245 × 270 cm, Semi-mega 285 cm, Mega 300 cm
   belmagasság). Ha a rakodótér egy része nem használható, jelölje be *„A szabad rakodótér eltér a névlegestől”*
   opciót, és adja meg a szabad méreteket.
2. **Rakomány** fül: vegyen fel rakománycsoportokat (azonos méretű egységek). Megadható a darabszám, a méret cm-ben,
   a tömeg egységenként vagy összesen, a halmozhatóság, a 90°-os forgathatóság, a halomban eltérő tájolás és az alsó
   egység megengedett felső terhelése. A *Példa betöltése* menüben a referenciapéldák is elérhetők.
3. A jobb oldali **Eredmények** panel minden módosítás után automatikusan újraszámol: elméleti, fizikai, tömegalapú
   és elszámolási LDM, kihasználtság, szabad terület, figyelmeztetések. Alatta a méretarányos rakodási terv,
   az elhelyezési koordináták és a szabad területek láthatók.
4. **Visszaigazolás** fül: töltse le a rakodási tervet (HTML) és küldje el a fuvarozónak. Rögzítse a visszaigazolás
   állapotát és a visszaigazolt LDM-et, majd a rakodás után a tényleges LDM-et és az eltérés indokát.
5. **Fuvardíj** fül: válassza ki a díjszámítás LDM-alapját (alapértelmezés: elszámolási LDM), a díjat és a felárakat.

### Számítási módszer

**Elméleti LDM** (területalapú alsó becslés):

$$\text{LDM}_{\text{elméleti}} = \frac{\text{darabszám} \times \text{hossz (cm)} \times \text{szélesség (cm)}}{\text{pótkocsi-szélesség (cm)} \times 100}$$

Halmozásnál a darabszám helyett az alapterületi helyek száma (⌈darab ÷ szint⌉) szerepel. Ez nem bizonyítja,
hogy a rakomány az adott hosszon fizikailag elhelyezhető.

**Fizikai LDM** = a rakodási tervben ténylegesen lefoglalt rakodótér-hossz (cm) ÷ 100. A program kétdimenziós
téglalap-elhelyezési optimalizálással keresi a legrövidebb elrendezést:

- heurisztikák (vegyes tájolású soros rakás, *skyline* elhelyezés több sorrendben) adnak egy érvényes elrendezést;
- alsó korlát: összes alapterület ÷ a ténylegesen kitölthető szélesség (pl. 70 és 100 cm-es méretekből a 245 cm-ből
  legfeljebb 240 cm tölthető ki), valamint az egymás mellé nem tehető egységek;
- pontos visszalépéses keresés a lehetséges hosszakon növekvő sorrendben – ha lefut, az eredmény a modellen belül
  **bizonyított optimum**; ha az időkeret lejár, a program **közelítő megoldásként** jelöli, és megadja az alsó korlátot.

Nincs korrekciós szorzó: a referenciapéldák (A: 4 db 140 × 100 cm → 240 cm; B: 7 db 70 × 100 cm → 210 cm)
a keresés eredményei, nem beégetett értékek.

**Tömegalapú LDM** = össztömeg ÷ elszámolási index (alapérték 1750 kg/LDM).
**Elszámolási LDM** = MAX(fizikai LDM, tömegalapú LDM), a beállított kerekítéssel. Az index díjszámítási
tömegegyenérték – nem azonos a jármű terhelhetőségével, amelyet a program külön ellenőriz.

**Halmozás**: a program ellenőrzi a halommagasságot a belmagassághoz, a legalsó egységre nehezedő tömeget a
megengedett felső terheléshez, a túlnyúlást és – ha megengedett – a felváltva forgatott halmozást (alátámasztás %,
túlnyúlás, befoglaló alapterület). Ha a teherbírási adat hiányzik, a halmozás állapota *„Nem igazolt”*.

**Tervezett, visszaigazolt és tényleges LDM**: a tervezett érték nem garantált. A fuvardíj nem módosul automatikusan
a rakodás után megadott LDM alapján; az elszámolást a visszaigazolt ajánlat és a szerződés határozza meg.

### Fuvardíj

| Tétel | Képlet |
|---|---|
| Alapfuvardíj | max(LDM × díj/LDM, minimumdíj) |
| Üzemanyag-pótdíj | alapdíj × pótdíj % |
| Várakozási díj | órák × óradíj |
| Beszerzési költség | alapdíj + összes felár |
| Fedezet | ajánlott ár − beszerzési költség |
| Fedezeti hányad (árrés) | fedezet ÷ ajánlott ár |

*Haszonkulcs* a költségre vetít (ár = költség × (1 + h)), *árrés* az eladási árra (ár = költség ÷ (1 − a)):
25 % haszonkulcs = 20 % árrés.

### Korlátok

A program nem modellezi a tengelyterhelést, a rakományrögzítést, a rakodási sorrendet és a különböző csoportok
egymásra helyezését; egyetlen megbízó rakományát tervezi. A szabad területek nem feltétlenül alkalmasak más
rakomány fogadására.
"""
    )

# ---------------------------------------------------------------------------
# Rövid összegző csík a fülek felett
# ---------------------------------------------------------------------------

with osszegzo_hely:
    if terv:
        allapot_jel = (
            '<span class="zold">✅ Elhelyezhető</span>' if terv.berakhato
            else '<span class="piros">⛔ Nem helyezhető el / nem igazolható</span>'
        )
        dij_csik = f"<span>💶 {penz(dij.ajanlott_ar, dij.penznem)}</span>" if dij else ""
        st.markdown(
            f'<div class="csik"><span>📦 {terv.darab} db</span><span>⚖️ {szam(terv.ossz_suly_kg, 0)} kg</span>'
            f'<span>📏 fizikai {szam(terv.fizikai_ldm)} LDM</span>'
            f'<span class="zold">🧾 elszámolási {szam(terv.elszamolas.elszamolasi_ldm)} LDM</span>{dij_csik}{allapot_jel}</div>',
            unsafe_allow_html=True,
        )
