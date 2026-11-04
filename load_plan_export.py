"""Fuvarozónak küldhető, nyomtatható rakodási terv (HTML) és koordinátatábla."""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import datetime

from load_planner import RakodasiTerv
from visualization import rakodasi_svg, szin


@dataclass
class TervFejlec:
    hivatkozas: str = ""
    viszonylat: str = ""
    fuvarozo: str = ""
    keszitette: str = ""


def _sz(x: float, tizedes: int = 2) -> str:
    return f"{x:,.{tizedes}f}".replace(",", " ").replace(".", ",")


def _e(s: str) -> str:
    return html.escape(str(s))


def elhelyezes_sorok(terv: RakodasiTerv) -> list[dict]:
    nevek = {c.index: c.csoport.nev for c in terv.csoportok}
    return [
        {
            "Hely": e.sorszam,
            "Rakománycsoport": nevek.get(e.csoport, ""),
            "x (cm)": e.x_cm,
            "y (cm)": e.y_cm,
            "Hossz x irányban (cm)": e.hossz_cm,
            "Szélesség y irányban (cm)": e.szelesseg_cm,
            "Forgatva": "igen" if e.forgatott else "nem",
            "Egymásra helyezett egységek": terv.halmok.get(e.sorszam, 1),
        }
        for e in terv.pakolas.elhelyezesek
    ]


def _tabla(fejlec: list[str], sorok: list[list], jobbra: set[int] = frozenset()) -> str:
    th = "".join(f"<th>{_e(f)}</th>" for f in fejlec)
    tr = "".join(
        "<tr>" + "".join(
            f'<td class="{"sz" if i in jobbra else ""}">{c}</td>' for i, c in enumerate(sor)
        ) + "</tr>"
        for sor in sorok
    )
    return f"<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table>"


