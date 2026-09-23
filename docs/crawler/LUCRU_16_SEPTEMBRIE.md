# Ce am lucrat pe 16 septembrie 2026

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 16 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

Material-sursă pentru sinteza către echipă. Conține cifrele exacte, ce s-a schimbat
în cod și ce nu merge încă.

Pagina de prezentare, deja făcută: https://claude.ai/artifact/N4sM5EF2e6BFwRxFEJh8rV
(privată până e distribuită din meniul de share)

Raportul tehnic detaliat: [ETALON_MANUAL.md](ETALON_MANUAL.md)

---

## Pe scurt

Patru blocuri de lucru, în ordinea în care s-au întâmplat:

1. **Etalon manual** — am verificat de mână, pe paginile live, dacă datele scoase
   de crawler sunt corecte. A găsit 6 defecte.
2. **Reparații la extragere** — rândurile de tabel și etichetele greșite.
3. **Reparații la validare** — regula de calendar IRCC, perioada de valabilitate,
   indicele implicit.
4. **Sondaj PDF** — am verificat ce conțin cele 320 de documente descărcate, ca să
   putem estima efortul de parsare.

Rezultatul cu valoare de intelligence competitiv: **trei bănci publică indici de
referință expirați** (Garanti BBVA, Libra, BRD), toate confirmate manual din surse
publice.

---

## 1. Etalonul manual

### De ce

Până acum validarea se autoevalua: parserul extrăgea, validatorul verifica ce
extrăsese parserul, iar amândouă foloseau aceleași ipoteze. Un etalon manual rupe
cercul — un om citește pagina și spune ce scrie acolo, independent de cod.

Etalonul măsoară **două lucruri distincte**, care nu trebuie confundate:

| | întrebarea | ce prinde |
|---|---|---|
| Precizie | valorile extrase sunt corecte? | valori și etichete greșite |
| Acoperire | ce nu am extras? | valori ratate |

### Cum

- Eșantion stratificat pe cele 10 tipuri de rată, maxim 3 pe bancă, seminificat
  (sămânța 1609) ca să poată fi reluat identic → **38 de valori, 26 de pagini,
  14 bănci**
- Cele 26 de pagini redescărcate live în 16.09.2026, cu robots.txt verificat per
  origine și pauzele respectate (26/26 reușite)
- Judecata s-a dat citind textul paginii de azi, nu fragmentul păstrat de parser
- Pentru acoperire: pe 3 pagini dense am enumerat *toate* procentele și le-am pus
  față în față cu ce extrăsesem

### Rezultatul

| criteriu | rezultat |
|---|---|
| **valoarea** corespunde paginii | **38 / 38** |
| **tipul** e corect | 33 / 38 (2 imprecise, 3 greșite) |
| **verdictul** validatorului | 37 / 38 |
| **acoperirea** pe pagini dense | **41 din 67 ≈ 61%** |

Acoperirea, detaliat:

| pagină | procente în pagină | extrase | ratări reale | corect ignorate |
|---|---|---|---|---|
| procredit — credit imobiliar | 14 | 9 | 1 | 4 |
| patria — credit ipotecar | 34 | 12 | 12 | 10 |
| revolut — pricing plans | 36 | 20 | 13 | 3 |
| **total** | **84** | **41** | **26** | **17** |

„Corect ignorate" = avans minim (15/25/35%), LTV maxim (65–85%), reduceri de
asigurare, „100% online". Utile ca date de produs, dar nu sunt rate.

**Concluzia de fond: cifrele sunt bune, acoperirea nu.** Precizia și acoperirea au
ieșit foarte diferit, iar până ieri raportam doar ceea ce semăna cu precizia.

### Cele 6 defecte găsite

| bancă | înregistrare | ce era greșit |
|---|---|---|
| brd | `ircc_valoare = 5.58` | valoare corectă, **verdict greșit** |
| ing | `nominala = 0.0` | promoție „3 rate cu 0% dobândă", nu rata cardului |
| tbi | `nominala = 0.0` | promoție „4 rate, 0% dobanda" |
| vista | `marja_fixa = 6.0` | 6% e rata fixă pe 3 ani, nu o marjă |
| patria | `marja_fixa = 2.2` | marjă peste EURIBOR; eticheta pierde indicele |
| patria | `marja_fixa = 10.0` | marjă peste IRCC; idem |

