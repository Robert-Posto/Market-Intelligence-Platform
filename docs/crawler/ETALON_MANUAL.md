# Etalon manual — referință verificată de mână

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 16 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

**Data verificării:** 16.09.2026
**Verificat de:** eșantion stratificat, citit pe pagina live, nu pe ieșirea parserului

---

## 1. De ce a fost nevoie de el

Până acum validarea se autoevalua: parserul extrăgea, validatorul verifica ce
extrăsese parserul, iar amândouă foloseau aceleași ipoteze. Un etalon manual rupe
cercul — cineva citește pagina și spune ce scrie acolo, independent de cod.

Etalonul măsoară **două lucruri distincte**, care nu trebuie confundate:

| | întrebarea | ce prinde |
|---|---|---|
| **Precizie** | valorile extrase sunt corecte? | valori greșite, etichete greșite |
| **Acoperire** | ce nu am extras? | valori ratate |

O precizie bună nu spune nimic despre acoperire. Măsurate separat, au ieșit
foarte diferit.

## 2. Metoda

1. **Eșantion stratificat, seminificat** (`scripts/alege_esantion.py`, sămânța 1609)
   — 38 de valori, stratificate pe cele 10 tipuri de rată, maxim 3 pe bancă,
   plus toate cele 7 marcate `SURSA_VECHE`. Rezultat: 38 de valori, 26 de
   pagini, 14 bănci. Seminificat ca să poată fi reluat identic.
2. **Reculegere live** (`scripts/culege_etalon.py`) — cele 26 de pagini descărcate
   din nou în 16.09.2026, cu robots.txt verificat per origine și pauzele
   respectate. 26/26 reușite.
3. **Citire manuală** (`scripts/context_etalon.py`) — pentru fiecare valoare,
   o fereastră largă din textul paginii de azi, plus toate aparițiile numărului
   în pagină. Judecata s-a dat pe textul paginii.
4. **Acoperire** (`scripts/acoperire_etalon.py`) — pe trei pagini dense, am
   enumerat *toate* procentele și le-am pus față în față cu ce am extras.
5. **Verdicte** (`scripts/etalon_verdicte.py`) → `output/etalon_manual.json`.

## 3. Precizia

Pe eșantionul de 38:

| criteriu | rezultat |
|---|---|
| **valoarea** corespunde paginii | **38/38** |
| **tipul** (nominala, marja_ircc, …) e corect | **33/38** (87%) |
| verdictul validatorului (OK / SURSA_VECHE) e corect | **37/38** (97%) |

Cu un eșantion de 38, „38/38" nu înseamnă 100% pe tot setul — înseamnă că rata
reală de eroare la valori e, cu încredere rezonabilă, sub ~9%. Dar direcția e
clară: **numerele sunt bune; etichetele și verdictele sunt partea slabă.**

### Cele 6 abateri

| # | bancă | înregistrare | ce e greșit |
|---|---|---|---|
| 5 | brd | `ircc_valoare = 5.58` | valoare corectă, **verdict greșit** — vezi §5.2 |
| 18 | ing | `nominala = 0.0` | promoție „3 rate cu 0% dobândă", nu rata cardului |
| 28 | patria | `marja_fixa = 2.2` | e marjă peste EURIBOR; eticheta pierde indicele |
| 29 | patria | `marja_fixa = 10.0` | e marjă peste IRCC; idem |
| 37 | tbi | `nominala = 0.0` | promoție „4 rate, 0% dobanda" |
| 38 | vista | `marja_fixa = 6.0` | 6% e rata **fixă pe 3 ani**, nu o marjă |

## 4. Acoperirea — partea slabă

Pe trei pagini dense am enumerat fiecare procent:

| pagină | procente în pagină | extrase | ratări reale | corect ignorate |
|---|---|---|---|---|
| procredit — credit imobiliar | 14 | 9 | 1 | 4 |
| patria — credit ipotecar | 34 | 12 | 12 | 10 |
| revolut — pricing plans | 36 | 20 | 13 | 3 |
| **total** | **84** | **41** | **26** | **17** |

„Corect ignorate" = avans minim (15/25/35%), LTV maxim (65–85%), reduceri de
asigurare, „100% online". Utile ca date de produs, dar nu sunt rate.

**Acoperire pe pagini dense: 41 din 67 de valori în scop ≈ 61%.**

