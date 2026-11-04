# 🚚 Fuvardíjkalkulátor 3.0 – rakománytervező

Magyar nyelvű Streamlit alkalmazás fuvarszervezőknek: elméleti, fizikai, tömegalapú és elszámolási
rakományméter (LDM), optimalizált raklapelrendezés, halmozási ellenőrzés, fuvarozónak küldhető
rakodási terv és fuvardíj-becslés.

## Funkciók

- **Pótkocsitípusok** (cm): Normál 1360 × 245 × 270, Semi-mega 1360 × 245 × 285, Mega 1360 × 245 × 300,
  vagy egyedi méret; a ténylegesen szabad rakodótér külön megadható.
- **Rakománycsoportok**: darabszám, méret (cm), tömeg egységenként vagy összesen, halmozhatóság
  (nem / 2 / 3 / 4 / egyedi szint), 90°-os forgathatóság, halomban eltérő tájolás, alsó egység
  megengedett felső terhelése. Különböző méretű egységek együtt is kezelhetők.
- **Elméleti LDM** = darab × hossz × szélesség ÷ (245 × 100) – területalapú alsó becslés.
- **Fizikai LDM**: kétdimenziós téglalap-elhelyezés (2D strip packing) – heurisztikák, alsó korlát és
  idő­korlátos pontos keresés. A bizonyított optimumot és a közelítő megoldást egyértelműen megkülönbözteti.
- **Tömegalapú és elszámolási LDM**: össztömeg ÷ 1750 kg/LDM (módosítható), elszámolási LDM =
  MAX(fizikai, tömegalapú), konfigurálható kerekítéssel.
- **Halmozás**: halommagasság, belmagasság, ráterhelés, túlnyúlás, felváltva forgatott halmozás;
  hiányzó adatnál „Nem igazolt” állapot.
- **Felülnézeti rakodási ábra** (méretarányos): lefedett terület, szabad területek, felhasznált sáv,
  kihasználtság, elhelyezési koordináták, automatikus átfedés-ellenőrzés.
- **Tervezett / visszaigazolt / tényleges LDM** külön kezelve, eltérésekkel és indokkal.
- **Rakodási terv export** (nyomtatható HTML, visszaigazolási mezőkkel) és CSV-k.
- **Fuvardíj**: EUR vagy HUF / LDM, minimumdíj, felárak, haszonkulcs vagy árrés.

## Használati útmutató (röviden)

1. Oldalsáv: válassza ki a pótkocsitípust; szükség esetén adja meg az eltérő szabad rakodóteret,
   az elszámolási indexet és a kerekítést.
2. **Rakomány** fül: vegye fel a rakománycsoportokat (vagy töltsön be egy példát). A jobb oldali
   eredménypanel és alatta a rakodási terv minden módosításkor újraszámolódik.
3. **Visszaigazolás** fül: töltse le a rakodási tervet, küldje el a fuvarozónak, majd rögzítse a
   visszaigazolt és a rakodás utáni tényleges LDM-et.
4. **Fuvardíj** fül: válassza ki a díj LDM-alapját (alapértelmezés: elszámolási LDM) és a díjtételeket.

Részletes leírás az alkalmazás **Útmutató** fülén.

## Telepítés és futtatás

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

## Tesztek

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

A tesztek lefedik az A és B referenciapéldát (240 cm, 210 cm), a díjpéldákat (2,00 és 4,00 LDM),
a forgatást, az átfedések kizárását, a határok betartását, a halmozási korlátokat, a kerekítést és
– a Streamlit `AppTest` segítségével – az eredmények megjelenítését a felületen.

## Streamlit Community Cloud

A tároló közvetlenül telepíthető: **Create app** → tároló, `main` ág, fő fájl: `app.py`.

## Modulok

| Fájl | Tartalom |
|---|---|
| `app.py` | Streamlit felület |
| `trailer_config.py` | Pótkocsitípusok, szabad rakodótér |
| `cargo_models.py` | Rakományadatok, validáció |
| `stacking_validator.py` | Halmozási korlátok |
| `packing_optimizer.py` | Geometriai elhelyezés (2D strip packing) |
| `ldm_calculator.py` | Elméleti, fizikai, tömegalapú, elszámolási LDM |
| `billing_config.py` | Elszámolási index és kerekítési szabályok |
| `load_planner.py` | A rakodási terv összeállítása |
| `ldm_tracking.py` | Tervezett / visszaigazolt / tényleges LDM |
| `visualization.py` | Felülnézeti SVG-ábra |
| `load_plan_export.py` | Fuvarozói rakodási terv (HTML) |
| `pricing.py` | Fuvardíj-becslés |
| `tests/` | Automatizált tesztek |

## Korlátok és továbbfejlesztés

Nem modellezett: tengelyterhelés, rakományrögzítés, rakodási sorrend, különböző csoportok egymásra
helyezése, több megbízó árujának együttes elhelyezése. A következő tervezett lépés egy AI-alapú
ajánlatkérés-feldolgozó, amely a beillesztett ügyfélszövegből nyeri ki a rakományadatokat ehhez a
számítómotorhoz (még nincs megvalósítva).

> Az eredmények tervezési becslések; a tervezett LDM a fuvarozó írásos visszaigazolásáig nem garantált.
