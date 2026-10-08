# 01. Cum am scos reclamele Google, pas cu pas

Totul s-a făcut de mână, în consola BigQuery, apoi local, cu scripturi care citesc doar fișierele descărcate. Niciun cod nu s-a conectat la Google și nicio cerere automată nu a ajuns la site-ul Ads Transparency Center (ATC).

## Sursa: setul public din BigQuery

- **Setul:** `bigquery-public-data.google_ads_transparency_center`.
- **Tabelul folosit:** `creative_stats`, cu un rând pe reclamă și statistici pe fiecare țară.
- **Al doilea tabel,** `removed_creative_stats`, are reclamele scoase de Google și motivul. Nu l-am folosit.
- Google publică aici reclamele livrate în Spațiul Economic European, obligat de Regulamentul UE privind serviciile digitale (DSA, art. 39).
- Setul e public și nu cere aprobare. Termenii sunt „Ads Transparency Center Additional Terms”; clauza de lămurit cu juristul e în documentul din `context/`.

## Pasul 1. Proiectul Google Cloud

- Consola: <https://console.cloud.google.com/bigquery>. Intri cu un cont Google.
- **Sandbox, fără card.** Proiectul rămâne gratuit și nu poate fi taxat. Limitele lui:
  - 1 TiB (1.024 GB) de interogări pe lună;
  - 10 GB de stocare, iar tabelele salvate se șterg după 60 de zile.
  - Peste 1 TiB, interogările dau eroare până luna următoare.
- **Proiectul folosit acum** e sandbox-ul personal al lui Nicolae, „Default Gemini Project”, pe contul lui Google. Pentru folosirea curentă trebuie un proiect al organizației, creat de IT.
- **Pe un proiect cu card,** ce trece de 1 TiB costă 6,25 USD/TiB. E prețul din regiunile US; locația setului n-am confirmat-o.

## Pasul 2. Tabelul și schema, gratuit

- Linkul direct: <https://console.cloud.google.com/bigquery?p=bigquery-public-data&d=google_ads_transparency_center&t=creative_stats&page=table>
- Taburile **Schema**, **Details** și **Preview** nu consumă nimic.
- Câmpurile, unul câte unul, sunt în [02_CAMPURI.md](02_CAMPURI.md).

## Pasul 3. Cum se citește costul unei interogări

- **Înainte de Run,** în dreapta sus a editorului apare „This query will process X GB when run”. Estimarea e gratuită. Uită-te la ea de fiecare dată.
- **Costul depinde doar de coloanele citite, pe tot tabelul.** Filtrele `WHERE` și `LIMIT` nu-l scad. Tabelul nu e partiționat pe advertiser, deci o căutare pe câteva bănci citește la fel de mult ca una pe toate.
- **Interogările pe rezultatul unei rulări anterioare sunt aproape gratuite.** Rezultatul stă 24 de ore într-un tabel temporar: în **Job information**, la „Destination table”. O interogare pe el costă câțiva MB (măsurat: 1,75 MB), nu zeci de GB.

## Pasul 4. Ce am rulat, în ordine

| # | zi | ce | cost | rezultat |
|---:|---|---|---:|---|
| 1 | 29.09 | Interogare copiată cu exemplul `'AR…'` nemodificat, rulată de două ori din greșeală | ~116 GB | 0 rânduri |
| 2 | 29.09 | Căutare după nume: reclamele livrate în RO ale advertiserilor al căror nume seamănă cu băncile | 55 GB | toate reclamele advertiserilor găsiți, cu multe potriviri false |
| 3 | 29.09 | Două rezumate pe tabelul temporar de la pasul 2: un rând pe advertiser, cu numărul de reclame | ~1,75 MB | lista advertiserilor, lipită apoi în chat |
| 4 | 29.09 | Clasificare de mână a advertiserilor, în `google_advertiseri.csv` | – | 22 de ID-uri numărate |
| 5 | 29.09 | Fotografia pe ID-uri, cu 11 coloane | neraportat | 17.461 de reclame, JSON de 8,51 MB (`atc_ro_2026-09-29.json`) |
| 6 | 29.09 | Căutarea celor 17 bănci negăsite, sub toate numele lor (`descoperire_banci_lipsa.sql`) | neraportat | 265 de advertiseri; nicio bancă din RO (`descoperire_2026-09-29.json`) |
| 7 | 29–30.09 | Verificări de mână pe site-ul ATC, în browser | 0 | vezi mai jos |
| 8 | 30.09 | Fotografia completă, cu 22 de coloane (`fotografie.sql`) | 131 GB | 17.262 de rânduri, CSV de 10,03 MB (`atc_ro_2026-09-30.csv`) |

În septembrie s-au consumat cel puțin 302 GB măsurați, din 1.024. Pentru rulările 5 și 6, costul nu l-am notat.

**Verificările de mână (pasul 7).** Nicolae a deschis paginile în browser, ca orice vizitator:
- **„Revolut” (RO), `AR02349465248282443777`:** 4 reclame, toate anunțuri Autovit.ro, de la un advertiser cu identitatea neconfirmată. Nu e Revolut, deci e exclus.
- **Raiffeisen Bank International, `AR09268197339212808193`:** 747 de reclame livrate și în RO, dar în germană. E exclus.
- **Căutarea după site `brd.ro`:** 4 reclame în RO, publicate de agenția Sense8 Digital Technology (`AR09791246187460820993`). Doar așa am găsit BRD.
- **Revolut Ltd, `AR07098428377224183809`:** ~20% dintre reclame sunt în română.
- **Testul de încadrare:** paginile ATC într-un iframe întorc 403. Vezi [04](04_LIMITE.md).

## Pasul 5. Găsirea advertiserilor

