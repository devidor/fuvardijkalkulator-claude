"""Kétdimenziós raklapelhelyezés a pótkocsi rakfelületén (2D strip packing).

Koordináták: x a pótkocsi hossza mentén a homlokfaltól, y a szélesség mentén a bal
oldalfaltól, centiméterben. Belül egész milliméterrel számol, hogy az átfedés- és
határellenőrzés lebegőpontos hiba nélkül pontos legyen.

Módszer
1. Heurisztikák (soros elrendezés vegyes tájolással, skyline „bottom-left” több
   sorrenddel) adnak egy érvényes elrendezést → felső korlát.
2. Alsó korlát: összes alapterület ÷ ténylegesen kitölthető szélesség (a szélesség
   azon része, amely egységméretek összegeként elérhető), az egymás mellé nem
   tehető egységek hossza, illetve a leghosszabb egység.
3. Pontos keresés: a lehetséges rakodási hosszakat („normál minták”: egységméretek
   összegei) növekvő sorrendben vizsgálja visszalépéses kereséssel, amely mindig
   az első szabad rácscellát tölti ki (egységgel vagy kihagyással). Ha minden
   rövidebb hosszra bizonyítja, hogy nem fér el, az eredmény a modellen belül
   bizonyított optimum. Idő- vagy lépéskorlát esetén a legjobb talált elrendezést
   adja vissza, közelítőként jelölve.

A modell: tengelyekkel párhuzamos téglalapok, 90°-os forgatás, átfedés nélkül.
Nem modellezi a tengelyterhelést, a rögzítést és a rakodási sorrendet.
"""

from __future__ import annotations

import math
import sys
import time
from dataclasses import dataclass, field
from typing import Optional

PONTOS_MAX_EGYSEG = 60  # e fölött csak heurisztika fut
PONTOS_MAX_CELLA = 4000
PONTOS_MAX_CSOMOPONT = 2_000_000

MODSZER_PONTOS = "Pontos keresés – bizonyított optimum"
MODSZER_KORLAT = "Heurisztika – az alsó korlát igazolja az optimumot"
MODSZER_KOZELITO = "Heurisztika – közelítő megoldás (nem bizonyított optimum)"


@dataclass(frozen=True)
class Tetel:
    """Alapterületi hely típusa (egy egység vagy egy halom) és darabszáma."""

    csoport: int
    hossz_cm: float
    szelesseg_cm: float
    forgathato: bool
    darab: int


@dataclass(frozen=True)
class Elhelyezes:
    sorszam: int
    csoport: int
    x_cm: float
    y_cm: float
    hossz_cm: float  # kiterjedés a pótkocsi hossza mentén
    szelesseg_cm: float  # kiterjedés a pótkocsi szélessége mentén
    forgatott: bool

    @property
    def x2_cm(self) -> float:
        return self.x_cm + self.hossz_cm

    @property
    def y2_cm(self) -> float:
        return self.y_cm + self.szelesseg_cm


@dataclass(frozen=True)
class SzabadTeglalap:
    x_cm: float
    y_cm: float
    hossz_cm: float
    szelesseg_cm: float

    @property
    def terulet_cm2(self) -> float:
        return self.hossz_cm * self.szelesseg_cm


@dataclass
class PakolasEredmeny:
    elhelyezesek: list[Elhelyezes]
    hasznalt_hossz_cm: float
    also_korlat_cm: float
    bizonyitott: bool
    modszer: str
    rakter_hossz_cm: float
    rakter_szelesseg_cm: float
    futasido_s: float = 0.0
    szabad_teruletek: list[SzabadTeglalap] = field(default_factory=list)

    @property
    def belefer(self) -> bool:
        return self.hasznalt_hossz_cm <= self.rakter_hossz_cm + 1e-9

    @property
    def fedett_terulet_cm2(self) -> float:
        return sum(e.hossz_cm * e.szelesseg_cm for e in self.elhelyezesek)

    @property
    def sav_terulet_cm2(self) -> float:
        return self.hasznalt_hossz_cm * self.rakter_szelesseg_cm

    @property
    def sav_szabad_terulet_cm2(self) -> float:
        return (_mm(self.hasznalt_hossz_cm) * _mm(self.rakter_szelesseg_cm) - sum(_mm(e.hossz_cm)*_mm(e.szelesseg_cm) for e in self.elhelyezesek)) / 100

    @property
    def sav_kihasznaltsag_pct(self) -> float:
        return self.fedett_terulet_cm2 / self.sav_terulet_cm2 * 100 if self.sav_terulet_cm2 else 0.0

    @property
    def maradek_rakter_cm2(self) -> float:
        """A felhasznált sávon túli, még üres rakodótér."""
        return max(0.0, self.rakter_hossz_cm - self.hasznalt_hossz_cm) * self.rakter_szelesseg_cm


