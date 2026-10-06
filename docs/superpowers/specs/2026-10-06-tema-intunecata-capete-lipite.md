# Tema întunecată și capete de tabel lipite: design

06.10.2026 · ramura `tema-intunecata` · interfața React (`web/`)

## 1. Ce se cere

Robert, 06.10.2026: un dark mode „făcut foarte bine, să nu existe probleme de înțelegere a logo-urilor sau a
textului sau a paginii”; și capul tabelului (ex. la Produse, „Administrare cont” cu descrierea dedesubt) „să se
vadă și dacă dau scroll în jos, ca să știi mereu pe ce categorie ești”, peste tot unde se aplică.

Criterii de reușită, fiecare verificabil:

1. Comutator cu trei stări, **Luminos / Întunecat / Ca sistemul**, în subsolul meniului, lângă RO/EN. Alegerea
   rămâne după reîncărcare; implicit: Ca sistemul (comportamentul de azi).
2. Comutarea schimbă imediat toată interfața: componentele Ant Design, culorile proprii, harta, barele de
   derulare și controalele native. Fără reîncărcare. „Ca sistemul” urmează și o schimbare din Windows făcută
   cu aplicația deschisă.
3. La deschidere nu apare niciun cadru în tema greșită (fără fulger alb în modul întunecat).
4. Tot textul trece WCAG AA în ambele moduri: 4,5:1, respectiv 3:1 pentru text mare și elemente grafice.
   Verificat automat pe paginile randate.
5. Toate cele 30 de logo-uri de bănci se citesc în ambele moduri.
6. În orice tabel mai înalt decât ecranul, rândul de antet (numele coloanei și descrierea ei) rămâne vizibil
   sub bara de filtre când derulezi în jos. În tabelele mai late decât ecranul, prima coloană (banca sau
   aplicația) rămâne vizibilă când derulezi la dreapta.
7. Nimic altceva nu se schimbă: `npm run typecheck` și `npm run build` trec; în modul luminos, paginile arată
   ca înainte, cu excepția capetelor lipite și a descrierii din capul tabelului, puțin mai închisă (4.7).

## 2. În afara scopului

- Aplicația veche (`app/index.html`).
- Explicațiile care azi apar doar la hover (inventar: ~36 ar încăpea ca subtitlu vizibil). Pas separat, dacă se cere.
- Variante întunecate ale logo-urilor (varianta B, respinsă) și filtre de inversare a culorilor (varianta C).
- Paleta existentă: se schimbă doar ce cere contrastul.
- Rămân luminoase intenționat: foaia PDF (ca hârtia), popup-urile hărții (MapLibre le desenează albe),
  etichetele albe ale băncilor de pe hartă.

## 3. Starea de azi

- **Tema urmează doar Windows.** `web/src/main.tsx` (`useIntunecat`, `matchMedia`) alege între paletele
  `LUMINOS` / `INTUNECAT` din `web/src/theme.ts`, iar Ant Design primește `darkAlgorithm`. Aceleași valori sunt
  scrise încă o dată, de mână, în `web/src/styles/global.css` (`:root` și `@media (prefers-color-scheme: dark)`).
  Nimic nu le ține sincronizate.
- **Harta** își alege stilul o dată, la import (`web/src/pages/harta/Mapa.tsx:13`): positron sau dark-matter.
- Nu există `color-scheme` nici `<meta name="color-scheme">`: barele de derulare și controalele native rămân luminoase.
- **Contrast**, calculat pe paletele de azi: toate perechile principale trec, cu două excepții:
  - `.cap-d` (descrierea din capul tabelului), modul luminos: 4,20:1, din cauza `opacity: .85`;
  - legenda hărții (`retea.css:34-41`, text și chenar `#fff` pe `--accent`), modul întunecat: 2,05:1.
- **Logo-uri:** 30 de fișiere în `app/logos/`, servite de `/api/logos`. 11 sunt închise la culoare, fără fundal,
  și dispar pe fundal închis: BRD, CEC, UniCredit, Libra, Raiffeisen, ING, TBI, Garanti, Patria, Nexent,
  BCR Locuințe. Le-ar mai putea avea și PNG-urile transparente: BCR, BID, Cetelem, Techventures, BRCI.
  Harta le pune deja pe alb (`.ht-logo`, `harta/desen.ts`). Tabelele și fișa băncii, nu.
- **Alte culori fixe:** `components/BareStele.tsx` (`#7fb893`, `#d9a441`). Restul sunt fixe intenționat și rămân:
  popup-ul hărții, foaia PDF, marcajul din citate, culorile rețelelor sociale, etichetele de pe hartă.
