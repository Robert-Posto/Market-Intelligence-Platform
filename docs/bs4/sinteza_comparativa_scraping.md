# Testare de fezabilitate: două abordări tehnice pentru colectarea de date publice bancare

Document de sinteză tehnică, complementar propunerii de arhitectură **Market
Intelligence Platform** (DRAFT, 2026-09-09). Scopul acestui test: să se vadă,
practic, ce funcționează și ce nu, înainte ca Faza 0 (validarea Juridic/DPO) să
înghețe un mod concret de lucru.

Au fost testate independent două moduri de a colecta date publice de pe
site-urile băncilor: unul cu **fetch static** (fără randare de JavaScript) și
unul cu **browser headless** (Playwright, care randează JavaScript ca un
browser real). Ambele au fost verificate direct pe rezultate, nu doar descrise.

Varianta cu fetch static a fost construită inițial cu un scop precis: să
verifice, bancă cu bancă, **care site-uri permit accesul automatizat și care
îl blochează** — deci un test de accesibilitate, nu o extragere de date de la
bun început. Extragerea structurată pe categoria "depozite" a venit ca a doua
etapă, peste aceeași bază tehnică, după ce testul de accesibilitate era deja
făcut.

---

## 1. Rezumat executiv

Cele două variante răspund la nevoi diferite, deși țintesc aceleași bănci.

- **Varianta cu fetch static** a servit inițial ca test de accesibilitate —
  care bănci pot fi accesate automatizat și care blochează — și, pe lângă
  asta, a produs rapid un livrabil citit și verificat de un om, pe o singură
  categorie de date (depozite).
- **Varianta cu browser headless** e construită ca un sistem: descoperă pagini
  prin sitemap, verifică robots.txt corect, descarcă PDF-uri, validează
  rezultatele împotriva unei surse oficiale (BNR). Bună pe termen lung, pentru
  toate cele 8 categorii de date din arhitectură — dar pasul final, cel care
  transformă textul brut în informație structurată și citibilă, nu e încă
  terminat.

Niciuna nu e completă singură, iar arhitectura propusă prevede deja folosirea
**amândoror** tehnologii în paralel (secțiunea 5 — crawler static *și*
crawler JS, ca module separate). Testul de accesibilitate arată concret de ce:
fiecare tehnologie acoperă exact ce cealaltă ratează.

Cel mai important rezultat pentru planul de livrare: **Banca Transilvania**,
listată explicit ca una din cele 5 bănci-pilot pentru Faza 1 (secțiunea 9),
s-a confirmat **inaccesibilă** prin ambele metode, din cauza unui firewall
aplicațional (WAF) — nu a unei limitări de unealtă. Detalii la secțiunea 6.

---

## 2. Ce a folosit fiecare variantă

| | Fetch static (HTTP simplu) | Browser headless (Playwright) |
|---|---|---|
| **Fetch** | `requests` — cerere HTTP simplă, fără JavaScript | Chromium headless — randează pagina complet, ca un browser |
| **Parsare** | BeautifulSoup + lxml | selectoare native din pagina randată |
| **Verificare robots.txt** | citire directă a fișierului, cu distincție între "interzis explicit" și "fișierul n-a putut fi citit" | matcher scris special, cu suport pentru wildcard-uri (`*`) și precedență pe regula cea mai specifică |
| **Găsirea paginilor** | doar linkuri de pe pagina principală, o singură rundă, cuvinte-cheie în română | sitemap.xml (inclusiv sitemap-uri imbricate) + fallback pe linkuri, cu scor de prioritate per pagină |
| **Extragere** | text curat, citit și interpretat manual pentru fiecare bancă | tabele HTML + linii de text cu procente/sume, extrase automat |
| **PDF-uri (tarife, comisioane)** | neabordat | descărcate (peste 300 de fișiere unice), dar **neparsate încă** |
| **Indici BNR (ROBOR/IRCC)** | neabordat — paginile BNR au nevoie de JavaScript | extras direct, cu succes |
| **Curs valutar BNR** | neabordat | feed XML oficial, fără nevoie de browser |
| **Validare a datelor** | manuală, în timpul citirii | script dedicat: intervale de valori plauzibile, comparație cu valoarea oficială BNR, detectare de format numeric ambiguu |
| **Rezultat final** | document citit de om, cu produsele reale descrise și numerele corecte | fișiere JSON cu text și tabele brute; pasul de transformare în informație structurată e planificat, dar neterminat |

---

## 3. Aliniere cu arhitectura propusă

Documentul de arhitectură fixează câteva reguli concrete (secțiunea 1) și un
stack tehnic țintă (secțiunea 5). Comparate cu ce s-a testat efectiv:

