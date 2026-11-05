# Nyilvános benchmarkforrások

Ellenőrizve: 2026-11-05. Ezek kutatási geometriai adatok, nem közúti fuvarozók által visszaigazolt rakodások.

| Forrás | Felhasználási helyzet | Kapcsolódás |
|---|---|---|
| Yajie Wen: BSPA, Mendeley Data, v1, 2025-03-10, DOI 10.17632/wpwrcxpwdp.1 | A forrásoldal CC BY 4.0 licencet tüntet fel; attribúcióval felhasználható. | 2D strip-packing kód és benchmarkadatok. https://data.mendeley.com/datasets/wpwrcxpwdp/1 |
| University of Bologna: 2DPackLib | Kutatási gyűjtemény; a konkrét fájl újraterjesztési feltételeit külön ellenőrizni kell. | Bin/strip packing és kapcsolódó problémák. https://site.unibo.it/operations-research/en/research/2dpacklib |
| ESICUP adatkatalógus | A közösség GitHubra költöztetett gyűjteménye; adatkészletenként eltérő eredet. | https://www.euro-online.org/websites/esicup/data-sets/ és https://github.com/ESICUP/datasets |

A jelen kiadásban a külső adatkészleteket nem importáltuk és nem futtattuk le; a 1024 esetes jelentés saját reprodukálható és a felhasználó projektjéből megőrzött bemeneteken alapul. A külső adatok későbbi integrálásakor a forgathatóságot, tengelyeket, egységeket és az ismert optimum eredetét az adapterben külön kell rögzíteni. A benchmark ismert legjobb eredménye nem automatikusan bizonyított optimum.

A BSPA forrásoldalon a leírás és licenc ellenőrizhető. A 24 régi rakodási példa `level_ldm` értékeit eredeti referenciaként őrizzük, nem optimális célértékként. A D/3-D/6 példák adatai és az eredeti egyszerűsített képlet eltérnek.
