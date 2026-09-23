# Briefing: crawling date bancare publice — ce am aflat cu Playwright

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 16 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

**Pentru:** colegul care implementează varianta cu BeautifulSoup
**De la:** varianta Playwright (Python)
**Data:** 16 septembrie 2026

Scopul: să nu pierzi timp pe lucrurile pe care le-am lovit deja și să avem o bază comună
de comparație. Tot ce scrie aici e verificat practic, nu presupus.

---

## 1. Ce extragem (cerința comună)

**2.1 Produse & prețuri:** conturi curente, pachete, carduri debit/credit · credite
(nevoi personale, ipotecar, Noua Casă, refinanțare, overdraft) · IMM & corporate
(credite, factoring, leasing, cash management) · depozite & economii · comisioane
(PDF-urile "Tarife și comisioane")

**2.2 Rate & indicatori:** dobânzi (nominală, DAE, marjă peste IRCC/EURIBOR) · curs
valutar propriu + referință BNR · indici de referință (IRCC, ROBOR, EURIBOR)

---

## 2. PRIORITATE MAXIMĂ: trei capcane care te vor lovi direct

Toate trei produc **conformitate aparentă, dar falsă** — nu dau erori, doar rezultate
greșite. Prima te afectează aproape sigur.

### 2.1 `urllib.robotparser` NU înțelege wildcard-uri

Modulul standard din Python face doar potrivire pe prefix. Implementarea internă e
literalmente `filename.startswith(self.path)`.

ING are în robots.txt:

```
User-agent: *
Disallow: *.pdf
Disallow: *.xml
Disallow: *.xlsx
```

Cu `robotparser`, modelul `*.pdf` devine prefix literal, iar
`"/dam/doc/lista.pdf".startswith("*.pdf")` este **mereu fals**. Rezultatul: interdicția
e ignorată complet și descarci sistematic documente interzise explicit, convins că
respecți regulile.

**Soluția:** matcher propriu conform RFC 9309, cu suport pentru `*`, ancora finală `$`
și precedența pe cel mai lung model (Allow câștigă la egalitate). Al nostru e în
`crawler/robots.py`, cu teste în `scripts/test_robots_matcher.py`. E independent de
Playwright — îl poți folosi direct.

**Efectul corect:** la ING trebuie să obții "378 PDF-uri găsite, 0 descărcate, 114
sărite pe motiv de robots.txt". Dacă descarci PDF-uri de la ING, ai bug-ul.

### 2.2 robots.txt servit ca `text/html`

BCR îl servește cu content-type `text/html`. Dacă îl citești prin text randat sau prin
ceva care normalizează spațiile, liniile se colapsează într-una singură:

```
'User-agent: * Allow: / User-agent: GPTBot Allow: / User-agent: ClaudeBot Allow: / ...'
```

Rezultat: **0 reguli parsate**. Iar "0 reguli" e indistingibil de "fără restricții", deci
ai crawla inclusiv căile interzise (`/search`, `/*.compare`).

**Soluția:** folosește corpul brut al răspunsului, niciodată text randat. După corectare,
BCR a trecut de la 0 la **24 de reguli**.

Cu `requests` + BeautifulSoup probabil eviți asta din start — dar verifică explicit că
numărul de reguli parsate e diferit de zero pentru fiecare domeniu.

### 2.3 robots.txt care declanșează descărcare

Raiffeisen îl servește cu antet de tip attachment. Navigarea în pagină eșuează cu
"Download is starting". La tine probabil merge din prima, la noi a necesitat un canal
alternativ de citire.

**Verificare obligatorie:** loghează starea robots.txt pentru fiecare domeniu și tratează
"necitit" diferit de "fără restricții". Nu presupune permisiune din eșec.

---

## 3. Sursele: ce merge, ce nu

### Blocate complet (403, orice unealtă — și curl, și browser)

| Bancă | Detaliu |
|---|---|
| **Banca Transilvania** | WAF, pagină brandată "Acces blocat", răspuns identic (3.955 octeți) pe toate URL-urile |
| **UniCredit** | WAF de grup, mesaj de eroare în croată |
| **Intesa Sanpaolo** | Akamai (`errors.edgesuite.net`) |

Nu pierde timp. **Nu încerca să le ocolești** — ar fi forțarea unei protecții active a
altei instituții financiare. Pentru datele lor: cerere formală sau consultare manuală.