**Identificare onestă (secțiunea 1).** Arhitectura cere un User-Agent
identificabil, cu contact, și interzice explicit imitarea unui browser real.
Varianta cu fetch static respectă asta — se identifică drept
`LibraBank-MarketIntel-Test`. Varianta cu browser headless folosește un
User-Agent care se prezintă ca Chrome obișnuit. E o alegere tehnică des
folosită pentru a trece de anumite filtre, dar intră direct în conflict cu
regula "fără spoofing de browser real" din document — merită discutat explicit
înainte de a deveni practica standard.

**Registru de surse cu decizie juridică (secțiunea 1 și 8).** Arhitectura cere
ca lista de surse și deciziile despre ce se poate colecta să vină dintr-un
registru administrat, nu dintr-o listă fixă în cod. Ambele variante testate
au folosit liste fixe, scrise direct în Python. Ambele ar trebui adaptate la
un registru real înainte de Faza 1 — nu e un dezavantaj al uneia față de
cealaltă, ci un pas comun rămas de făcut.

**Crawler static + crawler JS, în paralel (secțiunea 5).** Arhitectura nu
alege între cele două tehnologii — le cere pe amândouă, ca module separate,
exact pentru că unele site-uri sunt statice și altele randează conținutul prin
JavaScript. Testul de accesibilitate arată de ce e nevoie de amândouă în
practică: fetch-ul simplu nu vede deloc paginile de produs de la Nexent Bank
sau indicii BNR (randate prin JavaScript), în timp ce browserul headless e
mult mai lent și mai greu de instalat pe site-urile unde nu era nevoie de el.

**Extracție determinist + LLM cu schemă forțată (secțiunea 5).** Arhitectura
propune extragere automată din tabele/PDF-uri mai întâi, iar acolo unde nu
merge, un pas de extragere cu Claude, cu o schemă de date impusă și scor de
încredere per câmp. Niciuna din cele două variante testate nu are acest pas
implementat ca proces repetabil: varianta cu fetch static a avut interpretarea
făcută manual (fără schemă, fără scor de încredere), iar varianta cu browser
headless are validarea (utilă, dar diferită) fără pasul de extragere LLM.
Acesta e, de fapt, pasul cu cel mai mare impact rămas neconstruit din toată
arhitectura.

**PDF-urile de tarife — "sursa cea mai densă și cel mai des ignorată"
(secțiunea 2.1, formulare din documentul de arhitectură).** Rămâne așa și
după acest test: varianta cu browser headless le-a descărcat, dar nu le-a
citit; varianta cu fetch static nu le-a abordat deloc.

**Risc "Blocare IP / WAF" (secțiunea 10).** Arhitectura cere explicit ca o
sursă blocată să fie marcată și oprită, nu ocolită. Ambele variante au
respectat asta pentru băncile cu firewall activ (Banca Transilvania,
UniCredit, Intesa Sanpaolo) — niciuna nu a încercat vreo metodă de evitare.

---

## 4. Plusuri și minusuri

### Varianta cu fetch static

**Plusuri**
- Simplă de instalat și de rulat — fără dependențe de browser.
- Rapidă per pagină.
- Rezultatul final e deja un document citit de un om, cu produsele reale,
  ratele și condițiile corecte, atribuite corect fiecărei bănci.

**Minusuri**
- Nu vede deloc conținutul randat prin JavaScript (Nexent, indicii BNR,
  simulatoare de rate, unele pagini Revolut).
- Descoperă pagini doar din linkurile vizibile pe pagina principală, într-o
  singură trecere, și doar cu cuvinte-cheie în română — ratează pagini în
  engleză sau ascunse mai adânc în site.
- Nu are validare automată a valorilor extrase — se bazează pe atenția celui
  care citește, care nu se repetă automat la o rulare viitoare.
- Nu se poate reproduce fără intervenție umană la fiecare rulare — nu e un
  script care produce singur rezultatul final citibil.

### Varianta cu browser headless

**Plusuri**
- Vede tot ce e randat prin JavaScript — de aici acoperirea mult mai bună la
  Nexent, Revolut și la indicii BNR.
- Verificare de robots.txt mai riguroasă, cu suport pentru reguli cu
  wildcard, testată pe regulile reale ale mai multor bănci.
- Descoperă mult mai multe pagini, prin sitemap, nu doar prin noroc de link.
- Are un pas de validare cu rezultate concrete: a confirmat că doar o parte
  din liniile "cu rată" extrase conțin de fapt o valoare de dobândă
  interpretabilă, și a găsit — prin comparație cu valoarea oficială BNR — o
  bancă ce publică o valoare veche de câțiva ani, extrasă corect, dar
  neactualizată. E exact genul de eroare pe care nicio extragere, oricât de
  bună, nu o prinde fără o sursă independentă de verificare.