---

## 2. Reparațiile la extragere

### Cauza principală: rândurile de tabel

Tiparele se ancorează pe **eticheta** rândului, care apare o singură dată pe linie.
Căutarea găsea o potrivire, iar celulele următoare, care nu au etichetă, se pierdeau:

```
DAE 4    8,91%   8,04%   6,96%   5,49%        se lua doar 8,91%
Marja    2,90%   2,50%   4,05%   2,20%        se lua doar 2,90%
Rata     8,46%   5,99% fixă / 8,06% var. …    se lua doar 8,46%
```

Soluția propagă tipul etichetei pe coloanele următoare, **dar numai** când
potrivirea începe în celula de etichetă și se termină în prima celulă de valori.
Fără acest control ar fi stricat cazul Vista, unde celula 0 conține marja și
celula 1 o rată cu totul diferită.

### Ce s-a mai reparat

- **Tip nou `rate_fara_dobanda`** — 78 de promoții scoase din „dobândă nominală".
  Sunt facilități de plată în rate, nu rata produsului. Altfel datele spuneau
  „ING credit card: dobândă nominală 0%". Numărul de rate e păstrat la 77 din ele.
- **Marcajele de notă de subsol** — `2,20%* + IRCC` rupea tiparele de marjă.
  O singură corectură a rezolvat simultan o etichetă greșită (2,2 raportat ca
  nominală, deși e marjă) și o valoare ratată (2,6% peste EURIBOR).
- **Marjă contra rată fixă** — în `Marjă Fixă** 5,2 p.p. ▸ FIXĂ 3 ani 6% pe an`,
  tiparul sărea peste 5,2 și raporta 6% drept marjă.
- **Comision cu „p.a."** — `Comisionul anual de administrare: … 0.2% p.a.` ajungea
  dobândă nominală.
- **Pragul de semnalare** — era „≥ 2 procente pierdute", deci o linie care pierdea
  exact un procent trecea în silențiu. De aici discrepanța: 61 de linii pierdeau
  valori, doar 13 erau raportate.

### Cifrele

| | înainte | după |
|---|---|---|
| valori tipizate | 527 | **555** |
| dobânzi nominale | 347 *(82 false)* | **286** |
| promoții, separat | 0 | **78** |
| DAE | 29 | **36** |
| marjă peste EURIBOR | 3 | **4** |
| comisioane procentuale | 51 | **52** |
| linii de revizuit | 35 | **80** |
| linii care încă pierd valori | 61 | **55** |
| procente pierdute | 78 | **60** |
| recuperate din coloane de tabel | — | **19** |

Două cifre au mers **în jos, intenționat**:
- nominalele de la 347 la 286 — 347 includea 82 de zerouri, din care 77 erau promoții
- liniile de revizuit **au crescut** de la 35 la 80 — 35 era o cifră falsă, produsă
  de pragul care ascundea pierderile de un singur procent

### Corectură la un diagnostic al meu

Spusesem inițial că cele 78 de procente pierdute vin „toate din rânduri cu mai multe
coloane". **Greșit.** Rândurile cu tabulări sunt acum rezolvate (au rămas 4, și la
toate propagarea *ar fi* greșită), dar **51 de linii fără nicio tabulare** pierd în
continuare valori. Deci reparația a recuperat 19 valori, nu 78.

Restul sunt trei tipare diferite, pe care le confundasem cu coloane de tabel:

| tipar | exemplu | pierdut |
|---|---|---|
| capete de interval | „de la 5,79% până la 14,99%" | 14,99 |
| alternative pe monedă/tarif | „7% pentru RON sau 2,5% pentru EUR" | 2,5 |
| fix-apoi-variabil | „primele 36 luni 4,85% fixă, ulterior IRCC + 2,1%" | 4,85 |

---

## 3. Reparațiile la validare

Lecția centrală: **vechimea nu se detectează prin magnitudine.** Trimestrele IRCC
consecutive diferă uneori cu 0,02 puncte procentuale — mai puțin decât orice
toleranță rezonabilă. Criteriul corect e potrivirea exactă cu un trimestru încheiat
din seria BNR.

