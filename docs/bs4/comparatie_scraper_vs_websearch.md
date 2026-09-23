# Comparație directă: valorile extrase de scraper vs. valorile găsite prin web search

**Data:** 2026-09-21. Comparație pe date efective, nu pe acces — băncile complet blocate (CEC, Banca Transilvania) sunt excluse aici, pentru că nu există nimic de comparat. Rândurile de mai jos sunt din cele 7 bănci unde scraper-ul a extras și produse, și dobânzi: BCR, BRD, ING, Raiffeisen, Patria, Salt Bank, Garanti BBVA.

Verdict pe fiecare rând: **✅ corect** (scraper găsește aceeași valoare ca web search-ul, pe același produs), **⚠️ valoare corectă / etichetă greșită**, **❌ greșit** (valoarea e reală, dar nu e despre depozite), **∅ ratat** (web search a găsit ceva ce scraper-ul nu a extras deloc), **❓ neclar** (nu am cum să verific fără acces separat).

| Bancă | Produs / afirmație | Scraper a extras | Web search (referință) | Verdict |
|---|---|---|---|---|
| BCR | Depozit promo, sume noi, 5 luni | `nominala 6.0%`, „până la 6% dobândă la depozitul la termen pe 5 luni" | 6,20%/an lei | ✅ corect (aproximativ — diferă rotund, posibil variantă de pagină diferită) |
| BCR | 8 valori (16.41%, 14.99%, 13.9%, 10.0%, 9.94%, 9.42%, 5.99%, 4.79%) | extrase de pe pagina de depozit | — | ❌ greșit — text_sursa arată clar exemplu de **credit** („Rată fixă 714 lei/lună", „DAE=16,41%"), nu depozit |
| BRD | Depozit Progresso 1 an, interval I/II | *(nimic)* | 4,30% / 4,90% (interval I/II) | ∅ ratat — motiv găsit: în text apare „dobândă fixă **(% / an)** ... 4,30%", iar simbolul „%" din antetul coloanei rupe regex-ul înainte să ajungă la valoare |
| BRD | Cont economii YOU Save | `comision_procent 2.5%` | — | ⚠️ valoare corectă, etichetă greșită (e dobândă, nu comision — fraza are „fără comision ȘI cu o dobândă de 2,5%") |
| BRD | Cont economii YOU SAVE BUSINESS | `comision_procent 2.0%` | — | ⚠️ aceeași eroare de etichetă |
| Raiffeisen | Depozit Fresh Money, lei | `nominala 6.2% LEI` | 6,20% lei | ✅ corect, potrivire exactă |
| Raiffeisen | Depozit Fresh Money, euro | `nominala 2.5% EUR` | 2,50% euro | ✅ corect, potrivire exactă |
| Raiffeisen | valoare 5,95% pe aceeași pagină | `nominala 5.95%` | — | ❌ greșit — text_sursa: „dobândă de la 5,95% la **creditul** de nevoi personale" |
| Raiffeisen | Depozit USD 12 luni, Cont Economii pe valute | 3.3% USD, 2.8%/2.0%/1.2% EUR, 5.2%/3.0% LEI | *(nu am căutat separat)* | ❓ neclar — plauzibile ca structură, neverificate de mine |
| Patria | Depozit online, lei | `nominala 6.6% LEI` | până la 6,60% lei | ✅ corect, potrivire exactă |
| Patria | valoare 4,99% EUR pe aceeași pagină | `nominala 4.99% EURO` | — | ❌ greșit — text_sursa: „credit **ipotecar** în euro... 4,99% în primii 5 ani" |
| Salt Bank | Cont Economii Business | `nominala 4.0%` | până la 4% pe an | ✅ corect, potrivire exactă |
| Salt Bank | Depozit special, 5 luni | *(nimic)* | 6,25% | ∅ ratat — produsul „premium" nu apare deloc în cele 5 dobânzi extrase (toate sunt despre contul business) |
| Garanti BBVA | Depozit la termen, 12 luni | *(nimic)* | 5,10% | ∅ ratat |
| Garanti BBVA | valoare 7,2% extrasă în loc | `nominala 7.2% LEI` | — | ❌ greșit — text_sursa: „**credit** de nevoi personale cu dobândă fixă de 7,20%" |
| Garanti BBVA | valoare EURIBOR extrasă | `euribor_valoare 2.681%` | — | ❓ corect ca extracție, dar e un depozit **corporate** indexat EURIBOR, nu produsul retail căutat |
| ING | Depozit Bonus, 4 luni | `nominala 6.0% LEI`, 4 luni | până la 6%, 4 luni | ✅ corect, potrivire exactă |
| ING | Round Up, primii 2.000 lei | `nominala 10.0% LEI` | 10% pe primii 2.000 lei | ✅ corect, potrivire exactă |
| ING | ING Depo Invest | `nominala 50.0%` (marcat *scăzută* de sistem) | — | ❌ greșit — dar sistemul de încredere l-a prins singur, nu a trecut ca valoare sigură |
| ING | „ING Economii pentru copii" | `nominala 1.0%` | — | ❓ suspect — text_sursa vizibil spune „2% pe an"; posibil a doua cifră mai departe în linie, tăiată din afișare. De verificat direct pe pagină |
| ING | Decizii de politică monetară BNR menționate pe pagină | `nominala 6.75%`, `6.5%` | — | ❌ greșit — sunt despre rata de politică monetară a BNR, nu despre un produs ING |

## Tipare, nu incidente izolate

- **Fiecare bancă cu mai mult de o dobândă extrasă are cel puțin o valoare de credit/altă categorie amestecată cu depozitele** (BCR, Raiffeisen, Patria, Garanti BBVA) — nu e un caz izolat la BCR, e sistematic. Cauza: extractorul de rate citește orice mențiune de „dobândă/DAE/%" de pe pagină, fără să verifice dacă rândul respectiv e despre depozite.
- **Când produsul e clar și pagina e simplă (un singur headline, fără cross-sell de credit), extracția e exactă**: Fresh Money, Depozit online Patria, Cont Economii Business, Depozit Bonus, Round Up — toate 6 potriviri exacte cu web search-ul.
- **Produsele „premium"/secundare de pe o pagină cu mai multe oferte se ratează**: Progresso (BRD), depozitul special (Salt Bank), depozitul standard 12 luni (Garanti BBVA) — toate 3 rateuri complete au în comun faptul că nu erau *singurul* produs de pe pagină.
- **Plasa de siguranță funcționează parțial**: valoarea absurdă de 50% la ING a fost marcată singură ca „încredere scăzută" — sistemul de intervale plauzibile din `parser_rate.py` își face treaba când valoarea e clar imposibilă, dar nu ajută la 5,95%/4,99%/7,2% (credit), care sunt perfect plauzibile ca *procent*, doar greșite ca *categorie*.

## Concluzie practică

Recomandarea de la runda anterioară rămâne, dar precizată: nu e nevoie de un extractor de rate nou, e nevoie ca extractorul actual să verifice **categoria rândului** (are „credit"/"ipotecar"/"nevoi personale" în apropiere → exclude), nu doar plauzibilitatea valorii. Al doilea gap, ratarea produselor secundare, e o problemă diferită — de discutat separat dacă merită rezolvată acum sau e acceptabilă pentru un PoC.