- Descarcă și organizează PDF-urile de tarife (verificând robots.txt separat
  pentru fiecare domeniu unde stau — multe PDF-uri sunt pe alt domeniu decât
  banca).

**Minusuri**
- Mai greoi de instalat și de rulat (necesită browser headless), și mult mai
  lent per pagină.
- Rezultatul final rămâne text și tabele brute — pasul de transformare într-un
  document structurat, citibil, e planificat dar neterminat.
- PDF-urile descărcate nu sunt încă parsate — informația de tarife rămâne pe
  disc, neexploatată.
- O bancă (CEC Bank) nu apare deloc în configurație, nici testată, nici
  exclusă cu motiv — un gol de acoperire.

---

## 5. Rezultate — comparație numerică

Nu sunt direct comparabile 1:1 (bănci diferite, categorii diferite de date
acoperite), dar câteva puncte utile:

- **Bănci verificate:** 30 în varianta cu fetch static (inclusiv cele care au
  eșuat, documentate ca atare); 23 în configurația activă a variantei cu
  browser headless, care a exclus dinainte, cu motiv documentat, exact
  sursele confirmate blocate și de cealaltă variantă (Banca Transilvania,
  UniCredit, Intesa Sanpaolo, PKO, Banque Banorient, domeniul greșit
  `credexbank.ro`). **Cele două metode au ajuns independent la aceeași listă
  de surse cu adevărat inaccesibile** — un semn bun, arată că nu e o
  limitare a uneltei folosite, ci o caracteristică reală a acelor bănci.
- **Categoria "depozite" specific:** varianta cu fetch static are date mult
  mai dense aici (tabele complete de dobânzi, condiții exacte, pentru 14
  bănci), pentru că a țintit doar această categorie. Varianta cu browser
  headless acoperă 8 categorii deodată, dar pe depozite specific rămâne
  parțială — ratele apar des în PDF, nu direct în pagină.
- **Volum brut, varianta cu browser headless:** 510 pagini vizitate cumulat,
  450 de tabele HTML extrase, peste 300 de PDF-uri unice descărcate
  (aproximativ 217 MB) — cifre verificate direct din fișierele rezultat, nu
  reluate din documentele descriptive.
- **Volum brut, varianta cu fetch static:** până la 10 pagini de depozite per
  bancă, fără PDF-uri, cu structurarea finală terminată doar pe această
  categorie.

---

## 6. Constatare importantă pentru planul de livrare

Planul de livrare (secțiunea 9 din documentul de arhitectură) numește explicit
5 bănci pentru Faza 1 (PoC): "BCR, BRD, ING, **BT**, Revolut" — unde BT e
abrevierea uzuală pentru Banca Transilvania (folosită și în secțiunea 3, unde
banca apare cu numele complet, în lista Nivel 1).

Testul de față a confirmat, prin două metode complet diferite, că **Banca
Transilvania e inaccesibilă** — un firewall aplicațional respinge orice
cerere automatizată, indiferent de unealtă. Nu e o problemă de configurare
care se poate remedia; e o decizie a băncii, iar arhitectura însăși (secțiunea
10, risc "Blocare IP/WAF") cere ca o sursă blocată să fie marcată și oprită,
nu ocolită.

Concret, asta înseamnă că **scopul Fazei 1 ar trebui revizuit** înainte de
start: fie se înlocuiește Banca Transilvania cu o altă bancă din Tier 1 (ex.
Raiffeisen sau Garanti BBVA, ambele confirmate accesibile și cu date bogate),
fie se acceptă din start că pentru BT informația va veni doar din surse
oficiale/publice generale (rapoarte, comunicate), nu din crawling direct.

---

## 7. Concluzie

Diferența reală dintre cele două variante nu e alegerea de tehnologie — e
cât de mult sistem s-a construit în jurul ei. O variantă oferă un rezultat
citit și verificat de om, dar limitat la o categorie. Cealaltă oferă o bază
mai largă, pe toate categoriile, dar cu pasul final de structurare încă de
făcut. Arhitectura propusă anticipează deja nevoia de a combina ambele
tehnologii, iar testul de accesibilitate arată concret de ce e nevoie de
amândouă. Cel mai important rezultat operațional: Banca Transilvania, bancă-pilot pentru Faza
1, e confirmat inaccesibilă prin metode conforme cu regulile proprii ale
arhitecturii — o decizie care trebuie luată înainte de startul Fazei 1, nu
descoperită pe parcurs.
