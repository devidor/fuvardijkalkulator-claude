"""Intelligens fuvar- és rakománykalkulátor – Streamlit alkalmazás.

Indítás:  streamlit run app.py
"""

from __future__ import annotations

import html
from datetime import datetime

import pandas as pd
import streamlit as st

from kalkulacio import (
    RAKLAP_TIPUSOK,
    CsoportEredmeny,
    DijEredmeny,
    DijParameterek,
    Osszesites,
    Potkocsi,
    RakomanyCsoport,
    Uzenet,
    osszesit,
    szamol_csoport,
    szamol_dij,
    validal_csoport,
    validal_potkocsi,
)

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

SZINT_OPCIOK = {
    "1 szint – nem halmozható": 1,
    "2 szint – kettesével halmozható": 2,
    "3 szint – hármasával halmozható": 3,
    "4 szint – négyesével halmozható": 4,
    "Egyedi szintszám": None,
}

LDM_ALAP_ELMELETI = "Halmozás utáni elméleti LDM"
LDM_ALAP_ELRENDEZES = "Rakodási elrendezés szerinti hossz (m)"
LDM_ALAP_KEZI = "Kézi megadás"

ARAZAS_HASZONKULCS = "Haszonkulcs (beszerzési költségre vetítve)"
ARAZAS_ARRES = "Árrés (eladási árra vetítve)"

CSOPORT_SZINEK = ["#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#00ACC1", "#6D4C41", "#E53935", "#3949AB"]

CSOPORT_ALAP = {
    "nev": "Rakomány",
    "mod": MOD_SZABVANYOS,
    "tipus": "EUR-raklap (120 × 80 cm)",
    "hossz": 120.0,
    "szel": 80.0,
    "mag": 120.0,
    "darab": 1,
    "suly": 300.0,
    "szint_opcio": "1 szint – nem halmozható",
    "szint_egyedi": 5,
    "raterheles": 0.0,
    "forgathato": True,
}

# ---------------------------------------------------------------------------
# Megjelenés
# ---------------------------------------------------------------------------

