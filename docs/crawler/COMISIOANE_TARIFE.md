# Comisioanele din listele de tarife — 17 septembrie 2026

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 18 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

A doua sursă de comisioane: listele proprii de tarife, care **nu** sunt
standardizate prin lege. Volumul mare de date.

**Cod:** [crawler/parser_tarife.py](../crawler/parser_tarife.py) ·
**Rulare:** `python scripts/parseaza_tarife.py` ·
**Ieșire:** `output/comisioane_tarife.json`

Precedentul: [COMISIOANE_PDF.md](COMISIOANE_PDF.md) — cele 16 documente
standardizate prin Legea 258/2017, 430 de comisioane.

---

## 1. Documentele

31 de PDF-uri cu „tarife", „comisioane" sau „taxe" în nume, care nu sunt
formularul standardizat. După dedublare rămân **25**.

Dedublarea nu e o rafinare, e obligatorie: băncile lasă pe site toate versiunile
succesive. BCR are lista PJ în trei versiuni (martie, iulie, august 2026), BRCI
are PF și PJ în câte două (mai și octombrie 2024), iar Raiffeisen are același
document sub două nume. Fără dedublare, aceleași tarife ar fi intrat de trei ori
în date și ar fi dublat tot ce numărăm.

| bancă | documente | pagini |
|---|---|---|
| BCR | 5 | 8–17 |
| Libra | 7 | 1–12 |
| BRCI | 2 | 10–12 |
| Raiffeisen | 2 | 10–12 |
| BRD | 2 | 7–12 |
| TBI | 3 | 4–5 |
| Salt, Garanti, EximBank, BCR Locuințe | câte 1 | 1–24 |

**24 din 25 procesate.** Excepția e `Click24Banking_PlataImpoziteTaxe.pdf`: e un
scan, zero text extractibil. E singurul document scanat din toate cele 320 — de
aceea nu am construit OCR pentru unul.

## 2. Rezultatul

**4.015 valori din 24 de documente, 10 bănci.** De 9,3 ori setul standardizat,
dintr-o sursă care nu exista în date până azi.

| | |
|---|---|
| sume absolute | 2.651 |
| procente | 761 |
| „gratuit" declarat în cuvinte | 603 |
| în lei | 1.865 |
| în euro | 786 |
| cu secțiune | 3.836 |
| cu nume de coloană (tabel matriceal) | 1.506 |
| cu condiție de bandă | 196 |
| servicii distincte | 1.740 |

Pe bănci: BCR 1.165, Libra 673, BRD 584, BRCI 361, Raiffeisen 325, EximBank 283,
Salt 223, Garanti 214, TBI 163, BCR Locuințe 24.

**Nu tot ce e într-o listă de tarife e un comision**, așa că fiecare valoare are
o categorie: 3.926 comisioane, 47 limite de tranzacționare, 38 rate de dobândă,
4 cursuri de schimb. Doar categoria „comision" intră în comparația între bănci.
Verificarea de mână a găsit de trei ori valori din celelalte categorii raportate
ca preț — de aici câmpul.

## 3. Ce a trebuit învățat din date

Cinci lucruri, toate măsurate, niciunul presupus.

### Coloanele se citesc pe rând, nu pe pagină

Cea mai importantă. O pagină conține mai multe tabele, cu geometrii diferite.
Uniunea bordurilor pe toată pagina dă coloane false — pe `BCR_Tarife-PJ` pagina 9
ieșeau 14:

```
la nivel de pagină:  [23, 51, 203, 208, 244, 256, 285, 326, 367, 408, 450, 491, 532, 573]
la nivelul rândului: [23, 51, 207, 256, 573]
```

Nu era o problemă cosmetică: textul se rupea în `8 LEI +` și `TVA/entitate
client`, deci valoarea se **pierdea**, nu se muta. Cifra fără monedă lângă ea nu
mai e o sumă.

### O bordură nu taie niciodată un cuvânt

