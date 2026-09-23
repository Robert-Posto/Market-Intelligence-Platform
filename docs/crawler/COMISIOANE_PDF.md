# Comisioanele din PDF-uri — 17 septembrie 2026

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 18 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

Prima sursă de comisioane pe care o acoperim. Până acum era zero.

**Cod:** [crawler/parser_pdf.py](../crawler/parser_pdf.py) ·
**Rulare:** `python scripts/parseaza_pdf.py` ·
**Ieșire:** `output/comisioane_pdf.json`

---

## 1. De ce doar cele 16 documente standardizate

Din cele 320 de PDF-uri descărcate, 16 sunt „Document de informare cu privire la
comisioane" — formularul impus de **Legea 258/2017** (directiva UE 2014/92, PAD),
cu secțiuni și terminologie identice la toate băncile.

Asta e diferența care contează: **un singur parser le acoperă pe toate**, iar
terminologia standard face posibilă comparația între bănci. Paginile web nu permit
asta, fiindcă fiecare bancă își numește serviciile altfel.

| bancă | documente | pagini |
|---|---|---|
| BCR | 6 | 2–3 |
| CreditCoop | 5 | 2–3 |
| BRCI | 2 | 2 |
| Libra | 2 | 7 și 10 |
| ProCredit | 1 | 9 |

## 2. Rezultatul

**427 de comisioane din 16 documente, 5 bănci.** Comparabil în volum cu tot ce am
extras din web (555 de valori), dintr-o sursă neatinsă până acum.

| | |
|---|---|
| sume absolute | 330 |
| procente | 54 |
| „gratuit" declarat în cuvinte | 46 |
| în lei | 272 |
| în euro | 58 |
| cu frecvență (lunar/anual) | 106 |
| cu plafon `min`/`max` | 34 |
| cu condiție de bandă | 7 |
| servicii distincte | 163 |

Structura păstrată pentru fiecare comision: serviciul, subserviciul, tipul, valoarea,
moneda, frecvența, rolul (plafon minim/maxim al unui comision procentual), condiția
de bandă, documentul-sursă și pagina.

Exemple de structură recuperată corect:

```
0,1% min. 15 EUR, max. 500 EUR   ->  procent 0,1        (fără rol)
                                     sumă 15 EUR        rol=min
                                     sumă 500 EUR       rol=max

Transfer credit                  ->  3 lei   condiție: 0 – 49.999 lei
                                     20 lei  condiție: peste 50.000 lei
```

## 3. Ce a trebuit învățat din date

Trei lucruri pe care nu le-am putut presupune și le-am aflat măsurând.

### Bordurile nu se detectează după grosime

Băncile desenează o bordură ca **multe segmente scurte, câte unul pe celulă**.
Filtrul pe grosimea unui segment rata majoritatea; folosirea tuturor muchiilor
producea coloane false care tăiau cuvintele.

Criteriul corect e **lungimea acumulată pe aceeași poziție**. Măsurat pe BCR,
pagina 1:

```
x=90  -> 823      x=307 -> 650      x=523 -> 823      borduri reale
x=96  ->  80      x=165 ->  96      x=446 ->  96      decorații
```

### Nici rândurile de grilă singure nu ajung

Cele două layout-uri sunt opuse:

- **BCR** pune mai multe servicii într-un rând de grilă, ca rânduri de text fără
  bordură între ele
- **Libra** pune numele o singură dată, urmat de multe comisioane

Soluția folosește ambele: rândul de grilă mărginește zona de tabel (altfel numele
înghite antetul documentului și subsolul paginii, iar preambulul produce valori),
iar în interiorul lui se lucrează pe rânduri de text — atribuite prin poziție
verticală, nu în ordinea de citire (§5).

### Pragurile de tranzacție nu sunt comisioane

`0 – 49.999 Lei` e banda de sumă, nu prețul. Fără separare, 49.999 ajungea raportat
drept comision de transfer — aceeași capcană ca `avans 15%` pe web: o cifră cu
monedă lângă ea, care nu e un preț. Banda e însă utilă, deci se păstrează drept
*condiția* comisionului, nu se aruncă.

## 4. Verificare

Zece comisioane alese la întâmplare (sămânța 1709), textul-sursă căutat în pagina
originală: **10 din 10 confirmate.**

## 5. Calitatea etichetei de serviciu — rezolvată prin poziții verticale

**Actualizat 17 septembrie.** Limita marcată aici inițial a fost ridicată.

### Cum arăta problema

La BCR, etichetele și sumele se împletesc fără bordură între ele:

```
 576,7–588,7  nume:  "Retrageri de numerar în lei de la ghişeul"
 583,7–595,7  preț:  "2,5% min. 25 Lei"
 590,5–602,5  nume:  "băncii"
 611,3–623,3  preț:  "0 Lei"
 618,1–630,1  nume:  "Depuneri de numerar în contul clientului"
```

Trei etichete, trei valori, ordine împletită. Parserul lucra în **ordinea de
citire**, deci `0 Lei` pleca la serviciul precedent, iar numele se lipeau între ele.

### Ce spun pozițiile

Numele „Retrageri … de la ghişeul băncii" ocupă **576,7–602,5** (două rânduri, cu
un gol de 1,8 puncte între ele). Prețul `2,5% min. 25 Lei` stă la 583,7–595,7 —
vertical *înăuntru*. Centrul lui cade la 589,7, centrul blocului de nume la 589,6:
potrivire exactă, fiindcă coloana de preț e centrată vertical iar coloana de nume
aliniată sus.

Iar `0 Lei` (centru 617,3) e la **6,8 puncte** de următoarea etichetă și la **27,7**
de cea precedentă. Marginea e confortabilă, nu la limită.

Deci regula, în locul ordinii de citire:

1. Rândurile de nume se grupează în blocuri; ce le ține laolaltă e golul vertical
   mic (1,8 puncte în interiorul unui nume, 15,6 între două servicii — pragul de 6
   stă comod între ele). **Rândurile de preț nu închid blocul**, fiindcă numele se
   rupe în jurul lor.
2. Fiecare valoare merge la blocul cu care se suprapune vertical; dacă nu se
   suprapune cu niciunul, la cel mai apropiat centru.

Pagina studiată e acum **9 valori din 9 corecte**, inclusiv `0 Lei`.

### Rezultatul măsurat

| bancă | comisioane | curate înainte | curate acum |
|---|---|---|---|
| CreditCoop | 114 | 59% | **100%** |
| Libra | 65 | 80% | **93%** |
| ProCredit | 92 | 77% | 80% |
| BRCI | 47 | 78% | 78% |
| **BCR** | 112 | **37%** | **64%** |
| total | 427 | 62% | **83%** |

Coloana „înainte" e măsurată cu același instrument, ca să fie comparabilă. Toate
cele 427 de valori s-au păstrat, aceleași 7 condiții de bandă, iar cele 35 de teste
de pe web trec.

Din cele 83%, două treimi din câștig vin din pozițiile verticale (62 → 70%) și o
treime din două reparații mai mici: notele de valabilitate scrise în coloana de
nume (§6.5) și corectarea instrumentului de măsură (§6.6).

### Ce a rămas

