# Detecția schimbării — ce a publicat altfel banca

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 18 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

18 septembrie 2026. `crawler/urme.py`, `scripts/urmareste.py`,
`scripts/verifica_robots_origini.py`, `output/urme.json`.

Corespunde tabelei `URL_CHECK` din arhitectura țintă.

---

## 1. Amprenta stă pe octeți, nu pe valorile extrase

Asta e singura decizie de proiectare care conta, și are o dovadă măsurată.

Între 17 și 18 septembrie, `comisioane_pdf.json` a scăzut de la **430 la 427**
de valori. Un diff pe valorile extrase ar fi raportat:

> *„Au dispărut trei comisioane la bănci."*

Nu dispăruse nimic. **Eu** schimbasem regexul de bandă, în aceeași zi
([COMISIOANE_PDF.md §6k](COMISIOANE_PDF.md)).

Un sistem care nu separă „banca a schimbat" de „parserul meu a schimbat"
fabrică constatări false — iar o constatare falsă arată exact ca o descoperire,
deci trece nevăzută. Într-un proiect a cărui disciplină e să nu afirme mai mult
decât susține dovada, asta e cel mai rău fel de eșec.

Octeții documentului nu depind de versiunea parserului. De aceea amprenta stă pe
ei, și de aceea în arhitectura voastră hash-ul e la nivel de URL, nu la nivel de
valoare extrasă.

### Versiunea parserului se păstrează oricum — dar cu alt rol

Nu ca să identifice schimbări, ci ca să spună **dacă o comparație de valori are
voie să fie făcută**:

```
comparație de valori: NU — parserul s-a schimbat (1e009595 -> a4c71f02);
                           diferența de valori NU e interpretabilă ca
                           schimbare de piață
```

Versiunea e `sha256` peste cele cinci module care decid extragerea
(`parser_pdf`, `parser_tarife`, `parser_rate`, `vocabular`, `validator`),
calculată din surse. **Nu un număr scris de mână** — un număr de versiune pus
manual se uită exact când contează.

## 2. Șapte stări, nu două

| stare | înseamnă |
|---|---|
| `NOU` | URL-ul nu fusese văzut niciodată |
| `NESCHIMBAT` | aceiași octeți |
| `SCHIMBAT` | octeți diferiți — **asta e constatarea** |
| `LIPSA` | banca **a fost** recrawlată și nu mai referă documentul |
| `NEVERIFICAT` | banca **nu** a fost recrawlată, deci absența nu dovedește nimic |
| `AMBIGUU` | mai multe URL-uri scriu în același fișier local (vezi retragerea) |
| `NEDESCARCAT` | referit, dar deliberat neluat (interzis de robots.txt, ori nu e document de tarife) |

Distincția `LIPSA` / `NEVERIFICAT` e aceeași disciplină ca cele patru stări ale
validatorului: **o verificare care nu s-a putut face nu e un rezultat.** Fără
ea, o rulare în care un site a picat ar raporta că banca și-a retras tarifele —
a treia oară în proiect când aceeași eroare ar fi apărut sub o formă nouă.

Absența se judecă **pe bancă**, nu pe document: discriminantul e dacă
`moment_crawl` al băncii s-a schimbat de la ultima rulare.

## 3. Registrul nu se suprascrie cu o rulare goală

Pe 18 septembrie am pierdut zece zile de ROBOR pentru că un script a scris un
obiect de eroare peste seriile întregi și n-a spus nimic. Le-am recuperat din
arhivă — din noroc, nu din proiectare.

Aceeași greșeală aici ar șterge istoricul de amprente, care **nu se poate
reface**: octeții de ieri nu mai există nicăieri.

```
gol peste bun:   scris=False  registrul are 2 documente, iar rularea a produs 0
                              — NU s-a scris nimic, istoricul e păstrat
bun peste bun:   scris=True   3 documente în registru (erau 2)
gol peste nimic: scris=True   0 documente în registru (erau 0)
```

Și documentele `NEVERIFICAT` nu se ating la actualizare — ce n-a fost verificat
nu-și pierde amprenta veche.

## 4. Ce a scos la iveală imediat: robots.txt per origine

Registrul e cheiat pe URL, deci originea se citește din cheie. Prima rulare a
răspuns la o întrebare pe care nu o pusesem:

