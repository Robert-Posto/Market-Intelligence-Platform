# Handoff: interfața mutată pe React, stack-ul SCC (02–05.10.2026)

Pentru cine lucrează mai departe pe aplicație după merge-ul ramurii `stack-scc`.
**Nu s-a schimbat nimic în colectare, în bază sau în `app/`:** nicio migrare nouă,
`app/server.py` și `app/index.html` sunt exact cum erau. Interfața nouă stă alături,
în `web/` și `shared/`, și cere datele de la același `app/server.py`.

## De ce

Pe 02.10.2026, Doru a cerut ca aplicațiile de business să folosească stack-ul Sales
Command Center (TypeScript, React 18 + Vite 6 + Ant Design 5, Fastify 5, PostgreSQL 17,
LDAP, Debian), ca oamenii din business să poată dezvolta singuri funcționalități pe
o bază comună. MIP devine **Marketing Command Center**, cu depozitul
`github.com/Libra-Bank/marketing-command-center` (gol la 05.10). Decis de Nicolae
pe 05.10: **colectarea rămâne în Python**; s-a mutat doar interfața.

## Ce ai de făcut după `git pull`

```bash
npm install                 # Node 20+; instalează web/ și shared/ (npm workspaces)
python app/server.py        # API-ul, pe :8765, neschimbat
npm run dev                 # interfața nouă, pe http://localhost:5173
```

Aplicația veche rămâne la http://localhost:8765, pentru comparație. Interfața nouă
nu are server propriu: în dezvoltare, Vite trimite `/api`, `/pdf`, `/logos` spre :8765.

Înainte de commit, după orice modificare în `web/` sau `shared/`:

```bash
npm run typecheck && npm run build
```

`verifica_pagini.py` rămâne pentru `app/`; în `web/`, o ghilimea ASCII greșită într-un
text românesc e eroare de compilare, nu pagină albă.

## Structura

```
package.json            workspaces: shared, web (fără server/ încă)
shared/src/*.ts         schemele Zod ale răspunsurilor API, câte un fișier pe zonă
web/src/
  pages/                o pagină = un fișier (+ un folder când e mare: campanii/, versus/, harta/…)
  components/           Tabel, Sertar, Dovezi, Banda, Paginare, BareStele, comune (Pill, Despre, Pliat…)
  i18n/                 traducerile: index.tsx (t, tn, <T>), server.ts (deLaServer), dict/*.ts
  api/                  cererile, pe zone (useQuery + schema din shared)
  styles/               global.css + câte un fișier pe zonă
```

Versiunile sunt cele din `Libra-Bank/sales-command-center` (React 18.3, Vite 6, AntD 5,
TanStack Query 5, React Router 7, Zod 3, TypeScript 5.7). Dependențe noi față de SCC:
`maplibre-gl` 4.7.1 (harta, aceeași versiune ca în `harta.html`) și `pdfjs-dist` 4.10.38
(vizualizatorul), ambele din npm, fără CDN. Fonturile MIP (Source Serif 4, IBM Plex)
sunt incluse local, cu subsetul `latin-ext`, unde stau ș, ț, ă.

## Ce s-a mutat

Toate cele 12 pagini, cu aceleași adrese (`#/produse?grup=…`, `#/banca?b=…`, …), deci
linkurile salvate merg mai departe. Harta și vizualizatorul PDF au ieșit din fișierele
separate și sunt rute pe tot ecranul:

| înainte | acum |
|---|---|
| `/harta.html?banca=bcr,ing` | `#/harta?banca=bcr,ing` |
| `/pdf.html?u=…&p=…&q=…` | `#/document?u=…&p=…&q=…` (o singură funcție o construiește: `linkDocument` din `components/Dovezi.tsx`) |

Aspectul: componente Ant Design cu tema MIP (aceleași culori și fonturi, inclusiv tema
întunecată după sistem). Taburile, listele, sortarea și secțiunile pliate arată ca în AntD;
tabelele, cifrele și sertarul arată ca înainte.

## Română și engleză

Comutatorul e jos în bara laterală; limba se ține minte în browser, implicit română.
1.258 de texte la 05.10.2026, câte o pereche `[română, engleză]` pe cheie, în
`web/src/i18n/dict/*.ts`. Au fost extrase din toată interfața veche, traduse, verificate
automat (aceiași parametri și același marcaj în ambele limbi) și revizuite de un agent
separat (58 de observații, aplicate).

Reguli care contează când adaugi ceva:
- **Datele băncilor nu se traduc** (denumiri de servicii, citate, titluri de campanii,
  recenzii): sunt dovezi.
- **Textele românești trimise de server** (etichete de termen, motive din coadă, numele
  comenzilor de rulare) se traduc la afișare cu `deLaServer(text, lang)`, după textul exact
  sau după tipar dacă au parametri. Pe server rămân în română: unele sunt chei (`?motiv=`,
  „bănci” din `/api/sumar`, „fără datare”).