Am încercat mai întâi testul invers — „o bordură pe care o traversează multe
cuvinte nu e reală" — și **nu discriminează**: în documentul de control, unde
parserul merge deja corect, 9 cuvinte traversează o bordură adevărată, față de 18
la una falsă. Prea aproape.

Regula care ține: cuvintele se grupează în secvențe de text continuu, iar o
secvență se rupe doar acolo unde bordura cade **între** două cuvinte. Repartizarea
pe coloane se face apoi pe secvență, după suprapunere maximă — nu pe cuvânt, după
centru, fiindcă numele unei coloane e adesea mai lat decât coloana însăși.

### Unele tabele nu au nicio bordură

Toate paginile de tarife Garanti: `borduri=[]`. Acolo coloana se deduce din
golurile de spațiu alb, cu un prag derivat din rând (corpurile de literă merg de
la 6 la 12 puncte, deci un prag fix ar rupe rândurile dese și ar lipi rândurile
rare).

### Pragul relativ singur nu ajunge

Pe coperta Raiffeisen ieșeau 15 „coloane" din vectorii siglei: maxim acumulat
**35 de puncte pe o pagină de 595**, deci fiecare poziție trecea pragul relativ.
E nevoie și de un prag absolut — o bordură de celulă acoperă cel puțin un rând de
text.

### Multe liste nu scriu spațiile în PDF

pdfplumber lipea cuvintele: `OPERATIUNIFARANUMERAR`, `SchimbarecodPIN`. Măsurat pe
ghidul BRD, coborând toleranța orizontală de la 3 la 1,5 puncte:

| toleranță | cuvinte | lipite | rupte greșit |
|---|---|---|---|
| 3 | 3.413 | 168 | 24 |
| 1,5 | 5.058 | **6** | 45 |

Îmbunătățire strictă, iar documentele care au spații reale nu sunt afectate deloc
(`Tarif_standard` BCR: identic la orice toleranță).

## 4. Ce aduce în plus față de formularul standardizat

**Ierarhia de secțiuni.** Același nume de serviciu apare de mai multe ori sub
secțiuni diferite, deci fără ea valorile nu se pot deosebi: `4.2. PLĂȚI > A. În
lei` nu e același lucru cu `4.2. PLĂȚI > B. În valută`.

**Numele coloanei.** În tabelele matriceale coloana *e* informația: patru
„GRATUIT" pe un rând la Salt sunt patru pachete diferite, nu o valoare repetată.
1.506 valori au numele coloanei recuperat.

**Categoria**, explicată mai sus.

## 5. Verificare

### Automat: textul-sursă există în pagina lui

**4.013 din 4.015 (99%).** Asta prinde valorile fabricate de geometrie — cifre
lipite din două celule, sume compuse din bucăți de rând, texte mutate de pe altă
pagină. Nu prinde eticheta greșită, fiindcă eticheta e o judecată, nu o potrivire
de text.

### De mână: trei eșantioane, câte 24 de valori

Stratificat, câte o valoare din fiecare document, semințe 2609 / 4412 / 777.
Primul eșantion a fost cel pe care am făcut reparațiile; celelalte două sunt
măsurători curate, pe cod nemodificat după.

| | valorile | etichete curate | parțiale | greșite |
|---|---|---|---|---|
| înainte de reparații (2609) | 24/24 | 9 | 3 | 11 |
| după (4412) | 23/24 | 10 | 7 | 4 |
| după (777) | 23/24 | 10 | 5 | 8 |
| după pozițiile verticale (3110) | 24/24 | **17** | 4 | **2** |

**Valoarea: 94 din 96 corecte (98%).** Cele două greșeli erau amândouă praguri
raportate ca preț, iar cauza a fost reparată (vezi §6).

**Eticheta serviciului: de la 20 din 44 curate (45%) la 17 din 23 (74%)**, iar
greșelile clare au scăzut de la 8–11 pe eșantion la 2. Reparația e în §6.

## 6. Calitatea etichetei — reparată prin poziții verticale