> **63 de documente descărcate vin de pe 10 origini pentru care nu exista
> nicio regulă robots.txt citită.**

Regula „per origine" e scrisă în proiect de la început, exact pentru că
documentele băncilor stau des pe alt domeniu. Crawlul o aplicase însă numai
site-ului fiecărei bănci. Cele 25 de fișiere din `output/robots/` erau toate
pentru domeniile proprii.

O regulă citită pentru `www.bcr.ro` nu spune **nimic** despre ce se poate lua de
pe `cdn.erstegroup.com`. ING e cazul care a dovedit că diferența contează:
`Disallow: *.pdf` pe `ing.ro`.

Verificat cu `scripts/verifica_robots_origini.py`:

| origine | doc | verdict |
|---|---|---|
| cdn.erstegroup.com | 45 | citit, 84 reguli — permise |
| cdn0.erstegroup.com | 4 | citit, 84 reguli — permise |
| techventures.bank | 4 | citit, 1 regulă — permise |
| static.anaf.ro | 3 | 404 — fără restricții declarate |
| www.transfond.ro | 2 | 404 — fără restricții declarate |
| www.oecd.org | 1 | citit, 2 reguli — permis |
| www.arb.ro | 1 | 404 |
| procreditbank.ro | 1 | citit, 8 reguli — permis |
| assets.revolut.com | 1 | 404 |
| www.salt.bank | 1 | 404 |

**Zero documente interzise.** Nu era o încălcare — era o verificare care lipsea.
Acum există, cu fișierele brute păstrate în `output/robots/` ca dovadă.

### Trei detalii care puteau strica verdictul

1. **`RegulliRobots` nu păstra textul brut.** Scriptul de salvare îl scria
   dintr-o variabilă locală, deci originile verificate din alt script ar fi
   rămas fără dovadă — iar `getattr(reguli, "text_brut", None)` ar fi returnat
   `None` în silențiu. Adăugat ca atribut în modul, pentru toți apelanții.

2. **404 nu e același lucru cu „n-am citit".** Prin RFC 9309, un cod 4xx e un
   **răspuns**: originea nu declară restricții. O eroare de rețea nu e un
   răspuns deloc. Prima versiune a raportului le punea la comun și strigau toate
   „necitit" — o alarmă falsă, exact peste distincția pe care proiectul o face
   deja în două alte locuri.

3. **Alarma trebuie să se stingă.** Avertismentul citește acum și
   `robots_origini.json`, deci după rezolvare tace — și revine exact pentru
   originile **noi** de mâine. O alarmă care nu se stinge niciodată încetează să
   fie citită.

## 5. Ce dă azi, și ce nu

**Azi:** linia de bază. 804 URL-uri de document în registru, 316 cu amprentă
(restul nedescărcate deliberat), 24 de bănci urmărite, 10 origini terțe
verificate.

**Ce NU dă azi:** niciun diff al publicațiilor băncilor. Cele două instantanee
comparabile pe care le am (17 și 18 septembrie) sunt despărțite de propriile mele
modificări de parser — deci, prin chiar regula de la §1, nu sunt comparabile
pentru scopul ăsta.

Primul răspuns real vine la rularea următoare. Asta face ziua de azi momentul de
pornit ceasul, nu un motiv de amânare.

Calea `SCHIMBAT` e dovedită prin teste, nu prin date reale — 33 de cazuri noi în
`scripts/test_validare.py`, care acoperă toate șapte stările, clasificarea
semnalelor HTTP, refuzul comparației la parser schimbat, calea unică per URL și
protecția la scriere. **68 trecute, 0 eșuate** (erau 35 dimineață).

## 6. Rulare

```
python scripts/urmareste.py --uita-te          # doar raportează
python scripts/urmareste.py                    # compară și scrie registrul
python scripts/verifica_robots_origini.py      # robots.txt pentru originile terțe
python scripts/verifica_robots_origini.py --sterge   # șterge ce e interzis
```

`--sterge` există separat deliberat. Un script care șterge singur fișiere pe
baza unei reguli abia citite e exact felul de automatizare în care nu trebuie să
ai încredere; verdictul se citește întâi de om.

---

# Partea a doua: sonda de semnale

Recrawlarea completă a durat 56 de minute pe 16 septembrie și ar fi descărcat
316 documente ca să afle că vreo 310 sunt identice. Sonda pune aceeași întrebare
serverelor, cu cereri HEAD, fără să ia niciun octet inutil.

