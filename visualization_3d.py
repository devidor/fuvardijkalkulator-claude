"""Háromdimenziós rakodási nézet (Plotly). Egység: cm; x a homlokfaltól, y a bal oldalfaltól, z a padlótól."""

from __future__ import annotations

from dataclasses import dataclass

import plotly.graph_objects as go

from load_planner import RakodasiTerv
from visualization import szin

HEZAG_CM = 1.0  # az egységek közötti látható rés (csak megjelenítés)

# Egy téglatest 12 háromszöge a 8 csúcs indexeivel.
_I = [0, 0, 4, 4, 0, 0, 3, 3, 0, 0, 1, 1]
_J = [1, 2, 5, 6, 1, 5, 2, 6, 3, 7, 2, 6]
_K = [2, 3, 6, 7, 5, 4, 6, 7, 7, 4, 6, 5]
_ELEK = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)]


@dataclass(frozen=True)
class Doboz:
    """Egy rakományegység a térben."""

    sorszam: int  # alapterületi hely
    szint: int  # 1 = alsó
    csoport: int
    x0: float
    y0: float
    z0: float
    x1: float
    y1: float
    z1: float


def dobozok(terv: RakodasiTerv) -> list[Doboz]:
    """A rakodási terv egységei téglatestként, a halmokban egymásra helyezve."""
    magassag = {c.index: c.csoport.magassag_cm for c in terv.csoportok}
    eredmeny = []
    for e in terv.pakolas.elhelyezesek:
        m = magassag[e.csoport]
        for szint in range(terv.halmok.get(e.sorszam, 1)):
            eredmeny.append(Doboz(e.sorszam, szint + 1, e.csoport, e.x_cm, e.y_cm, szint * m, e.x2_cm, e.y2_cm, (szint + 1) * m))
    return eredmeny


def _csucsok(x0, y0, z0, x1, y1, z1):
    return [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]


def _drotvaz(csucs_listak, szin_, vastagsag, nev, latszik_jelmagyarazat=False):
    xs, ys, zs = [], [], []
    for cs in csucs_listak:
        for a, b in _ELEK:
            xs += [cs[a][0], cs[b][0], None]
            ys += [cs[a][1], cs[b][1], None]
            zs += [cs[a][2], cs[b][2], None]
    return go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color=szin_, width=vastagsag),
                        name=nev, hoverinfo="skip", showlegend=latszik_jelmagyarazat)


def rakodasi_3d_abra(terv: RakodasiTerv, csak_sav: bool = False) -> go.Figure:
    pk = terv.pakolas
    potkocsi = terv.potkocsi
    L, W, H = potkocsi.rakter_hossz_cm, potkocsi.rakter_szelesseg_cm, potkocsi.rakter_magassag_cm
    nezet_hossz = max(pk.hasznalt_hossz_cm, 50.0) if csak_sav else max(L, pk.hasznalt_hossz_cm)
    nevek = {c.index: c.csoport.nev for c in terv.csoportok}
    db = dobozok(terv)
    arany = (1.6 if csak_sav else 2.4) / max(nezet_hossz, W, H)

    fig = go.Figure()
    # padló és rakodótér-körvonal
    fig.add_trace(go.Mesh3d(
        x=[0, nezet_hossz, nezet_hossz, 0], y=[0, 0, W, W], z=[0, 0, 0, 0], i=[0, 0], j=[1, 2], k=[2, 3],
        color="#D5E3F2", opacity=0.55, hoverinfo="skip", name="Padló", showlegend=False,
    ))
    fig.add_trace(_drotvaz([_csucsok(0, 0, 0, min(L, nezet_hossz), W, H)], "#0B2545", 3, "Rakodótér"))
    if pk.hasznalt_hossz_cm > 0:
        fig.add_trace(_drotvaz([_csucsok(0, 0, 0, pk.hasznalt_hossz_cm, W, 0.5)], "#2E7D32", 5,
                               f"Felhasznált sáv: {pk.hasznalt_hossz_cm:g} cm", latszik_jelmagyarazat=True))

    h = HEZAG_CM / 2
    for csoport in sorted({d.csoport for d in db}):
        sajat = [d for d in db if d.csoport == csoport]
        xs, ys, zs, ii, jj, kk, szoveg, keretek = [], [], [], [], [], [], [], []
        for n, d in enumerate(sajat):
            cs = _csucsok(d.x0 + h, d.y0 + h, d.z0 + h, d.x1 - h, d.y1 - h, d.z1 - h)
            keretek.append(cs)
            for x, y, z in cs:
                xs.append(x)
                ys.append(y)
                zs.append(z)
            ii += [i + 8 * n for i in _I]
            jj += [j + 8 * n for j in _J]
            kk += [k + 8 * n for k in _K]
            felirat = (f"#{d.sorszam} · {nevek[csoport]}<br>{d.szint}. szint<br>"
                       f"x {d.x0:g}–{d.x1:g} cm, y {d.y0:g}–{d.y1:g} cm, z {d.z0:g}–{d.z1:g} cm")
            szoveg += [felirat] * 8
        fig.add_trace(go.Mesh3d(
            x=xs, y=ys, z=zs, i=ii, j=jj, k=kk, color=szin(csoport), opacity=0.92, flatshading=True,
            name=nevek[csoport], showlegend=True, hovertext=szoveg, hoverinfo="text",
            lighting=dict(ambient=0.55, diffuse=0.8, specular=0.1),
        ))
        fig.add_trace(_drotvaz(keretek, "#FFFFFF", 2, nevek[csoport]))

    fig.update_layout(
        scene=dict(
            xaxis=dict(title="hossz (cm)", range=[0, nezet_hossz], backgroundcolor="#F4F8FC"),
            yaxis=dict(title="szél. (cm)", range=[0, W], backgroundcolor="#F4F8FC"),
            zaxis=dict(title="mag. (cm)", range=[0, H], backgroundcolor="#F4F8FC"),
            # Méretarányos tengelyek; a leghosszabb oldal hossza rögzített, hogy a kamera távolsága kiszámítható legyen.
            aspectmode="manual",
            aspectratio=dict(x=nezet_hossz * arany, y=W * arany, z=H * arany),
            # A homlokfal felől, balról-felülről nézve.
            camera=dict(eye=dict(x=-1.5, y=-1.9, z=1.2) if not csak_sav else dict(x=-1.4, y=-1.6, z=1.1),
                        up=dict(x=0, y=0, z=1)),
        ),
        margin=dict(l=0, r=0, t=10, b=0),
        legend=dict(orientation="h", yanchor="bottom", y=0.0, x=0.0),
        height=520,
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig
