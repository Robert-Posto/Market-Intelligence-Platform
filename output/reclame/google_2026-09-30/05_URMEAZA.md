# 05. Ce se poate face mai departe

În ordinea în care le-aș face. Pașii 1–4 nu depind de nimeni altcineva; restul așteaptă avizul, IT-ul sau pe Robert.

## 1. A doua fotografie, la o săptămână

- **Ce:** rulezi aceeași interogare (`fisiere/fotografie.sql`) la o săptămână după 30.09 și compari cu fișierul din 30.09. Afli ce reclame au apărut și care s-au oprit, pe fiecare bancă.
- **De ce:** e dovada că reclamele se pot scoate și păstra în timp. Între 29.09 și 30.09 au apărut deja 118 reclame noi și au dispărut 28, deci mecanismul merge.
- **De făcut:** un script de comparație. Comparația de o zi s-a făcut direct în Python, nu cu un script păstrat.
- **Ritmul:** o fotografie pe lună e de ajuns ca să nu pierdem nimic, fiindcă o reclamă iese din set abia la un an după ultima afișare. Rulările periodice automate sunt înghețate în proiect, deci fotografia se face de mână.

## 2. O interogare mai ieftină

- Scoți din `fotografie.sql` coloanele fără informație, cele din lista de la [02](02_CAMPURI.md): granturile, verificarea, țara reclamei, linkul, numele juridic, țara advertiserului, data publicării pe platformă.
- Cu toate coloanele, costul a fost de 131 GB. Cât scade fără ele arată estimarea din consolă, înainte de Run.
- Tot aici ajustezi `interogare_fotografie.py`, care generează interogarea.

## 3. Băncile care lipsesc: căutare după site

Căutarea după `brd.ro`, făcută de mână pe <https://adstransparency.google.com/?region=RO>, a găsit BRD, care publică prin agenție. Aceeași căutare, pentru cele 11 bănci negăsite care au site propriu în România, durează cam 5 minute:

`intesasanpaolobank.ro` (verificare), `vistabank.ro`, `eximbank.ro`, `procreditbank.ro`, `creditcoop.ro`, `bidromania.eu`, `credex.ro`, `techventures.bank`, `brci.ro`, `bcrlocuinte.ro`, `cetelem.ro`

Pentru fiecare notezi câte reclame apar în RO și sub ce nume de advertiser. ID-ul se vede în adresa paginii advertiserului (`/advertiser/AR…`) și intră apoi în `google_advertiseri.csv`, cu un rol.

## 4. Categorizarea reclamelor cu AI: pilot pe capturi

- **Problema:** doar din datele Google nu știm despre ce e o reclamă. Un agent AI poate spune, dar trebuie să vadă reclama.
- **Cum:**
  - un om deschide reclama cu „Previzualizare” din galeria locală și face o captură;
  - AI-ul o categorizează după o schemă fixă;
  - eticheta se aplică întregului val de lansare.
- **De ce merge cu puține capturi:** cele 1.392 de reclame din sezonul de Crăciun 2025 vin din 51 de valuri, iar primele 10 acoperă 77%.
  - Pilotul: 2 capturi din fiecare dintre primele 10 valuri, adică 20 de capturi, cam 10 minute.
  - Dacă cele 2 capturi dintr-un val diferă, valul e „mixt” și are nevoie de mai multe.
- **Schema propusă:**

  | dimensiune | valori |
  |---|---|
  | sezon | Crăciun, Black Friday, Paște, vară, școală, niciunul |
  | produs | card, credit, cont, economii, investiții, asigurare, aplicație, altul |
  | mesaj | ofertă cu cifră, imagine de brand, concurs, recomandare |
  | limbă | română, engleză, alta |

- **De decis:** capturile ajung la un furnizor extern de AI. Pentru un pilot pe reclame publice decide Nicolae; pentru folosirea curentă intră în aviz. Capturile rămân locale și nu intră în git.
- **Interzis:** un agent care deschide singur paginile ATC (vezi [04](04_LIMITE.md)).

## 5. Conținutul reclamelor, de la Meta, LinkedIn și Microsoft

- Doar aceste API-uri dau textul reclamei. Cu textul, categorizarea de la pasul 4 se face automat, pe toate reclamele, fără capturi.
- Ce poți refolosi de aici e în [06](06_PENTRU_META_LINKEDIN_MICROSOFT.md).

## 6. Legătura cu campaniile de pe site-urile băncilor

Analiza generală a secțiunii 2.4 (`docs/NICOLAE_CHERASCU_MARKETING.md`, în repo) propune colectarea campaniilor de pe site-urile băncilor, cu perioada luată din regulament.
- O reclamă se poate lega apoi de o campanie după bancă și perioadă.
- Legătura rămâne aproximativă, cum a arătat exemplul Revolut de la Crăciun. Cu textul reclamei, de la pasul 5, devine sigură.

## 7. Ce așteaptă pe alții

| cine | ce |
|---|---|
| **Juridic** | avizul pe termenii Google, Meta, LinkedIn și Microsoft; trimiterea capturilor sau a textelor către un AI extern; politica de retenție, fiindcă Meta și LinkedIn cer ștergerea datelor, iar regula proiectului e „datele nu se aruncă” |
| **IT** | proiectul Google Cloud al organizației, în locul sandbox-ului personal; excepția de proxy pentru `facebook.com`; cine deține conturile de developer |
| **Robert** | tabela de reclame în bază, printr-o migrare nouă, după aviz. Apoi pagina din aplicație, pentru care galeria e prototipul |

## 8. Neexplorat încă

- **Tabelul `removed_creative_stats`:** reclamele scoase de Google, cu motivul. Ar arăta, de exemplu, dacă vreo bancă a avut reclame respinse.
- **Afișările pe fiecare platformă** sunt în date, dar galeria arată doar platforma principală. Ar putea da ponderea YouTube față de Search pe fiecare bancă.