## Regula

> **Semnalul serverului decide *dacă* merită să ne uităm.
> Octeții decid *dacă* s-a schimbat.**

`ETag` se poate schimba fără ca fișierul să se schimbe, și un fișier se poate
schimba păstrând aceeași lungime. Deci semnalul nu e crezut pe cuvânt: unde zice
„altfel", se descarcă și se confirmă prin `sha256`.

Pasul de confirmare e ce a salvat rezultatul. Dacă aș fi crezut semnalul — cum
face orice sistem care „economisește" descărcarea — prima sondă ar fi raportat
**58 de documente schimbate la bănci.** Unul singur era.

## Trei semnale care nu semnalau

Cele trei defecte găsite au toate aceeași formă: un antet HTTP care arată ca un
validator și nu e.

| semnal | de ce nu spune nimic | descărcări inutile |
|---|---|---:|
| `Content-Length` cu `Content-Encoding: gzip` | e mărimea comprimată, nu a fișierului | 37 |
| `Last-Modified` = ora cererii | ștampilă pusă de server, nu dată de conținut | 11 |
| `ETag` Apache într-o fermă | `mărime-mtime` diferă de la nod la nod | 6 |

**Compresia.** Măsurat pe Raiffeisen:

```
HEAD implicit   Content-Encoding: gzip   Content-Length:  91.339
HEAD identity   Content-Encoding: —      Content-Length: 105.454
fișierul pe disc                                         105.454
```

Reparat cu `Accept-Encoding: identity`, plus ignorarea lungimii oricum dacă
răspunsul vine comprimat — nu toate serverele respectă cererea. Și `0` se
tratează ca absență: un PDF de zero octeți nu există.

**Ștampila.** Raiffeisen răspunde `Last-Modified: <ora cererii>` pentru 11
documente. Comparam cu momentul descărcării noastre, deci ar fi cerut descărcare
la fiecare rulare, pe vecie. Corect e față de ce a spus serverul *ultima dată* —
atunci întrebarea devine „s-a schimbat ce spune serverul despre document?".
Comparația cu ceasul nostru rămâne doar pentru prima rulare. Iar un
`Last-Modified` aflat la mai puțin de 15 minute de acum se aruncă: un validator
care se schimbă singur nu e un validator.

**ETag-ul mincinos.** Șase documente, BCR (3) și ANAF (3), cu `ETag` **tare** —
care prin standard garantează egalitatea octeților — schimbat pe fișiere
identice. Formatul le explică:

```
"269c4-6482c041c7a40"     <- mărime-mtime, formatul Apache
```

Într-o fermă de servere, `mtime` diferă de la nod la nod pentru același fișier.
Care origine pățește asta nu se poate ști dinainte — **se află din măsurătoare:**
când `ETag`-ul unei origini se schimbă pe octeți identici, sonda o notează în
registru și nu-l mai folosește acolo, căzând pe `Content-Length`. Regula se
corectează singură.

## Costul, pe trei rulări

| rulare | descărcări inutile | ce s-a reparat între ele |
|---|---:|---|
| 1 | 57 din 58 | — |
| 2 | 17 | compresia, plus comparația cu valoarea precedentă |
| 3 | **0** | ștampila și ETag-ul pe origine |

Din 316 documente: 309 `NESCHIMBAT_PROBABIL`, 7 `FARA_SEMNAL`. Cele 7 sunt toate
de la `salt.bank`, care nu trimite niciun validator — acolo nu se poate ști fără
descărcare, și **nu** sunt raportate ca neschimbate.

## Constatarea, și ce valorează

Un singur document schimbat în cele două zile — **și s-a dovedit fals, vezi
retragerea de la finalul documentului:**

```
[tbi] DECLARATIE-pe-propria-raspundere-TBI-Bank_09_2022.pdf
      76311de31cc6 -> dd44ef17ef45   (68.548 -> 68.572 octeți)
```

24 de octeți, într-o declarație pe propria răspundere. Diferența nu era o
schimbare în timp, ci între două URL-uri care își împărțeau fișierul local.
Numărul real de documente schimbate în cele două zile e **zero**.

## A treia greșeală, cea care conta

Am suprascris documentul TBI cu versiunea nouă. Deci știu **că** s-a schimbat,
dar nu mai pot spune **ce** s-a schimbat în el.