### Interzis prin robots.txt — de exclus

**Banque Banorient** (`banorientfrance.com`) permite explicit doar motoare de căutare
numite (Googlebot, bingbot, yandex, slurp), iar pentru orice alt agent:

```
User-agent: *
Disallow: /
```

L-am exclus din crawler. Recomand să rămână exclus.

### Inaccesibile din motive tehnice

- **PKO Bank Polski** (`pkobp.pl`) — timeout TCP. Verificat și din altă rețea
  (infrastructura Anthropic): `ECONNRESET`. Nu e rețeaua noastră.
- **Citibank RO** — domeniu abandonat (Citi a ieșit din retail-ul românesc)

### Domenii greșite — verifică ÎNTÂI domeniul

Două "blocaje" s-au dovedit domenii greșite. E cel mai ieftin control și cel mai
costisitor de omis.

- **`bt.ro` NU este Banca Transilvania.** E site-ul firmei "Bucuresti-Tokyo Impex S.R.L."
  — pagină veche, fundal negru, hartă a Asiei, titlu "Bucuresti - Tokyo". Domeniul real:
  `bancatransilvania.ro`. Un crawl pe `bt.ro` reușește tehnic și întoarce 3 link-uri
  irelevante, fără nicio eroare.
- **`credexbank.ro` NU este site-ul Credex.** Handshake TLS se stabilește, apoi serverul
  cere renegociere în buclă și nu răspunde niciodată. Domeniul real: **`credex.ro`**
  (atenție: e **IFN**, nu bancă — "CREDEX IFN", grupul Altex).

### Atenție la www vs fără www

- `www.ing.ro/robots.txt` → **403**
- `ing.ro/robots.txt` → **200**, cu reguli importante (vezi 2.1)

Iar URL-urile reale ING au segmente cu majuscule: `/imm/Economii/depozite-la-termen`.
Ghicirea lor dă 404.

### Revolut: verifică locale-ul

`revolut.com` fără sufix servește versiunea **din UK**. Corect: `revolut.com/en-RO/`
(există și `/ro-RO/`). Ambele răspund 200 OK, deci greșeala e silențioasă.

### curl blocat nu înseamnă site blocat

**Cetelem:** robots.txt prin curl întoarce o pagină WAF "Request Rejected" (semnătură F5,
cu support ID). Prin browser, același fișier se citește normal și e permisiv. Verifică
ambele canale înainte de a declara un site blocat.

### Un eșec punctual nu dovedește o politică permanentă

Am concluzionat inițial că **BNR blochează automatizarea de browser** (Playwright primea
`ERR_CONNECTION_CLOSED`, în timp ce curl primea 200 OK). **Era greșit.** La re-testare
peste câteva ore funcționa normal. Blocajul era tranzitoriu — foarte probabil limitare de
rată provocată de propriile noastre cereri rapide din faza de diagnostic.

Un blocaj temporar arată identic cu unul definitiv. Re-testează înainte de a concluziona.

### Permisiune explicită pentru agenți AI

BCR, BRD și Libra au reguli explicite în robots.txt. BCR și BRD au chiar comentariul
literal `# Allow agentic-AI users`, urmat de `Claude-User`, `ChatGPT-User`,
`Perplexity-User`, `OAI-SearchBot`.

Distincția pe care o fac: **crawlere de antrenament** (`GPTBot`, `ClaudeBot`,
`Google-Extended`, `CCBot`) vs **agenți la cerere** (`*-User`). Merită respectată.

**Patria Bank** blochează explicit doar crawlerele de antrenament, dar regula generală
`User-agent: *` e `Disallow:` gol (permite tot), cu `Crawl-delay: 5` și interdicții pe
`/d/`, `/r/`, `/content/`, `/nav/`. Interpretarea noastră: refuză colectarea de corpus,
nu accesul la cerere. Am respectat `Crawl-delay: 5`.

---

## 4. Unde BeautifulSoup câștigă și unde pierde

Partea relevantă pentru comparația noastră. **Accesul și extragerea sunt două probleme
separate**, iar ordinea se inversează în funcție de sursă.

### Vei câștiga clar: pagini cu tabele HTML reale

Determinist, rapid, fără cost per token. Tabele găsite de noi:

| Bancă | Tabele |
|---|---|
| eximbank | **115** |
| nexent | **101** |
| procredit | 47 |
| patria | 30 |
| brci | 24 |
| garanti | 20 |

