# Vox: bula din dreapta jos, aceeași pe toate paginile

Data: 09.10.2026. Ramura `vox-chatbot` (intră în PR #7). Design aprobat în discuție cu Nicolae Cherascu, pe întrebări.

## Ce vrea utilizatorul

Vox se deschide azi dintr-un buton din bara laterală, sub meniu („Întreabă-l pe Vox”). Utilizatorul vrea intrarea în
Vox ca widgetul de chat de pe reginamaria.ro: o bulă rotundă, plutitoare, în colțul din **dreapta jos**, aceeași pe
toate paginile, care nu încurcă pe nicio pagină.

Decizii (09.10.2026):
- **La clic**, bula duce pe pagina Vox (`#/vox`). Nu se deschide un panou peste pagină.
- **Locul:** dreapta jos, ca la Regina Maria.
- **Textul** („Întreabă-l pe Vox” / „Ask Vox”) apare doar la hover sau la focus de la tastatură.
- **Butonul Vox din bara laterală dispare.** Bula devine singura intrare din meniu spre Vox. Linkurile directe
  (`#/vox`, `#/vox?c=<conversație>`) merg în continuare.

Criterii de reușită:
- bula apare în același loc, cu aceeași mărime, pe toate paginile din cadrul aplicației, mai puțin pe pagina Vox;
- derulat până jos, niciun element pe care se poate da clic (buton, link, câmp, paginare) nu stă sub bulă;
- un sertar sau o fereastră modală deschisă acoperă bula, nu invers;
- la hover apare textul, iar clicul duce pe `#/vox`;
- în RO și EN, în tema luminoasă și în cea întunecată, consola rămâne curată.

## Ce nu intră

- **Panoul de chat peste pagină.** Nu a fost ales (09.10.2026).
- **Bula pe ecranele pe tot ecranul:** harta (`#/harta`) și vizualizatorul PDF (`#/document`). Sunt în afara cadrului
  aplicației, fără bară laterală, și au propriile controale în colțuri.
- **Textul mereu vizibil sau un îndemn care apare o dată pe sesiune.** Nu au fost alese.

## Designul

- **Componenta.** `VoxBula` din `web/src/components/` devine iconița unui `FloatButton` din Ant Design (stack-ul SCC,
  antd 5.22; niciun pachet nou), cu `tooltip` pentru textul de la hover și cu navigarea spre `/vox`.
  - Stă într-o componentă mică, `web/src/layout/BulaVox.tsx`, pusă o singură dată în `AppShell`. Așa e identică pe
    toate paginile.
  - Pe ruta `/vox` componenta nu se randează.
- **Culorile.** Bula e rotundă, cu sigla în culoarea de accent a temei (`--accent`, cu forma ei din tema
  întunecată), prin tokenii AntD din `web/src/theme.ts` sau prin variabilele CSS ale temei. Nicio culoare scrisă direct.
- **Locul exact:**
  - zona principală (`main`) se derulează singură și are bara de derulare pe dreapta; bula stă la stânga barei, ca să
    nu o acopere;
  - bula stă deasupra marginii de jos, cu distanța obișnuită a unui `FloatButton`.
- **Spațiul de jos.** `main` are azi `padding-bottom: 60px`. El crește cât e nevoie (bula plus distanța ei), astfel
  încât, derulat până la capăt, ultimul tabel sau paginarea să rămână deasupra bulei.
- **Straturile.** Bula rămâne sub sertarele AntD (`Drawer`, z-index 1000: 2.1, Versus, Android, Capturi) și sub
  ferestrele modale. Un `FloatButton` are implicit un z-index mai mic decât ele; se verifică, nu se presupune.
- **Bara laterală.** Iese linkul `vox-nav` din `nav .jos`, cu regulile lui CSS (`nav a.vox-nav*` din `global.css`).
  - Piciorul barei (sumarul, utilizatorul, limba, tema) rămâne.
  - Comentariul din `AppShell` despre încăpere la 720 px rămâne adevărat; cu un rând mai puțin, meniul încape mai ușor.
- **Textele.** Cheia `vox.nav.buton` („Întreabă-l pe Vox” / „Ask Vox”) rămâne și devine textul de la hover al bulei,
  plus eticheta pentru cititoarele de ecran (`aria-label`). Nicio cheie nouă, dacă textul ajunge.

## Verificarea

- **`npm run typecheck`** și build-ul de verificare într-un dosar temporar (nu `npm run build`).
- **Un script Playwright** (Edge, pe :5173, cu API-ul pe un server temporar):
  - **Paginile:** toate paginile din cadrul aplicației. Utilizatorul local e admin, deci intră și Logging și Rulare
    manuală.
  - **Combinațiile:** RO luminos și EN întunecat, la 1366×768 și la 1920×1080.
  - **Ce verifică:**
    - bula există și are același dreptunghi pe fiecare pagină (în limita unui pixel), iar pe `#/vox` lipsește;
    - derulat până la capăt, niciun `a`, `button`, `input`, `[role=button]` sau `.ant-pagination` nu se intersectează
      cu dreptunghiul bulei;
    - cu sertarul din 2.1 deschis, punctul din mijlocul bulei aparține sertarului (`elementFromPoint`), nu bulei;
    - la hover apare textul în limba paginii, iar clicul duce pe `#/vox`, fără eroare;
    - bara laterală nu mai are linkul Vox;
    - consola rămâne curată.
  - **Capturile** (o pagină cu tabel lung, o pagină cu paginare, pagina cu sertarul deschis, ambele teme) se verifică
    cu ochii.
- **`python app/verifica_pagini.py`** pe serverul temporar: 0 pagini cu erori.
- **Testele Python** nu sunt atinse. Le rulez totuși o dată, ca dovadă că nimic din `app/` nu s-a mișcat.

## Fișiere

- `web/src/layout/BulaVox.tsx` (nou), `web/src/layout/AppShell.tsx` (bula intră, linkul `vox-nav` iese).
- `web/src/styles/global.css` (regulile `vox-nav` ies; `main` primește spațiul de jos; regula bulei, dacă tokenii
  AntD nu ajung).
- `web/src/i18n/dict/vox.ts`: doar dacă e nevoie de o cheie nouă (de pildă un comentariu care pomenește bara).
- `README.md`, secțiunea Vox: o propoziție despre noua intrare. Harta Serena (`cod/harta`): `BulaVox`.

## De știut la unirea cu `main`

`origin/main` are 4 commituri noi (Administrare / Utilizatori) care ating și ele `AppShell.tsx` (4 rânduri) și
`global.css` (2 rânduri). PR #7 se unea fără conflicte (`git merge-tree`, 09.10.2026). După schimbarea asta se verifică
din nou, iar un conflict mic se rezolvă la unire. `main` nu se aduce acum în ramură: commitul `05d6150` aduce o
schimbare de bază (rolurile) care ar strica serverul local fără migrare.
