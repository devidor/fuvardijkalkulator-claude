"""Távolság két cím között: Google Routes API (ha van kulcs), különben kézi megadás.

Kulcs: GOOGLE_MAPS_API_KEY környezeti változó vagy Streamlit Secrets. A Google Cloud
projektben a „Routes API” és a „Maps Embed API” legyen engedélyezve. Kulcs nélkül a
modul nem hív hálózatot; a felület kézi km-mezőt és egy Google Maps útvonal-linket ad.

Megjegyzés: a Routes API személyautós (DRIVE) útvonalat számol, tehergépkocsis
útvonalat nem – ez eltérhet a kamionos távolságtól.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

import rate_tables as rt

ROUTES_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"
IDOKORLAT_S = 15


class TavolsagHiba(Exception):
    pass


@dataclass(frozen=True)
class Tavolsag:
    km: float
    ido_perc: Optional[float]
    forras: str  # "google"


def google_kulcs() -> Optional[str]:
    kulcs = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if kulcs:
        return kulcs
    try:
        import streamlit as st
        return str(st.secrets.get("GOOGLE_MAPS_API_KEY", "")).strip() or None
    except Exception:  # nincs secrets.toml, vagy nem Streamlit alatt fut
        return None


def cim_szoveg(orszag: str, irsz: str = "", telepules: str = "") -> str:
    """Geokódolható cím, pl. „8000 Székesfehérvár, Magyarország”."""
    hely = " ".join(x for x in (irsz.strip(), telepules.strip()) if x)
    nev = rt.ORSZAGOK.get(orszag, orszag)
    return f"{hely}, {nev}" if hely else nev


def utvonal_link(honnan: str, hova: str) -> str:
    """Nyilvános Google Maps útvonal-link (kulcs nem kell) – kézi km-ellenőrzéshez."""
    q = urllib.parse.urlencode({"api": 1, "origin": honnan, "destination": hova, "travelmode": "driving"})
    return f"https://www.google.com/maps/dir/?{q}"


def beagyazott_terkep_url(honnan: str, hova: str, kulcs: str) -> str:
    q = urllib.parse.urlencode({"key": kulcs, "origin": honnan, "destination": hova, "mode": "driving"})
    return f"https://www.google.com/maps/embed/v1/directions?{q}"


def google_tavolsag(honnan: str, hova: str, kulcs: str, _urlopen=urllib.request.urlopen) -> Tavolsag:
    """Közúti távolság a Google Routes API-val. Hiba esetén TavolsagHiba."""
    torzs = json.dumps({
        "origin": {"address": honnan},
        "destination": {"address": hova},
        "travelMode": "DRIVE",
        "languageCode": "hu",
        "units": "METRIC",
    }).encode("utf-8")
    keres = urllib.request.Request(ROUTES_URL, data=torzs, method="POST", headers={
        "Content-Type": "application/json",
        "X-Goog-Api-Key": kulcs,
        "X-Goog-FieldMask": "routes.distanceMeters,routes.duration",
    })
    try:
        with _urlopen(keres, timeout=IDOKORLAT_S) as valasz:
            adat = json.loads(valasz.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            uzenet = json.loads(exc.read().decode("utf-8")).get("error", {}).get("message", "")
        except Exception:
            uzenet = ""
        raise TavolsagHiba(f"Google Routes API hiba ({exc.code}){': ' + uzenet if uzenet else ''}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TavolsagHiba(f"A Google Routes API nem érhető el: {exc}") from exc

    utvonalak = adat.get("routes") or []
    if not utvonalak or "distanceMeters" not in utvonalak[0]:
        raise TavolsagHiba("A Google nem talált közúti útvonalat a két cím között – ellenőrizze az irányítószámokat.")
    r = utvonalak[0]
    ido = r.get("duration")  # pl. "8123s"
    ido_perc = float(ido.rstrip("s")) / 60 if isinstance(ido, str) and ido.endswith("s") else None
    return Tavolsag(km=r["distanceMeters"] / 1000, ido_perc=ido_perc, forras="google")
