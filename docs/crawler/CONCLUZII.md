# Concluzii: crawling de date bancare publice în România

<!-- antet-vechime -->
> **Cifrele din documentul ăsta sunt cele de pe 18 septembrie 2026 și nu au fost
> actualizate.** Se păstrează ca jurnal de lucru: arată ce se știa atunci și
> cum s-a ajuns acolo. **Totalurile curente sunt în
> [CONSTATARI.md](CONSTATARI.md)**, iar regulile de filtrare pentru integrare
> în [CITESTE_PENTRU_MERGE.md](CITESTE_PENTRU_MERGE.md).

Document de sinteză, 16 septembrie 2026. Toate afirmațiile de aici au fost verificate
practic, nu presupuse — fiecare are metoda de verificare notată alături.

> **Actualizat 18 septembrie.** Documentul acesta acoperă **accesul**: ce se poate
> crawla, ce nu, și de ce. Partea de **extragere și comparație**, construită pe
> 17–18 septembrie, e în alte documente:
>
> - [COMISIOANE_PDF.md](COMISIOANE_PDF.md) — formularul standardizat (Legea 258/2017)
> - [COMISIOANE_TARIFE.md](COMISIOANE_TARIFE.md) — listele de tarife nestandardizate
> - [comparatie_comisioane.md](comparatie_comisioane.md) — tabelul între bănci
> - [comparatie_rate.md](comparatie_rate.md) — tabelul de rate
> - [BRIEFING_BEAUTIFULSOUP_3.md](BRIEFING_BEAUTIFULSOUP_3.md) — sinteza pentru colegi
>
> Cifrele pe scurt: **4.438 de comisioane** din 40 de documente PDF (10 bănci),
> **555 de rate** din web, **76 de linii de comparație** din care 48 de încredere.
> Limitarea de la §11 despre PDF-uri nu mai e valabilă — vezi nota de acolo.

---

## 1. Rezumatul pe scurt

Am pornit de la o listă de date dorite (produse, prețuri, comisioane, dobânzi, DAE,
marje peste IRCC, curs valutar, indici de referință) și de la o singură bancă țintă
(Banca Transilvania). Am terminat cu **23 de surse verificate**, dintre care **18-19
efectiv crawlabile**, un crawler funcțional și trei concluzii care schimbă modul în care
merită abordată problema:

1. **Blocajele nu sunt o problemă de metodă, ci politici individuale de bancă.** Aceeași
   abordare tehnică eșuează la BT și funcționează perfect la BCR. Nu există un „truc"
   care să deblocheze BT — și nici nu ar trebui căutat.
2. **Două din trei probleme iniţiale au fost domenii greșite, nu blocaje.** `bt.ro` și
   `credexbank.ro` nu sunt (sau nu mai sunt) site-urile băncilor respective. Verificarea
   domeniului trebuie să fie primul pas, nu ultimul.
3. **Uneltele standard de conformitate robots.txt sunt insuficient de riguroase.**
   Modulul `urllib.robotparser` din Python ar fi ratat silențios o interdicție explicită
   de la ING. Detaliile sunt în secțiunea 6.

Ce a rămas nerezolvat: valorile ROBOR/IRCC direct de la BNR. Dar problema s-a rezolvat
altfel — vezi secțiunea 5.

---

## 2. Concluzia centrală: trei tipuri distincte de blocaj

Cea mai utilă distincție pe care am făcut-o e că „nu merge" acoperă trei situații complet
diferite, cu implicații diferite.

### Tip A — WAF care blochează orice acces automatizat

**Bănci:** Banca Transilvania, UniCredit, Intesa Sanpaolo.

**Mecanism:** un firewall aplicațional (WAF) la marginea rețelei răspunde cu HTTP 403 și
o pagină de eroare, indiferent de unealta folosită. La BT pagina e brandată, cu
„Acces blocat / Access denied", un Reference ID și IP-ul clientului. La UniCredit mesajul
vine în croată (protecție la nivel de grup, nu doar pe România). La Intesa, antetele
trimit către `errors.edgesuite.net`, adică Akamai.