- **Conceptele canonice** (`camp.<slug>.eticheta` / `.descriere`): 76 din cele 129 de
  concepte din bază n-aveau etichetă nici în aplicația veche și apăreau ca slug. Acum au
  toate; variantele `_min` / `_max` iau eticheta conceptului de bază plus „minim/maxim”.
  Un concept nou din `vocabular.py` are nevoie de o pereche aici, altfel apare ca slug.
- Termenii bancari în engleză **încă n-au fost văzuți de un om din bancă**.

## Diferențe intenționate față de aplicația veche

- **Filtrele stau în adresă** pe toate paginile (o vedere filtrată se poate trimite ca link).
- **Singularele:** „1 bancă”, „1 lună”, „1 sursă” în loc de „1 bănci”, „1 luni”.
- **Datele** se scriu după limbă (30.09.2026 / 30/09/2026), nu ISO; numerele la fel
  (1.234,5 / 1,234.5).
- **Harta:** cele 66 de puncte cu `sursa='mock'` din `mip_stack` apar „date mock”, nu
  „Overture Maps” (regula din CLAUDE.md); trecerea pe OpenStreetMap nu mai pierde punctele.
- **Vizualizatorul PDF:** evidențiază doar citatul (pe BCR, 14 fragmente colorate → 5);
  „Deschide originalul” refuză orice nu e `http(s)` (un `u=javascript:…` devenea link executabil).
- **Versus:** limita de 3 bănci se aplică de la deschidere (înainte, a patra se tăia în tăcere).
- **Google, afișări:** „din {data}” e tradus „available from”, nu „since”.
- **Harta și vizualizatorul** se încarcă doar când se deschid: pachetul principal a scăzut
  de la ~2,6 MB la 1,39 MB.

## Ce s-a verificat și ce nu

Fiecare pagină a fost comparată cu cea veche, pe capturi și pe cifre, în română și
engleză, cu orice cerere în afara `localhost` blocată în testele automate (fundalul hărții
lipsea în capturi, intenționat). Consola fără erori pe toate paginile.

- **Pe date reale** (`mip_stack`, 05.10.2026): 2.1, 2.2, 2.3, rețelele sociale (120),
  Google (16.765 de reclame), 683 de locații, 140 de indici, 900 de schimbări de preț,
  6.332 de surse, 5.396 de valori în coadă, PDF-urile BCR din Bronze.
- **Doar pe date sintetice sau ca stări goale**, fiindcă pe laptopul lui Nicolae lipsesc:
  campaniile și comunicatele (goale în bază), Bing și YouTube (fără fișiere în `output/`),
  catalogul Libra (0 rânduri), IRCC (lipsă). Merită o trecere pe baza ta.
- **Rulările manuale** nu s-au putut porni cap-coadă: serverul refuză cererile de pe alt
  port, iar Vite e pe :5173. Verificarea Host/Origin/token n-a fost slăbită.

## Baza folosită la teste

Baza `mip` de pe laptopul lui Nicolae n-avea migrările 019–026, deci nici aplicația veche nu
putea deschide Overview acolo. Testele au rulat pe o copie, `mip_stack`, cu migrările aplicate;
`mip` n-a fost atinsă. Migrările finale sunt la tine. Datele Google au fost copiate în
`output/reclame/google_2026-09-30/` (structura pe care o caută `app/server.py`), local, nu în git.

## Ce rămâne deschis

1. **Livrarea interfeței pe server.** `web/dist` nu e servit de nimeni: `app/server.py`
   livrează tot `app/`. Pentru instalare trebuie servit `web/dist` de același server care
   răspunde la `/api` și `/pdf` (cel mai mic pas: `app/server.py` să servească `web/dist`),
   sau serverul Fastify din stack-ul SCC. Decizia e a lui Doru, care face instalarea.
2. **Urcarea în `Libra-Bank/marketing-command-center`**, cum a cerut Doru, după ce te uiți.
3. **CLAUDE.md** descrie încă doar `app/` (tabelul de verificări, regula ghilimelelor din
   `<script>`): trebuie adăugat `web/` cu `npm run typecheck && npm run build`.
4. **`app/index.html`, `harta.html`, `pdf.html`** rămân până se decide livrarea; după aceea
   se pot șterge.
5. **Engleza** — verificată de un om din bancă.

## Commiturile

```
801e1a8 restul paginilor: Rețea, harta, Context, Istoric, Versus, Fișă bancă, Surse, Coadă, PDF
8029d09 structura comună pentru restul paginilor
f1743b4 2.2 Rate, 2.3 Aplicații și 2.4 Campanii
afbed43 structura comună pentru 2.2, 2.3 și 2.4
b4c390e favicon-ul Libra și mesajul „serverul de date nu răspunde”
e0ae83f corecturile din revizia traducerilor
2d12099 Overview și 2.1, plus traducerea RO/EN a tuturor textelor
```