### Vei obține ZERO: conținut randat prin JavaScript

- **Credex** — 21 de pagini accesate, **0 cu date**. Ratele sunt exclusiv în simulatorul JS.
- **Revolut** — 0 tabele HTML, totul în grile React. Datele există (dobândă 4,25% p.a.,
  cashback 0,4–1%, comision 2% fair usage), dar numai după randare.
- **BCR, paginile de credit** — 0 tabele, dar 12 linii cu rate în textul randat.
- **BNR, paginile de indici** — vezi secțiunea 5.

Test de referință bun: dacă pe `credex.ro` obții zero, e comportamentul așteptat, nu un bug.

### Vei avea nevoie de LLM: rate în text liber

Linii cu rate în proză, nu în tabel:

| Bancă | Linii cu rate |
|---|---|
| raiffeisen | 107 |
| libra | 95 |
| tbi | 75 |
| bcr | 67 |
| ing | 58 |

Exemplu real de la BCR:

```
dobândă minimă (cu toate reducerile incluse): 5,79%, Rată fixă: 619 lei/lună
(include costul lunar cu asigurare: 42 lei); Valoare totală plătibilă: 37.xxx lei; DAE=13,90%
```

Un regex găsește valorile. Normalizarea lor în câmpuri (produs, dobândă nominală, DAE,
rată lunară, cost total, condiții) e altă problemă.

### Unde requests e mai bun decât browserul

- **BNR curs valutar** — feed XML oficial, gândit pentru consum automatizat. Fără browser.
- **Sitemap-uri** — cereri simple, fără randare.

---

## 5. Câștig important: indicii de referință se iau central de la BNR

Nu-i mai căuta prin site-urile băncilor, unde apar inconsecvent și adesea doar ca marjă
("IRCC + 2,3%"), nu ca valoare. BNR îi publică centralizat, în tabele structurate:

| Ce | URL |
|---|---|
| ROBID/ROBOR, serii zilnice, 7 scadențe | `bnr.ro/1973-ratele-medii-ale-dobanzilor-pe-piata-monetara-interbancara` |
| IRCC trimestrial + zilnic | `bnr.ro/1974-indicele-de-referinta-pentru-creditele-consumatorilor` |
| Curs de referință (XML) | `curs.bnr.ro/nbrfxrates.xml` |
| Curs, istoric pe ani (din 2005) | `curs.bnr.ro/files/xml/years/nbrfxrates2026.xml` |

Valori verificate la 16.09.2026: ROBOR O/N 5,64% · 1M 5,74% · **3M 5,84%** · 6M 5,92% ·
12M 5,98%. IRCC în vigoare **2026T1 = 5,56%**.

**ATENȚIE:** paginile de ROBOR/IRCC au nevoie de JavaScript. Cu requests + BeautifulSoup
**nu vei obține tabelele.** Noi le-am ratat inițial exact din acest motiv: am căutat
"ROBOR" în HTML-ul brut luat cu curl, am găsit 0 rezultate și am concluzionat greșit că
informația nu există pe site. **Metoda de verificare era greșită, nu concluzia despre
site.** Pentru aceste două pagini îți trebuie un browser, sau ia valorile de la noi.

Cursul valutar (XML) merge perfect cu requests.

---

## 6. Ce acoperire am obținut

23 de surse, maximum 32 de pagini pe bancă, zero erori aproape peste tot.

| Bancă | Cerințe acoperite (din 23) | PDF descărcate |
|---|---|---|
| eximbank | **20** | 16 |
| raiffeisen | **19** | 69 |
| bcr | **18** | 72 |
| brd | 17 | 159 |
| patria | 17 | 1 |
| garanti | 16 | 58 |
| ing | 15 | 1 (114 sărite — robots.txt) |
| libra | 15 | 74 |
| nexent | 14 | 44 |
| procredit | 14 | 65 |
| tbi / vista | 8 | 79 / 30 |
| salt / brci / revolut / techventures | 5–6 | 22 / 29 / 17 / 159 |
| credex / creditcoop | 4 | 21 / 19 |
| bcrlocuinte / cetelem | 3 | 11 / 0 |
| bid | 2 | 1 |
| **bnpparibas / bankofchina** | **0** | 0 |

### Lipsuri care NU sunt vina codului