st.markdown(
    """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1250px;}
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
.potkocsi-rajz svg {width: 100%; height: auto; display: block;}
.jelmagyarazat {display: flex; flex-wrap: wrap; gap: .8rem; font-size: .85rem; margin-top: .4rem;}
.jelmagyarazat i {display: inline-block; width: .9rem; height: .9rem; border-radius: 3px; margin-right: .3rem; vertical-align: -2px;}
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
    return f'<div class="uzenet {u.szint}">{ikon} {elotag}{html.escape(u.szoveg)}</div>'


def uzenetek_megjelenitese(uzenetek: list[Uzenet], elotag: str = "") -> None:
    if uzenetek:
        st.markdown("".join(uzenet_html(u, elotag) for u in uzenetek), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Munkamenet-állapot
# ---------------------------------------------------------------------------


def k(nev: str, gid: int) -> str:
    return f"{nev}_{gid}"


def csoport_hozzaad(**ertekek) -> None:
    gid = st.session_state.kovetkezo_id
    st.session_state.kovetkezo_id += 1
    adatok = {**CSOPORT_ALAP, "nev": f"Rakomány {len(st.session_state.csoport_idk) + 1}", **ertekek}
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


def alaphelyzet() -> None:
    for kulcs in list(st.session_state.keys()):
        del st.session_state[kulcs]


def allapot_init() -> None:
    if "csoport_idk" in st.session_state:
        # A feltételesen megjelenő mezők értéke elveszhet, amíg rejtve vannak.
        for gid in st.session_state.csoport_idk:
            for nev, ertek in CSOPORT_ALAP.items():
                st.session_state.setdefault(k(nev, gid), ertek)
        return
    st.session_state.csoport_idk = []
    st.session_state.kovetkezo_id = 1
    # Példa a vegyes halmozhatóságra
    csoport_hozzaad(
        nev="EUR-raklap, halmozható", darab=8, mag=120.0, suly=350.0,
        szint_opcio="2 szint – kettesével halmozható", raterheles=800.0,
    )
    csoport_hozzaad(nev="EUR-raklap, nem halmozható", darab=4, mag=180.0, suly=600.0)


allapot_init()

# ---------------------------------------------------------------------------
# Fejléc és oldalsáv
# ---------------------------------------------------------------------------

st.markdown(
    """
<div class="app-fejlec">
  <h1>🚚 Intelligens fuvar- és rakománykalkulátor</h1>
  <p>Rakományméter (LDM), halmozhatóság, rakodási helyigény és becsült fuvardíj egy helyen.</p>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("🚛 Pótkocsi")
    st.caption("Alapértelmezés: 13,6 m-es nyerges pótkocsi.")
    pk = Potkocsi(
        belso_hossz_m=st.number_input(
            "Belső hossz (m)", min_value=1.0, max_value=25.0, value=13.6, step=0.1, format="%.2f",
        ),
        belso_szelesseg_m=st.number_input(
            "Belső szélesség (m)", min_value=1.0, max_value=3.5, value=2.4, step=0.01, format="%.2f",
            help="Az LDM-képlet osztója és a keresztirányú elférés alapja. "
            "Az iparági szokás 2,4 m (3 EUR-raklap keresztben).",
        ),
        belso_magassag_m=st.number_input(
            "Belső magasság (m)", min_value=0.5, max_value=4.5, value=2.7, step=0.05, format="%.2f",
        ),
        teherbiras_kg=st.number_input(
            "Hasznos teherbírás (kg)", min_value=100.0, max_value=60000.0, value=24000.0, step=500.0,
            format="%.0f",
        ),
    )
    st.divider()
    st.button("↺ Alapértékek visszaállítása", on_click=alaphelyzet, width="stretch")
    st.caption("Az eredmények tájékoztató jellegű becslések, nem helyettesítik a rakodási tervet.")

pk_hibak = validal_potkocsi(pk)
if pk_hibak:
    for h in pk_hibak:
        st.error(h)
    st.stop()

osszegzo_hely = st.container()
tab_rakomany, tab_dij, tab_eredmeny, tab_sugo = st.tabs(
    ["📦 Rakomány", "💶 Fuvardíj", "📊 Eredmények", "ℹ️ Módszertan"]
)

# ---------------------------------------------------------------------------
# Rakomány fül
# ---------------------------------------------------------------------------


def csoport_urlap(gid: int, sorszam: int) -> tuple[RakomanyCsoport | None, list[str]]:
    ss = st.session_state
    with st.container(border=True):
        fej, torles = st.columns([4, 1], vertical_alignment="center")
        fej.markdown(f"##### {sorszam}. rakománycsoport")
        torles.button(
            "🗑️ Törlés", key=k("torol", gid), on_click=csoport_torol, args=(gid,), width="stretch",
        )

        c1, c2 = st.columns(2)
        c1.text_input("Megnevezés", key=k("nev", gid), max_chars=60)
        c2.radio(
            "Megadás módja", MODOK, key=k("mod", gid), horizontal=True,
            on_change=mod_valtozott, args=(gid,),
        )

        szabvany = None
        if ss[k("mod", gid)] == MOD_SZABVANYOS:
            st.selectbox(
                "Raklaptípus", list(RAKLAP_TIPUSOK), key=k("tipus", gid),
                on_change=tipus_valtozott, args=(gid,),
                help="A hosszúság és szélesség automatikusan kitöltődik, de a tényleges "
                "rakományméret (pl. túllógás) módosítható.",
            )
            szabvany = RAKLAP_TIPUSOK.get(ss[k("tipus", gid)])

        m1, m2, m3 = st.columns(3)
        m1.number_input("Hosszúság (cm)", min_value=1.0, max_value=2000.0, step=1.0, format="%.0f", key=k("hossz", gid))
        m2.number_input("Szélesség (cm)", min_value=1.0, max_value=500.0, step=1.0, format="%.0f", key=k("szel", gid))
        m3.number_input(
            "Magasság (cm)", min_value=1.0, max_value=500.0, step=1.0, format="%.0f", key=k("mag", gid),
            help="Egy rakományegység teljes magassága (raklappal együtt).",
        )

        d1, d2 = st.columns(2)
        d1.number_input("Darabszám", min_value=1, max_value=10000, step=1, key=k("darab", gid))
        d2.number_input(
            "Egy darab súlya (kg)", min_value=0.1, max_value=50000.0, step=10.0, format="%.1f",
            key=k("suly", gid),
        )

        h1, h2 = st.columns(2)
        h1.selectbox("Halmozhatóság", list(SZINT_OPCIOK), key=k("szint_opcio", gid))
        h2.number_input(
            "Max. ráterhelés egységenként (kg)", min_value=0.0, max_value=100000.0, step=50.0,
            format="%.0f", key=k("raterheles", gid),
            help="Mekkora tömeg helyezhető biztonságosan egy egységre. 0 = nincs megadva (nem ellenőrzött).",
        )
        szint = SZINT_OPCIOK[ss[k("szint_opcio", gid)]]
        if szint is None:
            h1.number_input("Szintek száma", min_value=1, max_value=20, step=1, key=k("szint_egyedi", gid))
            szint = int(ss[k("szint_egyedi", gid)])
        st.checkbox("90°-kal elforgatva is rakható", key=k("forgathato", gid))

        tipus = ss[k("tipus", gid)] if ss[k("mod", gid)] == MOD_SZABVANYOS else "Egyedi rakomány"
        cs = RakomanyCsoport(
            nev=ss[k("nev", gid)].strip() or f"{sorszam}. csoport",
            hossz_cm=float(ss[k("hossz", gid)]),
            szelesseg_cm=float(ss[k("szel", gid)]),
            magassag_cm=float(ss[k("mag", gid)]),
            darab=int(ss[k("darab", gid)]),
            suly_kg=float(ss[k("suly", gid)]),
            szint=szint,
            max_raterheles_kg=float(ss[k("raterheles", gid)]),
            forgathato=bool(ss[k("forgathato", gid)]),
            tipus=tipus,
        )
        hibak = validal_csoport(cs)
        for h in hibak:
            st.error(h)
        if szabvany and (cs.hossz_cm > szabvany[0] or cs.szelesseg_cm > szabvany[1]):
            st.markdown(
                uzenet_html(Uzenet("info", "A rakomány túllóg a raklapon – a számítás a megadott tényleges méretekkel készül.")),
                unsafe_allow_html=True,
            )
        return (None if hibak else cs), hibak


def csoport_mini_eredmeny(e: CsoportEredmeny) -> None:
    elr = f"{szam(e.elrendezes_hossz_m)} m" if e.elrendezes else "nem rakható"
    st.markdown(
        f'<div class="mini">📐 <b>{e.helyek}</b> alapterületi hely · '
        f'<b>{szam(e.ldm)}</b> LDM (halmozás nélkül {szam(e.ldm_halmozas_nelkul)}) · '
        f"elrendezés: <b>{elr}</b> · {szam(e.ossz_suly_kg, 0)} kg · "
        f"{e.alkalmazott_szint} szint, halommagasság {szam(e.halom_magassag_cm, 0)} cm</div>",
        unsafe_allow_html=True,
    )
    uzenetek_megjelenitese(e.uzenetek)


eredmenyek: list[CsoportEredmeny] = []
hibas_csoportok = 0

with tab_rakomany:
    st.markdown(
        "Vegyen fel egy vagy több **rakománycsoportot**. Minden csoport külön számítódik "
        "(saját méret, darabszám és halmozhatóság), majd az eredmények összesítődnek."
    )
    for sorszam, gid in enumerate(list(st.session_state.csoport_idk), start=1):
        cs, hibak = csoport_urlap(gid, sorszam)
        if cs is None:
            hibas_csoportok += 1
            continue
        try:
            e = szamol_csoport(cs, pk)
        except ValueError as exc:
            st.error(str(exc))
            hibas_csoportok += 1
            continue
        eredmenyek.append(e)
        csoport_mini_eredmeny(e)

    if not st.session_state.csoport_idk:
        st.info("Nincs rakománycsoport. Adjon hozzá legalább egyet a számításhoz.")
    st.button("➕ Új rakománycsoport hozzáadása", on_click=csoport_hozzaad, type="primary", width="stretch")

ossz: Osszesites | None = osszesit(eredmenyek, pk) if eredmenyek else None

# ---------------------------------------------------------------------------
# Fuvardíj fül
# ---------------------------------------------------------------------------

dij: DijEredmeny | None = None
dij_hiba: str | None = None

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
        [LDM_ALAP_ELMELETI, LDM_ALAP_ELRENDEZES, LDM_ALAP_KEZI],
        key="ldm_alap",
        help="Az elrendezés szerinti hossz a nem teljes sorokat is figyelembe veszi, ezért óvatosabb becslés.",
    )
    if ldm_alap == LDM_ALAP_KEZI:
        dij_ldm = l2.number_input(
            "Rakomány teljes LDM-értéke", min_value=0.0, max_value=100.0, step=0.1,
            value=round(ossz.ldm, 2) if ossz else 0.0, format="%.2f", key="kezi_ldm",
        )
    elif ldm_alap == LDM_ALAP_ELRENDEZES:
        dij_ldm = ossz.elrendezes_hossz_m if ossz else 0.0
        l2.metric("Számítási alap", f"{szam(dij_ldm)} LDM")
    else:
        dij_ldm = ossz.ldm if ossz else 0.0
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
        dij_hiba = str(exc)
        st.error(dij_hiba)

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
# Rakodási vázlat
# ---------------------------------------------------------------------------