### Regula de calendar a IRCC

BNR etichetează valorile pe trimestrul de **calcul**, nu de aplicare. Indicele
calculat pentru un trimestru intră în vigoare din al doilea trimestru calendaristic
următor. Regula e confirmată independent de paginile a trei bănci:

| etichetă BNR | valoare | se aplică | cine o folosește |
|---|---|---|---|
| 2026T1 | **5,56%** | 01.07 – 30.09.2026 | Patria, Nexent, Libra (ipotecar) |
| 2025T4 | 5,58% | 01.04 – 30.06.2026 | BRD |
| 2025T3 | 5,68% | 01.01 – 31.03.2026 | Libra (overdraft) |

Referința nu mai e „cel mai recent rând publicat", ci rândul al cărui interval
acoperă ziua de azi. Iar dacă BNR n-a publicat încă trimestrul curent, verificările
devin **explicit neconcludente** — testat pe 15.10.2026. Fără asta, de la 1 octombrie
toate băncile ar fi părut brusc învechite.

### Perioada de valabilitate din text

Când pagina scrie perioada, o citim și verificăm dacă acoperă ziua de azi.

Două situații arată identic pe magnitudine și trebuie separate:

| | pagina declară | BNR pentru acea perioadă | verdict |
|---|---|---|---|
| **BRD** | 5,58% pentru 01.04–30.06.2026 | 5,58% — se potrivește | chiar e veche |
| **Nexent** | 5,56% pentru 01.07–30.09.**2025** | 5,55% — nu se potrivește | eroare de an |

Departajarea: valoarea se potrivește *mai bine* cu trimestrul declarat sau cu cel în
vigoare? La BRD cu cel declarat (0,00 vs 0,02), la Nexent cu cel curent (0,00 vs 0,01).

Verdictul BRD arată acum așa:

```
SURSA_VECHE
  - pagina declara valoarea pentru 01.04.2026-30.06.2026, perioada incheiata acum 78 zile
  - valoarea era corecta pentru acea perioada (BNR 2025T4 = 5.58%)
  - in vigoare azi: 5.56%
```

### Indicele implicit

Aici estimarea mea inițială era greșită și măsurarea pe date a salvat-o.

Crezusem că e destul ca marja și rata să apară pe aceeași linie. Am măsurat: din 8
astfel de linii, **doar una** e un caz real de „indice + marjă = total". Restul sunt
forma dominantă din piață — *„4,89% fixă în primii 3 ani, **apoi** variabilă
IRCC + 2,10%"* — unde scăderea nu înseamnă nimic. O verificare construită pe
co-apariție ar fi produs mai ales rezultate false.

Verificarea cere deci dovadă structurală, una din două forme explicite:

```
A:  "9.06% (IRCC + 3.5%)"     totalul, apoi indicele și marja în paranteză
B:  "3% + IRCC (8.68%)"       marja, apoi totalul în paranteză
```

Rezultatul pe tot setul — 5 linii, toate corecte:

| bancă | citit din pagină | indice implicit | verdict |
|---|---|---|---|
| eximbank | 9,06% − 3,5% | **5,56%** | coincide cu IRCC în vigoare |
| ing | 8,05% − 2,49% | **5,56%** | coincide cu IRCC în vigoare |
| patria | 5,818% − 3,25% | **2,568%** | coincide cu EURIBOR în vigoare |
| libra | 8,68% − 3,0% | **5,68%** | trimestrul 01.01–31.03.2026 |
| libra | 10,18% − 4,5% | **5,68%** | trimestrul 01.01–31.03.2026 |

**Libra e prinsă automat**, cu proveniență completă. Diferența e de doar 0,12 p.p.,
deci un prag de magnitudine ar fi ratat-o.

### Marja adunată cu indicele potrivit

`marja_fixa` nu spune peste ce indice stă. Acum nu se mai adună IRCC la o marjă care
stă peste EURIBOR. Prima versiune a gărzii era prea brutală — excludea liniile care
citează ambii indici și pierduse 3 confirmări reale, fiindcă Patria pune lei și euro
pe același rând. Relaxată: exclude doar când apare EURIBOR/ROBOR **și** nu apare IRCC.

