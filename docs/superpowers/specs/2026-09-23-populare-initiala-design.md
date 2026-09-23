# Popularea inițială de la zero — design

Data: 23 septembrie 2026. Aprobat în conversație cu Robert, pe secțiuni.
Referința de arhitectură: `docs/arhitectura-flow.html`, figurile 2 și 3.

## Scop

Baza se populează **o singură dată, de la zero, numai cu scripturile din
repo**. Nu se folosește nimic colectat anterior: nici `date/pachet/*`, nici
`date/rezultate_*.json`, nici Bronze, nici inventarul actual din `surse`.
Rămân doar cataloagele (`banci`, `produse`, vocabularul), care sunt
configurare, nu date.

Nu se atinge stratul autonom (scheduler, rulări periodice, butoanele din
Overview).

## Constrângeri

- Doar date publice. `robots.txt` pe fiecare origine, inclusiv CDN-uri și
  după redirect.
- UA-ul unic din `crawler/__init__.py`, pe toate căile (requests și
  Playwright). Nu se imită un browser.
- **O bancă blocată se documentează ca blocată.** La 401/403/407/429/451, sau
  la o pagină de tip „Access denied" servită cu 200, cascada se oprește. Nu
  se încearcă alt canal. CEC, BT, UniCredit, Intesa ies astfel „blocate";
  completarea lor ulterioară cere o cale aprobată (comparator public sau aviz
  juridic pentru `web_search`) și se rulează doar pentru ele (`--banca`).
- Fără aviz juridic pe sursele noi, la cererea lui Robert (abatere de la
  figura 1 a artefactului, doar pentru popularea inițială).
- Crawl-delay din robots.txt respectat per origine.

## Flow

```
Banda A — DESCOPERIRE (scrie doar în `surse`)
  A1  crawler/main.py în mod descoperire
        robots → sitemap ∪ navigare BFS (2 niveluri) → clasificare
        → TOATE adresele clasificate salvate, nu doar cele vizitate
        + categoria nouă `locator` (ATM/sucursale)
  A2  claudeCrawl.py doar pentru cerințele încă lipsă la fiecare bancă
        cost înregistrat, URL verificat să existe, produse aliniate la
        cele 20 de CERINTE_TINTA
  → unire + deduplicare pe URL normalizat → `surse`

Banda B — EXTRACȚIE (citește `surse`, scrie `observations`), figura 3
  robots → requests
     ├─ blocat           → STOP, sursa marcată `blocat`, dovada salvată
     ├─ 404/410          → `disparut`
     ├─ 5xx / timeout    → reîncercare cu backoff, fără escaladare
     ├─ JS (200, gol)    → Playwright cu crawler.UA
     └─ OK
  → sanitizare (clean_main_text) → amprentă pe text sanitizat (PDF: octeți)
  → identică: STOP │ diferită: Bronze
  → structurat? (JSON locator, iTunes) → mapare directă
  → extracție deterministă (parserele din crawler/)
  → LLM doar pe liniile marcate `problema`, cifra verificată literal în text,
    încredere ≤ 0,6
  → validare (validator.py pe dobânzi; PRAGURI + ambiguitate pe tarife)
  → normalizare + deduplicare → `observations`; suspecte → coada de verificare

Banda C — HARTA
  surse `locator` → coordonate din răspunsul JSON al locatorului
  → `locatii` cu sursa `locator_banca`; rândurile `mock` se șterg
```

## Îmbunătățiri (fiecare măsurată înainte/după, în `docs/IMBUNATATIRI.md`)

1. Cascada corectă (regula de mai sus), robots după redirect, Crawl-delay.
2. `coloana`, `segment`, `categorie` transmise din parsere până în bază și
   incluse în cheia de deduplicare.
3. Descoperire completă în `crawler/main.py`: sitemap ∪ navigare, toate
   adresele salvate, EXCLUDE corectat, PDF fără sufix `.pdf`, `.xml.gz`.
4. `claudeCrawl.py`: doar pentru goluri, cost logat, URL-uri verificate,
   domeniul Salt corectat.
5. Amprentă pe text sanitizat; Bronze scris doar la schimbare.
6. Dobânzi pe toate coloanele unui rând (etalon: 41/67 prinse).
7. `validator.py` conectat pe dobânzi, înainte de scriere.
8. LLM ca rezervă de extracție, cu verificare literală.
9. Vocabular: concepte lipsă + etichete părinte pierdute.
10. Un singur parser robots (`crawler/robots.py`), cu testele portate.
11. Harta din locatoare, fără mock.
12. Defecte: importul `parser_rate` în `din_html`, `.pdf` la toate fișierele
    Bronze, răspunsurile „302" serializate (Patria), proxy `/pdf` fără robots,
    `--banca` care înlocuiește doar datele băncii respective.

Se păstrează doar ce crește acuratețea sau acoperirea, măsurat.

## Măsurare

- Teste existente: `scripts/test_validare.py`, testele din `ingest/`.
- Dobânzi: re-scorare pe `date/pachet/etalon_manual.json` (script nou
  `scripts/rescore_etalon.py`). Etalonul e folosit ca etalon, nu ca date.
- Tarife: nu există etalon; recall-ul nu se poate măsura până nu face cineva
  din echipă unul de mână (Claude nu extrage date manual).
- Raportul rulării: surse pe stare (ok / blocat / disparut / gol), valori
  brute, mapate, datate, ambigue, unite la deduplicare — pe bancă.

## Ce rămâne în afara acestui design

Google Places (condițiile de utilizare interzic stocarea și folosirea pe
altă hartă decât Google), cele 4 bănci blocate, pachetul nou al colegului
(se încarcă după popularea inițială), push-ul pe GitHub (doar cu acordul lui
Robert).