- **Leasing** (4/23) — se face prin entități separate, pe alte domenii:
  `unicreditleasing.ro` (200 OK), `raiffeisen-leasing.ro` (200 OK), `btleasing.ro` (403).
  BCR nu are pagină de produs pentru leasing, doar mențiuni pe blog.
- **Cash management** (2/23) — serviciu corporate, pe portaluri separate
- **Rate depozite** (4/23) — publicate în PDF, nu în pagină
- **BNP Paribas, Bank of China** — 0 pagini de produs retail. Sucursale corporate.
  Exclude-le, nu au ce oferi.
- **CREDITCOOP, BCR Locuințe, BID** — gamă restrânsă prin natura instituției

### Lipsuri care SUNT reparabile (le avem în plan)

- **Curs valutar propriu doar 5/23.** Dovada că e lacună de descoperire, nu absența
  datelor: `patriabank.ro/curs-valutar` există și răspunde 200 OK, dar nu e în sitemap-ul
  lor (624 URL-uri), deci nu l-am găsit.
- **Descoperirea e îngustă la 14 bănci.** Cele cu sitemap au dat 315–2.559 URL-uri; cele
  fără, unde mergem pe navigare, doar **19–117**. Navigarea se uită doar la link-urile din
  homepage, un singur nivel.

---

## 7. Calitatea datelor: ce am aflat făcând validare

Partea cea mai importantă, și probabil cea care ne va diferenția rezultatele.

### Metricile de volum înșală

Numerele de tip "721 linii cu rate" măsoară **prezența, nu corectitudinea**. Validarea
arată că doar **377 (52%)** produc o valoare interpretabilă. Iar dintre acelea, multe nu
sunt rate de dobândă.

Exemple reale de linii extrase, toate "valide" după criterii de volum:

- `[libra/depozite]` "credit pentru mașini electrice, cu dobândă fixă 7,81%" — e rată de
  **credit**, clasificată la **depozite**
- `[tbi/depozite]` "poți beneficia de dobândă de 20%" — tot credit, la depozite. Un
  depozit cu 20% ar fi absurd
- `[eximbank/credite]` "avans de minim 5%" — procentul e **avans**, nu rată
- `[brd]` "10% / 16% din dobânda brută" — e **impozitul pe venitul din dobândă**
- `[revolut]` "5.50% p.a." — valoare fără niciun context. Care produs?
- `[bcr]` "100% on[line]" — nu e nicio rată

### Capcana cea mai periculoasă: "IRCC + 2,1%" vs "IRCC = 5,56%"

Un parser naiv citește `2,1` ca valoarea IRCC, deși e **marja**. Distincția dintre valoare
și marjă e semantică, nu sintactică. Verifică explicit asta — noi am avut eroarea.

### Format zecimal: risc de eroare de factor 1000

39 de linii amestecă virgulă și punct. Revolut are `0,4%` **și** `0.5%` pe aceeași
pagină, plus `20,000 EUR` în format englez de mii. Un parser care presupune un singur
format transformă `20,000` în 20,0.

Regula pe care o folosim: dacă apar ambele separatoare, ultimul e cel zecimal.

### Validarea încrucișată prinde ce nimic altceva nu prinde

Comparând IRCC de pe site-uri cu BNR (5,56%):

| Bancă | Pe site | Verdict |
|---|---|---|
| BCR | 5,56% | potrivit |
| Libra | 5,56% | potrivit |
| BRD | 5,58% | trimestrul anterior |
| **Garanti** | **4,06%** | **învechit din 2020** |

Cazul Garanti merită atenție: pagina afirmă că indicele "se actualizează la fiecare
1 Ianuarie, 1 Aprilie, 1 Iulie și 1 Octombrie", dar singura dată calendaristică de pe
pagină e **08.07.2020**. Valoarea era corectă în 2020.

**Extragerea era corectă; datele băncii sunt vechi de șase ani.** Nicio îmbunătățire a
parserului nu ar fi găsit asta — doar comparația cu o sursă independentă.

Concluzia operațională: trebuie să distingem trei stări, nu două — "extras corect",
"extras greșit" și **"extras corect, dar sursa e învechită"**.

### Invarianți matematici utili

- **DAE ≥ dobânda nominală** (DAE include comisioanele — garantat matematic). Verificat pe
  5 cazuri cu ambele valori în aceeași linie, toate consistente.