**Actualizat 17 septembrie, după §5.** Cauza unică identificată mai jos a fost
rezolvată, iar reparația a venit din cealaltă sursă: aceeași regulă care a ridicat
formularul standardizat de la 62% la 83%
([COMISIOANE_PDF.md §5](COMISIOANE_PDF.md)).

### Ce nu s-a putut copia direct

Regula din formularul standardizat — „rândurile de nume se grupează după golul
vertical" — aplicată aici a dat **33%, mai rău decât cele 63% de la care plecam**,
iar serviciile distincte au scăzut de la 1.874 la 1.027. Blocurile înghițeau tot.

Cauza merită reținută: în formularul standardizat coloana de nume are rânduri
**goale** între servicii, fiindcă valorile stau pe rândurile dintre ele. Într-o
listă de tarife fiecare rând poartă un nume, deci toate rândurile sunt la fel de
apropiate și golul nu mai separă nimic.

Ce separă, aici:

1. **Un rând cu preț deschide întotdeauna un nume nou** — într-un tabel de tarife,
   rândul cu preț *este* rândul logic.
2. **Un rând fără preț continuă numele de deasupra** doar dacă arată ca o frază
   ruptă: începe cu literă mică, sau cel de dinainte se termină cu o legătură
   („…pentru retragere" + „numerar").
3. Când eticheta rezultată e **doar o bandă de sumă** (`≤ 100.000 EUR`,
   `sub 49.999,99 lei`), i se pune în față ultimul nume-părinte: fără el valoarea
   nu se poate compara cu nimic.

Pentru două treceri, nu una: continuarea unui nume poate veni **după** rândul cu
valoarea, deci într-o singură trecere valoarea se emitea înainte ca numele să fie
întreg. De aici veneau și numele trunchiate, și fragmentul „numerar" lipit la
serviciul următor.

### Rezultatul măsurat

| bancă | valori | curate înainte | curate acum |
|---|---|---|---|
| EximBank | 283 | 74% | **92%** |
| BRCI | 361 | 80% | **91%** |
| Raiffeisen | 325 | 76% | **84%** |
| Libra | 673 | 64% | **80%** |
| BCR | 1.165 | 58% | **72%** |
| BRD | 584 | 53% | **70%** |
| Salt | 223 | 57% | 69% |
| Garanti | 214 | 58% | 61% |
| TBI | 163 | 49% | 63% |
| BCR Locuințe | 24 | 100% | 100% |
| total | 4.015 | 63% | **77%** |

Toate cele 4.015 valori s-au păstrat, verificarea automată stă la 99%, iar acum
**fiecare valoare are un serviciu** (înainte 6 nu aveau).

Verificat de mână pe un eșantion nou, sămânța 3110, 24 de valori:
**17 curate, 4 parțiale, 2 greșite** — adică 74% curate, față de 45% înainte.
Numărul greșelilor a scăzut de la 8–11 la 2.

## 7. Limita care rămâne

Cum se măsoară (`scripts/calitate_tarife.py`): o etichetă e suspectă dacă începe
cu literă mică, se termină cu o legătură, conține un preț care nu e o bandă de
sumă, e mai scurtă de 6 caractere sau mai lungă de 100. Fiecare etichetă pe care
am judecat-o greșită de mână încalcă cel puțin una.

Cifra e o *limită de sus*: regulile prind forma stricată, nu eticheta care arată
bine și e a rândului vecin. De aceea măsurătoarea de mână rămâne cea care decide.

Ordinea pe bănci a rămas aceeași după reparație, doar ridicată: sus tabelele
simple de două coloane, jos matricile dense. Ce s-a schimbat e mărimea diferenței
— BRD a urcat de la 53% la 70%, iar EximBank, unde matricea are antet curat, la
92%.

**Ce rămâne greșit are acum altă cauză.** Cele două greșeli din eșantionul de mână
vin amândouă din ghidul de credite BRD, care nu e un tabel: e o pagină de revistă
pe două coloane („DOBÂNZI" și „COMISIOANE"), unde numele și prețul nu sunt aliniate
nici pe rând, nici pe poziție. Acolo geometria nu mai ajută, fiindcă nu există
tabel de citit.

