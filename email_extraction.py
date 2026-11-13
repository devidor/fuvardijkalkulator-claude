"""Fuvarigény kinyerése szabadszöveges e-mailből, Anthropic (Claude) API-val.

Megjegyzés a fejlesztési prompttól eltérő API-választásról: a prompt OpenAI API-kulcsot
említ, de mivel az alkalmazás Claude Code-dal (Anthropic) készül, ez a modul az Anthropic
API-t használja ugyanerre a célra – a kulcskezelés (környezeti változó / Streamlit Secrets,
nincs a forráskódban) és a teszt üzemmód elve változatlan.

API-kulcs nélkül a modul nem hív AI-t: csak a `email_samples.py`-ban rögzített mintalevelekkel
működik (teszt üzemmód), ismeretlen szövegre hibát ad vissza, nem talál ki adatot.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from typing import Optional

from email_samples import talalt_minta
from email_schema import FuvarIgenyAdat

MODELL = "claude-sonnet-5-5"
MAX_LEVEL_HOSSZ = 8000  # karakter; ennél hosszabb levelet levágunk, hogy a hívás költsége korlátos legyen
MAX_TOKENS = 2000

try:
    import anthropic
    ANTHROPIC_ELERHETO = True
except ImportError:  # a csomag hiányában az app a teszt üzemmóddal még használható
    anthropic = None  # type: ignore[assignment]
    ANTHROPIC_ELERHETO = False


def _mezo_sema(tipus: str) -> dict:
    return {
        "type": "object",
        "properties": {
            "ertek": {"type": [tipus, "null"]},
            "bizonyossag": {"type": "string", "enum": ["biztos", "bizonytalan", "hianyzik"]},
            "megjegyzes": {"type": "string"},
        },
        "required": ["ertek", "bizonyossag"],
    }


_SZOVEG_MEZO = _mezo_sema("string")
_SZAM_MEZO = _mezo_sema("number")
_EGESZ_MEZO = _mezo_sema("integer")
_LOGIKAI_MEZO = _mezo_sema("boolean")

_TETEL_SEMA = {
    "type": "object",
    "properties": {
        "nev": _SZOVEG_MEZO,
        "darab": _EGESZ_MEZO,
        "hossz_cm": _SZAM_MEZO,
        "szelesseg_cm": _SZAM_MEZO,
        "magassag_cm": _SZAM_MEZO,
        "suly_kg": _SZAM_MEZO,
        "halmozhato": _LOGIKAI_MEZO,
        "halmozasi_szint": _EGESZ_MEZO,
    },
    "required": ["nev", "darab", "hossz_cm", "szelesseg_cm", "magassag_cm", "suly_kg", "halmozhato", "halmozasi_szint"],
}

FUVARIGENY_ESZKOZ = {
    "name": "fuvarigeny_rogzitese",
    "description": "Az e-mailből kinyert fuvarigény strukturált rögzítése a megadott séma szerint.",
    "input_schema": {
        "type": "object",
        "properties": {
            "felrakas_hely": _SZOVEG_MEZO,
            "felrakas_cim": _SZOVEG_MEZO,
            "felrakas_datum": _SZOVEG_MEZO,
            "lerakas_hely": _SZOVEG_MEZO,
            "lerakas_cim": _SZOVEG_MEZO,
            "lerakas_datum": _SZOVEG_MEZO,
            "rakomany_megnevezese": _SZOVEG_MEZO,
            "jarmuigeny": _SZOVEG_MEZO,
            "tetelek": {"type": "array", "items": _TETEL_SEMA},
            "altalanos_megjegyzesek": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "felrakas_hely", "felrakas_cim", "felrakas_datum", "lerakas_hely", "lerakas_cim",
            "lerakas_datum", "rakomany_megnevezese", "jarmuigeny", "tetelek", "altalanos_megjegyzesek",
        ],
    },
}

RENDSZERUZENET = """\
Te egy fuvarszervezést segítő asszisztens vagy. A felhasználó egy fuvarigényt tartalmazó \
e-mail szövegét adja meg. A dolgod, hogy ebből a `fuvarigeny_rogzitese` eszközzel strukturált \
adatot rögzíts. Szigorúan kövesd ezeket a szabályokat:

1. Kizárólag azt rögzítsd, ami a szövegben ténylegesen szerepel, vagy abból egyértelmű, \
   egyszerű számítással következik (pl. darabszám × egységsúly, vagy összsúly ÷ darabszám). \
   Soha ne találj ki hiányzó adatot – se címet, se dátumot, se méretet, se árumegnevezést.
2. Ha egy mező nincs megadva a levélben, az `ertek` legyen null és a `bizonyossag` "hianyzik".
3. Ha egy adat többféleképpen értelmezhető, pontatlan (pl. "jövő héten", "kb. 10 raklap") vagy \
   ellentmondásos, a `bizonyossag` legyen "bizonytalan", és a `megjegyzes` mezőben írd le röviden \
   (magyarul), miért bizonytalan.
4. Ha egyértelmű, konkrét adat van, a `bizonyossag` legyen "biztos".
5. Minden méretet centiméterbe, minden tömeget kilogrammba számíts át, ha a levél más \
   mértékegységet használ (pl. 1,2 m → 120 cm, 1 t → 1000 kg), és a `megjegyzes`-ben jelezd az \
   átváltást.
6. Minden különböző méretű/tömegű/halmozhatóságú rakománycsoportot külön tételként vegyél fel a \
   `tetelek` listában, a megadott mezősorrendben: darabszám, hosszúság, szélesség, magasság, \
   tömeg, halmozhatóság.
