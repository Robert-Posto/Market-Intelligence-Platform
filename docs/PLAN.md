# Plan — unificarea celor 3 variante de colectare

**Scop:** un singur pipeline care combină cele 3 variante deja construite, nu
le rescrie. Majoritatea „combinării" e conectare, nu cod nou — verificat
piesă cu piesă înainte de a scrie ceva.

## Cele 3 surse

1. **`Desktop/Scraping/`** (a mea, BeautifulSoup, fără LLM) — `banks.py`
   (30 bănci, cu fix-ul de URL pentru Salt Bank), `extract_deposits.py`,
   `parser_rate.py`, `itunes_lookup.py` (track mobil, unic — nicio altă
   variantă nu are asta).
2. **`Downloads/flux-colectare/`** (discovery prin LLM) — `claudeCrawl.py`
   descoperă surse prin `web_fetch`/`web_search`, fără sitemap. `db.sql`
   (schema originală, 2 erori de sintaxă), `append.sql`, `append-surse.sql`
   (340 surse descoperite, 70 în pauză pentru review uman).
3. **`Downloads/pentru_coleg_bs4_21sept/`** (numele derutant — e varianta
   **Playwright**, cea mai matură pe calitatea extracției) — module noi
   verificate: `urme.py` (hash, separă schimbare reală de schimbare de
   parser), `diferente.py` (diff preț-la-preț, testat pe BRD), `data_document.py`
   (dată efectivă din text), `vocabular.py` (mapare canonică, empiric pe 4.356
   comisioane), `ambiguitate.py` (valori reale dar neatribuibile).

## Maparea (verificată, nu presupusă)

| Piesă | Sursă | Se conectează la |
|---|---|---|
| schema DB | v2, reparată | `db/schema.sql` din acest folder |
| 30 bănci + 13 produse | v2 `append.sql` | `db/seed_banks_products.sql` |
| 340 surse descoperite | v2 `append-surse.sql` | tabelul `surse` (de adaptat — vezi „Următorii pași") |
| valori extrase (comisioane/dobânzi) | v3 `comisioane_unificate.json` + `rate_validate.json`, filtrate `stare_data NOT IN (ISTORIC, DUBLURA)` | tabelul `observations` |
| `hashes` | v3 `urme.py` | tabelul `hashes` |
| `change_events` | v3 `diferente.py` | tabelul `change_events` |
| track mobil (iOS) | a mea, `itunes_lookup.py` | `app_release`/`app_review`/`app_screenshot` |
| indici BNR | v3 `bnr_indici.json` | `indici_referinta` |

## Schema — fix-uri aplicate față de v2 (vezi comentarii în `db/schema.sql`)

- 2 virgule orfane scoase (tabelele `hashes` și `observations` nu rulau).
- `surse.produse BIGINT[]` → tabel de legătură `surse_produse` (decizie deja
  luată în artifact-ul Flow-uri MIP, figura 2 — many-to-many, nu array).
- Index unic pe `surse` activat (era comentat).
- `observations.id_hash` — legătură reală spre `hashes`, care în v2 nu era
  referită de nimeni.
- `observations.metoda_extractie` — provenență (playwright/bs4/llm/manual),
  absentă în v2.
- Tabele noi: `change_events`, `app_release`, `app_review`, `app_screenshot`,
  `indici_referinta`.

## Ordinea de lucru

1. ✅ Folder nou, curat (`Desktop/mip/`).
2. ✅ Schema reparată + extinsă (`db/schema.sql`).
3. ✅ Seed bănci + produse (`db/seed_banks_products.sql`).
4. ⬜ Postgres local prin Docker (`docker-compose.yml`) — pornit acum.
5. ⬜ Rulare schema + seed în container.
6. ⬜ Adaptare `append-surse.sql` (340 surse) la schema nouă (fără coloana
   `produse` array — populare separată în `surse_produse`).
7. ⬜ Populare `observations` din `comisioane_unificate.json` + `rate_validate.json`
   (v3), cu filtrul `stare_data`.
8. ⬜ Populare `hashes` din `urme.json` (v3) și `change_events` din
   rezultatele `diferente.py` (v3).
9. ⬜ Populare `app_release`/`app_review`/`app_screenshot` din
   `rezultate_app_store.json` (al meu).
10. ⬜ Populare `indici_referinta` din `bnr_indici.json` (v3).
11. ⬜ Mini-aplicație de vizualizare (read-only), peste baza reală.

## Ce NU e în scop încă (semnalat explicit, nu ignorat)

- Router-ul care decide automat ce extractor rulează pe o sursă nouă,
  nedescoperită încă. Vine după ce toate datele deja existente sunt în bază.
- Bronze (bytes bruți) pentru colectări viitoare.
- Extracție PDF automatizată (41 documente din 340 rămân neacoperite, per
  `FLUX-COLECTARE.md`).
- Google Places API (secțiunea 2.5) — doar idee, nimic construit.