**Cum l-am confirmat:** același 403 la `curl` și la Playwright, pe homepage și pe
link-uri directe către PDF-uri publice. La BT, răspunsul avea exact aceeași lungime
(3.955 octeți) pentru toate URL-urile încercate — semnătura unei pagini de blocare
servite uniform, nu a unor erori diferite.

**Implicația:** nu e o barieră tehnică de ocolit, e o decizie a băncii. Tehnicile de
evitare (stealth plugins, falsificarea amprentei TLS, proxy-uri rotative, rezolvare de
CAPTCHA) ar însemna forțarea accesului peste protecția activă a altei instituții
financiare. Nu le-am aplicat și nu le recomand. Dacă datele BT sunt necesare, calea
corectă e o cerere formală către bancă sau consultarea manuală.

### Tip B — Blocaj TEMPORAR, confundat initial cu o politica permanenta

> **CORECTAT (16.09.2026, dupa re-testare):** concluzia de mai jos a fost greșită.
> `www.bnr.ro` functioneaza normal cu Playwright — 200 OK, pagina completa. Blocajul
> descris mai jos a fost **tranzitoriu**, cel mai probabil limitare de rata provocata
> de propriile mele cereri rapide din faza de diagnostic. Lectia reala: **un esec
> punctual nu dovedeste o politica permanenta** — un blocaj temporar arata identic cu
> unul definitiv. Trebuie re-testat inainte de a trage concluzii.

**Instituție:** BNR (site-ul principal `www.bnr.ro`).

**Mecanism:** cererile HTTP simple trec fără probleme (curl primește 200 OK și conținut
complet), dar Playwright nu reușește nici să deschidă conexiunea — `ERR_CONNECTION_CLOSED`,
apoi timeout. Conexiunea e închisă înainte ca vreun cod JavaScript să ruleze, ceea ce
indică o filtrare pe amprenta TLS/HTTP2 a browserului headless, nu o detecție bazată pe
comportament în pagină.

**Cum l-am confirmat:** același Playwright, în aceeași rulare, a încărcat `example.com`
și `google.com` cu 200 OK, dar a eșuat pe orice URL de pe `bnr.ro`. Deci nu era rețeaua
și nu era configurația noastră.

**Implicația:** e opusul intuiției. Pentru BNR, unealta „mai simplă" (cerere HTTP) e cea
care funcționează, iar browserul automatizat e cel blocat. Ceea ce ne aduce la o
observație mai generală: **alegerea uneltei trebuie făcută per sursă, nu global.**

### Tip C — Fără blocaj

**Majoritatea:** BCR, BRD, Raiffeisen, ING, Libra, Patria, Garanti BBVA, Nexent, Exim,
Vista, ProCredit, Salt, tbi, TechVentures, BRCI, BCR Locuințe, CREDITCOOP, BID, Revolut,
Cetelem, Credex.

Aici Playwright funcționează normal, iar datele se extrag fără dificultate.

---

## 3. Lecția despre domenii: verifică înainte de a depana

Două din problemele aparent tehnice s-au dovedit a fi domenii greșite. Merită subliniat,
pentru că e cel mai ieftin control de făcut și cel mai costisitor de omis.

### `bt.ro` nu este Banca Transilvania

E site-ul unei firme numite **Bucuresti-Tokyo Impex S.R.L.** — o pagină veche, cu fundal
negru, text verde și o hartă a Asiei. Titlul paginii este „Bucuresti - Tokyo". Domeniul
real al băncii este `bancatransilvania.ro`.

Dacă nu am fi deschis efectiv pagina, primul crawl ar fi „reușit" tehnic și ar fi
produs trei link-uri irelevante, fără nicio eroare. **Un crawl care merge fără erori nu
garantează că ai crawlat ce credeai.**

### `credexbank.ro` nu este site-ul Credex

Domeniul din listă răspunde, dar ciudat: handshake-ul TLS se stabilește, cererea se
trimite, apoi serverul cere renegociere TLS în buclă și nu răspunde niciodată — timeout
cu 0 octeți primiți. Playwright primește `ERR_HTTP2_PROTOCOL_ERROR`.

**Verificarea decisivă:** am testat același URL din infrastructura Anthropic, printr-un alt
punct de rețea. A eșuat și acolo. Deci domeniul e nefuncțional global, nu blocat local.

