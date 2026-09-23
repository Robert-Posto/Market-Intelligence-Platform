# Briefing 2: ce am acoperit deja — ca să nu-l implementezi a doua oară

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 17 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

**Pentru:** colegul care implementează varianta cu BeautifulSoup
**De la:** varianta Playwright (Python)
**Data:** 17 septembrie 2026
**Continuă:** [BRIEFING_BEAUTIFULSOUP.md](BRIEFING_BEAUTIFULSOUP.md) (16 septembrie)

Briefingul de ieri era despre *acces*: robots.txt, WAF-uri, domenii greșite. Ăsta e
despre *împărțirea muncii*. Am terminat între timp câteva lucruri pe care ieri le
aveam doar în plan, iar dacă le refaci pierzi zile fără să câștigăm nimic.

Structura: §1 ce e gata (nu implementa) · §2 unde ești tu mai bun (ia-l tu) · §3
capcane care nu depind de unealtă (te lovesc oricum) · §4 schema comună · §5 ce
primești în arhivă.

---

## 1. GATA — nu implementa

### 1.1 Toate PDF-urile: 4.445 de comisioane din 40 de documente

Ieri aveam 320 de PDF-uri descărcate și neparsate, iar recomandarea mea era să
țintești documentele standardizate. **Le-am făcut pe amândouă.**

| sursă | documente | valori | cod |
|---|---|---|---|
| formularul standardizat (Legea 258/2017) | 16 | 430 | `crawler/parser_pdf.py` |
| liste proprii de tarife | 24 | 4.015 | `crawler/parser_tarife.py` |

Ieșirea e în `output/comisioane_pdf.json` și `output/comisioane_tarife.json`, cu
schema din §4. **12 bănci** în total: 5 în formularul standardizat (BCR,
CreditCoop, BRCI, Libra, ProCredit) și 10 în listele de tarife (BCR, Libra, BRD,
BRCI, Raiffeisen, EximBank, Salt, Garanti, TBI, BCR Locuințe).

Dacă ai de gând să iei `pdfplumber` sau `PyPDF` — nu. Ia JSON-ul. Ce e util de
știut despre calitatea lui e în §3.6.

**Un singur PDF din 320 e scan** (`Click24Banking_PlataImpoziteTaxe.pdf`). 97% au
text extractibil, deci OCR nu ne trebuie niciunuia.

### 1.2 Dedublarea versiunilor de document

Băncile lasă pe site toate versiunile succesive. BCR are lista de tarife PJ în
trei versiuni (martie, iulie, august 2026), BRCI are PF și PJ în câte două,
Raiffeisen același document sub două nume. Din 31 de documente candidate, **6 erau
duplicate** — fără dedublare, aceleași tarife intră de trei ori și dublează orice
număr raportăm.

Logica e în `scripts/parseaza_tarife.py` (`dedubleaza`): amprentă SHA-256 pentru
identice, apoi grupare pe familie de nume cu data eliminată, păstrând cea mai
nouă. Merge pe orice listă de fișiere, nu depinde de Playwright.

### 1.3 Indicii de referință BNR + regula de calendar IRCC

`output/bnr_indici.json`, actualizat. ROBID/ROBOR pe 7 scadențe, serii zilnice;
IRCC trimestrial și zilnic; curs de referință.

**Partea care nu e evidentă și pe care ai nevoie să o iei de-a gata:** BNR
etichetează valorile IRCC după trimestrul în care s-au *calculat*, dar valoarea se
*aplică* începând cu prima zi a **celui de-al doilea** trimestru următor (OUG
19/2019). Deci `2026T1 = 5,56%` nu e indicele lui ianuarie–martie 2026, ci al lui
**1 iulie – 30 septembrie 2026**. Trei bănci confirmă independent asta pe
paginile lor (EximBank, Nexent, BCR).

Fără regula asta compari greșit și declari „învechit" ce e corect, sau invers.
Implementarea: `crawler/bnr_indici.py`, funcțiile `perioada_aplicare`,
`ircc_in_vigoare`, `ircc_pentru_perioada`.