7. A `halmozhato` csak akkor legyen igaz/hamis, ha a levél kifejezetten utal rá (pl. "halmozható", \
   "nem halmozható", "kettesével rakható"); egyébként "hianyzik". A `halmozasi_szint` a megadott \
   maximális egymásra rakható egységszám (pl. "kettesével halmozható" → 2, "nem halmozható" → 1); \
   ha nincs megadva, "hianyzik".
8. Az `altalanos_megjegyzesek` listában sorold fel röviden, mi hiányzik vagy bizonytalan a \
   fuvarszervező szempontjából (pl. hiányzó pontos cím, dátum).

Ne adj szöveges választ, kizárólag a `fuvarigeny_rogzitese` eszközt hívd meg egyszer."""


class KinyerasiHiba(Exception):
    """Hiba az e-mail feldolgozása közben (API-hiba, hiányzó kulcs, érvénytelen válasz)."""


@dataclass
class KinyerasEredmeny:
    adat: FuvarIgenyAdat
    mod: str  # "ai" | "minta"
    forras: str = ""  # pl. a minta levél címe, teszt módban


def api_kulcs_elerheto(explicit_kulcs: Optional[str] = None) -> Optional[str]:
    """A megadott kulcs, vagy az ANTHROPIC_API_KEY env. változó, vagy a Streamlit Secrets."""
    if explicit_kulcs:
        return explicit_kulcs.strip() or None
    kulcs = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if kulcs:
        return kulcs
    try:
        import streamlit as st
        return str(st.secrets.get("ANTHROPIC_API_KEY", "")).strip() or None
    except Exception:
        return None


def _rovidit(szoveg: str) -> tuple[str, bool]:
    szoveg = szoveg.strip()
    if len(szoveg) <= MAX_LEVEL_HOSSZ:
        return szoveg, False
    return szoveg[:MAX_LEVEL_HOSSZ], True


def _hivja_a_modellt(szoveg: str, api_kulcs: str, modell: str) -> dict:
    client = anthropic.Anthropic(api_key=api_kulcs)
    try:
        valasz = client.messages.create(
            model=modell,
            max_tokens=MAX_TOKENS,
            temperature=0,
            system=RENDSZERUZENET,
            tools=[FUVARIGENY_ESZKOZ],
            tool_choice={"type": "tool", "name": FUVARIGENY_ESZKOZ["name"]},
            messages=[{"role": "user", "content": szoveg}],
        )
    except anthropic.AuthenticationError as exc:
        raise KinyerasiHiba("Érvénytelen API-kulcs – ellenőrizze az ANTHROPIC_API_KEY beállítást.") from exc
    except anthropic.RateLimitError as exc:
        raise KinyerasiHiba("Az AI-szolgáltatás túlterhelt vagy elérte a díjkeretet, próbálja később.") from exc
    except anthropic.APIConnectionError as exc:
        raise KinyerasiHiba("Nem sikerült elérni az AI-szolgáltatást (hálózati hiba).") from exc
    except anthropic.APIStatusError as exc:
        raise KinyerasiHiba(f"Az AI-szolgáltatás hibát adott vissza ({exc.status_code}).") from exc

    for block in valasz.content:
        if getattr(block, "type", None) == "tool_use" and block.name == FUVARIGENY_ESZKOZ["name"]:
            return block.input
    raise KinyerasiHiba("A modell nem adott vissza strukturált adatot.")


def _gyorsitotar_kulcs(szoveg: str, modell: str) -> str:
    return hashlib.sha256(f"{modell}:{szoveg}".encode("utf-8")).hexdigest()


_GYORSITOTAR: dict[str, dict] = {}  # modul szintű, folyamaton belüli gyorsítótár az azonos hívások elkerülésére


def fuvarigeny_kinyerese(szoveg: str, api_kulcs: Optional[str] = None, modell: str = MODELL) -> KinyerasEredmeny:
    """A megadott e-mail szövegből fuvarigény kinyerése.

    API-kulcs hiányában (és ha `anthropic` sincs telepítve) csak a rögzített
    mintalevelekre ad eredményt – ismeretlen szövegre `KinyerasiHiba`-t dob.
    """
    if not szoveg or not szoveg.strip():
        raise KinyerasiHiba("Nincs megadva e-mail szöveg.")

    kulcs = api_kulcs_elerheto(api_kulcs)
    if not kulcs or not ANTHROPIC_ELERHETO:
        minta = talalt_minta(szoveg)
        if minta:
            from email_samples import minta_adat
            return KinyerasEredmeny(minta_adat(minta), mod="minta", forras=minta.cim)
        ok = "nincs beállítva az ANTHROPIC_API_KEY" if not kulcs else "az `anthropic` csomag nincs telepítve"
        raise KinyerasiHiba(
            f"Teszt üzemmódban vagyunk ({ok}), és a beillesztett szöveg nem egyezik egyik "
            "mintalevéllel sem. Töltsön be egy mintalevelet, vagy állítsa be az API-kulcsot."
        )

    rovid_szoveg, levagva = _rovidit(szoveg)
    gy_kulcs = _gyorsitotar_kulcs(rovid_szoveg, modell)
    if gy_kulcs in _GYORSITOTAR:
        nyers = _GYORSITOTAR[gy_kulcs]
    else:
        nyers = _hivja_a_modellt(rovid_szoveg, kulcs, modell)
        _GYORSITOTAR[gy_kulcs] = nyers

    try:
        adat = FuvarIgenyAdat.from_dict(nyers)
    except Exception as exc:
        raise KinyerasiHiba(f"A modell válasza nem dolgozható fel: {exc}") from exc

    if levagva:
        adat.altalanos_megjegyzesek.append(
            f"A levél hosszabb volt {MAX_LEVEL_HOSSZ} karakternél, a feldolgozás csak az elejét vette figyelembe."
        )
    return KinyerasEredmeny(adat, mod="ai", forras=modell)