### Cifrele

| | înainte | după |
|---|---|---|
| OK | 520 | **545** |
| SUSPECT | 0 | **0** |
| SURSA_VECHE | 7 *(doar Garanti)* | **10** *(Garanti 7, Libra 2, BRD 1)* |
| confirmate cu BNR | 15 | **14** |
| consistente aritmetic | 3 | **6** |
| cu indice implicit calculat | — | **5** |

Pe etalonul manual: **4 din 6 defecte rezolvate, 0 regresii.**
Teste automate: **35 / 35**, toate cazurile din pagini reale.

---

## 4. Sondajul PDF-urilor

Explicat separat mai jos, la secțiunea „PDF-urile, în detaliu".

---

## Constatările despre bănci

Toate verificabile din surse publice, toate confirmate manual.

### Garanti BBVA — pagina se contrazice singură

Tabelele de preț listează *marja fixă* și *rata dobânzii (IRCC + marjă)* pe același
rând, deci indicele folosit efectiv se obține prin scădere:

| tabel | marjă | rată | indice implicit |
|---|---|---|---|
| Nevoi pers. fără garanții (RON) | 5,55 / 4,95 | 11,53 / 10,93 | **5,98** |
| Nevoi pers. cu garanții (RON) | 3,45 / 3,15 | 9,43 / 9,13 | **5,98** |
| Imobiliar (RON) | 3,30 / 3,00 / 2,70 | 9,28 / 8,98 / 8,68 | **5,98** |
| Descoperit de cont (RON) | 7,98 | 13,92 | **5,94** |
| Nevoi pers. cu garanții (EUR) | 4,05 / 3,75 | 7,009 / 6,709 | **2,959** |
| Imobiliar (EUR) | 3,45 / 3,00 / 2,85 | 6,409 / 5,959 / 5,809 | **2,959** |

Tabelele implică IRCC ≈ **5,98%** și indice EUR ≈ **2,959%**. Notele de subsol ale
aceleiași pagini declară IRCC **4,06%** și EURIBOR 6M **0,66%**. ROBOR 6M publicat
**8,08%** față de **5,92%** la BNR în 16.09.2026.

Tabelele de preț sunt întreținute, notele cu indicii nu. Pagina nu are nicio dată de
actualizare.

