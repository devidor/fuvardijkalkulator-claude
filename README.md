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
- **3D rakodási nézet** (forgatható, nagyítható; halmok szintenként).
- **Felülnézeti rakodási ábra** (méretarányos): lefedett terület, szabad területek, felhasznált sáv,
  kihasználtság, elhelyezési koordináták, automatikus átfedés-ellenőrzés.
- **Tervezett / visszaigazolt / tényleges LDM** külön kezelve, eltérésekkel és indokkal.
- **Rakodási terv export** (nyomtatható HTML, visszaigazolási mezőkkel) és CSV-k.
- **Fuvardíj**: EUR vagy HUF / LDM, minimumdíj, felárak, haszonkulcs vagy árrés.
- **AI e-mail-feldolgozás**: beillesztett fuvarigény-e-mailből kinyeri a fuvarozási adatokat
  (felrakás/lerakás helye, dátuma, árumegnevezés, járműigény) és a rakománytételeket a Rakomány
  fülön megszokott sorrendben (darabszám, hosszúság, szélesség, magasság, tömeg, halmozhatóság).
  Amit a levél nem mond ki egyértelműen, azt **nem találja ki** – hiányzóként vagy bizonytalanként
  jelzi. Jóváhagyás/szerkesztés után egy gombnyomással átadható a kalkulátornak.

## Használati útmutató (röviden)

1. Oldalsáv: válassza ki a pótkocsitípust; szükség esetén adja meg az eltérő szabad rakodóteret,
   az elszámolási indexet és a kerekítést.
2. **AI e-mail-feldolgozás** fül (opcionális): illessze be a fuvarigény-e-mailt, kattintson a
   „Fuvaradatok kinyerése” gombra, ellenőrizze/javítsa a kinyert adatokat, majd adja át a
   kalkulátornak. Lásd lent: [AI e-mail-feldolgozás beállítása](#ai-e-mail-feldolgozás-beállítása).
3. **Rakomány** fül: vegye fel a rakománycsoportokat (kézzel, példával, vagy az AI-fülről átadva).
   A jobb oldali eredménypanel és alatta a rakodási terv minden módosításkor újraszámolódik.
4. **Visszaigazolás** fül: töltse le a rakodási tervet, küldje el a fuvarozónak, majd rögzítse a
   visszaigazolt és a rakodás utáni tényleges LDM-et.
5. **Fuvardíj** fül: válassza ki a díj LDM-alapját (alapértelmezés: elszámolási LDM) és a díjtételeket.

Részletes leírás az alkalmazás **Útmutató** fülén.

## Telepítés és futtatás

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

## AI e-mail-feldolgozás beállítása

A funkció az Anthropic (Claude) API-t használja – **API-kulcs nélkül is kipróbálható** a két
beépített mintalevéllel (teszt üzemmód: rögzített, kézzel ellenőrzött eredményt ad, nem hív AI-t).
Élő feldolgozáshoz:

1. Szerezzen Anthropic API-kulcsot: <https://console.anthropic.com/>.
2. **Helyi futtatáskor**: másolja le a `.streamlit/secrets.toml.example` fájlt
   `.streamlit/secrets.toml` néven, és írja bele a kulcsot –
   vagy állítsa be a `ANTHROPIC_API_KEY` környezeti változót. A `secrets.toml` a `.gitignore`
   miatt nem kerül fel GitHubra.
3. **Streamlit Community Cloudon**: App settings → Secrets → `ANTHROPIC_API_KEY = "sk-ant-..."`.

A kulcs sosincs a forráskódban. Egy e-mail feldolgozása kb. 1-2 ezer tokent használ (néhány
század dolláros nagyságrend); ugyanarra a szövegre ismételt kinyerés a folyamaton belül
gyorsítótárazott, nem hív újra API-t. A hosszú leveleket a program az első kb. 8000 karakterre
rövidíti, és ezt jelzi is.

**Korlátok**: a jelenlegi verzió csak a beillesztett szöveget dolgozza fel – postafiók-csatlakoztatás,
PDF/Excel-melléklet, duplikátumszűrés és automatikus levélküldés nincs megvalósítva (ezek a
fejlesztési prompt szerinti következő fázis részei). A kinyert adatok mindig felhasználói
jóváhagyásra/szerkesztésre várnak, mielőtt a kalkulátorba kerülnek.

## Tesztek

```bash
pip install -r requirements-dev.txt
python -m pytest tests
```

A tesztek lefedik az A és B referenciapéldát (240 cm, 210 cm), a díjpéldákat (2,00 és 4,00 LDM),
a forgatást, az átfedések kizárását, a határok betartását, a halmozási korlátokat, a kerekítést,
az AI e-mail-feldolgozás sémáját és teszt üzemmódját (API-kulcs nélkül, mockolt AI-hívással) és
– a Streamlit `AppTest` segítségével – az eredmények megjelenítését a felületen, a Rakomány fül
mezősorrendjét és az AI-fülről a kalkulátorba történő átadást.

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
| `visualization_3d.py` | 3D rakodási nézet (Plotly) |
| `load_plan_export.py` | Fuvarozói rakodási terv (HTML) |
| `pricing.py` | Fuvardíj-becslés |
| `email_schema.py` | Kinyert fuvarigény adatszerkezete (érték / megbízhatóság / megjegyzés) |
| `email_samples.py` | Mintalevelek és rögzített eredményük (teszt üzemmód, tesztek) |
| `email_extraction.py` | AI-hívás (Anthropic/Claude), séma, gyorsítótár, hibakezelés |
| `tests/` | Automatizált tesztek |

## Korlátok és továbbfejlesztés

Nem modellezett: tengelyterhelés, rakományrögzítés, rakodási sorrend, különböző csoportok egymásra
helyezése, több megbízó árujának együttes elhelyezése. Az AI e-mail-feldolgozás egyelőre csak
beillesztett szöveggel működik; a postafiók-csatlakoztatás, a melléklet-feldolgozás, a
duplikátumszűrés és az automatikus levélküldés a következő fejlesztési fázis része.

> Az eredmények tervezési becslések; a tervezett LDM a fuvarozó írásos visszaigazolásáig nem garantált.