### 1.4 Validatorul și marcajul de încredere

`crawler/validator.py` — **Python curat, fără Playwright, fără dependențe de
crawler.** Îl poți importa direct pe datele tale.

Șase verificări: validare încrucișată cu BNR, invarianți (DAE ≥ nominală),
intervale de plauzibilitate, format zecimal ambiguu, indice implicit
(total − marjă), perioada de valabilitate declarată pe pagină.

Ieșirea nu e binară. Sunt **trei** stări, iar a treia e cea care contează:
„extras corect", „extras greșit" și **„extras corect, dar sursa băncii e
învechită"**. Pe cele 555 de valori ale noastre: 545 OK, 10 `SURSA_VECHE`.
Încredere: 549 ridicată, 4 medie, 2 scăzută.

35 de teste în `scripts/test_validare.py`, toate trec.

### 1.5 Etalonul manual pentru partea web

`output/etalon_manual.json` — **38 de valori verificate de mână**, o dată,
păstrate ca referință fixă. Eșantion stratificat cu sămânță, deci reproductibil.

Rezultatul e fix cel care ne interesează pe toți trei:

| | |
|---|---|
| valoarea extrasă corect | **38 / 38** |
| tipul (nominală / DAE / marjă / comision) corect | 33 da, 3 nu, 2 imprecis |
| verdictul validatorului corect | 37 / 38 |

Fiecare intrare are o notă cu ce e în neregulă. Sunt cele mai utile 20 de rânduri
din tot proiectul — citește-le înainte să scrii parserul, sunt exact capcanele
semantice. Câteva:

- `bcr`: „10% e scenariul median al exemplului reprezentativ, nu rata oferită
  (oferta e 5,79–14,99%)"
- `nexent`: „«până la 6,75%» — plafon, nu rată efectivă"
- `libra`: „0,59% apare identic pe trei niveluri de pachet; nivelul nu e păstrat"
- `vista`: „6% e rata FIXĂ pe 3 ani, nu o marjă"
- `patria`: „coloana a doua a aceluiași rând (DAE 26,29%) nu a fost extrasă"

**Nu-l reface.** Folosește-l ca referință comună — dacă măsurăm toți pe aceleași
38 de valori, cifrele devin comparabile.

### 1.6 Matcherul robots.txt

Era deja în briefingul de ieri, dar îl repet fiindcă e singurul lucru pe care
**trebuie** să-l iei: `crawler/robots.py`, conform RFC 9309, cu `*`, ancoră `$` și
precedență pe cel mai lung model.

`urllib.robotparser` din biblioteca standard face doar potrivire pe prefix, deci
ratează complet `Disallow: *.pdf` de la ING. Rezultat: descarci sistematic
documente interzise explicit, fără nicio eroare. Teste:
`scripts/test_robots_matcher.py`.

---

## 2. AL TĂU — aici ești mai bun decât noi

Nu e politețe: sunt locuri unde `requests` + BeautifulSoup e unealta potrivită și
Playwright e risipă.

### 2.1 Cel mai valoros lucru pe care îl poți face: lărgirea descoperirii

**Asta e lacuna noastră reală și e a ta cu totul.**

Băncile cu sitemap ne-au dat 315–2.559 URL-uri. Cele **14 fără sitemap**, unde
mergem pe navigare, doar **19–117** — fiindcă ne uităm doar la link-urile din
homepage, un singur nivel. Nu e o limitare a extractorului, e una a descoperirii.

Dovada că acolo se pierd date, nu că nu există: `patriabank.ro/curs-valutar`
răspunde 200 OK, dar nu e în sitemap-ul lor de 624 de URL-uri, deci nu l-am găsit
niciodată. Cursul valutar propriu e acoperit la doar **5 din 23** de bănci, din
cauza asta.

Un crawl BFS pe 2–3 niveluri, cu `requests`, e ieftin la tine și scump la noi
(fiecare pagină costă o randare de browser). Dacă îmi dai doar **lista de URL-uri
descoperite**, fără extragere, e deja un câștig mare — le dăm noi prin randare pe
cele care au nevoie.

