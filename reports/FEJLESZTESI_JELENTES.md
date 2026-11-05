# FuvarDíj 4.0 - fejlesztési és tesztjelentés

Elkészült: 2026-11-05. Fő alap: Claude `b91fdd96b06dc9d5dc0912f94489afd9fdd7630b`; második forrás: ChatGPT `11496b19d7de71fa158f114afeec72ea8f3195d9`.

## Kódelemzés

| Terület | ChatGPT-alap | Claude-alap | 4.0 |
|---|---|---|---|
| Elhelyezés | Sarokpont + nyalábkeresés; globális forgatási kapcsoló; 120 egységkorlát | Soros/skyline és korlátozott pontos keresés; csoportonkénti forgatás | Claude-motor + kis esetekre határidős sarokpontkeresés |
| Optimális eredmény | Nem bizonyítja | Alsó korlát és befejezett keresés alapján | Megőrzött minősítés; független kisrács-orákulummal ellenőrizve |
| Halmozás | Felhasználói jelölésre engedélyezett | Magasság, felső terhelés, túlnyúlás elemzése | Claude-részletes ellenőrzés megőrizve; ismeretlen teherbírásnál nincs ajánlat-jóváhagyás |
| Ár | Régi tarifatáblázat, egyszerű elszámolási LDM | LDM + felárak, árrés/haszonkulcs | LDM/kg/fix teljeskamion-díj; szerződéses LDM-szabály |
| Megjelenítés | Matplotlib/PNG | Méretarányos SVG, HTML | SVG megőrizve, nagyítás és letöltés; PDF |
| Követés | Munkamenet | Munkamenet | Tervazonosítóhoz kötött visszaigazolás és JSON-napló |

Az SVG megtartásának oka: a koordináták közvetlenül a számításból származnak, méretezhető és új grafikus függőség nélkül letölthető. Plotly/canvas bevezetésére nem volt igazolt használhatósági előny; átfogó felhasználói összehasonlító vizsgálat nem készült.

## Javított hibák

- Szűkített rakodótérnél az elméleti LDM most a tényleges szélességgel számol.
- A közelítő terv túlhossza nem jelent automatikusan bizonyított lehetetlenséget.
- A geometriai végellenőrzés a jármű hosszát is vizsgálja, nem csak a talált strip hosszát.
- A milliméter alatti méretek és nem véges számok nem kerekítődnek észrevétlenül vagy kerülnek számításba.
- A független ütközésellenőrzés apró átfedést sem tüntet el milliméterre kerekítéssel.
- A szabad területek számítása söprő eljárást használ; a nagy darabszám kezelése gyorsabb.
- Pontos időkeret-ellenőrzés a keresés kezdetén és sűrűbb ellenőrzés a rekurzióban.
- Rakományváltozás törli a korábbi visszaigazolást; árváltozás törli az ajánlat jóváhagyását.
- Hibás/hiányos, túlsúlyos vagy a raktérbe nem férő tervből nem keletkezik automatikus ajánlati díj.
- Magyar ő/ű karaktereket tartalmazó, beágyazott betűkészletes PDF.

## Mért eredmények

1024 különböző bemenet, 3072 összehasonlító sor; rögzített véletlenmag: 20261105.
100 hibás bemenetet mindhárom előtt a közös validátor elutasít; a fennmaradó 924 geometrián futnak a motorok.

| Motor | Raktérbe férő érvényes terv | Bizonyított strip-optimum* | Külső időkorlát |
|---|---:|---:|---:|
| ChatGPT 3 | 812 | 0 | 0 |
| Claude eredeti | 867 | 809 | 0 |
| FuvarDíj 4 | 867 | 810 | 0 |

* A bizonyított strip-optimum a raktérnél hosszabb is lehet, ezért ez más mutató, mint a járműbe férő tervek száma.

A 4.0 15 esetben rövidebb, 909 esetben azonos, 0 esetben hosszabb tervet adott a Claude-alapnál. Ez a megadott tesztkészletre és rövid keresési keretre vonatkozik, nem általános optimalitási garancia.

A ChatGPT-motor 50 nagy darabszámú esetet saját 120 egységes korlátja miatt nem kezel. A két másik motor 57 esetben alsó korláttal igazolja a helyhiányt. A bemenetek teljes tömegét és halmozását a külön alkalmazástesztek vizsgálják; a fenti érvényesség geometriai fogalom.

A motorok 0,02 másodperces pontos keresési kerettel (ahol van ilyen) és 0,5 másodperces külső futáskorláttal futottak. A ChatGPT eredeti motorban nincs belső időkorlát. Futásidők a CSV-ben: egyetlen gépen mért értékek, újrafuttatáskor változhatnak. Azonos halmozási normalizálást kapnak, nem a régi teljes alkalmazásokat hasonlítjuk.

## Ellenőrzés

- **1125 pytest teszt sikeres**, 11,58 másodperc a végső teljes futásban.
- 1024 paraméterezett eset: ismert optimumok, EUR, vegyes geometria, halmozás, hibás bemenet, nagy darabszám és 24 eredeti referencia.
- 200 függetlenül bizonyítható teljes szélességű elrendezés; 32 további kis eset teljes, független egészrács-bejárással.
- Darabszám-megmaradás, tájolás, méretmegmaradás, átfedés, határok, szabad terület és elszámolási képlet ellenőrzése.
- Az eredeti 49 Claude-teszt megőrizve; felületi próbák Streamlit AppTesttel (bevitel, csoporttörlés, HUF, kg/fix díj, jóváhagyás érvénytelenítése).
- Külön 10 000 darabos futás: 10 000 elhelyezés, 4170 cm strip-hossz, 0 ütközés; körülbelül 0,43 s. Ez túllépi a 1360 cm-es járművet.
- Import- és Python-fordításellenőrzés; helyi Streamlit-szerver indítása.
- A mintaként készített PDF két oldalának képi ellenőrzése és az ékezetek szövegkinyerési vizsgálata sikeres.
- Böngészős képernyőkép-ellenőrzés nem készült: a tesztböngésző telepítése meghiúsult. A mobilnézet teljes vizuális ellenőrzése még szükséges; az örökölt reszponzív felület és az egyoszlopos alapmezők kerültek megőrzésre.

## Megmaradó korlátok

Nincs központi adatbázis, automatikus tanulás, e-mailküldés vagy általános 3D-pakolás. A naplót JSON-ba kell menteni. A keresési időkeret nem tartalmazza a teljes renderelési és előfeldolgozási időt. A geometriai eredmény nem rakodásbiztonsági tanúsítás. A névleges járműadatok szerkeszthető példák, nem konkrét kamion tanúsított adatai.

Külső jogszerűen használható benchmarkforrást találtunk (BSPA, CC BY 4.0), de az adatait ebben a kiadásban nem futtattuk; lásd BENCHMARK_FORRASOK.md. Fuvarozói ténymérés nem állt rendelkezésre. A 24 eredeti referencia változatlanul megmaradt, eltérő bizonyító erővel.

A GitHub main ág és a jelenlegi Streamlit-alkalmazás változatlan. A futtatható új verzió a feature/fuvardij-4 ágon található; külön Streamlit-alkalmazásként telepíthető a README szerint.
