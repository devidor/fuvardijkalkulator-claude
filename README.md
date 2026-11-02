# 🚚 Intelligens fuvar- és rakománykalkulátor

Magyar nyelvű Streamlit alkalmazás fuvarszervezőknek: rakományméter (LDM), halmozhatóság,
rakodási helyigény és becsült fuvardíj kiszámítása.

## Funkciók

- **Rakománycsoportok** – tetszőleges számú csoport felvétele és törlése (vegyes halmozhatóság).
- **Szabványos raklapok** (EUR 120×80, ipari 120×100, fél 80×60) automatikus méretkitöltéssel,
  vagy teljesen egyedi rakományméret.
- **Halmozás** 1–4 szinten vagy egyedi szintszámmal; ellenőrzi a belmagasságot és a ráterhelhetőséget,
  és ha a kért halmozás nem biztonságos, a legnagyobb megengedett szinttel számol.
- **Elméleti LDM és tényleges helyigény** elkülönítve: soros rakodási elrendezés (hosszirányban /
  elforgatva), felülnézeti vázlattal.
- **Fuvardíj** EUR vagy HUF / LDM alapon, minimumdíjjal, felárakkal (útdíj, üzemanyag-pótdíj,
  várakozás, egyéb), haszonkulccsal **vagy** árréssel – a két fogalom külön kezelve.
- **Figyelmeztetések**: túl magas rakomány, teherbírás túllépése, nem megengedett halmozás,
  el nem férő méret, nem igazolható berakhatóság.
- **CSV-export** (pontosvessző, tizedesvessző, UTF-8 BOM – Excelben közvetlenül megnyitható).

## Telepítés és futtatás helyben

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

A böngészőben a `http://localhost:8501` címen nyílik meg.

## Tesztek

```bash
python tests/test_kalkulacio.py
```

(vagy `pytest`, ha telepítve van)

## Közzététel Streamlit Community Cloudon

1. Töltse fel a mappa tartalmát egy GitHub-tárolóba.
2. A [share.streamlit.io](https://share.streamlit.io) oldalon: **Create app** → válassza ki a tárolót,
   az ágat és fő fájlként az `app.py`-t.
3. Frissítés: a GitHubra feltöltött (push) változások után az alkalmazás automatikusan újraépül.

## Fájlszerkezet

| Fájl | Tartalom |
|---|---|
| `app.py` | Streamlit felület |
| `kalkulacio.py` | Számítási logika (Streamlit-független, újrahasznosítható) |
| `tests/test_kalkulacio.py` | A számítások tesztjei |
| `.streamlit/config.toml` | Színtéma |
| `requirements.txt` | Függőségek |

## Bővítési ötletek

`kalkulacio.py` tiszta adatszerkezetekre épül (`RakomanyCsoport`, `Potkocsi`, `DijParameterek`),
így könnyen bővíthető pl. tengelyterhelés-számítással, kg/m³-alapú díjazással, árfolyam-átváltással
vagy több járműtípus összehasonlításával.

> Az eredmények tájékoztató jellegű becslések, nem helyettesítik a rakodási tervet és a fuvarozói ajánlatot.