# ---------------------------------------------------------------------------
# Belső segédek (milliméter)
# ---------------------------------------------------------------------------


def _mm(cm: float) -> int:
    if not math.isfinite(cm) or abs(cm * 10 - round(cm * 10)) > 1e-6:
        raise ValueError("A méret véges szám legyen, legfeljebb 0,1 cm pontossággal.")
    return int(round(cm * 10))


@dataclass(frozen=True)
class _Tipus:
    csoport: int
    l: int  # x-irányú méret forgatás nélkül
    w: int  # y-irányú méret forgatás nélkül
    forgathato: bool
    darab: int

    def iranyok(self, szel: int, hossz: Optional[int] = None) -> list[tuple[int, int, bool]]:
        """Érvényes tájolások: (x-kiterjedés, y-kiterjedés, forgatott)."""
        jeloltek = [(self.l, self.w, False)]
        if self.forgathato and self.l != self.w:
            jeloltek.append((self.w, self.l, True))
        return [
            (dx, dy, r) for dx, dy, r in jeloltek
            if dy <= szel and (hossz is None or dx <= hossz)
        ]


_Teglalap = tuple[int, int, int, int, int, bool]  # (típus index, x, y, dx, dy, forgatott)


def _mintaosszegek(opciok: list[tuple[int, ...]], korlat: int) -> list[int]:
    """Elérhető összegek, ha minden egység egyik megadott méretével (vagy sehogy) szerepel."""
    elert = {0}
    for opc in opciok:
        uj = set(elert)
        for s in elert:
            for o in opc:
                if s + o <= korlat:
                    uj.add(s + o)
        elert = uj
    return sorted(elert)


def _kiterjesztett(tipusok: list[_Tipus]) -> list[int]:
    return [i for i, t in enumerate(tipusok) for _ in range(t.darab)]


# ---------------------------------------------------------------------------
# Heurisztikák
# ---------------------------------------------------------------------------