> Corectură la o afirmație anterioară a mea: spusesem că singura dată de pe pagină e
> 08.07.2020, sugerând ultima actualizare. Fals — acea dată apare de 3 ori, toate ca
> prag contractual („refinanțarea creditelor contractate înainte de 08.07.2020").
> Dovada vechimii e contradicția internă, care e mai puternică oricum, fiindcă nu
> depinde de BNR.

### Libra — două valori IRCC pe același site

- `credit-nevoi-personale-fara-ipoteca`: „3% + IRCC (8,68%)" și
  „4,50% + IRCC (10,18%)" → indice implicit **5,68%** în ambele, adică trimestrul
  01.01–31.03.2026
- `dobanda-simulare-imprumut-credit-ipotecar`: „*IRCC valabil de la 01.07.2026:
  5.56%" → trimestrul în vigoare

Pagina de overdraft a rămas cu valoarea aplicabilă în urmă cu două trimestre.

### BRD — trimestru încheiat

„Dobânda anuală este compusă din marja băncii + IRCC. IRCC valabil în perioada
01.04.2026 – 30.06.2026 este 5,58%." Perioada s-a încheiat acum 78 de zile.

### Confirmate corecte

- **Patria**, credit ipotecar: marjă 6,67% → rată 12,23% și marjă 17,24% → rată
  22,80%, ambele cu indice implicit **5,56%**. Toate cele patru coloane ale tabelului
  de exemple se închid aritmetic.
- **Eximbank**: „9.06% (IRCC + 3.5%)" → 5,56 + 3,5 = 9,06
- **ING**: „8,05% (IRCC + 2,49%) p.a." → indice implicit 5,56%
- **Libra**, card de credit: 5,56 + 12,25 = 17,81%, rată afișată pe pagină
- **Nexent**: declară explicit IRCC 5,56% pentru 01.07–30.09.2026

---

## Ce nu merge încă

- **Acoperirea** — circa 61% din valorile în scop, pe paginile dense. Ratările nu
  sunt aleatorii: capete de interval, alternative pe monedă, forma fix-apoi-variabil.
- **Garanti nu e prins prin contradicția internă**, deși acolo e dovada cea mai
  clară. Cauza nu e validatorul, e extragerea: tabelele au coloanele separate prin
  spații, nu prin tabulări, așa că din pagina aceea avem doar notele de subsol.
  Rămâne semnalat, dar prin comparația directă cu BNR, care e mai slabă.
- **Trei bănci inaccesibile** — Banca Transilvania, UniCredit și Intesa blochează
  automatizarea prin firewall. Nu se poate ocoli legal.
- **Două defecte din etalon rămân** — eticheta de marjă nu poartă încă indicele peste
  care stă. Consecința e blocată, eticheta nu s-a schimbat.
- **PDF-urile sunt necitite** — 320 de documente, cea mai densă informație despre
  comisioane.

---

## Ce propunem

1. **Parsarea PDF-urilor**, începând cu cele 16 documente standardizate prin lege.
2. **Un etalon comun pentru comparația în trei.** Acum fiecare abordare —
   Playwright, BeautifulSoup, API Claude — își alege propriile pagini, deci „care
   merge mai bine" nu se poate răspunde: se compară selecția de adrese, nu
   extractoarele. Propunem o listă fixă de 15–20 de adrese, cu valorile verificate de
   mână, folosită de toți trei. Etalonul de azi e o bază bună, dar trebuie agreat
   împreună.
3. **Recuperarea intervalelor și a alternativelor pe monedă** — cele trei tipare
   rămase.

---

## PDF-urile, în detaliu

### Ce am făcut, exact

Nu am parsat niciun PDF. Am făcut o **sondare**, ca să pot răspunde la o singură
întrebare: cât costă parsarea lor. Nu voiam să propun un efort mare fără să știu
care e. Sondarea citește doar fișiere care erau deja pe disc — nu a descărcat nimic.

Am scris `scripts/sondaj_pdf.py`, care pentru fiecare document verifică patru lucruri:

1. are strat de text sau e imagine scanată?
2. conține titlul formularului standardizat prin lege?
3. câte procente conține (cât de dens e)?
4. tabelele au coloanele separate prin tabulări sau prin spații?

### Ce am găsit

**Inventarul:** 320 de documente, 217 MB, de la 20 de bănci. Cele mai multe la BCR
(42), Nexent (40), Libra (31), Raiffeisen (26), BRD (22).

**Strat de text — vestea bună.** 309 din 319 au text (97%). Doar 8 sunt scanuri, și
niciunul nu e relevant pentru comisioane (un ghid de plată a impozitelor, o hotărâre
AGA, câteva informări). **Deci nu e nevoie de OCR** — iar asta elimină riscul cel mai
serios: OCR-ul greșește exact pe cifre, și `5,58` în loc de `5,56` e o eroare pe care
nicio validare a noastră n-o poate prinde, fiindcă e perfect plauzibilă.

**Formularul standardizat — există.** Legea 258/2017 (directiva UE 2014/92, PAD)
impune un „Document de informare cu privire la comisioane" cu secțiuni și
terminologie identice la toate băncile. L-am găsit în **16 documente, la 5 bănci**:

| bancă | documente | dimensiune |
|---|---|---|
| BCR | 6 | 2–3 pagini |
| CreditCoop | 5 | 2–3 pagini |
| BRCI | 2 | 2 pagini |
| Libra | 2 | 7 și 10 pagini |
| ProCredit | 1 | 9 pagini |

> Corectură: acum o oră spusesem că niciun document nu conține formularul
> standardizat. Greșit — căutasem doar în fișierele numite „tarife" sau „comisioane",
> iar documentele standardizate se numesc altfel. Căutarea pe toate cele 319 le-a
> găsit.

**Problema reală — structura tabelelor.** Aproape niciun document nu are tabulări
(`tab = 0`). Coloanele sunt aliniate cu spații. Uite ce iese din „Tarife și
Comisioane PF" de la Libra:

```
intre 0 lei – 49.999,99 lei    18 lei   3 lei*
peste 50.000 lei               30 lei   20 lei
```

E un tabel cu trei coloane — descriere, comision standard, comision în aplicație —
ajuns o singură linie de text. Care sumă e din care coloană nu se poate spune.
Pentru asta ai nevoie de coordonatele x ale cuvintelor, iar biblioteca instalată
(`pypdf`) nu le dă. Cele care le dau — `pdfplumber`, `PyMuPDF` — nu sunt instalate.

E aceeași problemă ca la Garanti pe web: coloane aliniate cu spații în loc de
tabulări.

**Comisioanele sunt sume, nu procente.** Densitatea de procente e mică: „Tarife și
Comisioane PF" de la Libra are 12 procente pe 9 pagini. Comisioanele din PDF-uri sunt
mai ales sume absolute în lei și euro. Tot modelul nostru de date e construit pe
procente, deci ar trebui extins.

### Verdictul pe efort

**Nici o zi, nici o săptămână.** OCR nu e necesar, ceea ce elimină scenariul cel mai
rău. Dar sunt trei lucruri de făcut, niciunul banal:

1. o bibliotecă PDF care dă coordonatele cuvintelor
2. reconstrucția coloanelor din pozițiile x
3. extinderea modelului de date cu sume absolute, plus atribuirea pe coloană
   (standard vs. în aplicație, persoane fizice vs. juridice)

Începutul rezonabil sunt cele **16 documente standardizate**: sunt scurte (2–10
pagini), formatul e impus prin lege, și un singur parser acoperă cinci bănci. Dacă
merge acolo, extindem la cele 25 de documente „Tarife și comisioane", care au fiecare
formatul propriu.

---

## Fișiere

### Create azi

| fișier | ce face |
|---|---|
| `scripts/alege_esantion.py` | eșantionul stratificat, seminificat |
| `scripts/culege_etalon.py` | redescarcă paginile live |
| `scripts/context_etalon.py` | contextul din pagină, pentru citire manuală |
| `scripts/acoperire_etalon.py` | enumeră toate procentele unei pagini |
| `scripts/etalon_verdicte.py` | verdictele manuale + scorul |
| `scripts/etalon_recheck.py` | reevaluează etalonul după reparații |
| `scripts/test_validare.py` | 35 de teste, toate din pagini reale |
| `scripts/sondaj_pdf.py` | sondarea PDF-urilor |

### Modificate azi

| fișier | ce s-a schimbat |
|---|---|
| `crawler/parser_rate.py` | coloanele de tabel, promoțiile, marcajele de notă, pragul |
| `crawler/validator.py` | perioada de valabilitate, indicele implicit, referința pe calendar |
| `crawler/bnr_indici.py` | regula de aplicare a trimestrului IRCC |
| `scripts/ruleaza_validare.py` | raportarea indicelui implicit |
| `output/ETALON_MANUAL.md` | secțiunile 9 și 10 |

### Date

`output/etalon_esantion.json` · `output/etalon_manual.json` ·
`output/etalon_texte/` (26 de pagini) · `output/rate_tipizate.json` ·
`output/rate_validate.json` · `output/necesita_llm.json`

### Cum se reia totul

```bash
python scripts/test_validare.py      # 35 de teste
python scripts/parseaza_tot.py       # 721 linii -> 555 valori tipizate
python scripts/ruleaza_validare.py   # validarea + raportul
python scripts/etalon_recheck.py     # etalonul, după reparații
python scripts/sondaj_pdf.py         # sondarea PDF-urilor
```

---

## Notă de conformitate

Tot ce e aici provine din surse publice. Crawler-ul respectă `robots.txt` pentru
fiecare domeniu — inclusiv pauzele cerute (`Crawl-delay`) și căile interzise — și
verifică regulile separat pentru fiecare origine, fiindcă PDF-urile stau adesea pe
alt domeniu. Unde o bancă interzice descărcarea documentelor (ING: `Disallow: *.pdf`)
nu le-am descărcat, iar cele descărcate înainte de a putea citi regula au fost șterse.
Cele trei bănci care blochează automatizarea au fost lăsate în pace, nu ocolite.
