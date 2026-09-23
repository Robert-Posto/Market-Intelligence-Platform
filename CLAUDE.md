# Market Intelligence Platform

Monitorizarea concurenței bancare din România: date publice de la 30 de bănci
(comisioane, dobânzi, aplicații, recenzii, indici BNR), normalizate într-un
vocabular comun și comparate într-o aplicație read-only. Prototip în lucru.

Python 3.12 · PostgreSQL 16 (Docker, containerul `mip-db`) · SPA în JS simplu,
fără framework · Playwright + pdfplumber · dezvoltat pe Windows.

## Citește înainte, după zonă

- `README.md`: starea curentă, problemele cunoscute, ce e mock
- `PIPELINE.md`: drumul datelor de la sursă la `observations`
- `docs/crawler/CITESTE_PENTRU_MERGE.md`: câmpurile din `date/pachet/*.json`
  (`stare_data`, `ambiguu`, `rol`)
- Restul `docs/crawler/*.md` și `docs/bs4/*.md` sunt jurnale datate, nu
  instrucțiuni.

## Comenzi

```bash
pip install -r requirements.txt && playwright install chromium
python app/server.py                      # http://localhost:8765
python ingest/router.py --pas <playwright|bs4|descoperite|pdf|tot> [--banca <slug>]
docker exec -i mip-db psql -U mip -d mip < db/<fisier>.sql
```

Verificări, după zona atinsă:

| ai modificat | rulează | trebuie să vezi |
|---|---|---|
| `app/` | `python app/verifica_pagini.py` (cu serverul pornit) | toate paginile randate |
| `crawler/` | `python scripts/test_validare.py` și `python scripts/test_robots_matcher.py` | 0 eșuate |
| `ingest/` | numără ce produce extractorul, înainte să scrii în bază | cifrele din README |
| `ingest/scraper.py`, `robots_matcher.py` | `python ingest/test_robots_matcher.py`, `test_known_block.py`, `test_crawl_bfs.py` | OK |
| `db/` | `db/sincronizeaza_vederi.sql` după migrare, apoi reîncarcă o pagină din aplicație | fără 500 |

Rulează totul din rădăcina repo-ului: unele scripturi folosesc căi relative
(`output/...`).

## Reguli

**Conformitate.** Doar date publice. Se respectă `robots.txt` pe fiecare
origine, inclusiv CDN-ul de documente. Crawler-ul se identifică cu nume și
contact, cu ecusonul din `crawler/__init__.py` (un singur loc); nu imită un
browser real și nu se ascunde ca robot anonim.
IMPORTANT: nu se
ocolesc WAF, captcha sau un `Disallow`, nici „doar de test". O bancă blocată se
documentează ca blocată. Autorii recenziilor se pseudonimizează cu `MIP_SALT`.
Abatere asumată, nu o repara fără să întrebi: un `robots.txt` cu eroare 5xx
sau timeout e tratat ca permis (vezi README, „Conformitate").

**Datele nu se aruncă și nu se ghicesc.**
- O valoare peste pragurile din `normalizeaza.PRAGURI` se marchează
  `ambiguu`, nu se șterge.
- Un serviciu care nu se mapează rămâne `comision`; nu i se ghicește conceptul.
- `ISTORIC` și `DUBLURA` **se încarcă**. Se filtrează doar la afișare, în
  vederea `observatii_curente`. Asta contrazice intenționat
  `CITESTE_PENTRU_MERGE.md`: filtrarea la încărcare a pierdut 18 schimbări de
  preț reale.
- Aplicațiile mobile ale grupului de pe altă piață (franceză, poloneză) nu se
  încarcă: recenziile lor arată ca date bune și nu sunt.
- Ce e mock (secțiunea 2.5) rămâne etichetat ca mock în interfață.

**Un singur loc pentru fiecare regulă.**
- Extractoarele produc înregistrări brute și nu știu de baza de date.
- `ingest/normalizeaza.py` e singurul loc brut → rând din bază.
- Vocabularul canonic e doar în `crawler/vocabular.py`.
- Fiecare pas din `router.py` e idempotent: șterge doar ce a scris propria
  proveniență.

**Baza de date.** Migrare nouă = `db/migration_NNN_<nume>.sql`, următorul
număr, adăugată în lista din README. După orice coloană nouă în
`observations` rulezi `db/sincronizeaza_vederi.sql`: `SELECT *` din vedere
îngheață lista de coloane, iar API-ul dă 500 deși tabela are coloana.

**Serverul e read-only.** Nicio rută nu scrie în bază. Interogările folosesc
parametri (`%s`), nu text interpolat. `/pdf` servește doar URL-uri
înregistrate în `surse`, altfel devine proxy deschis.

**Frontend.** În textele românești din `<script>` se folosesc ghilimelele
„…” sau ”, niciodată `"` ASCII în interiorul unui șir. O singură ghilimea
greșită lasă pagina albă, iar serverul răspunde totuși 200.

**Zonă înghețată.** Nu se atinge scheduler-ul, rulările periodice și butoanele
`disabled` din Overview. Prioritatea e popularea inițială, nu automatizarea.

**Dependențe.** Orice pachet nou importat intră în `requirements.txt` în
același commit.

**Date generate.** Ce citește `ingest/` stă în `date/`. Crawler-ul Playwright
scrie în `output/` (în `.gitignore`), iar în bază ajunge doar ce e copiat
explicit în `date/pachet/`. Scripturile BS4 (`extract_deposits.py`,
`itunes_lookup.py`) scriu direct în `date/`; verifică `git diff` înainte să
încarci. `date/robots/` e dovadă de
conformitate, păstrată byte cu byte: nu se editează.

## Stil

- Identificatori în română, fără diacritice. Textele pentru utilizator și
  documentația sunt cu diacritice.
- Un comentariu spune **de ce**, de regulă cu cifra măsurată care a motivat
  decizia („BCR avea 2.559 de adrese în sitemap și ne uitam la 32"). Nu
  descrie ce face codul.
- O cifră din documentație e măsurată și datată, nu estimată.
- Pe Windows, consola e cp1252: scripturile care afișează diacritice
  reconfigurează `stdout` pe UTF-8.
- Commit-uri în română, cu subiect scurt de forma „zonă: ce și de ce”. Fără
  linii `Co-Authored-By`.

## Întreținere

Când Claude greșește ceva ce o regulă ar fi prevenit, adaugă regula aici.
Șterge o regulă care nu mai previne nimic. Țintă: sub 120 de linii.