## 7b. Antetul de matrice — și o premisă a mea, infirmată

**Adăugat 18 septembrie.** Numele coloanei e ce distinge patru valori identice pe
un rând ca fiind patru pachete diferite (§4). Era completat la 1.504 din 4.011
valori, dar în mare parte cu gunoi.

### Ținta nu e 100%, e 40%

Prima măsurătoare a fost a ce *merită* un antet: doar rândurile cu valori în două
sau mai multe coloane sunt matrici. Restul au un singur preț, iar antetul ar fi
„Comision", adică nimic.

```
valori în rânduri de tabel: 4.118
  din rânduri-matrice:      1.665  (40%)
```

Deci acoperirea era deja ~90% din țintă. **Problema nu era acoperirea, era
calitatea** — iar eu o citisem greșit în lista de probleme.

### Ce lua locul antetului

Trei feluri de rânduri fără valori intrau la antet și se lipeau peste el:

```
ANTET  3. TAXE ȘI COMISIOANE   || Standard || Standard || Platinum   <- antetul real
VAL                            || GRATUIT  || GRATUIT  || GRATUIT
ANTET                          || in limita primelor 5 retrageri     <- continuare de celulă
ANTET                          || sau pana la 1.500 RON/luna(        <- continuare
```

De aici antete-frază ca „Standard in limita primelor 5 retrageri sau pana la 1.500
RON/luna". Cele trei feluri, cu discriminantul fiecăruia:

| ce e | discriminant | exemplu |
|---|---|---|
| continuarea unei celule de valoare | începe cu literă mică sau paranteză | „in limita primelor 5 retrageri" |
| rând de prețuri cu benzi | conține o bandă de sumă (`RE_PRAG`) | „50-100 lei \| 5 – 100 lei" |
| rând de prețuri în valute | cifră lipită de monedă | „3 USD 2,5 GBP 3 CHF", „12 USD/" |

Primul discriminant e **exact cel folosit deja** la continuarea etichetelor
(`_e_continuare`). Plus o limită de lungime: un nume de coloană peste 48 de
caractere nu mai e un nume, iar acumularea înghițea rânduri care nu erau antet.

| | înainte | acum |
|---|---|---|
| antete completate | 1.504 | 958 |
| din care **curate** | 497 (33%) | **579 (60%)** |
| continuare de celulă | 285 | **0** |
| rânduri de prețuri | 353 | 138 |

Scăderea totalului e câștig: s-a completat mai puțin, dar mai mult *corect*.

### Premisa mea era greșită: antetul nu dă moneda

Scrisesem că reparația asta o deblochează pe cea a monedei lipsă (1.364 de valori).
**Nu o deblochează.** Verificarea de control: la valorile care au deja monedă *și*
un antet care conține o monedă, antetul e de acord doar în 85% din cazuri — iar
dezacordurile nu sunt erori:

```
antet "În EUR"     sursă "2% MIN 15 LEI"       -> contul e în EUR, comisionul în lei
antet "NOIR LEI"   sursă "2.000 EUR (echiv.)"  -> cardul e varianta lei, taxa în euro
```

Ambele sunt corecte, despre lucruri diferite: antetul numește moneda **contului sau
a cardului**, nu a comisionului. Aceeași lecție ca la ratele de pe web, unde o știre
despre mașini electrice aflată pe pagina Noua Casă era raportată drept dobânda Noua
Casă — **dovada locală bate contextul**, iar aici textul valorii e dovada locală.

Moneda lipsă rămâne o problemă deschisă, dar cu altă soluție decât credeam.

## 8. Erorile mele

1. **Am proiectat coloanele pe pagină, nu pe rând.** Prima versiune dădea 14
   coloane false și rupea valorile în două. A ieșit la măsurătoare, nu la citit
   cod.