72 de etichete din 427 mai sunt semnalate, dar majoritatea sunt **nume autentic
lungi**, nu defecte: „Transfer credit interbancar in orice altă valută decât euro,
către alte bănci din România sau din străinătate…" e chiar numele serviciului, iar
pachetul George are un nume de 992 de caractere, fiindcă formularul îi enumeră tot
conținutul. Defectele adevărate rămase, numărate de mână, sunt vreo 15 — mai ales
liste de conținut tăiate de granița rândului de grilă.

## 6. Erorile mele, pe parcurs

Merită notate, fiindcă trei din patru au fost **tăcute**.

1. **„comisioane" nu conține „comision".** Pluralul românesc nu e un sufix
   (`comisio-n` vs `comisio-ane`). Tiparul de căutare pe numele fișierelor nu
   potrivea nimic, iar un `except Exception: continue` ascundea și cauzele reale.
   Descoperirea raporta liniștit „zero documente".
2. **Regula de reunire a numelor o lua la goană** pe o paranteză nedeschisă și
   lipea serviciile între ele. După ce am pus limita, numele se trunchiau.
3. **Rolul `min`/`max` nu se atribuia niciodată** — tiparul cerea formele întregi,
   documentele scriu abrevieri. Pierdere silențioasă.
4. **Un `NameError` dintr-o refactorizare** a fost prins de `except Exception`,
   raportat ca „document problematic", iar un `grep` al meu a ascuns și acea linie.
   Rezultat: 177 de comisioane dispărute fără nicio alarmă (430 → 253). Scriptul
   afișează acum mesajul complet al erorii și avertizează explicit că totalul e
   incomplet.

Lecția comună: fiecare eroare a fost mascată de un mecanism care înghite eșecuri.

**Adăugate la 17 septembrie, din lucrul pe poziții verticale:**

5. **Am încercat testul invers și nu l-am verificat înainte de a-l crede.**
   Ipoteza era „o bordură pe care o traversează multe cuvinte nu e reală".
   Măsurată, nu discriminează: în documentul de control, unde parserul merge
   corect, 9 cuvinte traversează o bordură adevărată față de 18 la una falsă. Prea
   aproape ca să separe. Ipoteza corectă e alta — o bordură nu taie niciodată un
   cuvânt, deci se rupe doar acolo unde cade *între* două cuvinte.
6. **Am crezut că granița rândului de grilă e de prisos.** Odată ce atribuirea se
   face pe poziții, părea că golul vertical poate înlocui grila. Am încercat: 61%
   etichete curate față de 70%. Grila face **două** lucruri — filtrează textul din
   afara tabelului (fără ea ies 58 de valori din preambul) *și* separă servicii
   vecine pe care golul vertical nu le separă. Am renunțat la idee și am scris în
   cod de ce.
7. **Instrumentul de măsură greșea, nu parserul.** Regula „eticheta nu trebuie să
   conțină un preț" respingea toate cele 46 de etichete CreditCoop — dar
   `• Pentru sume ≤ 100 lei` **este** numele subserviciului acolo. CreditCoop era
   la 100%, nu la 59%. Am corectat măsurătoarea, nu datele: o bandă de sumă în
   etichetă e legitimă.

Lecția din 5, 6 și 7: de fiecare dată când am măsurat o ipoteză înainte să o
implementez, am economisit timp. De fiecare dată când n-am făcut-o, am scris cod
care trebuia scos.

## 6b. Dispersia s-a dovedit un detector de erori

**Adăugat 17 septembrie.** Coloana de dispersie din tabelul de comparație a fost
construită ca filtru de încredere: peste 5×, mediana nu mai reprezintă nimic, deci
linia se mută în tabelul al doilea. S-a dovedit că face altceva, mai util — **linia
cu cea mai mare dispersie e mereu linia care conține o cifră ce n-are ce căuta
acolo**, iar mărimea dispersiei e ordinea de prioritate a reparațiilor.

Am intrat în linia de vârf (111.111×) și am găsit:

```
transfer_credit / pf / LEI
      0,45  libra    "Comisioanele de plati percepute de banca includ:"
    50.000  garanti  "Transfer credit de mică valoare (sub"  ->  "50.000 LEI)"
```

Cifra de 50.000 făcea nefolositoare o linie cu 6 bănci. E o a doua rundă a aceleiași
capcane din §3: o cifră cu monedă lângă ea, care nu e un preț.

### Cinci familii, cinci discriminanți diferiți

Prima ipoteză a fost greșită și ar fi șters prețuri reale. Filtrasem pe **etichetă**
— orice etichetă care conține „limită", „de minim", „criteriilor". Verificat pe cele
130 de potriviri:

```
  15 LEI   etichetă "Plăți naționale de minimum 50.000 LEI"  ->  PREȚ REAL
1.000 LEI  sursă    "(i) există o încasare de minimum 1.000 LEI"  ->  cerință
```

Aceeași etichetă, verdict opus. Nici numărul de litere rămase în text nu separă:
„Comision anual total: 240 Lei" e preț, „Rulaj al încasărilor de minim 10.000 LEI"
nu. **Discriminantul e substantivul care guvernează cifra**, și e diferit pe fiecare
familie:

