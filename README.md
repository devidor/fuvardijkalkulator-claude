# FuvarDíj 4.0

Magyar nyelvű Streamlit rakománytervező és fuvardíjkalkulátor. A Claude-repository 2026. november 5-én beolvasott változatára épül, a másik projekt sarokpontkeresésével, eredeti 24 példájával és archivált tarifáival kiegészítve.

## Kipróbálás saját gépen

Python 3.12 ajánlott; Windows parancssorban a letöltött mappában:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Linux/macOS aktiválás: `source .venv/bin/activate`.

A terminálban megjelenő `http://localhost:8501` címet nyisd meg. A teljes projekt szükséges, nem csak az app.py.

## Streamlit Community Cloud

Új alkalmazást hozz létre a meglévő mellé:

- Repository: `devidor/fuvardijkalkulator-claude`
- Branch: `feature/fuvardij-4`
- Main file path: `app.py`
- Python: 3.12

A main ág változatlan. A fejlesztési ág kiválasztása önmagában nem cseréli le a meglévő, main ágról működő alkalmazást. A felhős telepítés ebben a fejlesztésben nem történt meg.
Hivatalos útmutató: https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## Használat

1. Pótkocsi: típusválasztás automatikus méretekkel; a névleges és a ténylegesen használható méretek módosíthatók.
2. Rakomány: **Darabszám → Hosszúság → Szélesség → Magasság → Súly → Halmozhatóság**. A méretek cm-ben, legfeljebb egy tizedessel; a súly egy egységre vagy a teljes csoportra adható meg. Több csoport hozzáadható és törölhető.
3. A lenyitható beállításokban forgatás, ráterhelés, raklap alátámasztási mérete és eltérő tájolás vizsgálata adható meg. A fő méretek a teljes, túlnyúlással együtt mért rakományt jelentik.
4. Eredmény: területi LDM, geometriai terv hossza, tömegalapú LDM, szerződés szerinti elszámolási LDM. Az alapértelmezés a fizikai és tömegalapú érték maximuma; választható csak fizikai vagy csak tömegalapú szabály és kerekítés.
5. Ábra: méretarányos SVG, színes csoportok, szintszámok, forgatásjel, nagyítás és letöltés. HTML-terv és koordináta-CSV is készül.
6. Visszaigazolás: A tervezett, B fuvarozói és C tényleges LDM külön adat. Az eltérés oka és a visszaigazolás hivatkozása rögzíthető. A napló JSON-ba menthető és visszatölthető.
7. Fuvardíj: LDM-, kg- vagy teljeskamion/fix díj, minimum, útdíj, üzemanyag, várakozás, egyéb felár, haszonkulcs vagy árrés, EUR/HUF. A két pénznem nem végez automatikus devizaváltást.
8. PDF: a fuvarozónak szánt lap a fuvarozói díjat tartalmazza; a belső ügyfélár és haszon nem kerül bele. A teljes belső árkalkuláció CSV-ben exportálható.
9. Jóváhagyás: visszaigazolás, hivatkozás, feltételek és ellenőrzött halmozási adatok után jelölhető. Bemenetváltozás érvényteleníti a korábbi visszaigazolást; díj/feltétel-változás az ajánlat jóváhagyását.
10. Tesztek és eredmények: letölthető összehasonlítás és a 24 eredeti példa.

## Számítás és értelmezés

- A motor egész milliméteres geometriát használ. Ennél finomabb bemenetet elutasít, nem kerekíti észrevétlenül kisebbre a rakományt.
- Több skyline/soros heurisztika, legfeljebb 16 alapterületi egységnél időkorlátos sarokpont-nyalábkeresés, legfeljebb 60 egységnél normálmintás pontos keresés fut.
- „Bizonyított optimum” csak a megadott kétdimenziós modellben, egyező alsó/felső korlát vagy befejezett pontos keresés alapján szerepel.
- A csúszka a keresés időkerete. Az induló heurisztikák, adatellenőrzés, ábrakészítés többletidőt igényelhetnek; nem szigorú teljes alkalmazás-futásidőkorlát.
- Ha az alsó korlát nagyobb a raktérnél, a geometriai modell szerint bizonyított a helyhiány. Ha csak a talált terv hosszabb, a jobb megoldás létezése nyitott kérdés.
- A hosszabb, pótkocsin túlnyúló strip-terv nem érvényes járműrakodás; ezt a külön járműhatár-ellenőrzés jelzi.
- A halmozási teherbírás hiányában feltételes geometriai terv készül, „Nem igazolt” státusszal; jóváhagyás nem engedélyezett.
- Az eltérő tájolású halmozás kompatibilitását elemzi, de a terv azonos tájolású, csoporton belüli halmokat használ. Nem általános 3D-optimalizáló.
- A tengelyterhelés, súlyeloszlás, ajtónyílás, rakományrögzítés és rakodási sorrend nincs ellenőrizve. A geometria nem rakodásbiztonsági tanúsítás.
- Legfeljebb 10 000 alapterületi hely. Nagy rakományoknál az ábra és táblázat megjelenítése lassulhat.
- A napló munkamenethez kötött: mentés nélkül újraindításkor elveszhet. A JSON-export a tartós megőrzés eszköze; központi adatbázis, automatikus tanulás és e-mailküldés nincs.

## Tesztelés

```bash
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python benchmark.py
```

A `benchmark.py` külső időkorlátozása Linux/macOS `SIGALRM`-ot használ; Windows alatt WSL-ben futtatható. Az alkalmazás és a pytest tesztek Windows alatt is futtathatók.

- 1024 reprodukálható bemenet, mag: 20261105.
- 200 függetlenül levezetett optimum; további 32 kis eset teljes rácsbejárásos, független ellenőrzése.
- A régi motorok változatlan másolata a `baselines/` mappában.
- Minden algoritmus azonos, előzetesen normalizált alapterületi egységeket kap. A benchmark a pakolómotorokat hasonlítja össze, nem a régi teljes felületek halmozási szabályait.
- Az érvényesség teljes darabszámot, átfedésmentességet és járműhatáron belüli elhelyezést jelent. A bizonyított strip-optimum lehet hosszabb a járműnél.
- Az eredmények szintetikus tesztbizonyítékok, nem fuvarozó által igazolt rakodások.

Részletek: [fejlesztési jelentés](reports/FEJLESZTESI_JELENTES.md), [nyers összehasonlítás](reports/comparison.csv), [bemenetek](reports/cases.json), [benchmarkforrások](reports/BENCHMARK_FORRASOK.md).