Pentru o comparație de piață, „s-a schimbat fișierul" nu valorează mai nimic
față de „prețul a trecut de la X la Y" — iar a doua are nevoie de octeții de
dinainte. Sonda păstrează acum versiunea veche în `output/crawl/pdf_istoric/`
**înainte** de suprascriere, iar registrul reține unde stă. Pe TBI e prea
târziu.

---

# Vechimea documentelor publicate

`Last-Modified` spune de când n-a mai atins banca documentul. E informație pe
care serverul o dă oricum la un HEAD și pe care o aruncam.

## Întrebarea trebuia pusă exact

Prima versiune a raportului a pus-o greșit, și ar fi mințit:

> **GREȘIT** — „cel mai vechi document de tarife al băncii".
> Băncile lasă pe site toate versiunile succesive: BRCI are „mai 2024" și „vers
> oct 2024" simultan, BCR are trei luni în paralel. Cel mai vechi document
> măsoară **adâncimea arhivei**, nu prospețimea prețurilor.

> **CORECT** — „cel mai *nou* document de tarife al băncii".
> Aia spune de când n-a mai publicat banca nimic.

Și filtrul era prea larg: căuta „taxe" în tot URL-ul, deci
`Click24Banking_PlataImpoziteTaxe.pdf` — un FAQ despre plata impozitelor prin
internet banking — ieșea drept cea mai veche listă de tarife a BCR, din 2017.
Acum se cere idiomul unei liste de tarife în **numele** fișierului, și câteva căi
(`/faq/`, `/campanii`) se exclud direct.

## O verificare independentă, gratis

Multe bănci pun data în numele fișierului. Unde ea și `Last-Modified` se
potrivesc, data nu mai e o presupunere despre server — **e confirmată de bancă:**

```
T0012-tarife-si-comisioane-standard-persoane-fizice-10-11-2025.pdf
Last-Modified: 13 nov 2025          -> concordă
```

Pe tot setul: 8 documente în care cele două date se potrivesc, 6 în care nu, 33
fără dată în nume. Unde nu se potrivesc, raportul le scrie pe amândouă, fără să
aleagă una — și diferența e adesea ea însăși informație:

```
tbi   server 2024-08-01, nume "incepand_cu_15_12_2019"
```

Adică: listă în vigoare din decembrie 2019, fișier atins în august 2024. Ambele
fapte sunt vechi.