| familie | discriminant | exemplu |
|---|---|---|
| cerință de client | substantiv de bani deținuți/primiți + `minim` | „sunt deținute minimum 2.000 EUR" |
| definiție de client | `venit` + `depășește` | BRD: „venit care nu depășește 60%" |
| reducere | procent lipit de `reducere` | „100% reducere față de plățile standard" |
| tabel de limite | eticheta **începe** cu `limită`/`plafon` | Garanti: „limită zilnică" → „500.000 LEI" |
| prag rupt de coloană | eticheta deschide o paranteză pe care valoarea o închide | „(sub" → „50.000 LEI)" |

Cuvântul „minim" **nu** poate fi criteriu: măsurat, 56 din cele 66 de apariții sunt
plafoane reale, unde 15 din `0,1% min. 15 EUR` chiar e prețul.

### Trei falși pozitivi prinși la verificare

Am verificat **fiecare** valoare marcată, nu un eșantion — și a meritat de trei ori:

1. **Zeroul nu e niciodată o cerință.** Regula avea 12 falși pozitivi din 23, toți cu
   valoarea 0: „0 Lei în limita primelor 5 retrageri" — acolo zeroul *este* prețul,
   iar limita e condiția lui. Nicio bancă nu cere un sold minim de 0 lei.
2. **Eticheta ancorată nu ajunge singură.** La Raiffeisen, eticheta „Limita zilnică de
   retragere numerar" prinsese prin atribuire un comision real, `5% (minim 10 lei) din
   suma utilizată`. Regula se aplică acum doar când celula e practic numai cifra, sau
   când textul vorbește el însuși despre o limită.
3. **Cuvântul de prag la capătul etichetei nu e semn.** BCR are „…administrare Pachet
   tuturor criteriilor **de la**" urmat de „39 LEI", unde „de la" e o referință la o
   secțiune și 39 e un preț adevărat. Semnul corect e structural: paranteza neînchisă.

**Rezultat: 37 de valori marcate, toate 37 verificate corecte.** 20 dintre ele erau
peste 5.000 — un „comision" de 5.000.000 EUR era condiția BRD de eligibilitate pentru
un pachet, iar 1.000.000 lei limita zilnică a Garanti.

Valorile **nu se aruncă**: limita zilnică a Garanti e informație reală despre bancă.
Primesc `rol="conditie"` și ies din comparația de prețuri, exact ca plafoanele
`min`/`max`. Aceeași decizie ca la benzile de sumă din §3.

### Frecvența trebuia să fie în cheia de grupare de la început

A doua reparație, independentă și mai simplă: `administrare_cont / pf / LEI` adunase
21 de valori lunare cu 8 anuale și 13 fără frecvență, la 9 bănci — iar mediana nu
descria niciuna. Frecvența e citită **determinist** din text, ca segmentul, deci nu e
o judecată și putea sta în cheie de la început. La fel rolul: un plafon `min. 15 EUR`
al unui comision procentual nu e același lucru cu un comision fix de 15 EUR.

| | înainte | acum |
|---|---|---|
| linii comparabile (≥3 bănci) | 72 | **73** |
| linii de încredere | 35 | **46** |
| linii prea eterogene | 37 | **27** |

Din cele 11 linii câștigate, trei vin dintr-o reparație descoperită abia la punerea
rolului în cheie: documentele scriu și `min` și `minim`, iar rolul nenormalizat
rupea același plafon pe două rânduri (287 de `min` față de 32 de `minim` în listele
de tarife). Se normalizează acum la sursă.

Linia care s-a deblocat e chiar cea mai citată din bancă — **comisionul lunar de
administrare de cont, la 8 bănci**: BCR 0–20, BRCI 5, CreditCoop 5–8, Garanti 7,5,
Libra 0, ProCredit 0–50, Salt 0, TBI 3.

## 6c. Două măsuri de eterogenitate, nu una

**Adăugat 18 septembrie.** Linia lunară de administrare de mai sus rămăsese în
tabelul „eterogene" din cauza unei singure valori — ProCredit are 50 lei la
„Administrarea contului **/ pachetului**". Cauza formală: dispersia se calcula
`max/min` pe toate valorile la comun, deci **un singur outlier condamna un rând
întreg**.

Dar `max/min` nu greșea doar în direcția aceea. O linie pune **două întrebări
diferite**, iar o singură cifră nu răspunde la niciuna:

- **între** — de câte ori diferă cifrele *afișate* (medianele) între bănci. Peste
  limită, băncile nu vând același lucru la prețuri comparabile.
- **intern** — cea mai mare împrăștiere din interiorul unei singure bănci. Asta era
  motivul original al măsurii: `transfer_credit LEI` la Libra avea interval
  0,45–50.000, adică transferuri domestice mici adunate cu RTGS urgent.

Măsurat pe toate cele 73 de linii, cele două măsuri separate dau **același număr**
de linii de încredere (46 față de 45) — deci măsura nu era problema principală, cum
crezusem. Sunt însă corecte pe toate cele trei linii unde diferă de cea veche, și
una dintre ele greșea **în celălalt sens**:

```
administrare_cont/pf/lunar   8 bănci   max/min=17×  între=4×    intern=5×
    -> comparabilă; cei 17 veneau din intervalul 0–50 al unui singur ProCredit
livrare_card/pf/LEI          3 bănci   max/min=3×   între=5,3×  intern=2×
    -> NU e comparabilă: Salt cere 30–50 lei, ceilalți 0–15. max/min ascundea
       asta punând toate valorile la comun.
```

Câștigul adevărat nu e numărul, e **diagnosticul**: tabelul arată acum ambele
coloane, deci spune *ce* e de reparat. `între` mare cere o cheie mai fină; `intern`
mare cere etichete mai bune.

### Ce a scos la iveală imediat

8 din cele 27 de linii nesigure aveau `intern` curat — fiecare bancă consecventă cu
ea însăși, dezacordul doar între ele. Părea o serie de constatări reale despre
prețuri. **Verificarea de mână a infirmat-o**, și a arătat cauza adevărată:

```
extras_de_cont:  Garanti   8 lei  "extras de cont pentru luna anterioară"
                 BRCI      5 lei  "eliberare duplicat extras de cont"
                 Libra    25 lei  "taxa extras de cont pe suport de hârtie"
                 BCR     100 lei  "transmitere extrase cont prin mesaje SWIFT"
```

Patru lucruri, nu unul. Axa `canal` din vocabular avea ATM, POS, internet/mobile
banking și ghișeu — dar **niciun canal de livrare a unui document**. Adăugate
`swift`, `curier_posta`, `hartie`, `email` (103 valori, 7 bănci), rândul s-a despicat
corect:

| | înainte | după |
|---|---|---|
| `extras_de_cont / pf / LEI` | între 12× | **între 4×, de încredere** |
| `extras_de_cont / pj / swift` | — | **3 bănci, între 1×, intern 1×** |

Linia de SWIFT nu exista: BCR 100, BRCI 125, **Libra 100** — o comparație curată,
în care Libra e la capătul de jos. La fel `speze_swift / pf / EUR`: Garanti 10,
Libra 10, TBI 15.

Numărul total de linii a scăzut de la 73 la 70, fiindcă unele rânduri s-au despicat
sub trei bănci. Asta e corect: o comparație între două bănci nu e o comparație.

## 6d. Destinația banilor — și a treia oară aceeași lecție

**Adăugat 18 septembrie.** Destinația (`intrabancar` / `interbancar` / `sepa` /
`extern`) era completată la 426 din 1.437 de valori unde contează — 29%.

### Ce lipsea din vocabular

Două valori întregi, pe care nu le avea deloc:

- **`ue`** — „în Uniunea Europeană", „UE/SEE". Vocabularul avea doar *negația*
  („în afara UE", „non-UE"), deci o plată *în* UE nu se potrivea nicăieri. 74 de
  valori, 5 bănci.
- **`national`** — „naţional", „domestic", „în România", „local". 46 de valori.

Plus semnalele de rețea proprie („ATM-uri BCR", „POS-uri Libra", „ghișeul băncii"),
care duc la `intrabancar`.

### Ordinea din listă e măsurată, nu aleasă

Trei capcane, fiecare verificată pe date înainte de a fi scrisă în cod:

1. **`extern` trebuie să stea înaintea lui `ue`.** „Plăți în afara UE/SEE sau în
   UE/SEE" conține ambele forme, iar „în afara UE" e sensul care determină prețul.
2. **Semnalele de rețea proprie stau la urmă**, cu același nume ca `intrabancar`.
   Puse la început, strică 4 atribuiri corecte: „Transfer credit **interbancar** EURO
   către alte bănci" devenea intrabancar, fiindcă undeva în context apare „ghișeul
   băncii". Cuvântul explicit bate semnalul indirect.
3. **Granița de cuvânt, a patra oară în proiect.** `\bnațional` **nu** potrivește în
   „internațional" (înaintea lui e „r", deci nu există graniță), și nici `\bintern\b`
   (urmează „a", caracter de cuvânt). Verificat, nu presupus.

### Verificarea de mână a găsit o eroare sistematică

Primul eșantion de 18: **15 corecte**. Dar două din cele trei greșeli aveau aceeași
cauză:

```
ue  salt  "Retragere de numerar ATM local"
          ctx: "In Romania ... ÎNCASĂRI ȘI PLĂȚI CĂTRE STATE MEMBRE ALE UE"
```

Eticheta spune „ATM **local**", secțiunea paginii spune UE — și secțiunea a câștigat,
fiindcă destinația se căuta în tot contextul deodată. **A treia oară în proiect când
e nevoie de aceeași regulă: dovada locală bate contextul** (prima dată la ratele de
pe web, apoi la moneda din antetul de matrice). Destinația se caută acum în numele
serviciului, și abia dacă acesta nu spune nimic se coboară la context — exact cum
făcea deja maparea conceptului.

### Și o regulă nouă: când scrie amândouă, nu alegem niciuna

```
"Eliberare de numerar în/afara României (de la ghișee/ATM-uri BCR sau ale altor bănci)"
"Cumpărare bunuri/servicii"  cu antetul  "Națională și internațională"
```

Comisionul se aplică la ambele destinații, deci nu e nici una, nici alta. Amândouă
primesc acum `None` — refuzul de a ghici e răspunsul corect, nu o lacună.

Cazul al doilea a scos la iveală un **cost al reparației de antet de la §7b din
[COMISIOANE_TARIFE.md](COMISIOANE_TARIFE.md)**: „internațională" e pe rândul următor
și începe cu literă mică, deci filtrul meu de continuare o respingea, iar antetul
rămânea „Națională și". Reparat cu poziția: un antet se continuă *înaintea* primului
rând cu valori al tabelului, o celulă de valoare *după*. Patru din cele șase antete
BCR s-au completat; ultimele două lovesc limita de 48 de caractere, dar sunt acoperite
oricum de regula „amândouă", care tratează și forma trunchiată „Națională și".

### Rezultatul

| | înainte | acum |
|---|---|---|
| destinație completată | 426 (29%) | **487 (34%)** |
| valori corecte pe eșantion de 18 | 15 | **16** |
| linii comparabile | 70 | 71 |
| linii de încredere | 45 | 45 |

Acoperirea a crescut mai puțin decât aș fi putut raporta: fără regula „eticheta
întâi" ieșeau 599 de valori (41%), dar cu greșeala sistematică înăuntru. **41% greșit
e mai puțin util decât 34% verificat.**

## 6e. Destinațiile se cuprind una pe alta — și moneda nu lipsea niciodată

**Adăugat 18 septembrie.** Continuarea §6d, plus două lucruri din lista mea de
probleme care s-au dovedit greșit puse.

### SEPA nu se scrie mereu „SEPA"

BRD numește o plată SEPA „Plăți **externe** către beneficiari din țările care aparțin
**zonei unice de plăți în EUR**", BCR „țări din **Comunitatea Europeană**". Adăugate
formele scrise pe litere, dar reparația a mutat doar 2 valori din 16 — fiindcă garda
de ambiguitate din §6d le anula: eticheta potrivea și `extern` și `sepa`, deci
„două destinații, nu alegem".

Garda era prea brutală. **Geografic, destinațiile se cuprind una pe alta:**

```
SEPA  ⊂  UE/SEE  ⊂  extern            se rezolvă la cea mai specifică
national | intrabancar | interbancar   se exclud reciproc -> None
```

„Plăți externe … zonei unice de plăți în EUR" nu e o contradicție, e o descriere
ierarhică; cea mai specifică o numește corect. Cu regula asta, `ue` a urcat de la
74 la 87 și `sepa` la 30.

### Bugul pe care l-am introdus cu regula de specificitate

Imediat după, cifrele au arătat prost: `extern` scăzuse de la 67 la 63 și `ue`
sărise la 105. Cauza:

```
tiparul `ue` conținea  \bUE\b  ->  potrivea și în "în afara UE" și în "non-UE"
"Plăți în afara UE"  ->  {extern, ue}  ->  regula de specificitate  ->  ue
```

Exact direcția opusă. Regula de specificitate transformase un tipar prea lax într-o
eroare activă — înainte, ordinea din listă îl acoperea, fiindcă `extern` venea primul.
Reparat cu priviri-în-urmă explicite pe formele negate. După reparație `extern`
a revenit la 81.

| | la început | acum |
|---|---|---|
| destinație completată | 426 (29%) | **513 (35%)** |
| `ue` | 0 | 87 |
| `national` | 0 | 46 |
| `sepa` | 35 | 30 |

### Moneda nu lipsea. Nici etichetele nu erau trunchiate.

Două intrări din lista mea de probleme erau greșite, și amândouă au căzut la o
măsurătoare de control.

**„1.364 de valori fără monedă"** — nu e o lacună. Împărțite pe fel:

```
815 (55%)  procente        -> un procent nu are monedă, prin natura lui
649 (44%)  zero / GRATUIT  -> nici gratuitatea nu are monedă
  0         sume fără monedă
```

**Zero lipsuri reale.** Trecusem un comportament corect drept defect. Pe drum am
măsurat și trei surse posibile, toate respinse: secțiunea e de acord cu moneda reală
în 43% din cazuri („(USD) (EUR)" — tabelul e multivalutar), eticheta în 80%, antetul
în 89%. Coroborarea a două câmpuri urcă la 91%, dar se aplică la 12 valori. Iar toate
dezacordurile sunt același lucru, nu zgomot:

```
"Plăți interbancare în euro"    ->  "3 lei in echivalent EURO"   moneda reală: LEI
"Retrageri din conturi în EUR"  ->  "2% MIN 15 LEI"              moneda reală: LEI
```

Contul e în euro, comisionul se încasează în lei. Eticheta numește moneda
**contului**; moneda comisionului stă în textul valorii, de unde se și citește acum.

**„Etichetele trunchiate"** — cazul pe care îl dădusem drept exemplu nu era trunchiat:
„Plati externe catre beneficiari din tarile care apartin zonei unice de plati in EUR6"
e complet, doar nu scrie „SEPA". Trunchierea reală există, dar e altceva: din 4.438 de
valori, 106 sunt tăiate la limita de 160 de caractere (enumerări de pachet, unde
tăierea e deliberată), 69 se termină cu o legătură deschisă și 49 au o paranteză
nedeschisă — 4,5% în total, nu cauza dominantă.

## 6f. Cele 1.900 de valori nemapate — și de ce nu sunt o problemă de vocabular

**Adăugat 18 septembrie.** Ultima intrare mare din listă: 1.906 valori fără concept
canonic, 44% din total.

### Discriminantul

Un serviciu nemapat care apare la **3 sau mai multe bănci** e un gol de vocabular
și merită un concept. Unul prezent la o singură bancă nu se poate compara oricum,
deci un concept pentru el n-ar produce nicio linie în tabel. Grupate pe
substantivul-cap al etichetei:

```
627 valori  in grupe prezente la >=3 banci   -> candidate
871 valori  in grupe la o singura banca      -> necomparabile prin definiție
```

### Trei concepte candidate, două adăugate

Măsurate pe date înainte de a fi scrise în cod:

| candidat | valori noi | bănci | verdict |
|---|---|---|---|
| `file_cec` — file cec, bilete la ordin, instrumente de debit | 34 | 6 | **adăugat** |
| `alerta_sms` — SMS Alert, notificări prin SMS | 12 | 4 | **adăugat** |
| `aviz_garantie` — AEGRM | 5 | 2 | respins, sub prag |
| `confirmare` — confirmare sold/semnătură | 3 | 2 | respins, sub prag |

### Poziția în listă, a patra oară

Puse unde le venea natural în listă, cele două **furau 22 de valori corect mapate**:

```
"Remitere la încasare a cecurilor"   -> este o INCASARE, nu file_cec
"Anulare serviciu SMS Alert"          -> este o ANULARE, nu alerta_sms
```

Instrumentul de plată e **obiectul** serviciului, nu capul lui. Puse la sfârșitul
listei: zero deplasări, 47 de valori câștigate. Aceeași regulă care a decis ordinea
la `transfer_credit`, la `credit_ipotecar` și la destinații.

### Un bug vechi, reparat pe drum

Îl notasem acum două runde și nu-l rezolvasem:

```
"Refuz cecuri/ bilete la ordin (neonorate la plata)"  ->  transfer_credit
```

Tiparul `refuz_plata` cerea „refuz" lipit de „plat", dar aici între ele stă „cecuri".
Potrivirea cădea apoi pe `transfer_credit`, prin „la plata" de la coadă — un refuz de
instrument raportat drept comision de transfer. `refuz_plata` are acum 25 de valori
la 4 bănci.

### Ce rămâne nemapat nu e de vocabular

Măsurat pe cele 1.846 rămase:

```
97%  eticheta e un FRAGMENT  ("Emitere", "- de la ATM-uri BCR tranzacție",
                              "POS alte banci din Romania valuta contului)")
51   etichete intregi, si NICIUNA nu apare la >=3 banci
     (sunt note de subsol, benzi de sumă, proză contractuală)
```

**Vocabularul nu poate mapa ce extragerea n-a prins.** Masa rămasă e mărginită de
calitatea etichetei (79% / 83%), nu de dicționar — deci dacă se continuă, se continuă
acolo, nu aici.

### O regulă măsurată și respinsă

Linia nouă `file_cec / pj` iese eterogenă cu `intern = 33.333×`, din cauza unei
singure valori la Libra:

```
etichetă: "Comision de eliberare file cec si bilet la ordin*"
celulă:   "50.000 lei) indiferent daca sunt urgente sau nu."
```

Iar un prag rupt peste granița coloanei, dar în formă nouă: paranteza a fost deschisă
altundeva, nu în etichetă, deci regula din §6b n-o prinde. Am încercat varianta
generală — *orice* celulă care închide o paranteză nedeschisă:

```
18 potriviri, din care 1 e chiar un prag
```

Restul sunt note de subsol („24%4)", „2) 20 lei pentru Mastercard Standard") și
plafoane („max 500 lei)") — **prețuri reale**. Regula ar corupe 17 ca să repare 1,
deci n-am adăugat-o. Dispersia rămâne să o semnaleze, ceea ce și face.

## 6g. Criteriul de „fragment" era lungimea. Trebuia să fie forma.

**Adăugat 18 septembrie.** Maparea coboară la context (secțiune, antet, text-sursă)
doar când eticheta e un fragment, iar criteriul era lungimea: sub 28 de caractere.
Măsurat pe cele 1.846 de valori nemapate, criteriul rata masa problemei:

```
1.573  eticheta incepe cu litera mica    ("îndeplinirea tuturor criteriilor de la 7.3)")
  180  eticheta incepe cu semn de lista  ("- de la ATM-uri BCR tranzacție")
   27  eticheta arata intreaga
```

„- de la ATM-uri BCR tranzacție" are **30** de caractere — trece pragul cu două, deci
nu primea contextul, deși despre serviciu nu spune nimic. Un semn de listă sau o
literă mică la început spun asta mult mai bine decât o numărătoare de caractere.

Cu criteriul structural: **+178 de valori**, zero deplasări, verificat de mână
13 din 14 corecte.

### O notă de subsol nu e un serviciu fără nume

Primul eșantion a găsit clasa de erori:

```
transfer_credit  brci  "Nota: pentru optiunea OUR se vor adauga comisioane"
```

Contextul îi dă un concept, deci un punct de date **inventat**. Notele sunt excluse
explicit din coborârea la context — 4 valori în eșantion.

### Coborârea la context amplifică orice gol de vocabular

Efectul secundar, pe care nu-l anticipasem: odată ce fragmentele ajung la secțiune,
un concept care lipsește din vocabular devine o eroare *activă*, nu o lacună.

```
1500 EUR  "Plata în cadrul cesiunii"        secțiune: FINANȚAREA COMERȚULUI
 200 EUR  "Remitere cerere de plată în SGB" secțiune: SGB PRIMITE
 150 EUR  "Se percepe o singură dată..."    secțiune: ACCEPTARE LA PLATĂ A CARDURILOR
```

Toate trei ajungeau la `transfer_credit`, prin cuvântul „plată" din secțiune. Cauza:
`documentar` acoperea doar jumătate din serviciile documentare. Extins cu SGB,
finanțarea comerțului, scrisoarea de confort și cesiunea de creanță — 20 de valori
mutate de la `transfer_credit`, 16 nou mapate, `documentar` ajunge la 189 de valori
la 6 bănci.

Iar acceptarea cardurilor la comerciant (banca încasează de la comerciant, nu de la
client) a primit concept propriu deși are doar 8 valori la 2 bănci, deci nu va face
niciodată o linie în tabel: erau 7 mapate **greșit**, iar o mapare greșită e mai rea
decât una lipsă. Asta e o excepție deliberată la regula celor 3 bănci, cu care
respinsesem `aviz_garantie` și `confirmare` — acelea erau nemapate, deci inofensive.

### A cincea oară cu pluralul românesc

```
"scrisoare" -> "scrisori"     tiparul cerea `scrisoar\w*`, stemul e "scriso"
```

„Eliberare **Scrisori** de confort" nu se mapa. Aceeași familie ca „comision" →
„comisioane" din §6, punctul 1.

### O ipoteză măsurată și respinsă

Dacă un fragment nu e un nume de serviciu prin definiție, atunci pentru fragmente
contextul ar trebui să bată eticheta, nu doar să o completeze. Cazul „Plata" (5
caractere) o susținea: potrivește `transfer_credit` la nivel de etichetă, deci
contextul nu e consultat niciodată.

Măsurat: acoperirea neschimbată (62%), dar **82 de concepte schimbate, cu regresii
clare**:

```
interogare_baze_date -> retragere_numerar   "Consultari Baze Date CIP, CRC"
file_cec             -> transfer_credit     "Refuz ID (instrument de debit)"
retragere_numerar    -> tranzactie_card     "Utilizare ATM Exim Banca Românească"
```

Respinsă. Regula „eticheta întâi" rămâne, iar cazurile ca „Plata"/FINANȚAREA
COMERȚULUI rămân greșite — puține, și semnalate de dispersie.

### Rezultatul

| | la începutul zilei | acum |
|---|---|---|
| mapate pe un concept | 2.443 (56%) | **2.703 (62%)** |
| nemapate | 1.906 | **1.650** |
| linii comparabile | 72 | **76** |
| **linii de încredere** | 35 | **48** |
| linii prea eterogene | 37 | 28 |
| concepte în vocabular | 26 | 29 |

## 6h. Marja peste indice → rată totală, și axa pe care a scos-o la iveală

**Adăugat 18 septembrie.** Ultima reparație a zilei, pe partea de rate.

### Problema

Libra publică **marjă peste IRCC** („IRCC + 2,15%"), majoritatea celorlalți publică
**rată nominală**. Aceeași informație în două unități, dar tabelul le pune pe rânduri
diferite — deci Libra lipsea din 8 din cele 13 linii, inclusiv creditul de nevoi
personale, unde stau 8 bănci.

Conversia e aritmetică: `nominală = marjă + IRCC în vigoare`. Se aplică la **toate
cele 9 bănci** care publică marje (Raiffeisen 8 valori, ProCredit 7, BRD 5), nu doar
la Libra — altfel am umflat exact banca proprie.

### Proveniența indicelui, nu o constantă

BNR era inaccesibil („ERR_CONNECTION_CLOSED"), deci seria trimestrială lipsea. În loc
de o constantă în cod, indicele se ia în ordinea: BNR → altfel **consensul paginilor
bancare**, dar numai pe valorile pe care validatorul le confirmase cu BNR la o rulare
anterioară, și numai de la **cel puțin două bănci independente**. Aici: 5,56%,
confirmat de BCR, Libra și Nexent. Proveniența se păstrează în date.

Nu s-a convertit de unde nu era sigur:

- **`marja_euribor`** — consensul vine de la o singură bancă (Patria). O sursă nu e
  un consens.
- **`marja_fixa`** (Patria, 16 valori) — am suspectat că sunt **totaluri clasificate
  greșit**, fiindcă un interval de 6,67–17,24 pare prea larg pentru o marjă.
  **Aritmetica m-a infirmat**, verificat a doua zi:

  ```
   6,67 + 5,56 = 12,23  ->  EXISTĂ ca rată nominală 12,23 pe aceeași pagină
  17,24 + 5,56 = 22,80  ->  EXISTĂ ca rată nominală 22,80
   3,17 + 5,56 =  8,73  ->  EXISTĂ ca rată nominală  8,73
  ```

  Patria publică pe aceeași pagină **și marja, și totalul**, iar parserul le-a extras
  corect pe amândouă. Clasificarea era bună. Excluderea de la conversie rămâne
  corectă, dar pentru motivul opus: a converti ar fi **dublat** totaluri care există
  deja. Bonus: e a patra confirmare independentă că IRCC = 5,56%, prin calcul.

### Verificarea a găsit o capcană mai gravă decât problema

După conversie, linia de credit de nevoi personale arăta așa: Libra 8,19 față de
Salt 5,49, BRD 5,70, Raiffeisen 5,95. Adică Libra scumpă. **Am verificat textul-sursă
înainte să raportez, și cifra era înșelătoare pe două axe deodată:**

```
Salt        "Dobândă fixă DE LA 5,49%"
BRD         "RATĂ FIXĂ DE LA 5,70%"
Raiffeisen  "dobândă fixă DE LA 5,95%"
ING         "Dobândă fixă ÎNTRE 5,99% - 15,99%"   <- reținusem doar 5,99
Libra       marjă variabilă + IRCC de azi = rata REALĂ de acum
```

Rate **fixe** față de una **variabilă**, și pe deasupra **capete de jos de interval**
(cel mai bun caz, pentru cel mai bun client) față de intervalul real.

### Deci felul ratei intră în cheie

Se citește determinist din text — 35% din rate spun „fixă", 20% „variabilă" — deci e
măsurătoare, nu judecată. Exact aceeași mișcare ca frecvența la comisioane (§6c). Iar
o marjă peste un indice e variabilă prin construcție.

Plus două marcaje noi în celule: `†` pentru o rată derivată (banca **nu** a publicat
cifra în forma asta) și `↓` pentru „de la X%".

### Rezultatul, mai puțin flatant și mai corect

| | înainte | acum |
|---|---|---|
| linii comparabile | 13 | **15** |
| linii de încredere | 9 | **10** |

**Libra tot nu apare la creditul de nevoi personale — dar ăsta e răspunsul, nu o
lacună.** Împărțit pe fel:

```
fixa       7 banci: bcr, brd, ing, patria, procredit, raiffeisen, salt
variabila  2 banci: libra, patria
```

Piața a trecut la nevoi personale cu dobândă fixă, iar Libra e una din două bănci
care mai cotează variabil. Asta e o observație de poziționare, nu un gol de date.

**Unde conversia a plătit:** `credit_ipotecar / nominala / variabila` e o linie nouă,
de încredere, cu **7 bănci** — la ipotecar variabilul e norma, deci comparația
funcționează:

| Libra | EximBank | Patria | ProCredit | Raiffeisen | BRD † | ING † |
|---|---|---|---|---|---|---|
| **7,78** (7,71–8,31) | 4,99 | 6,30 (4,77–8,46) | 7,66 (4,89–8,06) | 7,56 (4,90–7,66) ↓ | 7,66 | 8,05 |

Libra e cu o zecime peste BRD și ProCredit, în aceeași bandă. EximBank la 4,99 e
outlier, probabil un program special.

## 6i. Rândul care mințea — intervalul ca interval

**Adăugat 18 septembrie.** Continuarea directă a §6h: verificarea de acolo a arătat
că reținem capătul de jos al unui interval ca dacă ar fi prețul. Măsurat, era
recuperabil la **6 valori, 5 bănci** — dar exact cele cinci care contau:

```
BCR         reținut 5,79  ->  "de la 5,79% pana la 14,99%"
ING         reținut 5,99  ->  "Dobândă fixă între 5,99% - 15,99%"
Raiffeisen  reținut 5,95  ->  "cuprinsa intre 5.95% si 18.35%"   (×2)
ProCredit   reținut 7,40  ->  "Fixă între 7,40% – 12,40%"
Patria      reținut 12,23 ->  "variabile cuprinsă între 12,23% - 22,80%"
```

Parserul avea deja un `RE_INTERVAL`, dar acoperea o singură formă („de la X% la Y%").
Formele cu „între" — cele mai frecvente — se pierdeau. Extins, plus o regulă de
respingere: **un interval real are capătul mic scris primul**, iar ordinea inversă e
semnul că potrivirea a prins două cifre nelegate. La BRD ieșea `{min: 26,0, max: 16,9}`
dintr-un text despre cumularea cheltuielilor.

Capătul de sus se emite acum ca înregistrare separată, deci intră automat și în
celulă și în dispersie — la fel ca totalurile derivate din §6h.

### Efectul pe rândul care conta

```
înainte:  bcr 9,49 | brd 5,70↓ | ing 5,99  | patria 9,33 | procredit 7,40 | raiffeisen 5,95  | salt 5,49↓
acum:     bcr 9,49 | brd 5,70↓ | ing 10,99 | patria 9,33 | procredit 9,90 | raiffeisen 5,95  | salt 5,49↓
                              (5,99–15,99)              (7,40–12,40)    (5,95–18,35)
```

ING și Raiffeisen nu mai apar drept cele mai ieftine din piață. Cine citea tabelul
înainte trăgea o concluzie greșită despre concurență, dintr-o cifră corect extrasă
dar incompletă.

## 6j. O verificare care nu s-a putut face NU e o confirmare

**Adăugat 18 septembrie.** Cel mai important lucru găsit azi, și l-am găsit doar
pentru că am rulat lanțul din nou.

BNR a devenit inaccesibil („ERR_CONNECTION_CLOSED"). Lanțul de consecințe:

```
1. seria trimestrială IRCC lipsește
2. validatorul n-are referință -> marchează TOT "OK"            <- TĂCUT
3. cele 13 valori de IRCC ies "OK", inclusiv 4,05% si 5,58%     <- clar vechi
4. constatarea despre pagina Libra dispare, fără nicio alarmă
```

Cauza, în cod: `stare` pornește de la `"OK"` și **doar o referință o poate schimba**.
Fără referință, absența unei verificări arăta identic cu o verificare trecută. Al
treilea „mecanism care înghite eșecuri" găsit în proiect, după `except Exception` și
scrierea care suprascrie date bune cu o eroare.

Reparat: o valoare de indice pentru care n-avem referință primește `NEVERIFICAT`, nu
`OK`, cu motivul scris. Rezultatul de azi: 537 OK, **13 NEVERIFICAT**, 5 SURSA_VECHE
(cele de la Garanti, detectate prin ROBOR/EURIBOR, care se compară cu seria zilnică —
aceea o avem).

### Consens între surse, când autoritatea lipsește

Conversia marjă → total are nevoie de indice. Fără BNR, îl ia din **consensul
paginilor bancare** — dar nu prin unanimitate, care nu există niciodată (paginile
vechi rămân publicate: 5,56 la trei bănci, 5,58 la una, 4,05 la una). Regula e
valoarea declarată de cele mai multe bănci, cu minimum **trei independente** — două
pot copia aceeași pagină veche.

Aici 5,56% e coroborat de cinci surse, două prin calcul:

```
BCR, Libra, Nexent   o declară direct
Patria               marjă 6,67 + total 12,23  -> diferența 5,56
EximBank             marjă 3,50 + total 9,06   -> diferența 5,56
```

Proveniența intră în date: `"consens 3 bănci (bcr, libra, nexent), fără BNR"`.

### Consensul mutat în validator — reparat

**Adăugat imediat după.** Consensul era calculat în `compara_rate.py`, deci
validatorul nu-l vedea: putea deriva rate, dar nu putea verifica prospețimea. Mutat
în `crawler/validator.py` (`consens_indici`), ca să existe **un singur loc** care
decide ce credem despre un indice. Referința se ia acum în ordinea: BNR → consens.

Ce s-a recuperat:

```
Garanti  IRCC 4,05% si 4,06%  ->  SURSA_VECHE
         "difera de consens 3 bănci (bcr, libra, nexent), fără BNR cu 1,50 p.p."
Libra    marja 3,0% si 4,5%   ->  SUSPECT
         "8,68% - 3,0% = 5,68%; IRCC in vigoare e 5,56% — aritmetica paginii nu se
          potrivește cu indicele declarat de restul pieței; de verificat manual"
```

**Libra e `SUSPECT`, nu `SURSA_VECHE`, și distincția e deliberată.** Diferența e
0,12 p.p. — prea puțin pentru un prag de magnitudine, iar proiectul a respins deja
„vechime după mărime" în favoarea potrivirii exacte cu un trimestru încheiat. Pentru
aceea e nevoie de seria trimestrială, care există doar la BNR. Ce se poate spune cu
consensul: o verificare s-a făcut și a eșuat, dar cauza nu se poate atribui — adică
exact definiția lui `SUSPECT`.

Fiecare verdict numește acum sursa folosită: `„confirmat cu consens 3 bănci (bcr,
libra, nexent), fără BNR (5,56%)"` în loc de „confirmat cu BNR" — care ar fi fost o
minciună tocmai când BNR era inaccesibil.

Starea validării azi: 546 OK, 7 SURSA_VECHE, 2 SUSPECT. `NEVERIFICAT` nu mai apare,
fiindcă acum există o referință de rezervă — dar starea rămâne în cod pentru cazul
în care nici consensul nu se formează (sub trei bănci în acord).

## 6k. Ordinea alternativelor era bugul, nu regula lipsă

Patru probleme găsite prin rularea lanțului de la capăt. Trei erau ordonări
greșite, nu reguli care lipseau — iar una dintre reparații a fost respinsă după
ce am măsurat-o.

### Zece scripturi crăpau pe consola Windows

`unifica_comisioane.py` se oprea cu `UnicodeEncodeError` pe primul `print` care
conținea „destinație". Cauza: cp1252 e codificarea implicită a consolei, iar
scriptul nu avea linia pe care o au celelalte 34:

```python
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

Lipsea din zece scripturi, patru dintre ele în lanțul principal
(`parseaza_pdf`, `parseaza_tarife`, `unifica_comisioane`, `compara_rate`). Nu e
o eroare de logică, dar efectul e la fel: lanțul se oprea la jumătate, iar
ieșirea rămânea cea de la rularea anterioară — încă un mecanism care înghite
eșecuri, ca `except Exception` din §6 și ca suprascrierea din `test_indici.py`.

### A cincea familie de cifre care nu sunt prețuri: pragul spus prin comparativ

`RE_CERINTA` cere cuvântul „minim" lângă substantivul-cerință. Dar pragul se
poate spune și prin comparativ:

| text | cifră | ce e |
|---|---|---|
| Operațiuni de plată de mică valoare (mai mici decât 50.000 lei) | 50.000 | prag |
| se aplica la sold mai mare de 500 RON | 500 | prag |
| 0,5% din valoarea nominală totală, **dar nu** mai puțin de | 0,5 | preț |
| **dar nu** mai mult de 0,01% per zi de intarziere | 0,01 | preț |

Discriminantul nu e cuvântul comparativ — e negația. „nu mai puțin de" leagă
numărul de comisionul însuși (e plafonul lui); „mai puțin de" îl leagă de
operațiune. Verificat pe toate cele 9 valori din corpus care conțin un
comparativ: 6 sunt praguri, 2 sunt plafoane de comision, iar a noua e un
superlativ — „0,5% din valoarea **cea mai mare** a limitei de credit" — pe care
prepoziția obligatorie de după comparativ o lasă afară, fiindcă acolo urmează
„a", nu „de".

Și încă o dată pluralul românesc, a șasea oară în proiect: **„mare" face „mari",
deci tulpina e „mar", nu „mare".** Fără asta, „mai mari sau egale cu 50.000 lei"
trecea.

### Banda avea deja o regulă. Stătea după cea care o bloca.

Cea mai mare dispersie din tabel era `transfer_credit/pf/interbancar`, cu
**16.667× între bănci și 98.039× intern**. Cauza: șase valori Libra de
49.999,99 lei raportate drept comision de transfer.

`RE_PRAG` avea deja alternativa pentru bandă cu două capete. Problema era că
stătea **ultima**, iar alternarea în Python e ordonată: pe „intre 0 lei –
49.999,99 lei" varianta cu un singur capăt potrivea „intre 0 lei", se oprea, și
lăsa capătul din dreapta în linie — de unde ieșea un comision de 49.999,99 lei.

Reparația e o mutare, nu o regulă nouă. Plus o limită care vine din limbă:
**cuvântul spune singur câte capete are banda.** „între" și „de la" au două;
„peste", „sub" și „până la" au unul. De aceea extinderea se aplică numai primelor
două — pe „sub 1.000 lei - 5 lei" ar fi mâncat comisionul.

Un nivel mai jos, aceeași greșeală în `VAL`: `(?:lei|leu|ron|eur|euro)` potrivea
mereu „euro" ca „eur" și lăsa un „o" orfan în linie după tăierea benzii — iar
litera rămasă se numără în `_e_doar_banda`. Ordinea corectă e cea mai lungă
întâi.

Rezultat: rândul a scăzut de la 16.667×/98.039× la **29×/67×**.

### O frază întreagă nu e un fragment

`_e_fragment` trimitea la context orice etichetă care începe cu literă mică. Salt
explică pachetele într-un paragraf, iar din secțiunea „ÎNCASĂRI ȘI PLĂȚI" cele
trei prețuri de abonament (0 / 360 / 960 lei) primeau conceptul `incasare` —
prețul pachetului raportat drept comision de încasare.

`RE_ETICHETA_NOTA` exista deja, dar recunoaște nota doar după marcajul din fața
ei („Notă:", „*", „3)"). O notă poate fi și proză curată, fără marcaj.

Criteriul: **un fragment e o bucată dintr-un nume de serviciu, care are nevoie de
context ca să se completeze; o propoziție cu punct final își spune singură
sensul.** Dacă nu se potrivește pe vocabular de una singură, nu descrie un
serviciu — nu înseamnă că serviciul e scris mai sus.

Măsurat: 24 de valori au etichetă-frază, 9 erau mapate, iar 8 din 9 au potrivire
**directă** pe etichetă (BCR „Pachetul Servicii de Bază pentru persoane
nevulnerabile…", Garanti „interogare sold ATM GARANTI BANK S.A.", Raiffeisen
„Acreditive documentare accesând următorul link: SEPA countries.") și rămân
neatinse, fiindcă regula taie numai recursul la context. 9 → 7.

### Regula pe care am respins-o după ce am măsurat-o

Două valori Libra rămân raportate greșit, amândouă fragmente dintr-o notă tăiată,
iar una are un semn care pare curat: `50.000 lei) indiferent daca sunt urgente
sau nu.` — paranteză de închidere fără deschidere, deci coada unei fraze al cărei
început n-a ajuns în celulă.

Am vrut regula „numărul dintr-o paranteză a cărei deschidere n-am văzut-o nu se
poate atribui". Am numărat înainte s-o scriu: **35 de valori au paranteză
neînchisă, și vreo 30 sunt prețuri reale** — „650 euro)", „max 500 lei)", „1,5
lei/operatiune)", „3) 90 lei pentru Mastercard Gold Select" (acolo paranteza e
numerotarea notei). Ar fi distrus 30 de valori corecte ca să repare 2.

Nu am scris-o. Cele două rămân în rândul marcat `intern 111.111×`, deci
**excluse din setul de încredere** — plasa de siguranță pentru care a fost
construită măsura de dispersie face exact ce trebuie: nu repară maparea, dar
oprește cifra înainte să ajungă la cititor.

### Și ce NU era o problemă

779 de valori identice, până la 11 copii, aceeași bancă, același serviciu,
aceeași pagină, același text-sursă. Arătau ca un eșec de dedublare. **Diferă prin
`coloana`:** tabelul PJ al BCR are nouă coloane de produse de card, și „Blocare
card furat/pierdut — gratuit" e publicat o dată pentru fiecare. Nouă celule reale
în document, nouă valori. Extragerea e corectă.

A doua oară în proiect când am pus comportament corect pe lista de defecte (prima
a fost „1.364 de valori fără monedă"). Ce rămâne real e mai mic: numărătoarea
„33 valori / 5 bănci" sugerează mai multe dovezi independente decât există.

### Bilanț, cinstit

| | înainte | după |
|---|---|---|
| valori totale | 4.438 | 4.432 |
| cu rol `conditie` | 42 | 48 |
| valori ≥ 10.000 lei drept preț | 36 | 30 |
| dispersia maximă pe `transfer_credit/pf/interbancar` | 16.667× / 98.039× | 29× / 67× |
| linii comparabile / de încredere | 76 / 48 | 76 / 48 |
| teste | 35/35 | 35/35 |

**Numărul de linii de încredere nu s-a mișcat.** Reparațiile au scos cifre
greșite din rânduri care rămân eterogene din alte motive. Datele sunt mai curate,
titlul nu s-a schimbat — și e mai util spus așa decât ascuns.

## 7. Ce urmează

1. ~~**Atribuirea etichetei la BCR**~~ — făcut, 17 septembrie: BCR 37% -> 64%,
   total 62% -> 83%. Vezi §5. A reparat și listele de tarife (77% de la 63%),
   fiindcă era aceeași cauză în ambele.
2. ~~**Extinderea la cele 25 de documente „Tarife și comisioane"**~~ — făcut,
   17 septembrie: 4.015 valori din 24 de documente, 10 bănci. Vezi
   [COMISIOANE_TARIFE.md](COMISIOANE_TARIFE.md). A confirmat că problema de la
   punctul 1 e comună celor două surse și că rezolvarea ei le repară pe amândouă.
3. ~~**Un etalon manual pentru comisioane**~~ — făcut pe parcurs: 4 eșantioane
   de câte 24 de valori pe listele de tarife (§5 din
   [COMISIOANE_TARIFE.md](COMISIOANE_TARIFE.md)) plus 22 de valori pentru
   maparea canonică. Precizia valorii: 94 din 96.
4. ~~**Cifrele care nu sunt prețuri, runda a doua**~~ — făcut, 17 septembrie: 37 de
   cerințe și limite marcate `rol="conditie"`, plus frecvența și rolul în cheia de
   grupare. Tabelul a trecut de la 35/37 la **46 de linii de încredere / 27
   eterogene**. Vezi §6b.
5. ~~**Măsura de dispersie folosește `max/min`**~~ — făcut, 18 septembrie: două
   măsuri separate (`între` bănci și `intern` pe bancă), amândouă afișate în tabel.
   Vezi §6c. Numărul de linii de încredere e aproape același (45), dar diagnosticul
   e nou — și a dus direct la canalele de livrare a documentelor.
6. ~~**Destinația** (intra/inter/extern)~~ — făcut, 18 septembrie: 29% -> 34%, cu
   două valori noi în vocabular (`ue`, `national`), regula „eticheta întâi" și
   refuzul de a alege când documentul numește ambele destinații. 16 din 18 corecte
   pe eșantion. Vezi §6d.
7. ~~**Moneda lipsă** (1.364 de valori)~~ — **nu era o problemă.** Toate sunt
   procente sau zerouri, care nu au monedă prin natura lor. Vezi §6e.
8. ~~**Etichetele trunchiate**~~ — diagnostic greșit: exemplul pe care îl dădusem era
   complet, doar nu scria „SEPA". Trunchierea reală e 4,5% din valori și în mare
   parte deliberată (limita de 160 de caractere pe enumerările de pachet). Vezi §6e.
9. ~~**Valorile nemapate pe un concept**~~ — făcut, 18 septembrie: două concepte noi
   (`file_cec`, `alerta_sms`, +47 de valori la 6 și 4 bănci), plus bugul `refuz_plata`
   reparat. Maparea 56% -> 57%. Vezi §6f. Măsurat: restul **nu** e de vocabular — 97%
   din cele nemapate au eticheta fragmentară, iar dintre cele întregi niciuna nu apare
   la 3+ bănci.
10. ~~**Etichetele fragmentare**~~ — atacate din partea maperii, 18 septembrie:
    criteriul structural în locul lungimii a recuperat 178 de valori fără să atingă
    parserul. Vezi §6g. Maparea 56% -> 62%, linii de încredere 35 -> 48.
11. **Ce a rămas, măsurat:** 28 de linii eterogene (20 cu `intern` mare, 18 cu
    `între` mare) și 1.650 de valori nemapate. Reparația din §6g a luat ce se putea
    lua din partea maperii; restul cere **numele serviciului recuperat la extragere**,
    adică granița rândului de grilă care taie listele de conținut (§6, punctul 6).
    Acolo am încercat deja o dată și am pierdut (61% față de 70%), deci ar fi o
    rescriere, nu o reparație.
7. **Secțiunea PAD** e extrasă acum și aici (toate cele 427 de valori o au), iar
   ea s-a dovedit singura axă care se aliniază între bănci — vezi
   [comparatie_comisioane.md](comparatie_comisioane.md).