- Un advertiser are un ID fix (`AR…`). O bancă poate avea mai multe ID-uri: BT are 2, ING 2, Revolut 3.
- Căutarea se face o dată, după nume, iar fotografiile următoare se fac doar pe ID-uri.
- **Interogarea recomandată:** [fisiere/descoperire_advertiseri.sql](fisiere/descoperire_advertiseri.sql). Caută după nume, nume juridic și plătitor, pentru toate cele 30 de bănci, și întoarce un rând pe advertiser.
  - E reuniunea celor două căutări rulate pe 29.09; în forma asta n-a fost rulată.
  - Costul estimat e de zeci de GB, fiindcă citește coloanele de nume pe tot tabelul.
- **Capcanele,** toate întâlnite:

| capcană | exemplu măsurat |
|---|---|
| **firme cu nume asemănător** | „GARANTI PREST”, cu 1.796 de reclame; 151 de firme cu „Exim” în nume |
| **advertiser cu nume de bancă, dar altceva** | „Revolut” (RO) cu reclame Autovit; „BCR Asigurări de Viață”, care e Vienna Insurance Group, cu 230 de reclame |
| **aceeași bancă sub mai multe grafii** | „Banca Transilvania SA” și „BANCA TRANSILVANIA SA”, cu ID-uri diferite |
| **grupuri din alte țări cu reclame livrate și în RO** | RBI (Austria), Société Générale, Intesa (Italia), ProCredit, BNP și Cetelem (Spania), PKO, Citi: 513 reclame, plus cele 747 RBI |
| **bănci care publică prin agenții** | Intesa, prin WPP Media Romania, găsită după „plătit de”; BRD, prin Sense8, găsită doar căutând `brd.ro` pe site-ul ATC |

## Pasul 6. Clasificarea: `fisiere/google_advertiseri.csv`

Fiecare ID găsit primește un rol. Lista are 91 de rânduri (30.09):

| rol | ce înseamnă | câte |
|---|---|---:|
| `banca` | banca însăși sau singura entitate care face reclame pentru RO (Revolut Ltd, din Marea Britanie) | 17 ID-uri, 13 bănci |
| `filiala` | filiale, arătate separat și neincluse în comparație: BCR Social Finance, BCR Leasing, BCR Pensii, BRD Asset Management | 4 |
| `agentie` | o agenție care publică pentru o bancă. Contează la bancă doar dacă „plătit de” o numește | 2 (WPP pentru Intesa, Sense8 pentru BRD) |
| `exclus` | potriviri false, grupuri din alte țări, asiguratori | 67 |
| `de_verificat` | neclar: un advertiser „CETELEM” fără nume juridic și fără țară, cu 2 reclame | 1 |

Coloana `nota` spune de ce are fiecare ID rolul lui, cu data verificării.

## Pasul 7. Fotografia

- **Interogarea:** [fisiere/fotografie.sql](fisiere/fotografie.sql). Nu se scrie de mână, ci se generează din listă:

  ```
  python fisiere/interogare_fotografie.py > fisiere/fotografie.sql
  ```

- **Ce ia:** toate reclamele livrate în RO ale ID-urilor cu rol `banca` sau `filiala`, plus reclamele oricui are la „plătit de” numele unei bănci. Cu a doua regulă au apărut cele 42 de reclame Intesa publicate de WPP.
- **Agențiile nu intră pe ID.** Contul unei agenții aduce și reclamele altor clienți: Sense8 a adus 364 de reclame, toate cu „plătit de” gol.
- **Structurile devin text,** fiindcă un CSV nu poate ține liste:
  - `platforme` e de forma `SEARCH:1000-2000:<data>;YOUTUBE:…`;
  - țintirea e un text JSON.
- **Costul:** 131 GB pe 30.09, pentru toate cele 22 de coloane. Fără coloanele care nu aduc informație (vezi [02](02_CAMPURI.md)), ar costa mai puțin; cât anume, arată estimarea din consolă.

## Pasul 8. Descărcarea

1. Apeși **Run**, apoi, deasupra rezultatelor, **Save results**.
2. Alegi **CSV (local file)**. Consola descarcă local cel mult 10 MB pe fișier. Nu e un buget: poți descărca oricâte fișiere.
3. Dacă rezultatul e mai mare, alegi **CSV (Google Drive)** (până la 1 GB), apoi îl descarci din Drive. Pe 30.09, fișierul de 10,03 MB a mers așa.
4. **CSV, nu JSON.** Pentru aceleași 17.461 de rânduri din 29.09, JSON-ul a avut 8,51 MB, iar CSV-ul 3,71 MB.
5. **Fișierul nu se trimite în chat și nu se atașează.** Pe 29.09, un JSON de 8,5 MB atașat unei conversații cu Claude a blocat-o definitiv („Prompt is too long”). Fișierul se lasă pe disc, iar scripturile îl citesc de acolo.

## Pasul 9. Analiza locală

| comandă | ce face |
|---|---|
| `python fisiere/analiza_atc.py <fișier>` | tabelele pe bănci: reclame, active, noi, formate, afișări, platforme, liste de clienți, doar RO, agenții, reclame noi pe lună |
| `python fisiere/galerie.py <fișier> galerie.html` | construiește galeria din `galerie_sablon.html`; o deschizi cu dublu clic |
| `python fisiere/interogare_fotografie.py` | scrie interogarea fotografiei din lista de ID-uri |

- Toate merg și cu JSON-ul din 29.09, și cu CSV-ul din 30.09.
- `google_advertiseri.csv` trebuie să stea lângă scripturi.
- Dacă un fișier nou are un ID neclasificat, `analiza_atc.py` se oprește și îl numește: întâi îl treci în listă, cu un rol.
