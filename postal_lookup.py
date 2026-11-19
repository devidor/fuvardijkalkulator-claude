"""Település keresése ország + irányítószám alapján.

1. Zippopotam.us – ingyenes, kulcs nélküli szolgáltatás (pl. HU, AT, DE, PL, CZ, SK, SI, HR,
   BG, FR, IT, ES, PT, NL, BE, LU, LT, DK, SE, CH, GB …).
2. Google Geocoding API – ha van GOOGLE_MAPS_API_KEY, és a fenti nem talált semmit
   (pl. RO, EE, LV, GR, IE). A kulcsnál a „Geocoding API” legyen engedélyezve.

Csak az országkód és az irányítószám megy ki a szolgáltatásnak. Streamlit-független modul.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

import rate_tables as rt

ZIPPOPOTAM_URL = "https://api.zippopotam.us/{orszag}/{irsz}"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
IDOKORLAT_S = 6


@dataclass(frozen=True)
class Talalat:
    telepulesek: tuple[str, ...]
    forras: str  # "zippopotam" | "google"
    irsz: str = ""  # a szolgáltatás által visszaadott, formázott irányítószám

    @property
    def elso(self) -> str:
        return self.telepulesek[0]


def irsz_valtozatok(orszag: str, irsz: str) -> list[str]:
    """Az országra jellemző írásmódok (CZ/SK „110 00”, PL „00-001”, PT „1000-001”, LU „L-1009”)."""
    nyers = irsz.strip().upper()
    if not nyers:
        return []
    jegyek = re.sub(r"[^0-9A-Z]", "", nyers)
    if orszag == "LU":
        jegyek = jegyek.removeprefix("L")
    if orszag == "LV":
        jegyek = jegyek.removeprefix("LV")
    valtozatok: list[str] = []
    if orszag in ("CZ", "SK") and len(jegyek) == 5:
        valtozatok.append(f"{jegyek[:3]} {jegyek[3:]}")
    elif orszag == "PL" and len(jegyek) == 5:
        valtozatok.append(f"{jegyek[:2]}-{jegyek[2:]}")
    elif orszag == "PT" and len(jegyek) == 7:
        valtozatok.append(f"{jegyek[:4]}-{jegyek[4:]}")
    elif orszag == "LU" and len(jegyek) == 4:
        valtozatok.append(f"L-{jegyek}")
    elif orszag == "LV" and len(jegyek) == 4:
        valtozatok.append(f"LV-{jegyek}")
    for v in (nyers, jegyek):
        if v and v not in valtozatok:
            valtozatok.append(v)
    return valtozatok


def _egyedi(nevek) -> tuple[str, ...]:
    latott, ki = set(), []
    for n in nevek:
        n = (n or "").strip()
        if n and n.lower() not in latott:
            latott.add(n.lower())
            ki.append(n)
    return tuple(ki)


def _get_json(url: str, _urlopen) -> Optional[dict]:
    keres = urllib.request.Request(url, headers={"User-Agent": "fuvardijkalkulator/1.0", "Accept": "application/json"})
    try:
        with _urlopen(keres, timeout=IDOKORLAT_S) as valasz:
            return json.loads(valasz.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise
    except json.JSONDecodeError:
        return None


def zippopotam(orszag: str, irsz: str, _urlopen=urllib.request.urlopen) -> Optional[Talalat]:
    kod = rt.iso2(orszag).lower()
    for v in irsz_valtozatok(orszag, irsz):
        adat = _get_json(ZIPPOPOTAM_URL.format(orszag=kod, irsz=urllib.parse.quote(v)), _urlopen)
        helyek = (adat or {}).get("places") or []
        nevek = _egyedi(h.get("place name") for h in helyek)
        if nevek:
            return Talalat(nevek, "zippopotam", (adat or {}).get("post code", v))
    return None


def google_geocode(orszag: str, irsz: str, kulcs: str, _urlopen=urllib.request.urlopen) -> Optional[Talalat]:
    q = urllib.parse.urlencode({
        "components": f"postal_code:{irsz.strip()}|country:{rt.iso2(orszag)}",
        "language": "hu",
        "key": kulcs,
    })
    adat = _get_json(f"{GEOCODE_URL}?{q}", _urlopen) or {}
    eredmenyek = adat.get("results") or []
    if adat.get("status") not in (None, "OK") or not eredmenyek:
        return None
    r = eredmenyek[0]
    nevek = list(r.get("postcode_localities") or [])
    for tipus in ("locality", "postal_town", "administrative_area_level_3", "administrative_area_level_2"):
        for c in r.get("address_components") or []:
            if tipus in c.get("types", []):
                nevek.append(c.get("long_name"))
        if nevek:
            break
    nevek_t = _egyedi(nevek)
    return Talalat(nevek_t, "google", irsz.strip()) if nevek_t else None


def telepules_keresese(orszag: str, irsz: str, google_kulcs: Optional[str] = None,
                       _urlopen=urllib.request.urlopen) -> Optional[Talalat]:
    """Első találat a két forrásból; hálózati hiba esetén None (a felület kézi bevitelt kér)."""
    if not orszag or not irsz.strip():
        return None
    try:
        talalat = zippopotam(orszag, irsz, _urlopen)
    except (urllib.error.URLError, TimeoutError, OSError):
        talalat = None
    if talalat or not google_kulcs:
        return talalat
    try:
        return google_geocode(orszag, irsz, google_kulcs, _urlopen)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