Precizia e mult mai bună decât acoperirea. Cine citește doar „527 de valori
tipizate" trage o concluzie prea optimistă.

### 4.1 Cauza principală: rândurile de tabel trunchiate

Ratările nu sunt aleatorii. Parserul lucrează pe linii și ia prima potrivire,
abandonând restul rândului:

```
Marja fixă a dobânzii      2,90%   2,50%   4,05%   2,20%        → luat: 2,90
Rata anuală a dobânzii3     8,46%   5,99% fixă / 8,06% var.
                            6,618%  4,99% fixă / 4,768% var.    → luat: 8,46
DAE 4                       8,91%   8,04%   6,96%   5,49%       → luat: 8,91
Dobândă fixă între 5,99% - 15,99%   5,29% - 15,29%              → luat: 5,99
```

Măsurat pe tot setul: **61 din 412 linii-sursă (15%) pierd valori, în total 78
de procente** — toate din rânduri cu mai multe coloane. Sunt recuperabile fără
niciun crawl nou, din liniile pe care le avem deja.

### 4.2 Un prag care ascunde exact aceste cazuri

[crawler/parser_rate.py:233](../crawler/parser_rate.py#L233):

```python
elif len(neatinse) >= 2:
    problema = f"{len(neatinse)} procente neinterpretate in aceeasi linie"
```

Pragul `>= 2` face ca o linie care pierde **exact un** procent să treacă în
silențiu. De aceea `necesita_llm.json` are 35 de intrări, deși 61 de linii
pierd valori: 48 dintre ele pierd câte una singură și nu sunt raportate.

Coborârea pragului la `>= 1` ar duce setul de revizuit de la 35 la ~83. E o
cifră mai puțin flatantă, dar corectă.

### 4.3 „Rate fără dobândă" umflă numărul de nominale

Din 347 de `nominala`, **82 sunt 0,0 — iar 77 provin din formulări de tipul
„N rate fără dobândă"**. Sunt facilități promoționale de plată în rate, nu rata
dobânzii produsului. TBI singur are 60.

| | |
|---|---|
| nominale declarate | 347 |
| nominale nenule, reale | 265 |
| zerouri promoționale (de reclasificat) | 77 |
| zerouri autentice | ~5 |

Cele ~5 autentice sunt reale — de pildă BRCI: „dobanda standard pentru
disponibilitatile la vedere din contul curent este 0% p.a.". Aceea e o rată.

Nu e o pierdere de date, e o problemă de etichetă: cele 77 au nevoie de un tip
propriu (`rate_fara_dobanda`), altfel un consumator al datelor citește
„ING credit card: dobândă nominală 0%".

## 5. Ce a descoperit verificarea manuală și validatorul nu putea

### 5.1 Garanti: pagina se contrazice singură

Reformulez o concluzie anterioară, care era greșită. Spusesem că singura dată de
pe pagina Garanti e 08.07.2020, sugerând ultima actualizare. Fals: acea dată
apare de 3 ori, toate ca prag contractual („refinanțarea creditelor contractate
înainte de 08.07.2020"). **Pagina nu are nicio dată de actualizare.**

Dovada vechimii e mai bună și nu are nevoie de BNR. Tabelele listează *marja
fixă* și *rata dobânzii (IRCC + marjă)* pe același rând, deci indicele implicit
se obține prin scădere:

| tabel | marjă | rată | indice implicit |
|---|---|---|---|
| Nevoi pers. fără garanții (RON) | 5,55 / 4,95 | 11,53 / 10,93 | **5,98** |
| Nevoi pers. cu garanții (RON) | 3,45 / 3,15 | 9,43 / 9,13 | **5,98** |
| Imobiliar (RON) | 3,30 / 3,00 / 2,70 | 9,28 / 8,98 / 8,68 | **5,98** |
| Descoperit de cont (RON) | 7,98 | 13,92 | **5,94** |
| Nevoi pers. cu garanții (EUR) | 4,05 / 3,75 | 7,009 / 6,709 | **2,959** |
| Imobiliar (EUR) | 3,45 / 3,00 / 2,85 | 6,409 / 5,959 / 5,809 | **2,959** |

Tabelele implică IRCC ≈ **5,98%** și indice EUR ≈ **2,959%**. Notele de subsol
ale aceleiași pagini declară IRCC **4,06%** și EURIBOR 6M **0,66%**.

Tabelele de preț sunt actualizate; notele cu indicii nu. Iar secțiunea ROBOR/
EURIBOR e intitulată „pentru creditele **în sold**" — portofoliu vechi, deci
publicarea lor e legitimă; valorile însă nu corespund niciunei resetări recente
(ROBOR 6M 8,08% față de 5,92% azi, 16.09.2026).

Observație colaterală: tabelele în EUR sunt etichetate „IRCC + Marja fixă",
deși indicele implicit e clar EURIBOR. E o greșeală a paginii, pe care un
extractor fidel o propagă.

### 5.2 BRD: o confirmare falsă

Extras corect: `IRCC = 5,58%`. Dar pagina scrie **„IRCC valabil în perioada
01.04.2026 – 30.06.2026 este 5,58%"** — perioadă expirată. Validatorul a
comparat doar magnitudinea: |5,58 − 5,56| = 0,02 ≤ toleranța 0,05 → **„confirmat
cu BNR"**.

Trimestrele IRCC consecutive diferă cu 0,02–0,4 p.p., deci comparația pe
magnitudine **nu poate distinge „curent" de „vechi de un trimestru"**. Toleranța
de 0,05 p.p. e mai mică decât diferența dintre trimestre, ceea ce garantează
confirmări false ocazionale.

### 5.3 Regula de decalaj a IRCC, confirmată din trei surse

BNR etichetează valorile pe trimestrul de **calcul**, nu de aplicare. Paginile
băncilor dau perioada de aplicare explicit, ceea ce permite reconstituirea:

| etichetă BNR | valoare | aplicabil | confirmat de |
|---|---|---|---|
| 2025T3 | 5,68% | 01.01 – 31.03.2026 | Libra (overdraft, implicit) |
| 2025T4 | 5,58% | 01.04 – 30.06.2026 | BRD (explicit) |
| 2026T1 | **5,56%** | **01.07 – 30.09.2026** | Patria, Nexent (explicit), Libra (ipotecar) |

Trimestrul calculat se aplică din al doilea trimestru calendaristic următor.
`in_vigoare = 5,56%` e corect **azi**, dar e ales ca „cel mai recent rând" — dacă
BNR publică 2026T2 înainte de 1 octombrie, am lua o valoare viitoare și toate
băncile ar părea învechite dintr-odată.

### 5.4 Libra folosește două valori IRCC diferite pe același site

Pe `credit-nevoi-personale-fara-ipoteca`, parantezele dau totalul:
„3% + IRCC (8,68%)" și „4,50% + IRCC (10,18%)" → indice implicit **5,68%** în
ambele. Pe `dobanda-simulare-imprumut-credit-ipotecar` nota spune
„*IRCC valabil de la 01.07.2026: 5.56%".

Deci pagina de overdraft a rămas cu valoarea aplicabilă în T1 2026 — două
trimestre în urmă — în timp ce paginile de ipotecar sunt la zi.

### 5.5 Confirmări solide

Contrapondere la cele de mai sus — pagini complet consistente:

- **Patria, credit ipotecar:** marjă 6,67% → rată 12,23% și marjă 17,24% →
  rată 22,80%, ambele cu indice implicit **5,56%**, exact IRCC-ul de la BNR.
  Toate cele patru coloane ale tabelului de exemple se închid aritmetic.
- **Eximbank:** „9.06% (IRCC + 3.5%)" → 5,56 + 3,5 = 9,06. Exact.
- **Libra, card de credit:** 5,56 + 12,25 = 17,81%, rată afișată pe pagină.

## 6. Ce trebuie schimbat, în ordinea raportului efort/câștig

> **Stadiu (16.09.2026):** punctele 1, 2 și 6 sunt făcute (§9); punctele 3, 4
> și 5 sunt făcute (§10). Punctul 1 s-a dovedit mai îngust decât estimasem aici.

1. **Extrage toate valorile dintr-un rând, nu doar prima.** Recuperează ~78 de
   valori (+15%) fără crawl nou. Ideal, păstrând indicele de coloană, ca să se
   poată lega de capul de tabel.
2. **Coboară pragul de semnalare la `>= 1`.** O linie de cod. Setul de revizuit
   crește la ~83, ceea ce reflectă realitatea.
3. **Verifică indicele implicit.** Unde avem marjă și rată pe același rând,
   `rată − marjă` dă indicele pe care îl folosește efectiv banca. Comparat cu
   indicele declarat de pagină *și* cu BNR, prinde Garanti și Libra automat.
   E mai puternic decât verificarea actuală, pentru că nu depinde de BNR.
4. **Citește perioada de aplicabilitate din text.** Când pagina scrie „valabil
   în perioada 01.04.2026 – 30.06.2026", verifică dacă acoperă ziua de azi.
   Elimină confirmarea falsă de la BRD. Toleranța pe magnitudine nu poate.
5. **Leagă `in_vigoare` de calendar, nu de „cel mai recent rând".** Selectează
   trimestrul după regula de decalaj din §5.3.
6. **Tip separat pentru promoțiile „N rate fără dobândă".** 77 de înregistrări.
7. **Păstrează indicele în marjă** (`marja_euribor` vs `marja_ircc` vs marjă
   fără indice). Altfel verificarea aritmetică adună IRCC la o marjă EURIBOR.
8. **Marchează capetele de interval** („de la", „până la", „între X și Y").
   Apare des și schimbă sensul valorii.
9. **Deduplică** pe (bancă, url, tip, valoare).

## 7. Riscuri identificate dar neconfirmate

- **Calculatoare interactive.** Pagina `eximbank.ro/calculator-dobanda-anuala-efectiva`
  afișa „DAE 30.51%" în starea implicită a widget-ului, cu o rată lunară de
  35.264 lei la un credit de 35.000 lei — un artefact, nu o ofertă. Nu a fost
  extras, dar din întâmplare: 30,51% trece intervalul de plauzibilitate pentru
  DAE (0–50%) și invariantul DAE ≥ nominală. Dacă ar fi fost extras, nicio
  verificare actuală nu l-ar fi prins.
- **Provenienţa în pagină.** Nu distingem o valoare din tabelul de produs de una
  din blocul „Noutăți" (Libra, #20) sau din scenariul median al unui exemplu
  reprezentativ (BCR, #3). Ambele au fost corecte, dar nu prin construcție.

## 8. Reproducere

```bash
python scripts/alege_esantion.py      # eșantionul (seminificat, identic la reluare)
python scripts/culege_etalon.py       # reculege paginile live
python scripts/context_etalon.py      # contextul pentru citire manuală
python scripts/acoperire_etalon.py <url>   # acoperirea pe o pagină
python scripts/etalon_verdicte.py     # verdictele + scorul
```

Ieșiri: `output/etalon_esantion.json`, `output/etalon_texte/`,
`output/etalon_manual.json`.

---

## Anexă — nota de metodă

Două observații care nu țin de bănci, dar au afectat lucrul:

- **BNR, din nou asimetric la unelte.** Playwright a primit `ERR_CONNECTION_CLOSED`
  pe pagina IRCC, în timp ce curl a răspuns 200 în aceeași secundă. Dar tabelul
  IRCC e încărcat prin JS, deci curl vede doar navigația. Cele două unelte sunt
  complementare, nu interschimbabile — și niciuna singură nu ajunge.
- **`inspect.py` rătăcit în `%TEMP%`** umbrește stdlib-ul Python pentru orice
  script rulat de acolo (`ModuleNotFoundError: No module named 'app'`, pornind
  din `asyncio`). Merită șters.


---

## 9. Reparațiile 1, 2 și 6 — făcute

### 9.1 Ce s-a schimbat în cod

| reparație | fișier | ce face |
|---|---|---|
| rânduri de tabel | `_coloane_suplimentare()` | propagă tipul etichetei pe coloanele următoare |
| prag de semnalare | `parseaza_linie()` | `>= 2` → orice procent neinterpretat |
| promoții | `RE_PROMO_RATE` | tip nou `rate_fara_dobanda` |
| marcaje de notă | `SUP` | `2,20%* + IRCC` se potrivește acum ca marjă |
| marjă vs rată fixă | tipar `marja_fixa` | `[^%]` → `[^%\d]`, nu mai traversează o altă cifră |
| comision cu „p.a." | tipar nou `comision_procent` | `Comisionul ...: 0.2% p.a.` nu mai e dobândă |

### 9.2 Rezultatul măsurat

| | înainte | după |
|---|---|---|
| valori tipizate | 527 | **555** |
| din care promoții reclasificate | 0 | **78** |
| dobânzi nominale | 347 (82 false) | **286** |
| DAE | 29 | **36** |
| linii semnalate pentru revizuire | 35 | **80** |
| linii care încă pierd valori | 61 | **55** |
| procente pierdute | 78 | **60** |
| SUSPECT / SURSA_VECHE | 0 / 7 | 0 / 7 |

Pe etalonul manual: **3 din 6 defecte rezolvate, 0 regresii**
(`scripts/etalon_recheck.py`).

| # | defect | stare |
|---|---|---|
| 18 | ing `nominala 0.0` | → `rate_fara_dobanda` |
| 37 | tbi `nominala 0.0` | → `rate_fara_dobanda` |
| 38 | vista `marja_fixa 6.0` | eliminat (era rată fixă pe 3 ani) |
| 5 | brd, confirmare falsă | rămâne — cere reparația 4 |
| 28, 29 | patria, marjă fără indice | rămâne — cere reparația 7 |

În plus, nesemnalate în eșantion: ProCredit `nominala 2,2` → `marja_ircc 2,2`,
marja de 2,6% peste EURIBOR recuperată, Vista `nominala 0,2` → `comision_procent`.

### 9.3 Corectură la diagnosticul din §4.1

Scrisesem că cele 78 de procente pierdute vin „toate din rânduri cu mai multe
coloane". **Greșit.** Măsurat după reparație:

- **rândurile cu tab sunt rezolvate** — au rămas 4, și la toate patru propagarea
  *ar fi* greșită (două sunt capete de interval, două sunt cazul Vista);
- dar **51 de linii fără nicio tabulare** pierd în continuare valori.

Deci reparația 1 a recuperat 19 valori, nu 78 (numărabile: înregistrările care au câmpul `coloana`). Restul sunt trei tipare diferite,
pe care le confundasem cu coloane de tabel:

| tipar | exemplu | pierdut |
|---|---|---|
| capete de interval | „de la 5,79% până la 14,99%" | 14,99 |
| alternative pe monedă/tarif | „7% pentru RON sau 2,5% pentru EUR" | 2,5 |
| fix-apoi-variabil | „Primele 36 luni: 4.85% fixă ulterior IRCC + 2.1%" | 4,85 |

Toate trei sunt „aceeași măsură, a doua valoare" — o reparație separată, nu o
continuare a celei de aici.

### 9.4 Limită cunoscută, rămasă

Deduplicarea se face pe valoare, deci o linie care conține de două ori aceeași
cifră cu sensuri diferite păstrează un singur rezultat. Caz real Eximbank:
„Rate Destepte – cu 0% dobanda si 0% comision de activare" → se reține doar
`comision_procent 0.0`, promoția se pierde.

### 9.5 Notă de metodă

Cele două „regresii" pe care le-am raportat inițial nu existau: verificarea mea
compara tipul unic pe (bancă, url, valoare), iar după reparație aceeași cifră
apare legitim sub două tipuri — Raiffeisen are deopotrivă „0% comision" și
„Rate fără dobândă". La fel, două așteptări din bateria de teste erau greșite,
nu codul. De fiecare dată verificarea a fost confruntată cu datele de dinainte
înainte de a trage concluzia.

---

## 10. Reparațiile 3, 4 și 5 — făcute

### 10.1 Regula de calendar a IRCC (reparația 5)

BNR etichetează valorile pe trimestrul de **calcul**, nu de aplicare. Indicele
calculat pentru un trimestru se aplică din al doilea trimestru calendaristic
următor. `perioada_aplicare()` din `crawler/bnr_indici.py` implementează regula:

| etichetă BNR | valoare | se aplică |
|---|---|---|
| 2026T1 | 5,56% | 01.07.2026 – 30.09.2026 |
| 2025T4 | 5,58% | 01.04.2026 – 30.06.2026 |
| 2025T3 | 5,68% | 01.01.2026 – 31.03.2026 |

`in_vigoare` nu mai e „cel mai recent rând", ci rândul al cărui interval acoperă
ziua de azi. Dacă BNR n-a publicat încă trimestrul aplicabil, se folosește
ultimul aplicabil **și se marchează referința ca expirată** — verificările IRCC
devin explicit neconcludente, în loc să acuze în tăcere toate băncile.

### 10.2 Perioada de valabilitate din text (reparația 4)

Când pagina scrie perioada, o citim și verificăm dacă acoperă ziua de azi.
Comparația pe magnitudine nu putea: trimestrele IRCC consecutive diferă uneori
cu 0,02 p.p., mai puțin decât toleranța de 0,05.

Două situații arată identic pe magnitudine și trebuie separate:

| | pagina declară | BNR pentru acea perioadă | verdict |
|---|---|---|---|
| **BRD** | 5,58% pentru 01.04–30.06.2026 | 5,58% ✓ se potrivește | chiar e veche |
| **Nexent** | 5,56% pentru 01.07–30.09.**2025** | 5,55% ✗ nu se potrivește | eroare de an |

Departajarea: valoarea se potrivește *mai bine* cu trimestrul declarat decât cu
cel în vigoare? La BRD da (0,00 vs 0,02), la Nexent nu (0,01 vs 0,00).

Verdictul BRD arată acum așa:

```
stare: SURSA_VECHE
  - pagina declara valoarea pentru 01.04.2026-30.06.2026,
    perioada incheiata acum 78 zile
  - valoarea era corecta pentru acea perioada (BNR 2025T4 = 5.58%)
  - in vigoare azi: 5.56%
```

### 10.3 Indicele implicit (reparația 3)

Aici estimarea mea iniţială era greșită și verificarea pe date a salvat-o.

Crezusem că e de ajuns ca marja și rata să apară pe aceeași linie. Am măsurat:
din 8 astfel de linii, **doar una** e un caz real de „indice + marjă = total".
Restul sunt forma dominantă din piață — *„4,89% fixă în primii 3 ani, **apoi**
variabilă IRCC + 2,10%"* — unde scăderea nu înseamnă nimic. O verificare
construită pe co-apariție ar fi produs mai ales rezultate false.

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

**Libra e prinsă automat**, cu proveniență completă — exact constatarea pe care
o făcusem de mână la §5.4.

Criteriul de vechime nu e magnitudinea, ci potrivirea exactă cu un trimestru
încheiat din seria BNR. Libra e la doar 0,12 p.p. de valoarea curentă, deci sub
`PRAG_VECHI`; un prag de magnitudine ar fi ratat-o. Aceeași lecție ca la BRD.

### 10.4 Marja adunată cu indicele potrivit

`marja_fixa` nu spune peste ce indice stă. `_marja_peste_ircc()` nu adună IRCC la
o marjă care stă peste EURIBOR (Patria, defectele #28–29 din etalon).

Prima versiune a gărzii era prea brutală — excludea liniile care citează ambii
indici și a pierdut 3 confirmări reale, fiindcă Patria pune lei și euro pe același
rând. Relaxată: exclude doar când apare EURIBOR/ROBOR **și** nu apare IRCC.
Cele 6 confirmări aritmetice sunt intacte.

### 10.5 Rezultatul

| | înainte de §9 | acum |
|---|---|---|
| valori tipizate | 527 | **555** |
| OK | 520 | **545** |
| SUSPECT | 0 | **0** |
| SURSA_VECHE | 7 (doar Garanti) | **10** (Garanti 7, Libra 2, BRD 1) |
| confirmate cu BNR | 15 | **14** |
| consistente aritmetic | 3 | **6** |
| cu indice implicit calculat | — | **5** |

Pe etalonul manual: **4 din 6 defecte rezolvate, 0 regresii.** Rămân #28 și #29
— eticheta `marja_fixa` nu poartă încă indicele; consecința e blocată (§10.4),
dar eticheta în sine nu s-a schimbat.

Teste: `python scripts/test_validare.py` — 35 de cazuri, toate din pagini reale.

### 10.6 O limită de recunoscut

Verificarea indicelui implicit **nu prinde Garanti**, deși acolo am găsit cea mai
clară contradicție (§5.1). Motivul nu e validatorul, e extragerea: tabelele
Garanti au coloanele separate prin spații, nu prin tabulări, așa că din pagina
aceea am extras doar notele de subsol, nu rândurile cu marjă și rată. Dovada pe
care am citit-o de mână nu ajunge până la verificare.

Garanti rămâne semnalat — dar prin comparația directă cu BNR, care e mai slabă
(depinde de BNR și de un prag), nu prin contradicția internă, care e mai tare.
Ca să ajungem la ea, extractorul ar trebui să recunoască și tabelele cu coloane
separate prin spații.