def rakodasi_svg(eredmenyek: list[CsoportEredmeny], pk: Potkocsi) -> str:
    """Felülnézeti vázlat a soros elrendezésről (méretarányos, cm egységben)."""
    lt, w = pk.belso_hossz_m * 100, pk.belso_szelesseg_m * 100
    teljes = sum((e.elrendezes_hossz_m or 0) * 100 for e in eredmenyek)
    szelesseg = max(lt, teljes)
    margo = 20
    elemek = [
        f'<rect x="0" y="0" width="{lt}" height="{w}" fill="#F4F8FC" stroke="#0B2545" stroke-width="4" rx="6"/>'
    ]
    if teljes > lt:
        elemek.append(
            f'<rect x="{lt}" y="0" width="{teljes - lt}" height="{w}" fill="#FDECEA" '
            f'stroke="#C62828" stroke-width="4" stroke-dasharray="14 8"/>'
        )
    x = 0.0
    for i, e in enumerate(eredmenyek):
        if not e.elrendezes:
            continue
        szin = CSOPORT_SZINEK[i % len(CSOPORT_SZINEK)]
        halmok = e.egysegek_helyenkent()
        hely_index = 0
        for sor in e.elrendezes.sorok:
            for j in range(sor.helyek):
                y = j * sor.keresztben_cm
                db = halmok[hely_index] if hely_index < len(halmok) else 1
                hely_index += 1
                elemek.append(
                    f'<rect x="{x + 2:.1f}" y="{y + 2:.1f}" width="{sor.melyseg_cm - 4:.1f}" '
                    f'height="{sor.keresztben_cm - 4:.1f}" fill="{szin}" fill-opacity="0.82" '
                    f'stroke="#fff" stroke-width="2" rx="4"/>'
                )
                if db > 1:
                    elemek.append(
                        f'<text x="{x + sor.melyseg_cm / 2:.1f}" y="{y + sor.keresztben_cm / 2 + 9:.1f}" '
                        f'text-anchor="middle" font-size="26" font-weight="700" fill="#fff" '
                        f'font-family="sans-serif">×{db}</text>'
                    )
            x += sor.melyseg_cm
    elemek.append(
        f'<text x="{lt - 8}" y="{w + 34}" text-anchor="end" font-size="26" fill="#4A6380" '
        f'font-family="sans-serif">{szam(pk.belso_hossz_m)} m</text>'
    )
    elemek.append(
        f'<text x="0" y="{w + 34}" font-size="26" fill="#4A6380" font-family="sans-serif">◀ homlokfal</text>'
    )
    return (
        f'<div class="potkocsi-rajz"><svg viewBox="{-margo} {-margo} {szelesseg + 2 * margo} {w + 2 * margo + 30}" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Rakodási vázlat">{"".join(elemek)}</svg></div>'
    )


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def csoportok_df(eredmenyek: list[CsoportEredmeny]) -> pd.DataFrame:
    sorok = []
    for e in eredmenyek:
        cs = e.csoport
        sorok.append({
            "Megnevezés": cs.nev,
            "Típus": cs.tipus,
            "Hosszúság (cm)": cs.hossz_cm,
            "Szélesség (cm)": cs.szelesseg_cm,
            "Magasság (cm)": cs.magassag_cm,
            "Darabszám": cs.darab,
            "Súly/db (kg)": cs.suly_kg,
            "Össztömeg (kg)": e.ossz_suly_kg,
            "Kért szint": e.kert_szint,
            "Alkalmazott szint": e.alkalmazott_szint,
            "Alapterületi helyek": e.helyek,
            "LDM halmozás nélkül": round(e.ldm_halmozas_nelkul, 3),
            "LDM halmozással": round(e.ldm, 3),
            "Elrendezés hossza (m)": round(e.elrendezes_hossz_m, 3) if e.elrendezes else None,
            "Elrendezés": e.elrendezes.leiras if e.elrendezes else "nem rakható",
            "Berakható": "igen" if e.berakhato else "nem",
            "Megjegyzések": " | ".join(u.szoveg for u in e.uzenetek),
        })
    return pd.DataFrame(sorok)


