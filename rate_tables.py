"""Finian Logistics díjtáblák: országlista, FTL €/km javaslat, LTL-szorzótábla.

Forrás: Daniel Finian e-mailje (2026. 11. 13., „RE: Fuvardíjkalkulátor – első tesztváltozat”).
Az értékek a levélből változtatás nélkül átvett adatok; a tisztázatlan pontokat
(pl. a nem monoton szorzók) a modul nem javítja ki, csak a `gyanus_szorzok()` jelzi.
A modul Streamlit-független.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Országok
# ---------------------------------------------------------------------------

# Európai országok kódja → magyar név. A kód a levélben használt jelölés (pl. BIH, SRB, MNE).
ORSZAGOK: dict[str, str] = {
    "AL": "Albánia", "AD": "Andorra", "AM": "Örményország", "AT": "Ausztria", "AZ": "Azerbajdzsán",
    "BE": "Belgium", "BG": "Bulgária", "BIH": "Bosznia-Hercegovina", "BY": "Fehéroroszország",
    "CH": "Svájc", "CY": "Ciprus", "CZ": "Csehország", "DE": "Németország", "DK": "Dánia",
    "EE": "Észtország", "ES": "Spanyolország", "FI": "Finnország", "FR": "Franciaország",
    "GB": "Egyesült Királyság", "GE": "Grúzia", "GR": "Görögország", "HR": "Horvátország",
    "HU": "Magyarország", "IE": "Írország", "IS": "Izland", "IT": "Olaszország", "LI": "Liechtenstein",
    "LT": "Litvánia", "LU": "Luxemburg", "LV": "Lettország", "MC": "Monaco", "MD": "Moldova",
    "MK": "Észak-Macedónia", "MNE": "Montenegró", "MT": "Málta", "NL": "Hollandia", "NO": "Norvégia",
    "PL": "Lengyelország", "PT": "Portugália", "RO": "Románia", "RU": "Oroszország",
    "SE": "Svédország", "SI": "Szlovénia", "SK": "Szlovákia", "SM": "San Marino",
    "SRB": "Szerbia", "TR": "Törökország", "UA": "Ukrajna", "VA": "Vatikán", "XK": "Koszovó",
}

# ISO 3166-1 alpha-2 kódok a levél háromjegyű jelöléseihez (Google-útvonalhoz, AI-bemenethez).
ISO2 = {"BIH": "BA", "SRB": "RS", "MNE": "ME"}
_ISO2_VISSZA = {v: k for k, v in ISO2.items()}

HAZAI = "HU"

# Csak alvállalkozói díj bekérése után adható ki ajánlat.
EGYEDI_DIJAS = frozenset(
    "GB IE CH DK SE NO FI GR MD AL BIH SRB MNE UA TR GE AZ AM".split()
)
# A szankciók miatt nincs szállítás.
TILTOTT = frozenset({"BY", "RU"})


def orszag_cimke(kod: str) -> str:
    return f"{kod} – {ORSZAGOK.get(kod, kod)}"


def normalizal_orszagkod(kod: Optional[str]) -> Optional[str]:
    """ISO2 vagy levélbeli kódot a táblák kódjára alakít; ismeretlennél None."""
    if not kod:
        return None
    k = str(kod).strip().upper()
    k = _ISO2_VISSZA.get(k, k)
    if k in ("UK",):
        k = "GB"
    return k if k in ORSZAGOK else None


def iso2(kod: str) -> str:
    return ISO2.get(kod, kod)


# ---------------------------------------------------------------------------
# FTL €/km javaslat (Magyarországról indexálva)
# ---------------------------------------------------------------------------

EXPORT = "export"
IMPORT = "import"
BELFOLD = "belföld"
HARMADIK = "harmadik ország"  # egyik fél sem HU

# (országok, export €/km, import €/km)
_FTL_SOROK: tuple[tuple[str, float, float], ...] = (
    ("AT SK CZ SI HR RO BG", 2.0, 2.0),
    ("PL", 1.5, 2.0),
    ("DE IT BE NL LU", 1.6, 1.8),
    ("FR", 1.8, 1.6),
    ("PT ES LT LV EE", 1.3, 1.3),
)
FTL_EUR_PER_KM: dict[str, dict[str, float]] = {
    orszag: {EXPORT: exp, IMPORT: imp}
    for orszagok, exp, imp in _FTL_SOROK
    for orszag in orszagok.split()
}


@dataclass(frozen=True)
class Viszonylat:
    felrako: str
    lerako: str
    irany: str  # EXPORT | IMPORT | BELFOLD | HARMADIK
    partner: Optional[str]  # a nem magyar fél (export/import esetén)

    @property
    def tiltott(self) -> bool:
        return self.felrako in TILTOTT or self.lerako in TILTOTT

    @property
    def egyedi(self) -> bool:
        return self.felrako in EGYEDI_DIJAS or self.lerako in EGYEDI_DIJAS


def viszonylat(felrako: str, lerako: str) -> Viszonylat:
    if felrako == HAZAI and lerako == HAZAI:
        return Viszonylat(felrako, lerako, BELFOLD, None)
    if felrako == HAZAI:
        return Viszonylat(felrako, lerako, EXPORT, lerako)
    if lerako == HAZAI:
        return Viszonylat(felrako, lerako, IMPORT, felrako)
    return Viszonylat(felrako, lerako, HARMADIK, None)


def javasolt_eur_per_km(v: Viszonylat) -> Optional[float]:
    """A levél táblája szerinti €/km, ha van rá érték (csak HU-export/-import)."""
    if v.partner is None or v.tiltott or v.egyedi:
        return None
    sor = FTL_EUR_PER_KM.get(v.partner)
    return sor[v.irany] if sor else None


# ---------------------------------------------------------------------------
# LTL-szorzótábla
# ---------------------------------------------------------------------------

LTL_CSOPORTOK: tuple[tuple[str, ...], ...] = (
    ("AT", "SK", "CZ", "SI", "HR", "RO", "BG"),
    ("PL", "DE", "IT", "BE", "NL", "LU", "FR"),
    ("ES", "LT", "LV", "EE"),
    ("PT",),
)
LTL_CSOPORT_CIMKE = tuple(", ".join(cs) for cs in LTL_CSOPORTOK)
LDM_LEPES = 0.1
FTL_HATAR_LDM = 12.1  # ettől a szorzó 1 → az LTL-díj megegyezik az FTL-díjjal
MAX_LDM = 13.6

# ldm: (1. csoport, 2. csoport, 3. csoport, 4. csoport) – a levél táblája szerint.
# A tömeg oszlop (ldm × 1750 kg) a táblában csak tájékoztató, ezért nem tároljuk.
_LTL_NYERS = """
0.1 0.195 0.13 0.117 0.104
0.2 0.2049 0.1366 0.12294 0.10928
0.3 0.2148 0.1432 0.12888 0.11456
0.4 0.225 0.15 0.135 0.12
0.5 0.23625 0.1575 0.14175 0.126
0.6 0.2475 0.165 0.1485 0.132
0.7 0.25875 0.1725 0.15525 0.138
0.8 0.27 0.18 0.162 0.144
0.9 0.285 0.19 0.171 0.15
1.0 0.3 0.2 0.18 0.16
1.1 0.315 0.21 0.189 0.17
1.2 0.33 0.22 0.198 0.18
1.3 0.345 0.23 0.207 0.18
1.4 0.36 0.24 0.216 0.19
1.5 0.375 0.25 0.225 0.20
1.6 0.39 0.26 0.234 0.21
1.7 0.405 0.27 0.243 0.22
1.8 0.42 0.28 0.252 0.22
1.9 0.435 0.29 0.261 0.23
2.0 0.45 0.3 0.27 0.24
2.1 0.462 0.308 0.2772 0.25
2.2 0.474 0.316 0.2844 0.25
2.3 0.486 0.324 0.2916 0.26
2.4 0.4995 0.333 0.2997 0.27
2.5 0.5115 0.341 0.3069 0.27
2.6 0.5235 0.349 0.3141 0.28
2.7 0.5355 0.357 0.3213 0.29
2.8 0.549 0.366 0.3294 0.29
2.9 0.561 0.374 0.3366 0.30
3.0 0.573 0.382 0.3438 0.31
3.1 0.5865 0.391 0.3519 0.31
3.2 0.6 0.4 0.36 0.32
3.3 0.612 0.408 0.3672 0.33
3.4 0.624 0.416 0.3744 0.33
3.5 0.642 0.428 0.3852 0.34
3.6 0.6495 0.433 0.3897 0.35
3.7 0.6615 0.441 0.3969 0.35
3.8 0.6735 0.449 0.4041 0.36
3.9 0.6855 0.457 0.4113 0.37
4.0 0.699 0.466 0.4194 0.37
4.1 0.7125 0.475 0.4275 0.38
4.2 0.726 0.484 0.4356 0.39
4.3 0.7395 0.493 0.4437 0.39
4.4 0.75 0.5 0.45 0.40
4.5 0.759937 0.509 0.4581 0.41
4.6 0.769748 0.518 0.4662 0.41
4.7 0.779433 0.527 0.4743 0.42
4.8 0.788992 0.536 0.4824 0.43
4.9 0.798425 0.545 0.4905 0.44
5.0 0.806274 0.553 0.4977 0.44
5.1 0.815462 0.562 0.5058 0.45
5.2 0.82308 0.57 0.513 0.46
5.3 0.8298675 0.5775 0.51975 0.46
5.4 0.83655 0.585 0.5265 0.47
5.5 0.8431275 0.5925 0.53325 0.47
5.6 0.85668 0.605 0.5445 0.48
5.7 0.865126 0.614 0.5526 0.49
5.8 0.873446 0.623 0.5607 0.50
5.9 0.88164 0.632 0.5688 0.51
6.0 0.88832 0.64 0.576 0.51
6.1 0.890745 0.645 0.5805 0.52
6.2 0.8931 0.65 0.585 0.52
6.3 0.895385 0.655 0.5895 0.52
6.4 0.8976 0.66 0.594 0.53
6.5 0.898392 0.664 0.5976 0.53
6.6 0.899128 0.668 0.6012 0.53
6.7 0.899808 0.672 0.6048 0.54
6.8 0.8991 0.675 0.6075 0.54
6.9 0.899675 0.679 0.6111 0.54
7.0 0.900194 0.683 0.6147 0.55
7.1 0.900657 0.687 0.6183 0.55
7.2 0.89976 0.69 0.621 0.55
7.3 0.900118 0.694 0.6246 0.56
7.4 0.90042 0.698 0.6282 0.56
7.5 0.900666 0.702 0.6318 0.56
7.6 0.89958 0.705 0.6345 0.56
7.7 0.899721 0.709 0.6381 0.57
7.8 0.899806 0.713 0.6417 0.57
7.9 0.899835 0.717 0.6453 0.57
8.0 0.89856 0.72 0.648 0.58
8.1 0.898484 0.724 0.6516 0.58
8.2 0.898352 0.728 0.6552 0.58
8.3 0.898164 0.732 0.6588 0.59
8.4 0.8967 0.735 0.6615 0.59
8.5 0.896407 0.739 0.6651 0.60
8.6 0.896058 0.743 0.6687 0.61
8.7 0.895653 0.747 0.6723 0.61
8.8 0.894 0.75 0.675 0.62
8.9 0.9006 0.76 0.684 0.63
9.0 0.90706 0.77 0.693 0.64
9.1 0.91338 0.78 0.702 0.66
9.2 0.91956 0.79 0.711 0.67
9.3 0.9256 0.8 0.72 0.68
9.4 0.9315 0.81 0.729 0.69
9.5 0.93726 0.82 0.738 0.71
9.6 0.94288 0.83 0.747 0.72
9.7 0.94836 0.84 0.756 0.73
9.8 0.9537 0.85 0.765 0.74
9.9 0.9589 0.86 0.774 0.76
10.0 0.96396 0.87 0.783 0.77
10.1 0.96888 0.88 0.792 0.78
10.2 0.97366 0.89 0.801 0.80
10.3 0.9783 0.9 0.81 0.81
10.4 0.979128 0.9066 0.81594 0.82
10.5 0.9798636 0.9132 0.82188 0.83
10.6 0.9805068 0.9198 0.82782 0.84
10.7 0.9810576 0.9264 0.83376 0.85
10.8 0.981516 0.933 0.8397 0.86
10.9 0.981882 0.9396 0.84564 0.87
11.0 0.9821556 0.9462 0.85158 0.88
11.1 0.9823368 0.9528 0.85752 0.90
11.2 0.98304 0.96 0.8736 0.91
11.3 0.981405 0.965 0.8878 0.92
11.4 0.9797 0.97 0.9021 0.93
11.5 0.975 0.975 0.9165 0.94
11.6 0.9783 0.9783 0.929385 0.94
11.7 0.9816 0.9816 0.942336 0.95
11.8 0.9849 0.9849 0.955353 0.96
11.9 0.9882 0.9882 0.968436 0.97
12.0 0.9915 0.9915 0.981585 0.9766275
"""


def _beolvas() -> dict[int, tuple[float, float, float, float]]:
    tabla: dict[int, tuple[float, float, float, float]] = {}
    for sor in _LTL_NYERS.strip().splitlines():
        ldm, *szorzok = (float(x) for x in sor.split())
        tabla[round(ldm * 10)] = tuple(szorzok)  # type: ignore[assignment]
    for tized in range(round(FTL_HATAR_LDM * 10), round(MAX_LDM * 10) + 1):
        tabla[tized] = (1.0, 1.0, 1.0, 1.0)
    return tabla


# Kulcs: ldm tizedekben (1 = 0,1 ldm … 136 = 13,6 ldm).
LTL_SZORZOK: dict[int, tuple[float, float, float, float]] = _beolvas()


def ltl_csoport(v: Viszonylat) -> Optional[int]:
    """A szorzótábla oszlopa (0–3) a nem magyar fél országa szerint; None, ha nincs."""
    if v.partner is None:
        return None
    for i, cs in enumerate(LTL_CSOPORTOK):
        if v.partner in cs:
            return i
    return None


def dijszamitasi_ldm(ldm: float) -> float:
    """Felfelé kerekítés 0,1 ldm-re, legalább 0,1 ldm (lebegőpontos zaj nélkül)."""
    if ldm <= 0:
        raise ValueError("Az LDM legyen nagyobb 0-nál.")
    tized = -int(-round(ldm * 10, 6) // 1)  # ceil, 6 tizedesre kerekítve a zaj ellen
    return max(1, tized) / 10


def ltl_szorzo(ldm: float, csoport: int) -> float:
    """Szorzó a díjszámítási (0,1-re felkerekített) ldm-hez; 13,6 ldm felett 1."""
    if csoport not in range(len(LTL_CSOPORTOK)):
        raise ValueError("Ismeretlen LTL-szorzócsoport.")
    tized = round(dijszamitasi_ldm(ldm) * 10)
    if tized > round(MAX_LDM * 10):
        return 1.0
    return LTL_SZORZOK[tized][csoport]


def gyanus_szorzok() -> list[tuple[float, int, float, float]]:
    """(ldm, csoport, előző szorzó, szorzó) – ahol a szorzó nem nő az ldm-mel.

    A Danieltől kért ellenőrzéshez: az ilyen sorok valószínűleg elírások.
    """
    eredmeny = []
    kulcsok = sorted(LTL_SZORZOK)
    for elozo, akt in zip(kulcsok, kulcsok[1:]):
        for cs in range(len(LTL_CSOPORTOK)):
            a, b = LTL_SZORZOK[elozo][cs], LTL_SZORZOK[akt][cs]
            if b <= a and b < 1.0:
                eredmeny.append((akt / 10, cs, a, b))
    return eredmeny