Două rafinări au ieșit din măsurătoare, nu din presupuneri. Când numele dă doar
luna („mai 2024"), comparația trebuie făcută pe lună, nu pe ±14 zile — altfel un
fișier urcat pe 29 mai pentru versiunea „mai 2024" apărea drept dezacord. Iar
fereastra trebuie să treacă puțin înaintea lunii: e normal să publici pe 31
iulie lista care intră în vigoare pe 1 august, și BCR face exact asta.

## Ce spune tabelul

| bancă | cel mai nou | zile |
|---|---|---:|
| bcr | 2026-09-14 | 3 |
| creditcoop | 2026-09-10 | 7 |
| brd | 2026-09-01 | 17 |
| raiffeisen | 2026-08-31 | 17 |
| libra | 2026-08-25 | 23 |
| brci | 2026-08-17 | 31 |
| salt | 2026-08-03 | 45 |
| eximbank | 2026-04-08 | 162 |
| garanti | 2025-11-13 | 309 |
| techventures | 2025-11-11 | 310 |
| tbi | 2024-08-01 | 778 |
| bcrlocuinte | 2020-07-08 | **2.262** |

`Lista_de_dobanzi_si_comisioane_creditul_locativ.pdf` a BCR Locuințe e din iulie
2020 și e încă documentul curent, legat din „Informații utile". Șase ani și
două luni.

Tabelul complet, cu coloana de dovadă și avertismentele, e în
[VECHIME_DOCUMENTE.md](VECHIME_DOCUMENTE.md).

## Trei lucruri care NU se pot citi din el

1. **`Last-Modified` nu e data deciziei comerciale.** O bancă poate republica
   același conținut și data sare.
2. **Datele puse în masă nu sunt actualizări.** Când multe fișiere ale aceleiași
   bănci au *exact* aceeași dată, aceea e o migrare de site, nu o republicare
   editorială. Raportul le semnalează (bcr, creditcoop, libra).
3. **Patru documente de tarife n-au dată** (procredit, raiffeisen, salt).
   Acolo nu se poate spune nimic.

---

# Retragere: constatarea despre TBI era falsă

Sonda a raportat un document schimbat:

```
[tbi] DECLARATIE-pe-propria-raspundere-TBI-Bank_09_2022.pdf
      76311de31cc6 -> dd44ef17ef45   (68.548 -> 68.572 octeți)
```

**Nu se schimbase nimic.** Două URL-uri diferite duceau la același fișier local:

```
/2023/09/DECLARATIE-pe-propria-raspundere-TBI-Bank_09_2022.pdf   68.548 octeți
/2022/09/DECLARATIE-pe-propria-raspundere-TBI-Bank_09_2022.pdf   68.572 octeți
                              |
    output/crawl/pdf/tbi/DECLARATIE-pe-propria-raspundere-TBI-Bank_09_2022.pdf
```

Crawlul numește fișierele locale după `basename`. Sonda a descărcat unul și l-a
comparat cu amprenta celuilalt. Cei 24 de octeți sunt diferența **între două
URL-uri**, nu o schimbare în timp la unul.

Măsurat pe tot registrul: **8 căi locale folosite de 16 URL-uri** — BCR (4, prin
`cdn` față de `cdn0` și `www`), BRCI (`http` față de `https`), Salt, TBI,
TechVentures (`www` față de non-`www`).

## De ce a scăpat

Sistemul a fost construit ca să separe două cauze:

```
banca a schimbat        <- ce vrem
parserul meu a schimbat <- ce am eliminat cu amprenta pe octeți
```

Al treilea caz — **două URL-uri își împart un fișier** — nu era pe listă. E
aceeași clasă de eroare, altă față, și singura constatare pe care sistemul a
produs-o venea din el.

## Ce a expus-o

O inconsecvență, urmărită din reflex: `urmareste.py` arăta `SCHIMBAT 1` deși
sonda actualizase deja registrul. Cele două ar fi trebuit să fie de acord.

Verificând, amprenta din registru pentru primul URL era `76311d...`, iar fișierul
de pe disc avea `dd44ef...` — fiindcă descărcarea celui de-al doilea URL îl
suprascrisese. Fără urmărirea acelei nepotriviri, constatarea falsă ar fi rămas
în documentație.

## Reparat

A șaptea stare, `AMBIGUU`: când mai multe URL-uri trimit la același fișier,
octeții de pe disc aparțin celui descărcat ultimul, deci **nu se poate spune
nimic despre niciunul.**

Trei dintre cele șapte stări — `NEVERIFICAT`, `AMBIGUU`, `NEDESCARCAT` — spun
toate același lucru din trei motive diferite: *nu se poate spune*. E disciplina
din cele patru stări ale validatorului, a cincea oară în proiect.

`cale_unica(url, cale)` dă fiecărui URL fișierul lui, numit
`<sha1(url)[:8]>_<nume>`. Sonda descarcă o dată pentru cele 16, după care
ambiguitatea dispare definitiv și comparația redevine validă.

## Ce NU s-a spart

Niciunul dintre cele 8 documente care se calcă nu e listă de tarife sau formular
standardizat, deci lanțul de comisioane e neatins (427 + 4.005 valori, egal
înainte și după).

Iar pentru viitor, protecția există deja și a fost scrisă pentru alt motiv:
`parseaza_tarife.py` dedublează pe `sha256` de conținut, fiindcă băncile lasă pe
site toate versiunile succesive. Fișierul partajat rămas e byte-identic cu una
din copiile noi, deci cade acolo de la sine.

## A patra corectură a zilei

| ce am raportat | ce era |
|---|---|
| 1 document schimbat la TBI | **0** — coliziune de nume de fișier |
| 58 de descărcări necesare | 0, după trei reparații de filtru |
| vechimea, „cel mai vechi document" | răspundea la altă întrebare |
| listă de tarife BCR din 2017 | FAQ despre plata impozitelor |

Niciuna nu s-ar fi văzut fără pasul de confirmare pe octeți și fără verificarea
cifrelor care nu se potriveau. **Constatarea reală a zilei e că nicio bancă nu
și-a schimbat niciun document în două zile** — rezultatul așteptat, spus acum cu
temei.