def osszesito_df(ossz: Osszesites, pk: Potkocsi, dij: DijEredmeny | None) -> pd.DataFrame:
    sorok = [
        ("Pótkocsi belső mérete", f"{pk.belso_hossz_m:g} × {pk.belso_szelesseg_m:g} × {pk.belso_magassag_m:g}", "m"),
        ("Hasznos teherbírás", pk.teherbiras_kg, "kg"),
        ("Teljes darabszám", ossz.darab, "db"),
        ("Rakomány teljes tömege", ossz.ossz_suly_kg, "kg"),
        ("Alapterületi helyek", ossz.helyek, "db"),
        ("LDM halmozás nélkül", round(ossz.ldm_halmozas_nelkul, 3), "LDM"),
        ("LDM halmozás után (elméleti)", round(ossz.ldm, 3), "LDM"),
        ("Megtakarított LDM", round(ossz.megtakaritott_ldm, 3), "LDM"),
        ("Helymegtakarítás", round(ossz.megtakaritas_pct, 1), "%"),
        ("Rakodási elrendezés hossza", round(ossz.elrendezes_hossz_m, 3), "m"),
        ("Hosszkihasználtság (elméleti)", round(ossz.hossz_kihasznaltsag_pct, 1), "%"),
        ("Tömegkihasználtság", round(ossz.suly_kihasznaltsag_pct, 1), "%"),
        ("Berakható", "igen" if ossz.berakhato else "nem / nem igazolható", ""),
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
    for u in ossz.uzenetek:
        sorok.append(("Figyelmeztetés", u.szoveg, ""))
    return pd.DataFrame(sorok, columns=["Mutató", "Érték", "Egység"])


def csv_bajtok(df: pd.DataFrame) -> bytes:
    # Pontosvessző + tizedesvessző + BOM: a magyar Excel közvetlenül megnyitja.
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


# ---------------------------------------------------------------------------
# Eredmények fül
# ---------------------------------------------------------------------------

with tab_eredmeny:
    if not ossz:
        st.info("Nincs érvényes rakománycsoport – adjon meg adatokat a **Rakomány** fülön.")
    else:
        if hibas_csoportok:
            st.markdown(
                uzenet_html(Uzenet("hiba", f"{hibas_csoportok} rakománycsoport hibás adatok miatt kimaradt a számításból.")),
                unsafe_allow_html=True,
            )
        dij_ertek = penz(dij.ajanlott_ar, dij.penznem) if dij else "–"
        fedezet_ertek = penz(dij.fedezet, dij.penznem) if dij else "–"
        st.markdown(
            '<div class="kartya-racs">'
            + kartya("Teljes raklap-/darabszám", f"{ossz.darab} db", f"{ossz.helyek} alapterületi hely")
            + kartya(
                "Rakomány teljes tömege", f"{szam(ossz.ossz_suly_kg, 0)} kg",
                f"{szam(ossz.suly_kihasznaltsag_pct, 0)} % a teherbírásból",
                "narancs" if ossz.ossz_suly_kg > pk.teherbiras_kg else "",
            )
            + kartya("LDM halmozás nélkül", f"{szam(ossz.ldm_halmozas_nelkul)} LDM", "eredeti, elméleti")
            + kartya(
                "LDM halmozás után", f"{szam(ossz.ldm)} LDM", f"elrendezés szerint: {szam(ossz.elrendezes_hossz_m)} m",
                "narancs" if ossz.ldm > pk.belso_hossz_m else "zold",
            )
            + kartya("Megtakarított LDM", f"{szam(ossz.megtakaritott_ldm)} LDM", "halmozásnak köszönhetően", "zold")
            + kartya("Helymegtakarítás", f"{szam(ossz.megtakaritas_pct, 1)} %", "", "zold")
            + kartya("Becsült fuvardíj (ajánlott ár)", dij_ertek, "becslés, nettó", "zold")
            + kartya("Várható bruttó fedezet", fedezet_ertek, f"fedezeti hányad: {szam(dij.fedezeti_hanyad_pct, 1)} %" if dij else "", "zold")
            + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### Kihasználtság")
        k1, k2 = st.columns(2)
        with k1:
            hossz_pct = min(ossz.hossz_kihasznaltsag_pct, 100) / 100
            st.progress(hossz_pct, text=f"Rakfelület (elméleti LDM): {szam(ossz.hossz_kihasznaltsag_pct, 1)} %")
            elr_pct = ossz.elrendezes_hossz_m / pk.belso_hossz_m * 100
            st.progress(min(elr_pct, 100) / 100, text=f"Rakfelület (elrendezés szerint): {szam(elr_pct, 1)} %")
        with k2:
            st.progress(min(ossz.suly_kihasznaltsag_pct, 100) / 100, text=f"Teherbírás: {szam(ossz.suly_kihasznaltsag_pct, 1)} %")

        st.markdown("#### Ellenőrzések")
        osszes_uzenet = list(ossz.uzenetek)
        for e in eredmenyek:
            for u in e.uzenetek:
                if u.szint != "info":
                    osszes_uzenet.append(Uzenet(u.szint, f"{e.csoport.nev}: {u.szoveg}"))
        if ossz.berakhato and not any(u.szint != "info" for u in osszes_uzenet):
            osszes_uzenet.insert(0, Uzenet(
                "ok", "A megadott méretek, tömeg és halmozás alapján a rakomány elméletileg berakható.",
            ))
        uzenetek_megjelenitese(osszes_uzenet)

        st.markdown("#### Rakodási vázlat (felülnézet)")
        st.caption(
            "Egyszerűsített soros elrendezés csoportonként, a homlokfaltól indulva. "
            "A „×2” stb. jelölés a halmozott egységek számát mutatja. Nem helyettesíti a rakodási tervet."
        )
        st.markdown(rakodasi_svg(eredmenyek, pk), unsafe_allow_html=True)
        st.markdown(
            '<div class="jelmagyarazat">'
            + "".join(
                f'<span><i style="background:{CSOPORT_SZINEK[i % len(CSOPORT_SZINEK)]}"></i>{html.escape(e.csoport.nev)}</span>'
                for i, e in enumerate(eredmenyek)
            )
            + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("#### Rakománycsoportok részletesen")
        df_cs = csoportok_df(eredmenyek)
        st.dataframe(
            df_cs.drop(columns=["Megjegyzések"]), hide_index=True, width="stretch",
            column_config={
                "LDM halmozás nélkül": st.column_config.NumberColumn(format="%.2f"),
                "LDM halmozással": st.column_config.NumberColumn(format="%.2f"),
                "Elrendezés hossza (m)": st.column_config.NumberColumn(format="%.2f"),
            },
        )

        st.markdown("#### Letöltés")
        idobelyeg = datetime.now().strftime("%Y%m%d_%H%M")
        e1, e2 = st.columns(2)
        e1.download_button(
            "⬇️ Összesítő és díjkalkuláció (CSV)", csv_bajtok(osszesito_df(ossz, pk, dij)),
            file_name=f"fuvarkalkulacio_osszesito_{idobelyeg}.csv", mime="text/csv", width="stretch",
        )
        e2.download_button(
            "⬇️ Rakománycsoportok (CSV)", csv_bajtok(df_cs),
            file_name=f"fuvarkalkulacio_csoportok_{idobelyeg}.csv", mime="text/csv", width="stretch",
        )

# ---------------------------------------------------------------------------
# Módszertan fül
# ---------------------------------------------------------------------------

with tab_sugo:
    st.markdown(
        r"""
### Hogyan számol a program?

**1. Rakományméter (LDM)** – a rakomány által elfoglalt rakfelület-hossz a pótkocsi teljes szélességére vetítve:

$$\text{LDM} = \frac{\text{hosszúság (m)} \times \text{szélesség (m)}}{\text{pótkocsi belső szélessége (m)}}$$

Egy EUR-raklap: 1,2 × 0,8 ÷ 2,4 = **0,4 LDM**.

**2. Halmozás** – csoportonként:

- Alapterületi helyek = ⌈ darabszám ÷ halmozási szint ⌉ (felfelé kerekítve)
- LDM = alapterületi helyek × egy egység alapterülete ÷ pótkocsi szélessége

Példa: 10 EUR-raklap, 2 szint → 10 ÷ 2 = 5 hely → 5 × 0,4 = **2,0 LDM**.

**3. Biztonságos halmozhatóság** – a kért szintszámot a program csak akkor fogadja el, ha
- a halom magassága (szint × egységmagasság) nem haladja meg a belmagasságot, és
- a legalsó egységre nehezedő tömeg ((szint − 1) × egységsúly) nem haladja meg a megadott ráterhelhetőséget.

Ha valamelyik nem teljesül, figyelmeztet, és a legnagyobb megengedett szinttel számol.

**4. Vegyes rakomány** – minden csoport külön számítódik, majd összeadódik
(pl. 8 db 2 szinten = 1,6 LDM + 4 db nem halmozva = 1,6 LDM → **3,2 LDM**).

**5. Elméleti LDM ≠ tényleges helyigény** – a képlet a teljes szélesség tökéletes kihasználását feltételezi.
A program ezért egy **soros rakodási elrendezést** is tervez (hosszirányban és 90°-kal elforgatva, a kettőt keverve),
amely figyelembe veszi a nem teljes sorokat és a keresztirányú hézagokat. Például 4 nem halmozott EUR-raklap
elméletileg 1,6 LDM, és elforgatva 2 sorban (2 × 0,8 m) valóban 1,6 m-en elfér – de ha nem forgatható,
hosszirányban 2 sor × 1,2 m = 2,4 m kell. A tényleges rakodásnál a tengelyterhelés, a rakományrögzítés
és a csoportok egymás mellé rakása is számít – ezeket a program nem modellezi.

**6. Fuvardíj** – becslés:

| Tétel | Képlet |
|---|---|
| Alapfuvardíj | max(LDM × díj/LDM, minimumdíj) |
| Üzemanyag-pótdíj | alapdíj × pótdíj % |
| Várakozási díj | órák × óradíj |
| Beszerzési költség | alapdíj + összes felár |
| Fedezet | ajánlott ár − beszerzési költség |
| Fedezeti hányad (árrés) | fedezet ÷ ajánlott ár |

**Haszonkulcs vs. árrés** – két különböző fogalom:

- *Haszonkulcs* a **költségre** vetít: ár = költség × (1 + h). 1 000 € költség, 25 % haszonkulcs → 1 250 €.
- *Árrés* az **eladási árra** vetít: ár = költség ÷ (1 − a). 1 000 € költség, 20 % árrés → 1 250 €.

Tehát 25 % haszonkulcs = 20 % árrés. A program mindkét mutatót megjeleníti.

> ⚠️ Nem minden fuvarozó áraz LDM alapján: gyakori a teljes kocsis viszonylati ár, a kg- vagy m³-alapú díj
> (gyűjtőfuvarban fuvarozónként eltérő LDM–kg átváltással) és a minimumdíj. Az eredmény tájékoztató jellegű.
"""
    )

# ---------------------------------------------------------------------------
# Rövid összegző csík a fülek felett
# ---------------------------------------------------------------------------

with osszegzo_hely:
    if ossz:
        allapot = (
            '<span class="zold">✅ Berakható</span>' if ossz.berakhato
            else '<span class="piros">⛔ Nem berakható / nem igazolható</span>'
        )
        dij_csik = f"<span>💶 {penz(dij.ajanlott_ar, dij.penznem)}</span>" if dij else ""
        st.markdown(
            f'<div class="csik"><span>📦 {ossz.darab} db</span><span>⚖️ {szam(ossz.ossz_suly_kg, 0)} kg</span>'
            f'<span class="zold">📏 {szam(ossz.ldm)} LDM</span>{dij_csik}{allapot}</div>',
            unsafe_allow_html=True,
        )
