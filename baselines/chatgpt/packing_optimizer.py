"""Deterministic 2D rectangle packing; heuristic, NOT proof of global optimality.
Units are centimetres, x = across trailer width, y = along trailer length.
"""
from dataclasses import dataclass
from math import ceil
from typing import List, Tuple

@dataclass(frozen=True)
class Item:
    name: str
    width: float
    length: float
    height: float = 0
    weight: float = 0

@dataclass(frozen=True)
class Placement:
    name: str
    x: float
    y: float
    width: float
    length: float
    rotated: bool = False

@dataclass
class PackingResult:
    placements: List[Placement]
    used_length: float
    trailer_width: float
    valid: bool
    method: str = 'heurisztikus, nem bizonyított optimum'


def validate(placements: List[Placement], trailer_width: float, trailer_length: float, clearance: float = 0.0) -> bool:
    eps = 1e-7
    for p in placements:
        if p.x < -eps or p.y < -eps or p.width <= 0 or p.length <= 0:
            return False
        if p.x + p.width > trailer_width + eps or p.y + p.length > trailer_length + eps:
            return False
    for i,a in enumerate(placements):
        for b in placements[i+1:]:
            if (a.x < b.x+b.width+clearance-eps and b.x < a.x+a.width+clearance-eps
                and a.y < b.y+b.length+clearance-eps and b.y < a.y+a.length+clearance-eps):
                return False
    return True


def _candidate_points(placed):
    xs = {0.0}; ys = {0.0}
    for p in placed:
        xs.add(round(p.x+p.width, 6))
        ys.add(round(p.y+p.length, 6))
    return sorted(xs), sorted(ys)


def pack(items: List[Item], trailer_width=245., trailer_length=1360., allow_rotate=True, beam_width=36) -> PackingResult:
    if not items:
        return PackingResult([], 0., trailer_width, True)
    if len(items)>120:
        return PackingResult([], 0., trailer_width, False, 'Legfeljebb 120 alapterületi egység optimalizálható')
    if any(it.width<=0 or it.length<=0 for it in items):
        raise ValueError('Minden méretnek pozitívnak kell lennie')
    # Larger pieces placed first; deterministic ordering helps repeatability.
    ordered = sorted(enumerate(items), key=lambda t: (-t[1].width*t[1].length, -max(t[1].width,t[1].length), t[0]))
    beam = [([], 0.0)]
    for index, item in ordered:
        choices = [(item.width,item.length,False)]
        if allow_rotate and item.width != item.length:
            choices.append((item.length,item.width,True))
        next_beam = []
        seen = set()
        for placed, used in beam:
            xs, ys = _candidate_points(placed)
            for w,l,rot in choices:
                if w>trailer_width+1e-8:
                    continue
                for x in xs:
                    if x+w>trailer_width+1e-8:
                        continue
                    for y in ys:
                        new_end = max(used,y+l)
                        if new_end > trailer_length+1e-8:
                            continue
                        q=Placement(str(index),x,y,w,l,rot)
                        if any(x < r.x+r.width-1e-8 and r.x < x+w-1e-8 and y < r.y+r.length-1e-8 and r.y < y+l-1e-8 for r in placed):
                            continue
                        next_placed=placed+[q]
                        # Canonicalize geometry to eliminate item permutations.
                        signature=tuple(sorted((round(z.x,3),round(z.y,3),round(z.width,3),round(z.length,3)) for z in next_placed))
                        if signature in seen:
                            continue
                        seen.add(signature)
                        occupied = sum(z.width*z.length for z in next_placed)
                        compactness = occupied/max(trailer_width*new_end, 0.01)
                        score=(round(new_end,5), -round(compactness,5), round(sum(z.y for z in next_placed),4))
                        next_beam.append((score,next_placed,new_end))
        if not next_beam:
            return PackingResult([],0.,trailer_width,False,'Nem található megfelelő elrendezés a megadott feltételekkel')
        next_beam.sort(key=lambda t:t[0])
        beam=[(p,u) for _,p,u in next_beam[:beam_width if len(items)<=20 else 7]]
    best=min(beam,key=lambda t:t[1])
    placements=[Placement(items[int(p.name)].name,p.x,p.y,p.width,p.length,p.rotated) for p in best[0]]
    return PackingResult(placements,best[1],trailer_width,validate(placements,trailer_width,trailer_length))
