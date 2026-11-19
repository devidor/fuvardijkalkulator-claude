"""Ország + település felismerése csak az irányítószámból (Google Geocoding API).

Minden jelölt országa és települése ugyanabból a Google-találatból származik; a kódot és a
nevet a válasz `country` komponenséből olvassuk. Csak a díjtáblákban szereplő (európai)
országok maradnak meg. Külön modul (nem a postal_lookup bővítése), mert a Streamlit Cloud
frissítéskor nem tölti újra a már importált modulokat. Streamlit-független.
"""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Optional

import rate_tables as rt
from postal_lookup import GEOCODE_URL, _egyedi, _get_json

ELUTASITO_STATUSZOK = ("REQUEST_DENIED", "OVER_QUERY_LIMIT", "OVER_DAILY_LIMIT", "INVALID_REQUEST")


@dataclass(frozen=True)
class Jelolt:
    orszag: str  # a díjtáblák kódja (pl. AT, SRB)
    orszag_nev: str  # a Google által adott név (pl. „Ausztria”)
    telepules: str
    irsz: str

    @property
    def cimke(self) -> str:
        return f"{self.orszag_nev} ({self.orszag}) – {self.telepules}, {self.irsz}"


class GeocodeHiba(Exception):
    """A Google Geocoding API elutasította a kérést (pl. nincs engedélyezve a kulcson)."""


_ORSZAG_ELOTAG = re.compile(r"^\s*([A-Za-z]{2,3})\s*[- ]\s*(\S.*)$")


def orszag_elotag(szoveg: str) -> tuple[Optional[str], str]:
    """„AT-1230” / „at 1230” → („AT”, „1230”); ismeretlen előtagnál (None, a szöveg)."""
    m = _ORSZAG_ELOTAG.match(szoveg or "")
    if m:
        kod = rt.normalizal_orszagkod(m.group(1))
        if kod:
            return kod, m.group(2).strip()
    return None, (szoveg or "").strip()


def _komponens(r: dict, tipus: str, mezo: str = "long_name") -> str:
    for c in r.get("address_components") or []:
        if tipus in c.get("types", []):
            return c.get(mezo) or ""
    return ""


def _telepulesek(r: dict) -> list[str]:
    nevek = list(r.get("postcode_localities") or [])
    if not nevek:
        for tipus in ("locality", "postal_town", "administrative_area_level_3", "administrative_area_level_2"):
            nev = _komponens(r, tipus)
            if nev:
                nevek.append(nev)
                break
    return list(_egyedi(nevek))


def orszag_felismerese(irsz: str, kulcs: str, elonyben: Optional[str] = None,
                       _urlopen=urllib.request.urlopen) -> list[Jelolt]:
    """Jelöltek (ország, település) az irányítószámhoz.

    `elonyben`: a jelenleg választott ország – a Google ezt részesíti előnyben (region), és
    ennek a jelöltjei kerülnek a lista elejére. Üres lista: nincs (európai) találat.
    GeocodeHiba: a kérést a Google elutasította (kulcs / API-engedély / kvóta).
    """
    irsz = (irsz or "").strip()
    if not irsz:
        return []
    parameterek = {"components": f"postal_code:{irsz}", "language": "hu", "key": kulcs}
    if elonyben:
        parameterek["region"] = rt.iso2(elonyben).lower()
    adat = _get_json(f"{GEOCODE_URL}?{urllib.parse.urlencode(parameterek)}", _urlopen) or {}
    statusz = adat.get("status")
    if statusz in ELUTASITO_STATUSZOK:
        raise GeocodeHiba(f"Google Geocoding API: {statusz}"
                          + (f" – {adat['error_message']}" if adat.get("error_message") else ""))

    jeloltek: list[Jelolt] = []
    for r in adat.get("results") or []:
        kod = rt.normalizal_orszagkod(_komponens(r, "country", "short_name"))
        if not kod:
            continue
        orszag_nev = _komponens(r, "country") or rt.ORSZAGOK[kod]
        talalt_irsz = _komponens(r, "postal_code") or irsz
        for telepules in _telepulesek(r):
            j = Jelolt(kod, orszag_nev, telepules, talalt_irsz)
            if j not in jeloltek:
                jeloltek.append(j)
    if elonyben:
        jeloltek.sort(key=lambda j: j.orszag != elonyben)
    return jeloltek