Site-ul real este **`credex.ro`**, funcționează normal și are `robots.txt` permisiv. O
precizare relevantă pentru analiză: entitatea e **IFN, nu bancă** („CREDEX IFN", parte din
grupul Altex), deci probabil merită clasificată separat.

### O pistă falsă pe care am urmat-o

Prima verificare DNS pentru Credex a returnat doar adrese IPv6, iar rețeaua voastră nu
are conectivitate IPv6 (confirmat separat: `ipv6.google.com` eșuează). Am concluzionat
prematur că asta era cauza. **Era greșit** — domeniul are și adrese IPv4 (2.19.193.146 și
2.19.193.178, Akamai), iar forțarea IPv4 eșuează identic. Lipsa de IPv6 e reală, dar
irelevantă aici. O interogare DNS incompletă poate produce o explicație plauzibilă și
falsă.

---

## 4. Ce spune robots.txt și cum merită interpretat

Aici e partea cu cele mai multe nuanțe, pentru că `robots.txt` nu e un simplu
„da/nu".

### Distincția care contează: crawlere de antrenament vs. agenți la cerere

Ecosistemul face de ceva vreme diferența între două categorii de acces automatizat:

- **Crawlere de colectare corpus pentru antrenament AI:** `GPTBot`, `Google-Extended`,
  `CCBot`, `ClaudeBot`. Adună masiv conținut pentru antrenarea modelelor.
- **Agenți care acționează la cererea unui utilizator:** `Claude-User`, `ChatGPT-User`,
  `Perplexity-User`, `OAI-SearchBot`. Cineva a cerut ceva concret, aici și acum.

Băncile românești cunosc explicit distincția. BCR și BRD au în `robots.txt` un comentariu
literal `# Allow agentic-AI users`, urmat de exact acele nume.

### Situația pe bănci

**Permisiune explicită pentru agenți AI** — BCR, BRD, Libra:

```
# BCR
User-agent: ClaudeBot      → Allow: /
User-agent: Claude-User    → Disallow:   (gol = permis)

# BRD
# Allow agentic-AI users
User-agent: Claude-User, ChatGPT-User, Perplexity-User, OAI-SearchBot

# Libra (banca voastră)
User-agent: ClaudeBot      → Allow: /
```

**Permisiv fără mențiuni AI** — Garanti BBVA (309 reguli `Allow`, **zero** `Disallow`),
Raiffeisen, Cetelem, Nexent, Credex, ProCredit și altele.

**Fără `robots.txt`** — Exim, Vista, Salt, BRCI, BID (cod 404 sau pagină HTML). Conform
RFC 9309, absența fișierului înseamnă că nu există restricții declarate.

**Caz care cere judecată — Patria Bank:**

```
User-agent: *
Disallow:                    ← gol: permite tot
Crawl-delay: 5
Disallow: /d/ /r/ /content/ /nav/

User-agent: GPTBot           → Disallow: /
User-agent: Google-Extended  → Disallow: /
User-agent: CCBot            → Disallow: /
```

Cele trei blocate sunt **toate crawlere de antrenament**. Regula generală pentru `*`
rămâne permisivă, iar agenții la cerere (`Claude-User`, `ChatGPT-User`) nu sunt blocați.
Interpretarea rezonabilă: Patria refuză colectarea de corpus, nu accesul la cerere. Am
crawlat respectând `Crawl-delay: 5` și evitând cele patru căi interzise. Dacă preferi o
abordare mai conservatoare, exclude-o — e o decizie de politică internă, nu tehnică.

**Interdicție fără ambiguitate — Banque Banorient France:**

```
User-agent: bingbot / Googlebot / yandex / slurp ...
Disallow: /ffmpeg/ ...        (doar căi tehnice)
Crawl-delay: 10

User-agent: *
Disallow: /                   ← tot interzis
```

Permit exclusiv motoarele de căutare numite. Pentru orice alt agent, acces interzis
complet. **Am exclus-o din crawler** și recomand să rămână exclusă.

**Reguli neverificabile — ING:** `www.ing.ro/robots.txt` returnează 403 chiar și din
browser. Dar — detaliu important — **`ing.ro/robots.txt` (fără `www`) returnează 200**.
Merită întotdeauna încercate ambele variante de hostname. Regulile lor sunt restrictive
pe documente (vezi secțiunea următoare).

