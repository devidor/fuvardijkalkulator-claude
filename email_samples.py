"""Minta fuvarigény-levelek és a hozzájuk tartozó, előre rögzített kinyerési eredmény.

Ezeket használja a felület a „Minta levél betöltése” gombnál, a teszt üzemmód
(API-kulcs nélküli, offline kipróbálás) és az automatizált tesztek is.
A mintaeredmények kézzel ellenőrzött, a levélben ténylegesen szereplő adatok –
ugyanazt a fegyelmet követik, amit az AI-tól is elvárunk: amit a levél nem mond
ki egyértelműen, az „hiányzik” vagy „bizonytalan”, nincs kitalálva.
"""

from __future__ import annotations

from dataclasses import dataclass

from email_schema import FuvarIgenyAdat

MEZO = lambda ertek, bizonyossag="biztos", megjegyzes="": {  # noqa: E731
    "ertek": ertek, "bizonyossag": bizonyossag, "megjegyzes": megjegyzes,
}
HIANYZIK = lambda: {"ertek": None, "bizonyossag": "hianyzik", "megjegyzes": ""}  # noqa: E731


@dataclass(frozen=True)
class MintaLevel:
    cim: str
    szoveg: str
    adat: dict  # a FuvarIgenyAdat.from_dict bemenete


BUDAPEST_MUNCHEN = MintaLevel(
    cim="Budapest – München, 6 EUR-raklap (a fejlesztési prompt tesztlevele)",
    szoveg=(
        "Tisztelt Fuvarszervező!\n\n"
        "Budapestről Münchenbe szeretnénk szállítani 6 EUR-raklapot. Raklaponként "
        "120 × 80 × 150 cm, 500 kg. Az áru nem halmozható. Felrakás 2026. november 18-án.\n\n"
        "Kérjük árajánlatukat."
    ),
    adat={
        "felrakas_hely": MEZO("Budapest"),
        "felrakas_cim": HIANYZIK(),
        "felrakas_datum": MEZO("2026-11-18"),
        "lerakas_hely": MEZO("München"),
        "lerakas_cim": HIANYZIK(),
        "lerakas_datum": HIANYZIK(),
        "rakomany_megnevezese": MEZO("EUR-raklap", "bizonytalan", "a levél csak a raklaptípust nevezi meg, az áru fajtáját nem"),
        "jarmuigeny": HIANYZIK(),
        "tetelek": [{
            "nev": MEZO("EUR-raklap"),
            "darab": MEZO(6),
            "hossz_cm": MEZO(120),
            "szelesseg_cm": MEZO(80),
            "magassag_cm": MEZO(150),
            "suly_kg": MEZO(500, "biztos", "raklaponkénti tömeg"),
            "halmozhato": MEZO(False),
            "halmozasi_szint": MEZO(1),
        }],
        "altalanos_megjegyzesek": ["A pontos felrakási és lerakási cím, valamint a lerakási időpont nem szerepel a levélben."],
    },
)

GYOR_HAMBURG = MintaLevel(
    cim="Győr – Hamburg, vegyes rakomány, 2 tétel",
    szoveg=(
        "Jó napot kívánok!\n\n"
        "Szállítást kérnénk Győrből Hamburgba. 10 db ipari raklap, raklaponként "
        "120×100×140 cm, 650 kg/db, kettesével halmozható. Emellett 3 db egyedi doboz "
        "is megy, 200×120×90 cm, összesen 1800 kg, nem halmozható.\n\n"
        "Felrakás jövő héten, pontos időpontot még egyeztetünk. Hűtős felépítmény szükséges."
    ),
    adat={
        "felrakas_hely": MEZO("Győr"),
        "felrakas_cim": HIANYZIK(),
        "felrakas_datum": MEZO("jövő hét", "bizonytalan", "a levél csak hozzávetőleges időpontot ad meg, pontos dátum nincs"),
        "lerakas_hely": MEZO("Hamburg"),
        "lerakas_cim": HIANYZIK(),
        "lerakas_datum": HIANYZIK(),
        "rakomany_megnevezese": MEZO("ipari raklapos áru és egyedi dobozos áru", "bizonytalan", "két eltérő tételtípus, pontos árumegnevezés nélkül"),
        "jarmuigeny": MEZO("hűtős felépítmény"),
        "tetelek": [
            {
                "nev": MEZO("Ipari raklap"),
                "darab": MEZO(10),
                "hossz_cm": MEZO(120),
                "szelesseg_cm": MEZO(100),
                "magassag_cm": MEZO(140),
                "suly_kg": MEZO(650, "biztos", "raklaponkénti tömeg"),
                "halmozhato": MEZO(True),
                "halmozasi_szint": MEZO(2),
            },
            {
                "nev": MEZO("Egyedi doboz"),
                "darab": MEZO(3),
                "hossz_cm": MEZO(200),
                "szelesseg_cm": MEZO(120),
                "magassag_cm": MEZO(90),
                "suly_kg": MEZO(600, "biztos", "a levélben megadott 1800 kg összsúlyból, 3 db-ra osztva"),
                "halmozhato": MEZO(False),
                "halmozasi_szint": MEZO(1),
            },
        ],
        "altalanos_megjegyzesek": ["A felrakás pontos dátuma még nem ismert, csak a hét van megadva."],
    },
)

MINTAK: dict[str, MintaLevel] = {m.cim: m for m in (BUDAPEST_MUNCHEN, GYOR_HAMBURG)}


def minta_adat(level: MintaLevel) -> FuvarIgenyAdat:
    return FuvarIgenyAdat.from_dict(level.adat)


def talalt_minta(szoveg: str) -> MintaLevel | None:
    """Ha a beírt/beillesztett szöveg megegyezik (vagy majdnem megegyezik) egy mintával."""
    tisztitott = " ".join(szoveg.split()).strip().lower()
    for m in MINTAK.values():
        if tisztitott == " ".join(m.szoveg.split()).strip().lower():
            return m
    return None
