# Reclamele Google ale băncilor: ce avem, cum le-am obținut, ce urmează

Nicolae Cherascu · 30.09.2026 · Market Intelligence Platform, secțiunea 2.4 („reclame active”)

Pentru colegul care verifică API-urile de reclame de la Meta, LinkedIn și Microsoft.

## Pe scurt

- **Sursa.** Reclamele Google ale băncilor se pot lua gratuit din setul public Google Ads Transparency, publicat de Google în BigQuery. Nu e nevoie de nicio aprobare de la Google.
- **Ce am descărcat.** Pe 29 și 30.09 am descărcat toate reclamele Google livrate în România de băncile noastre: **16.765 de reclame din ultimul an, de la 14 dintre cele 30 de bănci**. Ultima zi din date e 29.09.2026.
- **Ce avem despre fiecare reclamă:**
  - cine a publicat-o și, uneori, ce agenție a plătit-o;
  - în ce zile a rulat;
  - de câte ori a fost afișată, ca interval și cu 90 de zile întârziere;
  - pe ce platformă Google (Search, YouTube etc.);
  - dacă a rulat doar în România;
  - după ce criterii a fost aleasă audiența.
- **Ce nu avem:** textul, imaginea sau videoclipul reclamei. Google nu le pune în set, iar pagina lor nu se poate încadra în alt site și nici citi automat.
- **Conținutul vine doar prin API-urile Meta, LinkedIn și Microsoft**, adică exact partea ta. Fișierul [06](06_PENTRU_META_LINKEDIN_MICROSOFT.md) spune ce poți refolosi de aici.
- **Totul e o copie locală, pentru analiză internă:** nimic în bază, nimic în git. Avizul juridic pe termenii bibliotecilor de reclame nu e încă cerut (30.09).

## Ce e în arhivă

| fișier | ce găsești |
|---|---|
| [01_PASI_GOOGLE.md](01_PASI_GOOGLE.md) | pas cu pas cum am scos datele: proiectul BigQuery, interogările, costul, descărcarea, analiza |
| [02_CAMPURI.md](02_CAMPURI.md) | fiecare informație despre o reclamă, ce înseamnă și ce am măsurat în ea |
| [03_REZULTATE.md](03_REZULTATE.md) | cifrele pe bănci: reclame, platforme, agenții, țintire, sezonul de Crăciun |
| [04_LIMITE.md](04_LIMITE.md) | ce nu există în date, ce nu merge tehnic, ce nu avem voie, ce n-am putut |
| [05_URMEAZA.md](05_URMEAZA.md) | ce se poate face mai departe, în ordine |
| [06_PENTRU_META_LINKEDIN_MICROSOFT.md](06_PENTRU_META_LINKEDIN_MICROSOFT.md) | ce poți refolosi pentru celelalte API-uri: lista de bănci, capcanele, un model comun de date |
| `fisiere/` | interogările SQL, scripturile Python, lista de advertiseri, șablonul galeriei |
| `fisiere/date/` | datele descărcate (29.09 și 30.09) și galeria locală |
| `context/RECLAME_BIBLIOTECI_OFICIALE_2026-09-28.md` | documentul din 28.09 despre cele patru biblioteci: termeni, acces, pași. Partea despre Google e depășită de arhiva asta; secțiunile Meta, LinkedIn și Microsoft sunt valabile. |

## De unde începi

1. **Vezi datele.** Deschide `fisiere/date/galerie.html` în browser, cu dublu clic. E prototipul unei pagini din aplicație: câte un card pe reclamă, cu filtre după bancă, format, perioadă, sezon, platformă și țintire. „Previzualizare” deschide reclama pe Google, într-o fereastră mică.
2. **Dacă lucrezi la Meta, LinkedIn sau Microsoft,** citește [06](06_PENTRU_META_LINKEDIN_MICROSOFT.md), apoi [04](04_LIMITE.md).
3. **Dacă vrei să refaci partea Google,** citește [01](01_PASI_GOOGLE.md) și [02](02_CAMPURI.md).
4. **Scripturile** cer Python 3.12 și doar biblioteca standard. Se rulează din folderul arhivei:

   ```
   python fisiere/analiza_atc.py fisiere/date/atc_ro_2026-09-30.csv
   python fisiere/galerie.py fisiere/date/atc_ro_2026-09-30.csv galerie.html
   python fisiere/interogare_fotografie.py > fotografie.sql
   ```

## Regulile proiectului care se aplică și aici

- **Doar date publice, din surse oficiale.**
- **Fără scraping pe platformele de reclame:** nu deschidem automat paginile lor și nu le citim API-urile interne.
- **Fără servicii terțe care colectează în locul nostru**, cum sunt Apify sau SerpApi.
- **Fără ocolirea protecțiilor anti-bot.**
- **Orice cerere HTTP automată** trece prin fluxul proiectului, cu ecusonul din `crawler/__init__.py`, care conține nume și contact, și cu `robots.txt` respectat.
- **Datele de reclame nu intră în git și nici în bază până la aviz.** Stau în foldere ignorate de git; în repo, în `output/reclame/`.
- **O cifră scrisă într-un document e măsurată și datată.** Estimările sunt marcate ca atare.