### Un `403` la `robots.txt` nu înseamnă automat blocare

Cetelem returnează pentru `robots.txt` o pagină „Request Rejected" cu un support ID
(semnătură F5 BIG-IP) când cererea vine de la `curl`. Din browser, același fișier se
citește normal și e permisiv. **Deci verifică întotdeauna și prin browser înainte de a
declara un site blocat.**

---

## 5. Problema ROBOR/IRCC și cum s-a rezolvat indirect

Datele cerute includeau indicii de referință. Traseul a fost mai complicat decât părea.

> **CORECTAT (16.09.2026):** ROBOR si IRCC **se pot extrage direct de la BNR**.
> Exista pagini dedicate, cu tabele structurate:
> - ROBID/ROBOR, serii zilnice, toate cele 7 scadente:
>   `bnr.ro/1973-ratele-medii-ale-dobanzilor-pe-piata-monetara-interbancara`
> - IRCC trimestrial si zilnic:
>   `bnr.ro/1974-indicele-de-referinta-pentru-creditele-consumatorilor`
>
> Verificat: ROBOR 3M = 5,84%, 6M = 5,92%, 12M = 5,98% (16.09.2026);
> IRCC in vigoare 2026T1 = 5,56%. Modul: `crawler/bnr_indici.py`.
>
> **De ce am ratat asta initial:** am cautat "ROBOR" in HTML-ul neradat, obtinut cu
> `curl`. Navigatia si conținutul acelor pagini sunt incarcate prin JavaScript, deci
> HTML-ul brut nu le contine. **Metoda de verificare a fost greșită, nu concluzia
> despre site.** Aceeasi capcana ca la robots.txt: absenta unui termen din HTML-ul
> brut nu dovedeste absenta informatiei din pagina.
>
> Validare incrucisata utila: BNR publica IRCC 2026T1 = 5,56%, iar pagina BCR afisa
> "IRCC = 5,56%". Se confirma reciproc.