def _soros(tipusok: list[_Tipus], W: int) -> list[_Teglalap]:
    """Típusonként keresztirányú sorok; a két tájolás sorainak legrövidebb keveréke."""
    eredmeny: list[_Teglalap] = []
    x = 0
    for ti, t in enumerate(tipusok):
        iranyok = []
        for dx, dy, r in t.iranyok(W):
            iranyok.append((dx, dy, r, W // dy))
        a = iranyok[0]
        b = iranyok[1] if len(iranyok) > 1 else None
        legjobb = None
        for a_sor in range(math.ceil(t.darab / a[3]) + 1):
            maradek = max(0, t.darab - a_sor * a[3])
            if b is None and maradek:
                continue
            b_sor = math.ceil(maradek / b[3]) if b else 0
            hossz = a_sor * a[0] + (b_sor * b[0] if b else 0)
            if legjobb is None or (hossz, a_sor + b_sor) < legjobb[:2]:
                legjobb = (hossz, a_sor + b_sor, a_sor, b_sor)
        _, _, a_sor, b_sor = legjobb
        hatra = t.darab
        for irany, sorok in ((a, a_sor), (b, b_sor)):
            for _ in range(sorok):
                dx, dy, r, n = irany
                for k in range(min(n, hatra)):
                    eredmeny.append((ti, x, k * dy, dx, dy, r))
                hatra -= min(n, hatra)
                x += dx
    return eredmeny


def _skyline(tipusok: list[_Tipus], sorrend: list[int], W: int, also_bal: bool) -> list[_Teglalap]:
    """Skyline elhelyezés: minden egység oda kerül, ahol a legkisebb x-végpontot adja."""
    sky = [[0, W, 0]]  # szegmensek: [y0, y1, x-magasság]
    eredmeny: list[_Teglalap] = []
    for ti in sorrend:
        legjobb = None
        for dx, dy, r in tipusok[ti].iranyok(W):
            pozicioy = sorted({s[0] for s in sky} | {s[1] - dy for s in sky})
            for y0 in pozicioy:
                if y0 < 0 or y0 + dy > W:
                    continue
                xm = max(s[2] for s in sky if s[0] < y0 + dy and s[1] > y0)
                kulcs = (xm, xm + dx, y0) if also_bal else (xm + dx, xm, y0)
                if legjobb is None or kulcs < legjobb[0]:
                    legjobb = (kulcs, xm, y0, dx, dy, r)
        _, xm, y0, dx, dy, r = legjobb
        eredmeny.append((ti, xm, y0, dx, dy, r))
        uj = []
        for s in sky:
            if s[1] <= y0 or s[0] >= y0 + dy:
                uj.append(s)
                continue
            if s[0] < y0:
                uj.append([s[0], y0, s[2]])
            if s[1] > y0 + dy:
                uj.append([y0 + dy, s[1], s[2]])
        uj.append([y0, y0 + dy, xm + dx])
        uj.sort()
        sky = []
        for s in uj:
            if sky and sky[-1][2] == s[2] and sky[-1][1] == s[0]:
                sky[-1][1] = s[1]
            else:
                sky.append(s)
    return eredmeny


def _hossz(teglalapok: list[_Teglalap]) -> int:
    return max((x + dx for _, x, _, dx, _, _ in teglalapok), default=0)


def _legjobb_heurisztika(tipusok: list[_Tipus], W: int) -> list[_Teglalap]:
    egysegek = _kiterjesztett(tipusok)

    def nagyobb_meret(i):
        return -max(tipusok[i].l, tipusok[i].w)

    def terulet(i):
        return -tipusok[i].l * tipusok[i].w

    sorrendek = [
        sorted(egysegek, key=lambda i: (nagyobb_meret(i), i)),
        sorted(egysegek, key=lambda i: (terulet(i), i)),
        sorted(egysegek, key=lambda i: (-min(tipusok[i].l, tipusok[i].w), i)),
        list(egysegek),
    ]
    jeloltek = [_soros(tipusok, W)]
    for s in sorrendek:
        for also_bal in (False, True):
            jeloltek.append(_skyline(tipusok, s, W, also_bal))
    return min(jeloltek, key=_hossz)


def _sarok_nyalab(tipusok, W, incumbent, deadline):
    """ChatGPT-változat sarokpont-keresése: csoportonkénti forgatás és időkorlát.

    A résztervek sosem írják felül a teljes incumbent tervet.
    """
    units = sorted(_kiterjesztett(tipusok), key=lambda i: -tipusok[i].l*tipusok[i].w)
    beam = [([], 0)]
    upper = _hossz(incumbent)
    for ti in units:
        candidates, seen = [], set()
        for placed, used in beam:
            xs = sorted({0} | {x+dx for _,x,y,dx,dy,r in placed})
            ys = sorted({0} | {y+dy for _,x,y,dx,dy,r in placed})
            for dx,dy,rot in tipusok[ti].iranyok(W):
                for x in xs:
                    if time.perf_counter() >= deadline: return incumbent
                    if x+dx >= upper: continue
                    for y in ys:
                        if y+dy>W: continue
                        if any(x<a+c and a<x+dx and y<b+d and b<y+dy for _,a,b,c,d,_ in placed): continue
                        plan = placed+[(ti,x,y,dx,dy,rot)]
                        signature = tuple(sorted((a,b,c,d) for _,a,b,c,d,_ in plan))
                        if signature in seen: continue
                        seen.add(signature)
                        candidates.append((plan,max(used,x+dx)))
        if not candidates: return incumbent
        candidates.sort(key=lambda z:(z[1],sum(r[1] for r in z[0])))
        beam=candidates[:12]
    return min(beam,key=lambda z:z[1])[0]


# ---------------------------------------------------------------------------
# Alsó korlát
# ---------------------------------------------------------------------------


def _also_korlat(tipusok: list[_Tipus], W: int) -> int:
    egysegek = _kiterjesztett(tipusok)
    y_opciok = [tuple({dy for _, dy, _ in tipusok[i].iranyok(W)}) for i in egysegek]
    w_eff = max(_mintaosszegek(y_opciok, W))
    terulet = sum(tipusok[i].l * tipusok[i].w for i in egysegek)
    korlat = (terulet + w_eff - 1) // w_eff
    # Minden egységnek el kell férnie hosszában.
    min_dx = [min(dx for dx, _, _ in tipusok[i].iranyok(W)) for i in egysegek]
    korlat = max(korlat, max(min_dx))
    # Amelyek közül semelyik kettő nem fér el egymás mellett, azok egymás mögé kerülnek.
    szeles = [
        k for k, i in enumerate(egysegek)
        if min(dy for _, dy, _ in tipusok[i].iranyok(W)) * 2 > W
    ]
    korlat = max(korlat, sum(min_dx[k] for k in szeles))
    return korlat


# ---------------------------------------------------------------------------
# Pontos keresés
# ---------------------------------------------------------------------------


class _Megszakitva(Exception):
    pass


def _pontos_kereses(
    tipusok: list[_Tipus], W: int, L: int, X: list[int], Y: list[int],
    hatarido: float, max_csomopont: int,
) -> Optional[list[_Teglalap]]:
    """Elfér-e minden egység a W × L területen? Elrendezés, None (nem fér el) vagy _Megszakitva."""
    nx, ny = len(X) - 1, len(Y) - 1
    xi = {v: i for i, v in enumerate(X)}
    yi = {v: j for j, v in enumerate(Y)}
    fedett = [bytearray(ny) for _ in range(nx)]
    hatra = [t.darab for t in tipusok]
    iranyok = [t.iranyok(W, L) for t in tipusok]
    sorrend = sorted(range(len(tipusok)), key=lambda t: -tipusok[t].l * tipusok[t].w)
    max_pazarlas = W * L - sum(t.l * t.w * t.darab for t in tipusok)
    if max_pazarlas < 0:
        return None
    elhelyezve: list[_Teglalap] = []
    csomopont = 0
    if time.perf_counter() >= hatarido:
        raise _Megszakitva

    def kereses(i: int, j: int, pazarlas: int, maradt: int) -> bool:
        nonlocal csomopont
        csomopont += 1
        if csomopont > max_csomopont or (csomopont & 127 == 0 and time.perf_counter() > hatarido):
            raise _Megszakitva
        if maradt == 0:
            return True
        while i < nx:  # első szabad cella (oszlopfolytonosan)
            oszlop = fedett[i]
            while j < ny and oszlop[j]:
                j += 1
            if j < ny:
                break
            i, j = i + 1, 0
        if i >= nx:
            return False
        x0, y0 = X[i], Y[j]
        for t in sorrend:
            if not hatra[t]:
                continue
            for dx, dy, r in iranyok[t]:
                i1, j1 = xi.get(x0 + dx), yi.get(y0 + dy)
                if i1 is None or j1 is None:
                    continue
                if any(fedett[a][b] for a in range(i, i1) for b in range(j, j1)):
                    continue
                for a in range(i, i1):
                    for b in range(j, j1):
                        fedett[a][b] = 1
                hatra[t] -= 1
                elhelyezve.append((t, x0, y0, dx, dy, r))
                if kereses(i, j, pazarlas, maradt - 1):
                    return True
                elhelyezve.pop()
                hatra[t] += 1
                for a in range(i, i1):
                    for b in range(j, j1):
                        fedett[a][b] = 0
        cella = (X[i + 1] - X[i]) * (Y[j + 1] - Y[j])
        if pazarlas + cella <= max_pazarlas:  # a cella üresen marad
            fedett[i][j] = 1
            if kereses(i, j, pazarlas + cella, maradt):
                return True
            fedett[i][j] = 0
        return False

    regi_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(regi_limit, nx * ny + sum(hatra) + 500))
    try:
        return list(elhelyezve) if kereses(0, 0, 0, sum(hatra)) else None
    finally:
        sys.setrecursionlimit(regi_limit)


# ---------------------------------------------------------------------------
# Szabad területek
# ---------------------------------------------------------------------------


def szabad_teglalapok(elhelyezesek: list[Elhelyezes], hossz_cm: float, szelesseg_cm: float) -> list[SzabadTeglalap]:
    """A [0, hossz] × [0, szélesség] sáv le nem fedett részei téglalapokra bontva."""
    L, W = _mm(hossz_cm), _mm(szelesseg_cm)
    if L <= 0 or W <= 0:
        return []
    events = {}
    for i, e in enumerate(elhelyezesek):
        a, b = max(0, _mm(e.x_cm)), min(L, _mm(e.x2_cm))
        if a < b:
            events.setdefault(a, []).append((i, (_mm(e.y_cm), _mm(e.y2_cm))))
            events.setdefault(b, []).append((i, None))
    xs = sorted({0, L} | set(events))
    active, opened, result = {}, {}, []
    for a, b in zip(xs, xs[1:]):
        for i, interval in events.get(a, []):
            if interval is None: active.pop(i, None)
            else: active[i] = interval
        free, y = [], 0
        for low, high in sorted(active.values()):
            if low > y: free.append((y, min(low, W)))
            y = max(y, high)
        if y < W: free.append((y, W))
        new = {interval: opened.pop(interval, a) for interval in free}
        for (low, high), x in opened.items():
            result.append(SzabadTeglalap(x/10, low/10, (a-x)/10, (high-low)/10))
        opened = new
    for (low, high), x in opened.items():
        result.append(SzabadTeglalap(x/10, low/10, (L-x)/10, (high-low)/10))
    return sorted(result, key=lambda r: (r.x_cm, r.y_cm))


def ellenoriz_elhelyezest(elhelyezesek: list[Elhelyezes], hossz_cm: float, szelesseg_cm: float) -> list[str]:
    """Független ellenőrzés: határon belül vannak-e, és nincs-e átfedés. Üres lista = rendben."""
    hibak = []
    active = []
    for e in sorted(elhelyezesek, key=lambda e: e.x_cm):
        values = (e.x_cm, e.y_cm, e.hossz_cm, e.szelesseg_cm)
        if not all(math.isfinite(v) for v in values) or min(e.hossz_cm, e.szelesseg_cm) <= 0:
            hibak.append(f"A(z) {e.sorszam}. egység mérete érvénytelen.")
            continue
        if e.x_cm < 0 or e.y_cm < 0 or e.x2_cm > hossz_cm + 1e-8 or e.y2_cm > szelesseg_cm + 1e-8:
            hibak.append(f"A(z) {e.sorszam}. egység kilóg a rakodótérből.")
        active = [a for a in active if a.x2_cm > e.x_cm + 1e-8]
        for a in active:
            if a.y_cm < e.y2_cm - 1e-8 and e.y_cm < a.y2_cm - 1e-8:
                hibak.append(f"A(z) {a.sorszam}. és {e.sorszam}. egység átfedi egymást.")
        active.append(e)
    return hibak


# ---------------------------------------------------------------------------
# Fő függvény
# ---------------------------------------------------------------------------


def elfer_egyseg(hossz_cm: float, szelesseg_cm: float, forgathato: bool, rakter_hossz_cm: float, rakter_szel_cm: float) -> bool:
    t = _Tipus(0, _mm(hossz_cm), _mm(szelesseg_cm), forgathato, 1)
    return bool(t.iranyok(_mm(rakter_szel_cm), _mm(rakter_hossz_cm)))


def optimalizal(
    tetelek: list[Tetel], rakter_hossz_cm: float, rakter_szelesseg_cm: float, idokorlat_s: float = 2.0,
) -> PakolasEredmeny:
    """A rakodási hossz minimalizálása a megadott szélességű rakodótéren.

    A hossz nincs felülről korlátozva: ha a rakomány nem fér el, a szükséges hossz
    meghaladja a rakodótér hosszát (``belefer`` hamis).
    """
    if not math.isfinite(idokorlat_s) or idokorlat_s < 0:
        raise ValueError("Az időkeret véges, nemnegatív szám legyen.")
    if rakter_hossz_cm <= 0 or rakter_szelesseg_cm <= 0:
        raise ValueError("A rakodótér méretei pozitívak legyenek.")
    _mm(rakter_hossz_cm)
    for t in tetelek:
        if (not math.isfinite(t.darab) or int(t.darab) != t.darab or t.darab < 0
                or t.hossz_cm <= 0 or t.szelesseg_cm <= 0):
            raise ValueError("Érvénytelen méret vagy darabszám.")
    if sum(t.darab for t in tetelek) > 10000:
        raise ValueError("Legfeljebb 10 000 alapterületi hely tervezhető egy futásban.")
    kezdet = time.perf_counter()
    W = _mm(rakter_szelesseg_cm)
    tipusok = [
        _Tipus(t.csoport, _mm(t.hossz_cm), _mm(t.szelesseg_cm), t.forgathato, int(t.darab))
        for t in tetelek if t.darab > 0
    ]
    for t in tipusok:
        if not t.iranyok(W):
            raise ValueError("Van olyan egység, amely semmilyen tájolásban nem fér el a rakodótér szélességében.")

    if not tipusok:
        return PakolasEredmeny([], 0.0, 0.0, True, MODSZER_KORLAT, rakter_hossz_cm, rakter_szelesseg_cm)

    legjobb = _legjobb_heurisztika(tipusok, W)
    felso = _hossz(legjobb)
    also = _also_korlat(tipusok, W)
    if felso > also and sum(t.darab for t in tipusok) <= 16:
        legjobb = _sarok_nyalab(tipusok, W, legjobb, min(kezdet+idokorlat_s*0.2, time.perf_counter()+0.15))
        felso = _hossz(legjobb)
    modszer = MODSZER_KORLAT if felso <= also else MODSZER_KOZELITO
    bizonyitott = felso <= also

    egysegek = _kiterjesztett(tipusok)
    if not bizonyitott and len(egysegek) <= PONTOS_MAX_EGYSEG and time.perf_counter() < kezdet + idokorlat_s:
        x_opciok = [tuple({dx for dx, _, _ in tipusok[i].iranyok(W)}) for i in egysegek]
        y_opciok = [tuple({dy for _, dy, _ in tipusok[i].iranyok(W)}) for i in egysegek]
        x_minta = _mintaosszegek(x_opciok, felso)
        Y = sorted(set(_mintaosszegek(y_opciok, W)) | {W})
        hatarido = kezdet + idokorlat_s
        megszakitva = False
        for L in (v for v in x_minta if also <= v < felso):
            X = [v for v in x_minta if v <= L]
            if (len(X) - 1) * (len(Y) - 1) > PONTOS_MAX_CELLA:
                also, megszakitva = L, True
                break
            try:
                talalat = _pontos_kereses(tipusok, W, L, X, Y, hatarido, PONTOS_MAX_CSOMOPONT)
            except _Megszakitva:
                also, megszakitva = L, True
                break
            if talalat is not None:
                legjobb, felso = talalat, L
                break
            also = L + 1  # erre a hosszra bizonyítottan nem fér el
        if not megszakitva:
            bizonyitott, modszer, also = True, MODSZER_PONTOS, felso

    rendezett = sorted(legjobb, key=lambda r: (r[1], r[2]))
    elhelyezesek = [
        Elhelyezes(k + 1, tipusok[t].csoport, x / 10, y / 10, dx / 10, dy / 10, rot)
        for k, (t, x, y, dx, dy, rot) in enumerate(rendezett)
    ]
    hasznalt = felso / 10
    return PakolasEredmeny(
        elhelyezesek=elhelyezesek,
        hasznalt_hossz_cm=hasznalt,
        also_korlat_cm=min(also, felso) / 10,
        bizonyitott=bizonyitott,
        modszer=modszer,
        rakter_hossz_cm=rakter_hossz_cm,
        rakter_szelesseg_cm=rakter_szelesseg_cm,
        futasido_s=time.perf_counter() - kezdet,
        szabad_teruletek=szabad_teglalapok(elhelyezesek, hasznalt, rakter_szelesseg_cm),
    )