2. **`\b` nu se declanșează lângă underscore.** Regula de dedublare trebuia să
   taie `_vers_` din numele fișierelor; underscore-ul e caracter de cuvânt, deci
   nu există graniță între `_` și `v`. Rezultat: două versiuni BRCI numărate
   amândouă, 4.150 în loc de 4.044.
3. **Regula „text scurt cu majuscule = titlu" a fost greșită de două ori.**
   Întâi am comparat lățimea *tabelului* în loc de a *celulei*, deci `EUR` și
   `ATM` din coloane înguste treceau drept secțiuni. Apoi codurile de monedă:
   `USD/` ajunsese secțiunea cu cele mai multe valori din ghidul BRD. Rău dublu —
   la detectarea unei secțiuni se golește tamponul de etichetă, deci un titlu
   fals *șterge* numele serviciului.
4. **Am acceptat indexul fără punct.** `RE_INDEX_LA_INCEPUT` potrivea orice rând
   care începe cu o cifră, așa că nota de subsol „2 intrări gratuite pe an," a
   devenit titlu de secțiune. Un număr de secțiune se scrie cu punct.
5. **Praguri scrise cu simbol.** `RE_PRAG` acoperea „peste", „sub", „până la",
   dar nu `≤ 1.500 LEI` sau `> 20.000 LEI` — 149 de praguri raportate ca preț.
   Apoi, după prima reparație, tot nu acopeream `>=12.000 lei`: simbolul urmat de
   `=`.
6. **Frecvența doar în cuvinte.** `RE_FRECVENTA` cerea „lunar", „anual", dar
   listele scriu `5 lei/lună`, `1% /an`, `min. 1 LEI/tranzacție` — adică exact
   forma cea mai folosită lipsea. După reparație, setul standardizat a câștigat 81
   de frecvențe „pe operațiune" care se pierdeau în silențiu.

Prima e o eroare de proiectare; celelalte cinci sunt toate aceeași eroare: **am
scris un tipar pentru forma pe care mă așteptam să o vadă, nu pentru forma din
documente.** Antidotul care a funcționat de fiecare dată a fost să măsor
distribuția înainte, nu să citesc regexul după.

## 9. Ce nu s-a schimbat

Setul standardizat a rămas la **430 de comisioane din 16/16 documente**, cu
aceleași 7 condiții de bandă, iar cele 35 de teste de pe web trec — la fiecare
pas, fiindcă `parser_pdf.py` e comun celor două surse și l-am modificat de mai
multe ori (praguri cu simbol, frecvențe cu bară, poziții verticale, note de
valabilitate). Numărul de valori a fost invariantul pe care l-am verificat după
fiecare schimbare; etichetele s-au schimbat intenționat, în bine (§6).

## 10. Ce urmează

1. ~~**Atribuirea valorii la etichetă prin poziții verticale.**~~ Făcut în
   aceeași zi, pentru ambele surse: 63% -> 77% aici, 62% -> 83% la formularul
   standardizat. Vezi §6.
2. ~~**Numele coloanei în matricile cu antet pe mai multe rânduri**~~ — făcut,
   18 septembrie: antete curate de la 497 la 579, clasa „continuare de celulă"
   eliminată complet. Vezi §7b. Diagnosticul meu era însă greșit pe două puncte:
   ținta reală e 40% din valori (doar matricile), nu toate, iar antetul **nu**
   poate da moneda lipsă — numește moneda contului, nu a comisionului.
3. ~~**Unificarea celor două seturi**~~ — făcut, 17 septembrie:
   [comparatie_comisioane.md](comparatie_comisioane.md), 72 de linii comparabile
   din care 35 de încredere. Cod: `crawler/vocabular.py`,
   `scripts/unifica_comisioane.py`. Ce am aflat pe drum: secțiunile PAD sunt
   axa care se aliniază între bănci (5/5 bănci, literal), denumirile nu (4 din
   116). Iar un concept singur nu ajunge — trebuie și canalul, destinația și
   segmentul de clienți, altfel se compară un preț PF cu unul PJ.