### 2.2 Tabelele HTML reale

Determinist, rapid, fără cost per token. Unde sunt:

| bancă | tabele |
|---|---|
| eximbank | 115 |
| nexent | 101 |
| procredit | 47 |
| patria | 30 |
| brci | 24 |
| garanti | 20 |

### 2.3 BNR curs valutar — XML, fără browser

`curs.bnr.ro/nbrfxrates.xml` și istoricul pe ani
`curs.bnr.ro/files/xml/years/nbrfxrates2026.xml`. Feed oficial, gândit pentru
consum automatizat.

**Dar nu paginile de ROBOR și IRCC** — alea au nevoie de JavaScript (§2.4).

### 2.4 Ce vei obține ZERO, și e comportamentul corect

Nu-ți pierde timpul, și nu-l trata ca bug:

- **Credex** — 21 de pagini, 0 cu date. Ratele sunt doar în simulatorul JS.
- **Revolut** — 0 tabele, totul în grile React.
- **BCR, paginile de credit** — 0 tabele, dar 12 linii cu rate în textul randat.
- **BNR, paginile de indici** — tabelele se încarcă prin JS. Noi am ratat asta
  inițial: am căutat „ROBOR" în HTML-ul brut, am găsit 0 și am concluzionat că
  informația nu e pe site. **Metoda de verificare era greșită, nu concluzia
  despre site.** Ia valorile din `output/bnr_indici.json`.

---

## 3. Capcane care NU depind de unealtă

Astea te lovesc identic în HTML. Le-am plătit deja, fiecare o dată.

### 3.1 Pluralul românesc nu e un sufix

`"comisioane"` **nu** conține `"comision"` — e `comisio-ane` vs `comisio-n`.

Am scris un tipar de căutare cu forma de singular, n-a potrivit niciun nume de
fișier, iar un `except Exception: continue` a ascuns și cauzele. Descoperirea
raporta liniștit „zero documente". Rădăcina corectă e `comisio`.

Aceeași capcană la „taxă/taxe", „dobândă/dobânzi", „tarif/tarife".

### 3.2 Pragurile nu sunt prețuri

Cea mai productivă sursă de valori false. Toate formele următoare sunt **benzi de
sumă**, nu comisioane:

```
0 – 49.999 Lei        peste 50.000 Lei       ≤ 1.500 LEI
> 20.000 LEI          >=12.000 lei           sume < 1.000,00 EUR
intre 1.000,00 99.999,99 EUR
```