def rakodasi_terv_html(terv: RakodasiTerv, fejlec: TervFejlec) -> str:
    pk, p, el = terv.potkocsi, terv.pakolas, terv.elszamolas
    most = datetime.now().strftime("%Y.%m.%d. %H:%M")

    meta = [
        ["Hivatkozás / ajánlatszám", _e(fejlec.hivatkozas) or "–"],
        ["Viszonylat", _e(fejlec.viszonylat) or "–"],
        ["Fuvarozó", _e(fejlec.fuvarozo) or "–"],
        ["Készítette", _e(fejlec.keszitette) or "–"],
        ["Készült", most],
        ["Pótkocsi", f"{_e(pk.tipus)}: {pk.hossz_cm:g} × {pk.szelesseg_cm:g} × {pk.magassag_cm:g} cm "
                     f"(H × Sz × M), hasznos teherbírás {_sz(pk.teherbiras_kg, 0)} kg"],
        ["Tervezéshez használt rakodótér", f"{pk.rakter_hossz_cm:g} × {pk.rakter_szelesseg_cm:g} × "
                                           f"{pk.rakter_magassag_cm:g} cm"],
    ]
    osszesito = [
        ["Rakományegységek", f"{terv.darab} db ({terv.helyek} alapterületi hely)"],
        ["Teljes tömeg", f"{_sz(terv.ossz_suly_kg, 0)} kg"],
        ["Felhasznált rakodótér-hossz", f"{_sz(p.hasznalt_hossz_cm, 0)} cm"],
        ["Fizikai LDM", f"<b>{_sz(el.fizikai_ldm)}</b>"],
        ["Elméleti (területalapú) LDM", _sz(terv.elmeleti_ldm)],
        ["Tömegalapú LDM", f"{_sz(el.tomegalapu_ldm)} ({_sz(terv.ossz_suly_kg, 0)} kg ÷ {el.kg_per_ldm:g} kg/LDM)"],
        ["Elszámolási LDM", f"<b>{_sz(el.elszamolasi_ldm)}</b> = {_sz(el.tomegegyenertek_kg, 0)} kg "
                            f"tömegegyenérték (kerekítés: {_e(el.kerekites.lower())})"],
        ["Elrendezés", _e(p.modszer)],
        ["Rakodósáv kihasználtsága", f"{_sz(p.sav_kihasznaltsag_pct, 1)} % "
                                     f"(szabad: {_sz(p.sav_szabad_terulet_cm2 / 10000)} m²)"],
    ]
    egysegek = []
    for c in terv.csoportok:
        cs, h = c.csoport, c.halmozas
        halm = "nem halmozható" if cs.max_szint == 1 else f"max. {cs.max_szint} szint, tervezve {h.alkalmazott_szint}"
        ter = "nem ismert" if cs.raterheles_kg is None else f"{cs.raterheles_kg:g} kg"
        egysegek.append([
            f'<span class="folt" style="background:{szin(c.index)}"></span>{_e(cs.nev)}',
            cs.darab, f"{cs.hossz_cm:g} × {cs.szelesseg_cm:g} × {cs.magassag_cm:g}",
            _sz(cs.suly_kg, 1), _sz(cs.ossz_suly_kg, 0), halm, _e(h.statusz),
            "igen" if cs.forgathato else "nem", ter,
        ])
    koord = [
        [r["Hely"], _e(r["Rakománycsoport"]), _sz(r["x (cm)"], 1), _sz(r["y (cm)"], 1),
         _sz(r["Hossz x irányban (cm)"], 1), _sz(r["Szélesség y irányban (cm)"], 1), r["Forgatva"],
         r["Egymásra helyezett egységek"]]
        for r in elhelyezes_sorok(terv)
    ]
    szabad = [
        [_sz(s.x_cm, 1), _sz(s.y_cm, 1), _sz(s.hossz_cm, 1), _sz(s.szelesseg_cm, 1), _sz(s.terulet_cm2 / 10000, 3)]
        for s in p.szabad_teruletek
    ]
    feltetelek = "".join(f"<li>{_e(f)}</li>" for f in terv.feltetelezesek)
    figyelm = [u for u in terv.uzenetek] + [u for c in terv.csoportok for u in c.uzenetek]
    figy_html = "".join(f'<li class="{u.szint}">{_e(u.szoveg)}</li>' for u in figyelm) or "<li>Nincs.</li>"

    return f"""<!doctype html>
<html lang="hu"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rakodási terv {_e(fejlec.hivatkozas)}</title>
<style>
body {{font-family: "Segoe UI", Helvetica, Arial, sans-serif; color: #0B2545; margin: 24px auto; max-width: 1000px; padding: 0 16px; background: #fff;}}
h1 {{font-size: 22px; margin: 0 0 4px;}} h2 {{font-size: 16px; margin: 22px 0 8px; border-bottom: 2px solid #1E88E5; padding-bottom: 3px;}}
.al {{color: #4A6380; font-size: 13px;}}
table {{border-collapse: collapse; width: 100%; font-size: 13px;}}
th, td {{border: 1px solid #C9D7E6; padding: 5px 7px; text-align: left; vertical-align: top;}}
th {{background: #E3EEF9;}} td.sz {{text-align: right;}}
.meta td:first-child {{width: 34%; background: #F4F8FC; font-weight: 600;}}
.folt {{display: inline-block; width: 10px; height: 10px; border-radius: 2px; margin-right: 6px;}}
li {{margin: 3px 0; font-size: 13px;}} li.hiba {{color: #B71C1C;}} li.figyelmeztetes {{color: #9A4A00;}}
.abra {{border: 1px solid #C9D7E6; border-radius: 8px; padding: 8px; margin: 6px 0 10px;}}
.visszaig td {{height: 30px;}} .doboz {{display: inline-block; width: 13px; height: 13px; border: 1.5px solid #0B2545; margin-right: 6px; vertical-align: -2px;}}
@media print {{ body {{margin: 0;}} h2 {{break-after: avoid;}} .abra, table {{break-inside: avoid;}} }}
</style></head><body>
<h1>Rakodási terv – fuvarozói visszaigazolásra</h1>
<div class="al">Tervezett rakodás. A terv a megadott adatokon és az alább felsorolt feltételezéseken alapul; nem garantált, amíg a fuvarozó írásban vissza nem igazolja.</div>
<h2>Alapadatok</h2>{_tabla(["Adat", "Érték"], meta).replace("<table>", '<table class="meta">', 1)}
<h2>Összesítés</h2>{_tabla(["Mutató", "Érték"], osszesito).replace("<table>", '<table class="meta">', 1)}
<h2>Rakományegységek és halmozási szabályok</h2>
{_tabla(["Csoport", "Darab", "Méret (H × Sz × M, cm)", "Tömeg/db (kg)", "Össztömeg (kg)", "Halmozás", "Halmozás állapota", "Forgatható", "Megengedett felső terhelés"], egysegek, {1, 3, 4})}
<h2>Javasolt elrendezés (felülnézet)</h2>
<div class="al">x: távolság a homlokfaltól, y: távolság a bal oldalfaltól. Zöld szaggatott keret: felhasznált rakodósáv; narancs sraffozás: szabad terület a sávon belül; „×2”: egymásra helyezett egységek.</div>
<div class="abra">{rakodasi_svg(p, pk, terv.halmok, csak_sav=False, azonosito="teljes")}</div>
<div class="abra">{rakodasi_svg(p, pk, terv.halmok, csak_sav=True, azonosito="sav")}</div>
<h2>Elhelyezési koordináták</h2>
{_tabla(["Hely", "Csoport", "x (cm)", "y (cm)", "Hossz x (cm)", "Szélesség y (cm)", "Forgatva", "Egymásra (db)"], koord, {0, 2, 3, 4, 5, 7})}
<h2>Szabad területek a felhasznált sávon belül</h2>
{_tabla(["x (cm)", "y (cm)", "Hossz (cm)", "Szélesség (cm)", "Terület (m²)"], szabad, {0, 1, 2, 3, 4}) if szabad else '<div class="al">Nincs.</div>'}
<div class="al">A szabad területek nem feltétlenül alkalmasak más rakomány fogadására (alak, hozzáférhetőség, rögzítés).</div>
<h2>Ellenőrzendő feltételek és feltételezések</h2><ul>{feltetelek}</ul>
<h2>Figyelmeztetések</h2><ul>{figy_html}</ul>
<h2>Fuvarozói visszaigazolás</h2>
<p><span class="doboz"></span>A rakodási tervet elfogadom, a rakomány <b>{_sz(el.fizikai_ldm)} LDM</b> rakodótéren elhelyezhető.<br>
<span class="doboz"></span>Módosítással fogadom el: ____________ LDM, indok: ____________________________________<br>
<span class="doboz"></span>Nem fogadom el, indok: ________________________________________________</p>
<table class="visszaig"><tbody><tr><td style="width:34%">Fuvarozó cég</td><td></td></tr><tr><td>Név, beosztás</td><td></td></tr>
<tr><td>Dátum</td><td></td></tr><tr><td>Aláírás</td><td></td></tr></tbody></table>
</body></html>"""