- **Curs valutar: cumpărare < referință BNR < vânzare.** Dacă nu se respectă, ori ai
  extras greșit, ori ai confundat coloanele.

---

## 8. Ce urmează: planul de verificări

Ne apucăm de validare sistematică. Etapele:

1. **Strat de interpretare în câmpuri tipizate.** Momentan extragem linii de text, deci
   nu există validare pe câmp — nu există câmpuri. Ținta:
   `{banca, produs, tip_rata: nominala|DAE|marja, valoare, moneda, valabil_de_la, sursa_url}`
2. **Etalon manual fix** — 30–40 de valori verificate de mână o singură dată, păstrate ca
   referință. Orice rulare se compară cu ele.
3. **Verificări automate la fiecare rulare** — validare încrucișată cu BNR, invarianți
   (DAE ≥ nominală), intervale de plauzibilitate, detectare de format zecimal ambiguu.
   Validatorul există deja: `scripts/valideaza.py`
4. **Diferență între rulări** — comisioanele nu se schimbă zilnic, cursul valutar da.
   Orice abatere de la asta e suspectă.
5. **Marcaj de încredere pe fiecare valoare** — "confirmată cu BNR" / "doar extrasă" /
   "sursă posibil învechită"
6. **Parsarea PDF-urilor** — avem **320 de documente unice** descărcate (217 MB),
   neparsate. Acolo e cea mai densă informație despre comisioane. Nota: cifrele
   "descărcate" din tabelul de la secțiunea 6 numără evenimente de descărcare, iar
   același document e adesea linkat din mai multe pagini — de aceea suma lor (~1.000)
   e mai mare decât numărul de fișiere unice.

### Un câștig legal pentru partea de comisioane

**Legea 258/2017** (transpunerea Directivei europene PAD 2014/92/UE) obligă băncile să
publice un **"Document de informare cu privire la comisioane"** în **format prescris**, cu
terminologie standardizată la nivel național.

Le-am văzut la BCR: "Document de informare cu privire la comisioane Cont George",
"cont EUR BCR", "Pachet George". Fiind format impus prin lege, **un singur parser
funcționează la toate băncile** — spre deosebire de PDF-urile de tarife generale, fiecare
altfel structurat.

Recomandare: țintește specific aceste documente, nu PDF-urile generice de tarife.

Aceeași lege obligă ANPC să asigure existența unui site de comparare a comisioanelor. Nu
am verificat încă dacă e utilizabil cu date structurate.

---

## 9. Cum comparăm corect cele trei abordări

O avertizare metodologică importantă: cifrele noastre depind de **euristica de selecție a
paginilor**, nu doar de extractor. BCR are 10/16 pagini cu date pentru că 6 pagini alese
au fost slabe — nu pentru că extragerea a eșuat.

**Dacă fiecare rulăm pe alt set de URL-uri, comparăm euristici de selecție, nu
extractoare.**

Propunerea: **listă fixă de 15–20 URL-uri identice**, acoperind deliberat cele trei tipuri
structurale:

- pagini cu tabele curate (ex. eximbank, nexent, procredit)
- pagini randate prin JS (ex. credex, revolut)
- pagini cu rate în text liber (ex. bcr credite, raiffeisen)

Plus metrici agreate dinainte: câmpuri corect extrase · câmpuri ratate · valori greșite ·
timp pe pagină · cost pe pagină.

URL-urile exacte vizitate de noi sunt în `output/crawl/*.json`, câte unul pe bancă — de
acolo putem lua lista comună.

---

## 10. Rezumat în trei puncte

1. **Nu pierde timp pe** BT, UniCredit, Intesa (WAF) · Banorient (interzis prin
   robots.txt) · PKO, Citibank (inaccesibile) · BNP Paribas, Bank of China (zero retail).
   Verifică întâi domeniul: `bt.ro` și `credexbank.ro` sunt greșite.
2. **Repară conformitatea robots.txt înainte de orice** — `urllib.robotparser` ratează
   `Disallow: *.pdf` de la ING. Ia matcher-ul nostru din `crawler/robots.py`.
3. **Volumul extras nu e calitate.** Doar 52% din liniile noastre produc o valoare
   interpretabilă, iar validarea încrucișată cu BNR a prins o pagină învechită din 2020
   la Garanti. Fără validare, ai date care arată bine și sunt greșite.