La noi erau **149 de praguri raportate ca preț** (3,6% din valorile listelor de
tarife) înainte de reparație. Și le-am prins în două runde: prima versiune
acoperea cuvintele („peste", „sub", „până la") și simbolurile simple, dar nu `>=`
și `<=` — simbolul urmat de `=`.

Ruda lor din HTML, pe care o știi deja din briefingul de ieri: `avans de minim 5%`
— procentul e avansul, nu rata.

**Nu le arunca, mută-le în `conditie`.** Banda e informația care spune *când* se
aplică comisionul.

### 3.3 Nu tot ce e într-o listă de tarife e un comision

În același document, în același tabel, amestecate: comisioane, rate de dobândă,
limite de tranzacționare, cursuri de schimb, taxe către bugetul de stat.
Verificarea de mână a găsit de trei ori valori din alte categorii raportate ca
preț: `Valoare tranzactii POS / zi 10.000 Lei` (limită),
`Dobanda aferenta descoperitului de cont neautorizat: 50% pe an` (dobândă).

Soluția e un câmp `categorie`, nu un filtru care aruncă. La noi: 3.929
comisioane, 49 limite, 33 dobânzi, 4 cursuri.

### 3.4 Frecvența se scrie cu bară, nu în cuvinte

Tiparul meu cerea „lunar", „anual". Documentele scriu `5 lei/lună`, `1% /an`,
`min. 1 LEI/tranzacție`, `20 lei / document` — adică exact forma cea mai folosită
lipsea. După reparație, setul standardizat a câștigat **81 de frecvențe „pe
operațiune"** care se pierdeau în silențiu.

Atenție și la `anuală`: în Python, `\banual\b` **nu** potrivește în „anuală",
fiindcă `ă` e caracter de cuvânt.

### 3.5 Vechimea nu se detectează după mărime

Cea mai importantă de aici, și e contraintuitivă.

Prima mea versiune compara IRCC-ul de pe site cu cel de la BNR și accepta o
toleranță. **Nu funcționează:** trimestre IRCC consecutive diferă cu 0,02 puncte
procentuale (5,58 → 5,56). Orice toleranță rezonabilă e mai mare decât diferența,
deci o valoare expirată trece drept confirmată. Exact asta a pățit validatorul meu
cu BRD: a declarat „confirmat cu BNR" o valoare de trimestrul anterior.

**Criteriul corect: potrivire exactă cu un trimestru BNR încheiat.** Nu „diferă
mult de cel curent", ci „este identic cu unul expirat". Reparația a prins automat
și BRD și Libra, care nu-și actualizaseră notele.

Test bun de referință: **Garanti afișează IRCC 4,06%** — valoare reală, corectă în
2020. Pagina promite că indicele „se actualizează la 1 ianuarie, 1 aprilie, 1
iulie și 1 octombrie". Nu s-a actualizat de șase ani. Dacă parserul tău scoate
4,06 de la Garanti, e **corect** — datele băncii sunt vechi.

### 3.6 Precizia și acoperirea sunt două măsurători, nu una

Asta e concluzia de care depinde comparația noastră, deci merită insistența.

Cifrele de volum („555 de valori", „4.015 valori") măsoară **prezența, nu
corectitudinea**. Iar precizia și acoperirea pot merge în direcții opuse pe
aceeași pagină:

| | web (555 valori) | tarife PDF (4.015 valori) |
|---|---|---|
| valoarea corectă | 38/38 verificate de mână | 70/72 verificate de mână (97%) |
| acoperirea pe pagini dense | ~61% | nemăsurată |
| eticheta corectă | 33/38 tipul | **20/44 curate (45%)** |

Deci: **valorile sunt aproape perfecte, etichetele nu.** La noi eticheta de
serviciu e curată la 45% din valorile din liste — de la 100% pe tabele simple de
două coloane, până la 32% pe ghidul de credite BRD.

Și toate greșelile rămase au o cauză unică: când un tabel are 9 coloane și numele
serviciului se rupe pe trei rânduri, lucrăm în ordinea de citire, nu pe poziții
verticale. **Dacă în HTML ai `<td>`-uri, tu nu ai problema asta deloc** — și
acolo o să ne baţi clar. Merită să ne uităm împreună la ce iese, sunt curios cât
din avantaj se păstrează.

Cum am măsurat, dacă vrei să faci la fel: eșantion stratificat cu sămânță (câte o
valoare din fiecare document), verificat de mână cu contextul paginii alături;
reparațiile făcute pe primul eșantion, măsurarea pe al doilea și al treilea, pe
cod nemodificat după. Altfel îți verifici reparațiile pe cazurile după care le-ai
făcut. `scripts/etalon_tarife.py` generează eșantionul cu tot cu context.

### 3.7 Mecanismele care înghit eșecuri

Patru din erorile mele de ieri și trei de azi au fost **tăcute**, și toate au avut
același ajutor: un `except Exception` care raporta „document problematic", un
`grep` al meu care filtra exact linia de eroare, un prag care trecea în silențiu.

Cea mai scumpă: un `NameError` dintr-o refactorizare a fost prins de un
`except Exception`, iar **177 de comisioane au dispărut fără nicio alarmă**
(430 → 253). Am prins-o doar pentru că urmăream totalul.

Recomandarea concretă: afișează mesajul complet al excepției, nu doar tipul, și
pune un avertisment explicit când un total e incomplet. Și numără zerourile — la
noi, din 347 de valori „nominale", 82 erau zero, iar 77 din ele erau promoții
„rate fără dobândă", nu rate de dobândă.

---

## 4. Schema comună — propunere

Ca să putem pune rezultatele noastre unul lângă altul fără muncă de traducere.
Dacă ai deja altă schemă, spune-mi și convertesc eu.

**Rate și dobânzi** (`output/rate_tipizate.json`, 555 de valori):

```json
{
  "banca": "bcr",
  "categorie": "credite",          // credite|conturi_carduri|depozite|business|comisioane|dobanzi|curs_valutar
  "produs": "Credit George",
  "tip_rata": "dae",               // nominala|dae|marja_ircc|marja_euribor|marja_fixa|
                                   // ircc_valoare|robor_valoare|euribor_valoare|
                                   // comision_procent|rate_fara_dobanda|cashback
  "valoare": 13.9,
  "moneda": null,
  "perioada": null,
  "nr_rate": null,
  "incredere": "ridicata",
  "sursa_url": "https://...",
  "text_sursa": "..."              // obligatoriu: fara el nu se poate verifica nimic
}
```

Distribuția noastră pe `tip_rata`: nominala 286, rate_fara_dobanda 78,
comision_procent 52, marja_ircc 45, dae 36, cashback 16, marja_fixa 16,
ircc_valoare 13, euribor_valoare 6, marja_euribor 4, robor_valoare 3.

**Comisioane** (`comisioane_pdf.json`, `comisioane_tarife.json`):

```json
{
  "banca": "libra",
  "sectiune": "4.2. PLĂȚI > A. În lei",   // ierarhia de titluri
  "serviciu": "Transfer credit intrabancar",
  "coloana": "Pachet Gold",               // numele coloanei in tabele matriceale
  "tip": "comision_suma",                 // comision_suma|comision_procent|gratuit
  "valoare": 15.0,
  "moneda": "LEI",
  "frecventa": "lunar",
  "conditie": "0 – 49.999 lei",           // banda de suma, nu prețul
  "rol": "min",                           // plafon al unui comision procentual
  "categorie": "comision",                // comision|dobanda|limita|curs
  "sursa_pdf": "libra/Tarife_si_Comisioane_PF.pdf",
  "pagina": 5,
  "text_sursa": "0,1% min. 15 EUR, max. 500 EUR"
}
```

Trei câmpuri pe care te rog să le păstrezi chiar dacă schimbi restul:
**`text_sursa`** (fără el nicio verificare nu e posibilă), **`sursa_url`/`pagina`**
și **`categorie`**.

---

## 5. Ce e în arhivă

```
crawler/          modulele. Cele independente de Playwright:
                    robots.py        matcher RFC 9309        ← ia-l
                    validator.py     cele 6 verificari       ← ia-l
                    bnr_indici.py    regula de calendar IRCC ← ia-l
                    parser_rate.py   tipare pentru rate din text
                    parser_pdf.py    formularul standardizat
                    parser_tarife.py listele de tarife
scripts/          rulare, verificare, eșantioane, teste
output/*.md       cele 5 documente, inclusiv briefingul de ieri
output/*.json     datele: rate, comisioane, indici BNR, etalonul manual
```

`crawler/main.py` și `extractor.py` depind de Playwright, restul nu.

---

## 6. Ce aș vrea de la tine

1. **Lista de URL-uri descoperite** pentru cele 14 bănci fără sitemap (§2.1). E
   cel mai mare câștig și e exact unde unealta ta e mai bună.
2. **Acord pe cele 15–20 de URL-uri de referință** — propunerea din briefingul de
   ieri, §9, rămâne. Cu etalonul manual de 38 de valori (§1.5) avem deja cu ce
   măsura precizia, nu doar volumul. Fără listă comună comparăm euristici de
   selecție a paginilor, nu extractoare.
3. **Spune-mi dacă schema din §4 îți convine** sau ce ai schimba.
4. **Zi-mi dacă găsești erori în ce am trimis.** Etalonul manual e judecata mea pe
   38 de rânduri; dacă nu ești de acord cu vreo notă, aia e exact discuția utilă.
