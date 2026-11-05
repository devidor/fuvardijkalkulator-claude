"""Méretarányos felülnézeti rakodási ábra (SVG, egység = cm)."""

from __future__ import annotations

import html

from packing_optimizer import PakolasEredmeny
from trailer_config import Potkocsi

CSOPORT_SZINEK = ["#1E88E5", "#43A047", "#FB8C00", "#8E24AA", "#00ACC1", "#6D4C41", "#E53935", "#3949AB"]


def szin(csoport: int) -> str:
    return CSOPORT_SZINEK[csoport % len(CSOPORT_SZINEK)]


def _szam(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def rakodasi_svg(
    pakolas: PakolasEredmeny,
    pk: Potkocsi,
    halmok: dict[int, int] | None = None,
    csak_sav: bool = False,
    azonosito: str = "abra",
) -> str:
    """Felülnézet. ``csak_sav``: csak a felhasznált rakodósáv, nagyítva, méretekkel."""
    halmok = halmok or {}
    hasznalt = pakolas.hasznalt_hossz_cm
    rh, rsz = pk.rakter_hossz_cm, pk.rakter_szelesseg_cm
    nevl_h, nevl_sz = pk.hossz_cm, pk.szelesseg_cm
    if csak_sav:
        nezet = max(hasznalt, 50.0) + 10
    else:
        nezet = max(nevl_h, hasznalt)
    # Betűméret a nézet méretéhez igazítva, hogy kirajzolva közel azonos méretű legyen.
    fs = max(nezet, nevl_sz * 1.6) / 45
    margo = fs * 1.2
    magas = nevl_sz
    e: list[str] = [
        f'<defs><pattern id="sraf-{azonosito}" patternUnits="userSpaceOnUse" width="{fs * .8:.2f}" '
        f'height="{fs * .8:.2f}" patternTransform="rotate(45)"><rect width="{fs * .8:.2f}" height="{fs * .8:.2f}" '
        f'fill="#FFF3E0"/><line x1="0" y1="0" x2="0" y2="{fs * .8:.2f}" stroke="#F57C00" '
        f'stroke-width="{fs * .18:.2f}"/></pattern>'
        f'<pattern id="tul-{azonosito}" patternUnits="userSpaceOnUse" width="{fs:.2f}" height="{fs:.2f}" '
        f'patternTransform="rotate(45)"><rect width="{fs:.2f}" height="{fs:.2f}" fill="#FDECEA"/>'
        f'<line x1="0" y1="0" x2="0" y2="{fs:.2f}" stroke="#C62828" stroke-width="{fs * .2:.2f}"/></pattern></defs>',
        # pótkocsi padlója (névleges)
        f'<rect x="0" y="0" width="{min(nevl_h, nezet):.1f}" height="{nevl_sz:.1f}" fill="#F4F8FC" '
        f'stroke="#0B2545" stroke-width="{fs * .15:.2f}"/>',
    ]
    if pk.eltero_szabad_rakter:
        e.append(
            f'<rect x="0" y="0" width="{min(rh, nezet):.1f}" height="{rsz:.1f}" fill="none" stroke="#1E88E5" '
            f'stroke-width="{fs * .12:.2f}" stroke-dasharray="{fs * .6:.1f} {fs * .4:.1f}"/>'
        )
    if hasznalt > rh:
        e.append(
            f'<rect x="{rh:.1f}" y="0" width="{min(hasznalt, nezet) - rh:.1f}" height="{rsz:.1f}" '
            f'fill="url(#tul-{azonosito})" stroke="#C62828" stroke-width="{fs * .12:.2f}"/>'
        )
    # felhasznált rakodósáv
    if hasznalt > 0:
        e.append(
            f'<rect x="0" y="0" width="{hasznalt:.1f}" height="{rsz:.1f}" fill="#E8F5E9" stroke="#2E7D32" '
            f'stroke-width="{fs * .14:.2f}" stroke-dasharray="{fs * .5:.1f} {fs * .3:.1f}"/>'
        )
    for s in pakolas.szabad_teruletek:
        e.append(
            f'<rect x="{s.x_cm:.1f}" y="{s.y_cm:.1f}" width="{s.hossz_cm:.1f}" height="{s.szelesseg_cm:.1f}" '
            f'fill="url(#sraf-{azonosito})" stroke="#F57C00" stroke-width="{fs * .05:.2f}"/>'
        )
        if csak_sav and min(s.hossz_cm, s.szelesseg_cm) >= fs * 1.3:
            e.append(
                f'<text x="{s.x_cm + s.hossz_cm / 2:.1f}" y="{s.y_cm + s.szelesseg_cm / 2 + fs * .3:.1f}" '
                f'text-anchor="middle" font-size="{fs * .7:.2f}" fill="#7A3E00">'
                f'{_szam(s.hossz_cm)}×{_szam(s.szelesseg_cm)}</text>'
            )
    for el in pakolas.elhelyezesek:
        res = min(fs * .08, min(el.hossz_cm, el.szelesseg_cm) * .06)
        label_fs = min(fs, min(el.hossz_cm, el.szelesseg_cm) / 5)
        e.append(
            f'<rect x="{el.x_cm + res:.2f}" y="{el.y_cm + res:.2f}" width="{el.hossz_cm - 2 * res:.2f}" '
            f'height="{el.szelesseg_cm - 2 * res:.2f}" fill="{szin(el.csoport)}" fill-opacity="0.88" '
            f'stroke="#ffffff" stroke-width="{fs * .1:.2f}" rx="{fs * .2:.2f}"><title>{el.sorszam}. hely: '
            f'x={_szam(el.x_cm)}, y={_szam(el.y_cm)} cm, {_szam(el.hossz_cm)}×{_szam(el.szelesseg_cm)} cm'
            f'{", forgatva" if el.forgatott else ""}</title></rect>'
        )
        cx, cy = el.x_cm + el.hossz_cm / 2, el.y_cm + el.szelesseg_cm / 2
        db = halmok.get(el.sorszam, 1)
        felirat = f"#{el.sorszam}" + (f" ×{db}" if db > 1 else "") + (" ↻" if el.forgatott else "")
        e.append(
            f'<text x="{cx:.1f}" y="{cy + label_fs * .35:.1f}" text-anchor="middle" font-size="{label_fs:.2f}" '
            f'font-weight="700" fill="#fff">{felirat}</text>'
        )
        if csak_sav:
            e.append(
                f'<text x="{cx:.1f}" y="{cy + label_fs * 1.4:.1f}" text-anchor="middle" font-size="{fs * .7:.2f}" '
                f'fill="#fff">{_szam(el.hossz_cm)}×{_szam(el.szelesseg_cm)}</text>'
            )
    # méretvonal a felhasznált sávhoz
    y_vonal = magas + fs * 1.1
    if hasznalt > 0:
        e.append(
            f'<line x1="0" y1="{y_vonal:.1f}" x2="{hasznalt:.1f}" y2="{y_vonal:.1f}" stroke="#2E7D32" '
            f'stroke-width="{fs * .12:.2f}"/>'
            f'<line x1="0" y1="{y_vonal - fs * .4:.1f}" x2="0" y2="{y_vonal + fs * .4:.1f}" stroke="#2E7D32" stroke-width="{fs * .12:.2f}"/>'
            f'<line x1="{hasznalt:.1f}" y1="{y_vonal - fs * .4:.1f}" x2="{hasznalt:.1f}" y2="{y_vonal + fs * .4:.1f}" '
            f'stroke="#2E7D32" stroke-width="{fs * .12:.2f}"/>'
            f'<text x="{hasznalt / 2:.1f}" y="{y_vonal + fs * 1.25:.1f}" text-anchor="middle" font-size="{fs * .85:.2f}" '
            f'font-weight="700" fill="#2E7D32">{_szam(hasznalt)} cm = '
            f'{f"{hasznalt / 100:.2f}".replace(".", ",")} LDM</text>'
        )
    e.append(
        f'<text x="0" y="{-fs * .45:.1f}" font-size="{fs * .8:.2f}" fill="#4A6380">◀ homlokfal · '
        f'szélesség {_szam(rsz)} cm</text>'
    )
    if not csak_sav:
        e.append(
            f'<text x="{nezet:.1f}" y="{-fs * .45:.1f}" text-anchor="end" font-size="{fs * .8:.2f}" '
            f'fill="#4A6380">ajtó ▶ {_szam(nevl_h)} cm</text>'
        )
    also = y_vonal + fs * 1.8
    return (
        f'<svg viewBox="{-margo:.1f} {-margo * 1.4:.1f} {nezet + 2 * margo:.1f} {also + margo * 1.4:.1f}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI, Helvetica, Arial, sans-serif" role="img" '
        f'aria-label="{html.escape("Rakodási terv felülnézetben")}" '
        f'style="width:100%;height:auto;{"max-height:440px;" if csak_sav else ""}display:block">'
        + "".join(e) + "</svg>"
    )