- **Capete de tabel.** Trei tipare există deja:
  - chenar propriu de 70vh cu antetul fix: Android, Istoric, catalogul din Fișa băncii;
  - bara de filtre măsurată cu `ResizeObserver` și variabila `--sub-bara`: `useSubBara` din `Versus.tsx`;
  - prima coloană fixă: `android.css:14-16`.

  Pe restul paginilor (Produse, Rate, Mobil, Campanii, Coadă, Surse, Overview, Context), capul dispare la
  derulare. `.ant-table-content { overflow-x: auto }` (`global.css:106`) face din fiecare tabel un container de
  derulare, deci un `position: sticky` simplu pe antet nu se lipește de pagină.

## 4. Design: tema

### 4.1 Starea
- Tipul `Tema = 'luminos' | 'intunecat' | 'sistem'`.
- Un context React (`TemaProvider`, lângă `LangProvider`) și un hook `useTema()` care întorc:
  - `tema` (alegerea);
  - `intunecat` (rezultatul efectiv);
  - `setTema`.
- Alegerea se salvează în `localStorage['mcc-tema']`, după modelul `mcc-lang`.
- Orice altă valoare, lipsa ei sau o eroare de acces la stocare înseamnă `'sistem'`. Citirea și scrierea sunt
  în `try/catch`.
- În starea `'sistem'`, aplicația ascultă `matchMedia('(prefers-color-scheme: dark)')` și se schimbă din mers.

### 4.2 Aplicarea pe pagină
- Pe `<html>` stau mereu `data-theme="light|dark"`, cu valoarea efectivă, și `color-scheme` potrivit.
- **`web/public/tema-init.js`:**
  - script clasic, sincron, pus în `<head>` înainte de orice stil;
  - citește aceeași cheie, cu aceeași validare, și pune atributul înainte de primul cadru;
  - e fișier separat, nu script inline, ca să meargă și sub un CSP strict (`script-src 'self'`), când serverul
    de producție va avea unul;
  - React reia controlul la montare.
- `<meta name="color-scheme" content="light dark">` în `web/index.html`.
- **`global.css`:**
  - `:root` rămâne paleta luminoasă, cu `color-scheme: light`;
  - blocul `@media (prefers-color-scheme: dark)` devine `:root[data-theme="dark"]`, cu `color-scheme: dark`;
  - celelalte 11 fișiere CSS folosesc doar variabile, deci nu se ating.

### 4.3 Ant Design
- `ConfigProvider` primește `temaMip(intunecat)` din `useTema()`. `useIntunecat` dispare.
- Al doilea `ConfigProvider` (`Document.tsx`, butoanele de pe banda vișinie) rămâne cum e.
- **Sursa unică a paletei.** Valorile stau în continuare în `theme.ts` și în `global.css`. Un script Node fără
  dependențe (`web/scripts/verifica_tema.mjs`) compară cele două seturi, culoare cu culoare, și oprește
  `npm run typecheck` dacă diferă.

### 4.4 Comutatorul
- Un `Segmented` cu trei opțiuni, în `.picior` din `layout/AppShell.tsx`, lângă RO/EN.
- Fiecare opțiune are o icoană (soare, lună, monitor) și un nume accesibil și tooltip în dicționar (RO/EN).
- Meniul întreg încape în continuare fără derulare la 720px înălțime.

### 4.5 Harta
- `Mapa.tsx` primește `intunecat` din `useTema()`. Constanta de la import dispare.
- La schimbare, harta trece pe celălalt stil (positron ↔ dark-matter) fără reîncărcarea paginii. Straturile,
  imaginile și ascultătorii proprii se refac după încărcarea stilului.
- Centrul, zoom-ul și banca aleasă se păstrează.

### 4.6 Logo-urile (varianta A, aleasă de Robert)
- Toate imaginile de logo primesc o clasă comună, `.sigla`. Locuri:
  - `EtichetaBanca` din `components/comune.tsx`;
  - `.bk-logo` din `Banca.tsx`;
  - logo-ul din popup-ul hărții;
  - `.ht-logo`, care e deja pe alb.
- O singură regulă CSS: în modul întunecat, `.sigla` are fundal alb, câțiva pixeli de margine interioară și
  colțuri rotunjite. În modul luminos nu se schimbă nimic.
- Marginea interioară nu schimbă locul ocupat de logo. Tabelele nu sar la comutare.

### 4.7 Culorile fixe și contrastul
- **Legenda hărții:** text și chenar pe `var(--on-accent)`.
- **`BareStele`:** cele două culori fixe devin variabile noi, `--stele-4` și `--stele-2`, definite în ambele moduri.
- **`.cap-d`:** fără opacitate (culoarea `--muted`, 5,86:1 în modul luminos).
- Ce găsește verificarea automată (secțiunea 7) se repară în variabile, nu pe pagini.

## 5. Design: capete de tabel lipite

### 5.1 Comportament
- **Lipirea:** rândul de antet se lipește sub bara de filtre a paginii, cu numele și descrierea coloanei. Pe
  paginile fără bară, se lipește sus de tot în zona derulată (`<main>`).