**Ce nu a funcționat initial (si de ce concluzia era greșită):** `curs.bnr.ro` e un server dedicat **exclusiv** cursului valutar —
am verificat, nu există echivalent pentru ROBOR sau IRCC. Pagina „Piața monetară" de pe
`bnr.ro` are **zero tabele și zero mențiuni „ROBOR"** în HTML: e doar text descriptiv.
Valorile există numai în instrumentul „Bază de date interactivă", care cere interacțiune
UI (arbore de selecție + buton „Generate statistics"). Iar acel instrument nu poate fi
automatizat, pentru că BNR blochează conexiunile de browser automatizat (Tip B, secțiunea 2).

**Ce a funcționat:** **băncile comerciale publică ele însele valoarea IRCC**, pentru că
sunt obligate să o afișeze în ofertele de credit. BCR scrie direct în pagină:
`IRCC = 5,56% (valabil până la 30.09.2026)`. Patria afișează
`IRCC + marja fixă a băncii (de la 6,67% la 17,24%)`.

Deci nu mai avem nevoie de instrumentul interactiv al BNR. Indicele îl luăm de la bănci,
iar cursul de referință de la feedul oficial BNR, care funcționează impecabil.

**Feedurile BNR care merg** (cerere HTTP simplă, fără browser):

| Feed | Conținut |
|---|---|
| `curs.bnr.ro/nbrfxrates.xml` | ultima cotație |
| `curs.bnr.ro/nbrfxrates10days.xml` | ultimele 10 zile |
| `curs.bnr.ro/files/xml/years/nbrfxrates2026.xml` | anul curent, plus arhivă până în 2005 |

---

## 6. Capcane tehnice: două bug-uri care ar fi trecut silențios

Ambele au fost prinse doar pentru că am testat împotriva regulilor reale ale băncilor, nu
împotriva unor exemple inventate. Merită reținute, pentru că amândouă produceau
**conformitate aparentă, dar falsă**.

### Bug 1 — `urllib.robotparser` nu înțelege wildcard-uri

Modulul standard din Python face doar potrivire pe prefix. Implementarea internă e
literalmente `filename.startswith(self.path)`.

ING are în `robots.txt`:

```
Disallow: *.pdf
Disallow: *.xml
Disallow: *.xlsx
```

Cu `robotparser`, modelul `*.pdf` devine un prefix literal, iar verificarea
`"/dam/doc/lista.pdf".startswith("*.pdf")` este mereu falsă. **Rezultatul: interdicția
ar fi fost ignorată complet** și am fi descărcat sistematic documente interzise explicit,
cu impresia că respectăm regulile.

Am scris un matcher propriu, conform RFC 9309, cu suport pentru `*`, ancora finală `$` și
precedența pe cel mai lung model (`Allow` câștigă la egalitate). Testele sunt în
`scripts/test_robots_matcher.py`, rulate pe regulile reale ING, BCR și Patria.

**Efectul în practică:** la crawl-ul de test, ING a raportat **165 de PDF-uri găsite, 0
descărcate, 29 sărite explicit** pe motiv de robots.txt. Exact comportamentul corect.

Consecință de igienă: în faza de diagnostic descărcasem două documente ING
(`Lista-de-taxe-si-comisioane.pdf` și `rate_dobanzi.pdf`), pe vremea când `robots.txt`-ul
lor părea inaccesibil. **Le-am șters** după ce am putut citi regulile.

### Bug 2 — `inner_text()` colapsa robots.txt într-o singură linie

BCR servește `robots.txt` cu content-type `text/html`. Browserul îl tratează deci ca
HTML, unde liniile noi se colapsează în spații. Conținutul citit cu `inner_text()` arăta
așa:

```
'User-agent: * Allow: / User-agent: GPTBot Allow: / User-agent: ClaudeBot Allow: /  ...'
```

O singură linie, 0 reguli parsate. Iar „0 reguli" e indistingibil de „fără restricții",
deci crawler-ul ar fi tratat BCR drept complet nerestricționat — inclusiv căile pe care
le interzic explicit (`/search`, `/*.compare`).

Soluția: **corpul brut al răspunsului HTTP** (`response.text()`), nu textul randat. După
corectare, BCR a trecut de la **0 la 24 de reguli** detectate corect, iar `/search` este
acum respins cum trebuie.

### Alte două observații de mediu

- **Verificarea PDF-urilor trebuie făcută per origine, nu per bancă.** Documentele stau
  adesea pe alt domeniu — PDF-urile BCR sunt pe `cdn.erstegroup.com`, care are propriul
  `robots.txt` (84 de reguli). Crawler-ul citește acum `robots.txt` pentru fiecare
  origine întâlnită și îl păstrează în cache.
- **Un fișier rătăcit vă poate rupe scripturile Python.** Există un `inspect.py` în
  `%TEMP%` pe stația voastră, care umbrește modulul standard `inspect` pentru orice script
  rulat din acel director. Efectul e o eroare complet derutantă
  (`ModuleNotFoundError: No module named 'app'`) care nu are nicio legătură cu codul
  rulat. Merită șters.

---

## 7. Ce date se pot extrage efectiv

Verificat concret, nu presupus. Exemple reale din rulările de test:

| Categorie din cerință | Se poate? | Dovada |
|---|---|---|
| Comisioane (PDF-uri „Tarife și comisioane") | **Da** | BCR: 8 PDF-uri; `Tarif_standard_comisioane_PF.pdf` descărcat, 284 KB, PDF valid |
| Dobânzi nominale + DAE | **Da** | BCR `george-credit`: dobândă 5,79%–14,99%, **DAE 13,90% / 16,41%** |
| Marjă peste IRCC | **Da** | BCR `casa-mea-bcr`: fix 4,99% 3 ani, apoi **IRCC + 2,3%**; `descoperit-de-cont`: **IRCC + 7,99%** |
| Valoarea IRCC | **Da** | BCR publică direct: **IRCC = 5,56%**, valabil până la 30.09.2026 |
| Credit ipotecar / DAE | **Da** | Patria `patria-acasa`: **DAE de la 8,04%** la creditele în lei |
| Curs valutar propriu | **Da** | BCR: 6 tabele, EUR **5,1880 / 5,3390** cumpărare/vânzare |
| Curs de referință BNR | **Da** | Feed XML oficial: 2026-09-15, EUR **5,2636**, USD **4,5624** |
| Conturi / pachete / carduri | **Da** | Structuri de URL curate la toate băncile mari |
| Depozite | **Parțial** | Tabele prezente (ING: 3 tabele, 7 linii cu rate), dar unele bănci afișează ratele doar în PDF |
| ROBOR direct de la BNR | **Da** | Pagina dedicata BNR: ROBOR 3M=5,84% 6M=5,92% 12M=5,98% (16.09.2026) |

---

## 8. Statusul final, pe surse

| Sursă | Acces | robots.txt | Verdict |
|---|---|---|---|
| BCR | 200 OK | permite explicit ClaudeBot + Claude-User | ✅ crawlabil, testat în profunzime |
| BRD | 200 OK | permite explicit agenți AI | ✅ crawlabil |
| Raiffeisen | 200 OK | permisiv | ✅ crawlabil |
| ING | 200 OK | **`*.pdf`, `*.xml` interzise** | ✅ pagini da, documente nu |
| Libra Internet Bank | 200 OK | permite explicit ClaudeBot | ✅ crawlabil |
| Patria Bank | 200 OK | Crawl-delay 5; blochează crawlere de antrenament | ✅ crawlabil cu prudență |
| Garanti BBVA | 200 OK | 309 Allow, 0 Disallow | ✅ crawlabil |
| Nexent Bank (ex-Credit Europe) | 200 OK | permisiv | ✅ crawlabil, date retail bogate |
| Exim, Vista, Salt, BRCI, BID | 200 OK | inexistent (404) | ✅ crawlabil |
| ProCredit, TechVentures, CREDITCOOP, BCR Locuințe | 200 OK | permisiv | ✅ crawlabil |
| tbi bank, Revolut | 200 OK | permisiv | ✅ crawlabil |
| Cetelem | 200 OK (prin browser) | permisiv | ⚠️ crawlabil, dar nu publică DAE |
| Credex (`credex.ro`) | 200 OK | permisiv | ⚠️ crawlabil; e IFN, nu bancă |
| BNP Paribas SA Paris | 200 OK | permisiv | ⚠️ zero date retail (corporate) |
| Bank of China (CEE) | 200 OK | permisiv | ⚠️ zero date retail (corporate) |
| BNR — curs valutar | 200 OK | feed oficial | ✅ funcționează impecabil |
| **Banque Banorient** | 200 OK | **`*` → `Disallow: /`** | ⛔ exclus, interzis explicit |
| **Banca Transilvania** | 403 | — | ❌ WAF |
| **UniCredit** | 403 | — | ❌ WAF de grup |
| **Intesa Sanpaolo** | 403 | — | ❌ WAF (Akamai) |
| **PKO Bank Polski** | timeout TCP | — | ❌ inaccesibil (verificat din 2 rețele) |
| BNR — site principal | 200 OK | — | ✅ functioneaza (blocajul initial era tranzitoriu) |
| Citibank RO | fără răspuns | — | ❌ domeniu abandonat (Citi a ieșit din retail RO) |
| ~~credexbank.ro~~ | TLS în buclă | — | ❌ domeniu nefuncțional; folosește `credex.ro` |

---

## 9. Arhitectura soluției

```
crawler/
  banci.py       configurația celor 23 de surse, cu excluderile documentate
  robots.py      conformitate robots.txt (matcher propriu, RFC 9309)
  extractor.py   extragere tabele/PDF/rate + scor de prioritizare a paginilor
  bnr.py         cursul oficial BNR din feedul XML
  main.py        orchestrator cu CLI
scripts/
  raport.py              JSON → raport Markdown
  test_robots_matcher.py teste pentru matcher-ul robots
  verifica_robots_reale.py verificare pe domenii reale
```

Rulare:

```bash
python -m crawler.main                        # toate băncile
python -m crawler.main --banci bcr,ing --pdf  # selectiv, cu descărcare de documente
python scripts/raport.py                      # generează raportul
```

**Două decizii de design care s-au dovedit necesare:**

*Prioritizare prin scor, nu în ordinea din sitemap.* Prima versiune lua primul URL care
se potrivea pe categorie și alegea pagini precum „Sistemul Biroului de Credit" pentru
categoria credite, sau „Fondul de garantare a depozitelor" pentru depozite — pagini
informative, fără prețuri. Acum fiecare URL primește un scor: bonus pentru semnale de
pagină de produs, penalizare pentru pagini informative, bonus pentru `persoane-fizice` la
categoriile retail, penalizare pentru adâncime excesivă. Rezultatul: BCR a trecut de la
0 la 12 linii cu rate pe pagina de credite.

*Distribuție round-robin între categorii.* Plafonul de pagini pe bancă tăia complet
ultimele categorii — BCR nu ajungea niciodată la cursul valutar. Acum se ia câte o pagină
din fiecare categorie pe rând.

---

## 10. Recomandări operaționale

**Cadență.** Comisioanele și dobânzile se schimbă rar, dar cursul valutar zilnic, iar
IRCC trimestrial. Un crawl săptămânal pentru produse și comisioane, plus unul zilnic doar
pentru curs valutar, ar fi proporțional. Mai des nu aduce informație, doar trafic.

**Ce se va strica primul.** Selecția paginilor se bazează pe cuvinte-cheie din URL. O
bancă își poate restructura site-ul oricând (ING a făcut-o deja: URL-urile reale au
segmente cu majuscule, `/imm/Economii/`, iar ghicirea lor a dat 404). Monitorizează
numărul de pagini extrase pe bancă: o scădere bruscă la zero înseamnă restructurare, nu
blocare.

**Verifică robots.txt la fiecare rulare, nu o singură dată.** Politicile se schimbă.
Crawler-ul le recitește deja la fiecare rulare și le loghează în rezultat — un
`Disallow: /` nou apărut trebuie observat, nu ignorat.

**Datele din PDF-uri rămân neexploatate.** PDF-urile de tarife sunt descărcate, dar nu
parsate. Acolo e cea mai densă informație despre comisioane. Un pas următor firesc ar fi
extragerea tabelelor din ele (`pdfplumber` sau similar) — dar atenție: pentru ING,
documentele sunt interzise de `robots.txt`, deci pasul acesta nu se aplică uniform.

**Nu încerca să deblochezi BT, UniCredit sau Intesa.** Sunt decizii ale băncilor, iar
ocolirea lor ar fi forțarea unei protecții active. Pentru datele lor, calea corectă e
cererea formală sau consultarea manuală.

---

## 11. Limitări cunoscute

- ~~**PDF-urile nu sunt parsate**, doar descărcate și indexate.~~ **REZOLVAT**
  (17–18 septembrie): **4.438 de comisioane** din 40 de documente, prin citire
  geometrică — borduri acumulate pe poziție, atribuirea etichetei prin poziții
  verticale, coloane per rând. 99% din valori au textul-sursă regăsit automat în
  pagina lor. Vezi [COMISIOANE_PDF.md](COMISIOANE_PDF.md) și
  [COMISIOANE_TARIFE.md](COMISIOANE_TARIFE.md).
  Limita care rămâne: **38% din valori nu se mapează** pe un concept canonic, iar
  cauza e măsurată — 97% dintre ele au eticheta fragmentară, adică numele
  serviciului s-a pierdut la granița rândului de grilă.
- **Ratele din calculatoare JavaScript nu sunt extrase.** Credex, de exemplu, își
  afișează ratele într-un simulator dinamic; pagina statică arată doar DAE 22,67%.
- ~~ROBOR nu e acoperit.~~ **REZOLVAT:** ROBOR si IRCC se iau direct de la BNR,
  din pagini dedicate cu tabele structurate (vezi secțiunea 5).
- **Plafoane de pagini.** Rulează implicit maximum 3 pagini pe categorie și 18 pe bancă,
  ca să rămână proporțional. Sunt parametri de linie de comandă, se pot ridica.
- **Clasificarea pe categorii e euristică**, bazată pe cuvinte-cheie din URL. Funcționează
  bine pe băncile mari, cu structuri curate; la cele mici poate rata pagini.
- **Rularea completă pe toate băncile era încă în desfășurare** la momentul scrierii
  acestui document. Cifrele de acoperire din secțiunea 7 provin din rulările de test pe
  BCR, ING, Patria și Credex.
