# 02. Ce știm despre o reclamă Google, câmp cu câmp

Tabelul `creative_stats` are **23 de informații despre fiecare reclamă, plus țintirea**, care are 5 criterii. Fotografia din 30.09 (`fisiere/date/atc_ro_2026-09-30.csv`) le are pe toate. Observațiile de mai jos sunt măsurate pe cele 16.723 de reclame ale băncilor din ea, dacă nu scrie altfel.

Exemplul din coloana a treia e o reclamă video Raiffeisen, `CR00542680405023653889`.

## Despre advertiser

| # | câmp | ce înseamnă | exemplu | ce am observat |
|---:|---|---|---|---|
| 1 | `advertiser_id` | codul advertiserului la Google | AR05866526753370931201 | cheia de legătură cu banca; o bancă poate avea mai multe |
| 2 | `advertiser_disclosed_name` | numele afișat | Raiffeisen Bank SA | aceeași bancă apare sub mai multe grafii |
| 3 | `advertiser_legal_name` | numele juridic | Raiffeisen Bank SA | la advertiserii neverificați poate lipsi |
| 4 | `advertiser_location` | țara advertiserului | RO | ING, Nexent și TBI sunt sucursale, cu RO; Revolut Ltd are GB |
| 5 | `advertiser_verification_status` | dacă și-a confirmat identitatea la Google | VERIFIED | 17.261 VERIFIED și 1 UNVERIFIED, în tot fișierul; nu deosebește nimic la bănci |
| 6 | `ad_funded_by` | cine a plătit, dacă altcineva decât advertiserul | DQ&A Technology NL BV | completat la 1.588 de reclame ale băncilor, niciodată cu numele advertiserului. **Arată agenția.** |
| 7 | `is_funded_by_google_ad_grants` | dacă e plătită din granturile Google pentru ONG-uri | false | `false` la toate |

## Despre reclamă

| # | câmp | ce înseamnă | exemplu | ce am observat |
|---:|---|---|---|---|
| 8 | `creative_id` | codul reclamei | CR00542680405023653889 | unic: 17.461 de coduri distincte în 17.461 de rânduri (29.09) |
| 9 | `creative_page_url` | linkul spre reclamă, pe site-ul ATC | …/advertiser/AR0586…/creative/CR0054… | se reface mereu din #1 și #8, deci poate lipsi din interogare |
| 10 | `ad_format_type` | formatul | VIDEO | TEXT, IMAGE sau VIDEO |
| 11 | `topic` | tema, pusă automat de Google | Finance | **poate diferi de pagina ATC:** la exemplul de alături, pagina scrie „Mâncare și produse alimentare” (29.09). E utilă doar ca indiciu. |

## Pentru fiecare țară în care a rulat; interogarea ia România

| # | câmp | ce înseamnă | exemplu | ce am observat |
|---:|---|---|---|---|
| 12 | `region_code` | țara | RO | mereu RO, fiindcă așa filtrăm |
| 13 | `first_shown` | prima zi de afișare în țară | 2025-04-08 | la zi, cu o zi întârziere |
| 14 | `last_shown` | ultima zi de afișare | 2026-09-28 | ultima zi din fișier e ziua de dinaintea descărcării |
| 15 | `times_shown_lower_bound` | afișările, limita de jos | 10000000 | trepte: 0–1.000, 1.000–2.000, … Cea mai frecventă e 0–1.000 (5.236 de reclame, 29.09) |
| 16 | `times_shown_upper_bound` | afișările, limita de sus | 9223372036854775807 | valoarea maximă a tipului INT64 înseamnă treapta deschisă „peste 10 milioane” |
| 17 | `times_shown_start_date` | de când sunt numărate afișările | 2025-04-08 | egală cu prima afișare la 13.850 din 13.900 (29.09) |
| 18 | `times_shown_end_date` | până când sunt numărate | 2026-06-30 | **ultima zi din date minus 90 de zile.** Înaintează zilnic: 30.06 pe 29.09, 01.07 pe 30.09 |
| 19 | `times_shown_availability_date` | data la care Google publică afișările | 2026-12-07 | completată doar la reclamele fără afișări (3.593), unde e **exact prima afișare plus 90 de zile** |

## Pentru fiecare platformă, în țara respectivă

| # | câmp | ce înseamnă | ce am observat |
|---:|---|---|---|
| 20 | `surface` | platforma: SEARCH, YOUTUBE, MAPS, PLAY, SHOPPING | **fiecare reclamă cu date le are pe toate cinci** (9.670 din 9.670). Numele nu deosebesc nimic; contează afișările de pe fiecare |
| 21 | `times_shown_lower_bound` | afișările pe platforma respectivă, limita de jos | exemplu: `YOUTUBE:400000-450000`, iar celelalte `0-1000`. Platforma principală e cea cu treapta cea mai mare |
| 22 | `times_shown_upper_bound` | limita de sus | la fel |
| 23 | `times_shown_availability_date` | data publicării, pe platformă | goală în toate cele 50.265 de perechi reclamă–platformă din fotografia din 30.09 |

7.053 de reclame n-au date de platformă: cele 3.593 fără afișări și 3.460 mai vechi.

## Țintirea: `audience_selection_approach_info`

Cinci criterii, fiecare cu una dintre valorile `CRITERIA_INCLUDED`, `CRITERIA_EXCLUDED`, `CRITERIA_INCLUDED_AND_EXCLUDED` sau `CRITERIA_UNUSED`. Sunt completate la toate reclamele.

| criteriu | ce înseamnă | folosit la |
|---|---|---:|
| `demographic_info` | vârstă, gen | 99,4% |
| `geo_location` | locație | 99,3% |
| `contextual_signals` | subiectul paginii sau al căutării | 99,9% |
| `customer_lists` | o listă încărcată de advertiser, cel mai probabil clienții proprii | 68,8% |
| `topics_of_interest` | interese | 33,2% |

**Listele de clienți** sunt criteriul care deosebește băncile:
- `EXCLUDED` înseamnă că reclama n-a fost arătată celor din listă, deci probabil banca a căutat clienți noi;
- `INCLUDED` înseamnă că li s-a arătat doar lor.

Cifrele pe bănci sunt în [03](03_REZULTATE.md).

## Câmpuri calculate de noi

| câmp | cum | ce am observat |
|---|---|---|
| `nr_tari` | câte intrări de țară are reclama | **niciuna nu are sub 2,** deci una dintre intrări pare un total. Atunci 2 înseamnă „doar în România”. E o deducție, neconfirmată de documentația Google. |
| platforma principală | platforma cu treapta de afișări cea mai mare | YouTube la 2.895 de reclame, Search la 2.742, Maps la 93, Play la 63; neclară la restul |

## Coloane fără informație pentru noi

Se pot scoate din interogare, ca să coste mai puțin:
- `is_funded_by_google_ad_grants`;
- `advertiser_verification_status`;
- `region_code`;
- `creative_page_url`, care se reface din coduri;
- `advertiser_legal_name` și `advertiser_location`, care sunt deja în lista de advertiseri;
- data publicării pe platformă (#23).

## Ce nu există deloc în setul Google

Textul, imaginea și videoclipul reclamei, pagina spre care duce, numele campaniei, cuvintele-cheie, bugetul, clicurile și numărul exact de afișări.