- **Aspectul:** fundal opac (`--surface`) și o linie dedesubt. Stă sub bara de filtre, peste celule, și sub
  sertare și meniurile Ant Design.
- **Tabelele late:** prima coloană se lipește la stânga, cu fundalul rândului ei (rândul Libra își păstrează
  nuanța). Celula din colț, antetul primei coloane, stă deasupra amândurora.
- **Sortarea** din antet merge ca înainte.

### 5.2 Mecanism
- **Bara de filtre:** `useSubBara` se mută din `Versus.tsx` într-un loc comun. Bara de filtre a fiecărei pagini
  își publică înălțimea măsurată în variabila `--sub-bara`. Pe ecrane înguste, bara se rupe pe mai multe rânduri.
- **`Tabel.tsx`:** capătă comportamentul pentru toate tabelele care trec prin el. Varianta de implementare
  se alege în plan, printr-o probă:
  - `sticky` din Ant Design (`offsetHeader` și `getContainer` pe `<main>`, cu `scroll.x` pentru lățime);
  - sau CSS `position: sticky` pe antet, cu derularea orizontală mutată într-un loc care nu rupe lipirea.
- **Criteriul de alegere:** lipirea verticală și derularea orizontală merg împreună, iar antetul rămâne aliniat
  cu coloanele.
- **Tabelele cu chenar propriu de 70vh** (Android, Istoric, catalogul din Fișa băncii) au deja antetul fix și
  rămân cum sunt.
- **Tabelele construite altfel** (Ant Design direct, `<table>` simplu, grila din Versus) se inventariază în plan.
  Primesc același comportament acolo unde pot fi mai înalte decât ecranul.

## 6. Securitate

- Nu se ating API-ul, baza de date, autentificarea sau serverul. Nu e nevoie de threat model.
- **Valoarea din `localStorage`:** trece printr-o listă albă de trei valori și nu ajunge niciodată ca text liber
  în HTML, CSS sau atribute.
- **`tema-init.js`:**
  - fișier static de pe aceeași origine;
  - fără `eval`, fără `innerHTML`, fără date din afară;
  - compatibil cu un CSP strict.
- **Dependențe:** nicio dependență nouă de producție. `axe-core` intră doar ca `devDependency` (versiune
  fixată), pentru verificarea contrastului, și nu ajunge în pachetul aplicației.
- **Înainte de merge:** audit de securitate pe tot diff-ul față de `main`, apoi review de cod.

## 7. Verificare

- `npm run typecheck` (include acum verificarea paletei) și `npm run build`.
- Un script Playwright (Python, deja în proiect), păstrat în repo pentru rulări viitoare, care trece prin toate
  paginile din meniu, plus hartă și documentul PDF, la 1440×900, în ambele moduri. El:
  - salvează capturi de ecran, revăzute vizual (de un subagent și de Robert);
  - rulează regula `color-contrast` din axe-core. Pragul este zero încălcări, iar excepțiile, dacă rămân, se
    listează cu motiv;
  - pe Produse, Rate, Mobil și Coadă: derulează 1500px și verifică faptul că antetul tabelului e în ecran,
    imediat sub bara de filtre. Pe Produse și Android derulează și la dreapta și verifică faptul că prima
    coloană e încă vizibilă;
  - deschide pagina cu `mcc-tema=intunecat` deja salvat și verifică că `data-theme="dark"` există înainte să
    pornească React (fără fulger);
  - comută tema din meniu pe Hartă și verifică schimbarea stilului fără reîncărcare.
- Comparație vizuală în modul luminos, înainte și după: diferențele permise sunt cele din criteriul 7.

## 8. Fișiere atinse (orientativ)

`web/index.html`, `web/public/tema-init.js` (nou), `web/src/main.tsx`, `web/src/theme.ts`, un modul nou pentru
starea temei, `web/src/layout/AppShell.tsx`, `web/src/i18n/dict/*.ts`, `web/src/styles/global.css`,
`web/src/styles/retea.css`, `web/src/components/{Tabel,comune,BareStele}.tsx`, `web/src/pages/Banca.tsx`,
`web/src/pages/harta/Mapa.tsx`, `web/src/pages/Versus.tsx` (hook-ul mutat), paginile cu tabele construite
altfel, `web/scripts/verifica_tema.mjs` (nou), scriptul Playwright (nou), `web/package.json`.

## 9. Riscuri

- **Lipirea și derularea orizontală.** Cel mai probabil punct de eșec. De aceea mecanismul se alege printr-o
  probă, în primul task al părții de capete.
- **Schimbarea stilului hărții** pierde straturile proprii, dacă refacerea lor nu e legată de încărcarea stilului.
- **Paleta în două locuri:** acoperită de verificarea din `typecheck`.
- **Logo-urile cu fundal propriu opac** (`vista.png`, `banorient.jpg`, `creditcoop.jpg`) primesc chenar alb în
  jurul unui dreptunghi alb. Nu deranjează, dar se verifică în capturi.
