# Tema întunecată și capete de tabel lipite — plan de implementare

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** comutator de temă (Luminos / Întunecat / Ca sistemul) care schimbă toată interfața React fără reîncărcare și fără fulger, cu logo-uri și text lizibile; capul tabelelor (nume + descriere) lipit sub bara de filtre la derulare, prima coloană fixă la derularea pe orizontală.

**Architecture:** o stare de temă (context React, `localStorage['mcc-tema']`) pune `data-theme` pe `<html>`; un script static din `public/` face același lucru înainte de primul cadru. CSS-ul trece de la `@media (prefers-color-scheme)` la `[data-theme="dark"]`, Ant Design primește `darkAlgorithm` din aceeași stare, harta își schimbă stilul din mers. Capul lipit e în componenta comună `Tabel`, cu `sticky` din Ant Design plus un rând „fantomă” care ține coloanele cel puțin cât capul (varianta V5, aleasă prin proba din 06.10.2026, vezi „Decizii luate”).

**Tech Stack:** React 18, Vite 6, Ant Design 5.29, MapLibre 4, TypeScript 5.7; verificări în browser cu Playwright (Python, deja în proiect) și axe-core (doar unealtă de dezvoltare).

**Spec:** `docs/superpowers/specs/2026-10-06-tema-intunecata-capete-lipite.md`

## Global Constraints

- Lucrezi DOAR în worktree-ul `C:\Users\robert.postolache\Downloads\mip-tema`, ramura `tema-intunecata`. Nu atingi `C:\Users\robert.postolache\Downloads\mip` (copia de pe `main`). Fără `git push`.
- Commit-uri în română, scurte, prefix de zonă (`web: …`), fără `Co-Authored-By`.
- Shell: Git Bash. Node nu e în PATH: `export PATH="/c/Program Files/nodejs:$PATH"`. npm 11 blochează scripturile de instalare (esbuild merge fără ele): NU aproba nimic cu `npm install-scripts`.
- Python: `/c/Users/robert.postolache/AppData/Local/Programs/Python/Python314/python.exe`, cu `PYTHONIOENCODING=utf-8`.
- Interfața de test: Vite din worktree pe **http://localhost:5174** (pornit de controller, cu HMR), API-ul pe :8765. Nu le opri și nu porni altele. Dacă 5174 nu răspunde, raportează BLOCKED.
- Nu modifici `app/` (aplicația veche și serverul Python), datele, migrările, `vite.config.ts`.
- Nicio dependență nouă de producție. Singura dependență nouă: `axe-core@4.14.0`, `devDependency` în `web/`, versiune exactă (Task 7).
- Valori exacte: cheia `mcc-tema`; valorile `luminos` | `intunecat` | `sistem` (orice altceva = `sistem`); pe `<html>`: `data-theme="light"` sau `data-theme="dark"`.
- Orice text nou pentru utilizator stă în dicționar (`web/src/i18n/dict/*.ts`), ca pereche `[română, engleză]`.
- Stilul codului existent: TypeScript fără punct și virgulă, ghilimele simple, comentarii în română care spun DE CE.
- La finalul fiecărui task: `npm run typecheck` și `npm run build` trec (din rădăcina worktree-ului).

## Review Focus

1. `localStorage` inaccesibil (navigare privată, politică de firmă) → aplicația pornește, tema urmează sistemul. Testat în Task 1 (`v_tema`, cazul „fără localStorage”).
2. Valoare străină în `mcc-tema` (versiune veche, alt program, text cu ghilimele sau HTML) → tratată ca „sistem”, nu ajunge niciodată în pagină ca text. Testat în Task 1 (cazul `gunoi"><b>`).
3. Sortarea din capul lipit → clicul pe antet schimbă ordinea exact ca înainte. Testat în Task 6 (`v_capete`, `aria-sort`).
4. Tabel fără rânduri după filtrare (căutare fără rezultat) → mesajul de „nimic de afișat”, fără erori JavaScript. Testat în Task 6.
5. Tabelele din chenare cu derulare proprie (Android, Istoric, catalog) și din sertare → NU primesc lipirea pe pagină (ar ieși din chenar sau din sertar). Testat în Task 6 (Istoric) și prin `lipit={false}` pe toate cele 8 locuri.

## Decizii luate (controller, înainte de plan)

- **Mecanismul capului lipit (spec 5.2), proba din 06.10.2026 pe Produse, la 1440, 1280 și 1000 px:**
  - V1 (`sticky` AntD + `scroll.x: 'max-content'`): lipește, dar tabelul nu mai încape la 1440 (textul nu se mai rupe) și o coloană iese din aliniere.
  - V3 (chenar cu derulare proprie): merge, dar derulare în derulare.
  - **V5, aleasă:** `sticky` + `scroll.x: '100%'` + `tableLayout: 'auto'` + prima coloană `fixed: 'left'` + rând fantomă în corp (textul capului, invizibil, înălțime zero, cu locul săgeții de sortare rezervat alături) + tabelul capului cu `table-layout: fixed; width: 1px`. Rezultat: lipit exact sub bară, 0 coloane nealiniate la toate lățimile, aceeași lățime ca azi, prima coloană fixă la 1000 px.
- **Versus** își păstrează hook-ul propriu: `useSusCap` (Task 6) găsește singur bara de dinaintea tabelului, deci nu e nevoie să mutăm hook-ul din Versus (abatere mică de la spec 5.2, fără efect pentru utilizator).
- **Popup-ul hărții** nu primește `.sigla`: e mereu alb (spec 2), deci n-are nevoie.
- `tema-init.js` pune și `style.colorScheme`, nu doar atributul: în dezvoltare CSS-ul vine prin JavaScript, iar `color-scheme: dark` face fundalul implicit închis până atunci (fără fulger alb).

## Fișiere

| fișier | ce face |
|---|---|
| `web/public/tema-init.js` (nou) | tema pe `<html>` înainte de primul cadru |
| `web/index.html` | `<meta name="color-scheme">` și scriptul de mai sus |
| `web/src/tema/context.ts` (nou) | tipul `Tema`, cheia, validarea, contextul |
| `web/src/tema/index.tsx` (nou) | `TemaProvider`, `useTema()` |
| `web/src/main.tsx` | AntD primește tema din `useTema()` |
| `web/src/theme.ts` | doar comentariul |
| `web/src/styles/global.css` | blocul întunecat pe atribut, `color-scheme`, sigle, culori stele, cap lipit |
| `web/src/layout/AppShell.tsx` | comutatorul |
| `web/src/i18n/dict/comun.ts` | textele comutatorului |
| `web/scripts/verifica_tema.mjs` (nou) | paleta din `theme.ts` = cea din `global.css` |
| `web/package.json` | verificarea paletei în `typecheck`/`build`; `axe-core` dev |
| `web/src/pages/harta/Mapa.tsx` | stilul hărții urmează tema |
| `web/src/styles/retea.css` | text lizibil pe insignele legendei și pe grupuri |
| `web/src/components/comune.tsx`, `web/src/pages/Banca.tsx`, `web/src/pages/versus/CardBanca.tsx` | clasa `.sigla` pe logo-uri |
| `web/src/components/BareStele.tsx` | culorile fixe devin variabile |
| `web/src/components/lipire.tsx` (nou) | `useSusCap`, `propsLipit`, `RandFantoma` |
| `web/src/components/Tabel.tsx` | capul lipit, prop `lipit` |
| 7 fișiere cu tabele în chenare/sertar | `lipit={false}` |
| `web/src/pages/campanii/Google.tsx` | același cap lipit pe tabelul AntD direct |
| `web/verifica_ui.py` (nou) | verificările în browser |
| `.gitignore` | `web/.capturi/` |

---

### Task 1: Starea temei, aplicată înainte de primul cadru

**Files:**
- Create: `web/public/tema-init.js`, `web/src/tema/context.ts`, `web/src/tema/index.tsx`, `web/verifica_ui.py`
- Modify: `web/index.html`, `web/src/main.tsx`, `web/src/theme.ts:3-8`, `web/src/styles/global.css:3-25`

**Interfaces:**
- Produces: `type Tema = 'luminos' | 'intunecat' | 'sistem'`; `CHEIE_TEMA = 'mcc-tema'`; `valideazaTema(v: unknown): Tema`; `interface TemaState { tema: Tema; intunecat: boolean; setTema: (t: Tema) => void }`; `TemaProvider`; `useTema(): TemaState` (import din `'../tema'` / `'./tema'`). În `web/verifica_ui.py`: `verifica(conditie, ce) -> bool`, `deschide(b, url, *, tema=None, sistem='light', lat=1440, inalt=900, fara_react=False, fara_stocare=False, cereri=None) -> Page`, `asteapta(pg, js, ms=5000) -> bool`, `incarcata(pg) -> bool`, `inchide(pg)`, registrul `VERIFICARI: dict[str, Callable[[Browser, str], None]]`.

- [ ] **Step 1: Scrie verificatorul cu verificarea `tema` (testul care pică)**

`web/verifica_ui.py`:

```python
"""Verificările interfeței React în browser, cu Playwright: tema și capetele de tabel lipite.

Cere serverul API (`python app/server.py`, :8765) și interfața (`npm run dev`) pornite.
    python web/verifica_ui.py                      # toate, pe http://localhost:5173
    python web/verifica_ui.py --doar tema,capete   # doar unele
    python web/verifica_ui.py --url http://localhost:5174
Iese cu 1 dacă pică ceva. Capturile (`capturi`) merg în web/.capturi/, care nu intră în git.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Callable

from playwright.sync_api import Browser, Page, sync_playwright

AICI = Path(__file__).resolve().parent
ESECURI: list[str] = []


def verifica(conditie: bool, ce: str) -> bool:
    print(('ok    ' if conditie else 'PICĂ  ') + ce)
    if not conditie:
        ESECURI.append(ce)
    return conditie


def deschide(b: Browser, url: str, *, tema: str | None = None, sistem: str = 'light', lat: int = 1440,
             inalt: int = 900, fara_react: bool = False, fara_stocare: bool = False,
             cereri: list[str] | None = None) -> Page:
    """Pagină nouă, cu tema salvată (`mcc-tema`) și tema sistemului date dinainte.
    `fara_react` blochează main.tsx (ce se vede înainte de React); `fara_stocare` face localStorage inaccesibil."""
    ctx = b.new_context(viewport={'width': lat, 'height': inalt}, color_scheme=sistem)
    if fara_stocare:
        ctx.add_init_script("Object.defineProperty(window, 'localStorage', { get() { throw new Error('blocat') } })")
    elif tema is not None:
        ctx.add_init_script(f"localStorage.setItem('mcc-tema', {json.dumps(tema)})")
    if cereri is not None:
        ctx.on('request', lambda r: cereri.append(r.url))
    pg = ctx.new_page()
    erori: list[str] = []
    pg.on('pageerror', lambda e: erori.append(str(e)))
    pg.erori = erori  # citite în inchide()
    if fara_react:
        pg.route('**/src/main.tsx*', lambda r: r.abort())
    pg.goto(url)
    return pg


def asteapta(pg: Page, js: str, ms: int = 5000) -> bool:
    try:
        pg.wait_for_function(js, timeout=ms)
        return True
    except Exception:
        return False


def incarcata(pg: Page) -> bool:
    """Pagina a randat ceva în <main> și datele au avut timp să vină."""
    ok = asteapta(pg, "!!document.querySelector('#principal section, #principal .ant-table-wrapper, .ht-zona')", 20000)
    pg.wait_for_timeout(1500)
    return ok


def inchide(pg: Page) -> None:
    if pg.erori:
        verifica(False, f'erori JavaScript pe {pg.url}: {pg.erori[:3]}')
    pg.context.close()


def v_tema(b: Browser, url: str) -> None:
    # 1. Înainte de React (main.tsx blocat): tema-init.js pune singur tema pe <html>.
    cazuri = [(None, 'light', 'light'), (None, 'dark', 'dark'), ('intunecat', 'light', 'dark'),
              ('luminos', 'dark', 'light'), ('sistem', 'dark', 'dark'),
              ('gunoi"><b>', 'dark', 'dark'), ('gunoi', 'light', 'light')]
    for tema, sistem, asteptat in cazuri:
        pg = deschide(b, url, tema=tema, sistem=sistem, fara_react=True)
        pg.wait_for_load_state('domcontentloaded')
        got = pg.evaluate("[document.documentElement.dataset.theme, document.documentElement.style.colorScheme]")
        verifica(got == [asteptat, asteptat], f'înainte de React: mcc-tema={tema!r}, sistem {sistem} → {asteptat} (am {got})')
        inchide(pg)
    pg = deschide(b, url, sistem='dark', fara_react=True, fara_stocare=True)
    pg.wait_for_load_state('domcontentloaded')
    got = pg.evaluate("document.documentElement.dataset.theme")
    verifica(got == 'dark', f'fără localStorage, înainte de React: urmează sistemul (am {got})')
    inchide(pg)
    # 2. Cu React: variabilele CSS urmează tema aleasă, nu pe a sistemului.
    for tema, sistem, fundal in (('intunecat', 'light', 'rgb(27, 21, 23)'), ('luminos', 'dark', 'rgb(245, 241, 236)')):
        pg = deschide(b, url, tema=tema, sistem=sistem)
        asteapta(pg, "!!document.querySelector('nav .picior .limba')", 15000)
        bg = pg.evaluate("getComputedStyle(document.body).backgroundColor")
        verifica(bg == fundal, f'fundalul paginii, tema {tema} pe sistem {sistem}: {bg}')
        inchide(pg)
    pg = deschide(b, url, sistem='dark', fara_stocare=True)
    verifica(asteapta(pg, "!!document.querySelector('nav .picior .limba')", 15000)
             and pg.evaluate("document.documentElement.dataset.theme") == 'dark',
             'fără localStorage: aplicația pornește și urmează sistemul')
    inchide(pg)
    # 3. „Ca sistemul” urmează o schimbare din Windows, fără reîncărcare.
    pg = deschide(b, url, tema='sistem', sistem='light')
    asteapta(pg, "!!document.querySelector('nav .picior .limba')", 15000)
    pg.emulate_media(color_scheme='dark')
    verifica(asteapta(pg, "document.documentElement.dataset.theme === 'dark'"), 'sistemul trece pe întunecat: pagina urmează')
    inchide(pg)


VERIFICARI: dict[str, Callable[[Browser, str], None]] = {
    'tema': v_tema,
}


def main() -> int:
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description='Verificările interfeței React în browser.')
    ap.add_argument('--url', default='http://localhost:5173')
    ap.add_argument('--doar', default='', help='separate prin virgulă: ' + ', '.join(VERIFICARI))
    a = ap.parse_args()
    alese = [x for x in a.doar.split(',') if x] or list(VERIFICARI)
    necunoscute = [x for x in alese if x not in VERIFICARI]
    if necunoscute:
        ap.error('verificări necunoscute: ' + ', '.join(necunoscute))
    with sync_playwright() as p:
        b = p.chromium.launch()
        for nume in alese:
            print(f'== {nume}')
            VERIFICARI[nume](b, a.url.rstrip('/'))
        b.close()
    print(f'\n{len(ESECURI)} verificări picate' if ESECURI else '\ntoate verificările au trecut')
    return 1 if ESECURI else 0


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 2: Rulează și confirmă că pică**

Run: `cd /c/Users/robert.postolache/Downloads/mip-tema && PYTHONIOENCODING=utf-8 /c/Users/robert.postolache/AppData/Local/Programs/Python/Python314/python.exe web/verifica_ui.py --url http://localhost:5174 --doar tema`
Expected: `PICĂ` la „înainte de React” (atributul lipsește: `[None, '']`) și la „fundalul paginii, tema intunecat pe sistem light”; exit 1.

- [ ] **Step 3: Contextul temei**

`web/src/tema/context.ts`:

```ts
import { createContext } from 'react'

/**
 * Tema: luminoasă, întunecată sau ca sistemul (implicit). Contextul stă separat de
 * provider din același motiv ca la limbă (i18n/context.ts): la reîncărcarea în
 * dezvoltare, paginile trebuie să găsească același context ca providerul montat.
 */
export type Tema = 'luminos' | 'intunecat' | 'sistem'

/** Aceeași cheie și aceeași validare ca în public/tema-init.js. */
export const CHEIE_TEMA = 'mcc-tema'
const TEME: readonly string[] = ['luminos', 'intunecat', 'sistem']

/** Orice altă valoare (lipsă, veche, străină) înseamnă „ca sistemul”: nu ajunge niciodată în pagină ca text. */
export function valideazaTema(v: unknown): Tema {
  return typeof v === 'string' && TEME.includes(v) ? (v as Tema) : 'sistem'
}

export interface TemaState {
  tema: Tema
  /** tema efectivă, după alegere și după sistem */
  intunecat: boolean
  setTema: (t: Tema) => void
}

export const TemaContext = createContext<TemaState>(null as never)
```

- [ ] **Step 4: Providerul**

`web/src/tema/index.tsx`:

```tsx
import { useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { CHEIE_TEMA, TemaContext, valideazaTema, type TemaState } from './context'

export type { Tema, TemaState } from './context'

const SISTEM_INTUNECAT = '(prefers-color-scheme: dark)'

function citesteTema() {
  try {
    return valideazaTema(localStorage.getItem(CHEIE_TEMA))
  } catch {
    return 'sistem' as const
  }
}

/**
 * Alegerea se ține minte în browser. public/tema-init.js a pus deja tema pe <html>
 * înainte de primul cadru; de aici React o ține la zi: la comutare și, pe „Ca
 * sistemul”, la o schimbare din Windows făcută cu aplicația deschisă.
 */
export function TemaProvider({ children }: { children: ReactNode }) {
  const [tema, setTemaState] = useState(citesteTema)
  const [sistemIntunecat, setSistemIntunecat] = useState(() => window.matchMedia(SISTEM_INTUNECAT).matches)
  useEffect(() => {
    const mq = window.matchMedia(SISTEM_INTUNECAT)
    const f = (e: MediaQueryListEvent) => setSistemIntunecat(e.matches)
    mq.addEventListener('change', f)
    return () => mq.removeEventListener('change', f)
  }, [])
  const intunecat = tema === 'intunecat' || (tema === 'sistem' && sistemIntunecat)
  useEffect(() => {
    const html = document.documentElement
    html.dataset.theme = intunecat ? 'dark' : 'light'
    html.style.colorScheme = intunecat ? 'dark' : 'light'
  }, [intunecat])
  const value = useMemo<TemaState>(() => ({
    tema,
    intunecat,
    setTema: (t) => {
      try {
        localStorage.setItem(CHEIE_TEMA, t)
      } catch {
        /* fără stocare: alegerea ține până la reîncărcare */
      }
      setTemaState(t)
    },
  }), [tema, intunecat])
  return <TemaContext.Provider value={value}>{children}</TemaContext.Provider>
}

export function useTema(): TemaState {
  return useContext(TemaContext)
}
```

- [ ] **Step 5: Scriptul de dinaintea primului cadru**

`web/public/tema-init.js`:

```js
/* Tema aleasă (localStorage „mcc-tema”), pusă pe <html> înainte de primul cadru, ca pagina
   să nu clipească în tema greșită. Aceeași validare ca în src/tema/context.ts: orice altă
   valoare înseamnă „ca sistemul”. Fișier separat, nu script inline: merge și sub un CSP
   cu script-src 'self'. `color-scheme` face și fundalul implicit închis până vine CSS-ul. */
(function () {
  var t = null
  try { t = localStorage.getItem('mcc-tema') } catch (e) { /* fără stocare: ca sistemul */ }
  var intunecat = t === 'intunecat' ||
    (t !== 'luminos' && window.matchMedia('(prefers-color-scheme: dark)').matches)
  var html = document.documentElement
  html.setAttribute('data-theme', intunecat ? 'dark' : 'light')
  html.style.colorScheme = intunecat ? 'dark' : 'light'
})()
```

În `web/index.html`, după `<link rel="icon" … />`:

```html
    <meta name="color-scheme" content="light dark" />
    <!-- tema aleasă, pusă pe <html> înainte de primul cadru (public/tema-init.js) -->
    <script src="/tema-init.js"></script>
```

(La `vite build` apare avertismentul că un `<script>` fără `type="module"` nu se împachetează: e voit, fișierul se copiază din `public/` ca atare.)

- [ ] **Step 6: CSS-ul pe atribut**

În `web/src/styles/global.css`:
- primul comentariu (rândurile 1-2) devine: `/* Paleta aplicației vechi (fildeș cald + vișiniu); aceleași valori stau în theme.ts pentru componentele AntD (verificat de scripts/verifica_tema.mjs). Tema întunecată vine din data-theme pe <html> (src/tema), nu direct din sistem. */`
- în blocul `:root {` adaugă ca prim rând `color-scheme: light;`
- `@media (prefers-color-scheme: dark) {` + `:root {` devin un singur `:root[data-theme="dark"] {`, cu `color-scheme: dark;` ca prim rând; scoate acolada în plus de la final. Valorile rămân identice.

- [ ] **Step 7: Ant Design din aceeași stare**

În `web/src/main.tsx`:
- șterge funcția `useIntunecat` (rândurile 38-48) și `useState` din importul React (rămâne `React, { useEffect }`);
- adaugă `import { TemaProvider, useTema } from './tema'`;
- în `CuTema`: `const intunecat = useIntunecat()` → `const { intunecat } = useTema()`;
- în randare, `TemaProvider` învelește `CuTema`, sub `LangProvider`:

```tsx
      <LangProvider>
        <TemaProvider>
          <CuTema />
        </TemaProvider>
      </LangProvider>
```

În `web/src/theme.ts`, comentariul de sus devine:

```ts
/**
 * Tema MIP peste Ant Design: aceeași paletă ca aplicația veche (fildeș cald +
 * vișiniu), luminoasă sau întunecată după alegerea din meniu (src/tema). Culorile
 * stau și ca variabile CSS în global.css, pentru elementele care nu sunt
 * componente AntD; scripts/verifica_tema.mjs verifică că sunt aceleași.
 */
```

- [ ] **Step 8: Verifică**

Run: `export PATH="/c/Program Files/nodejs:$PATH" && cd /c/Users/robert.postolache/Downloads/mip-tema && npm run typecheck && npm run build`
Expected: ambele trec (avertismentul despre `tema-init.js` e așteptat).

Run: `PYTHONIOENCODING=utf-8 /c/Users/robert.postolache/AppData/Local/Programs/Python/Python314/python.exe web/verifica_ui.py --url http://localhost:5174 --doar tema`
Expected: toate `ok`, „toate verificările au trecut”, exit 0. Dacă `fara_stocare` nu reușește să redefinească `localStorage` (eroare la `defineProperty`), raportează DONE_WITH_CONCERNS cu mesajul, nu ocoli verificarea.

- [ ] **Step 9: Commit**

```bash
git add web/public/tema-init.js web/index.html web/src/tema web/src/main.tsx web/src/theme.ts web/src/styles/global.css web/verifica_ui.py
git commit -m "web: tema aleasă (luminos / întunecat / ca sistemul), aplicată înainte de primul cadru"
```

---

### Task 2: Comutatorul din meniu

**Files:**
- Modify: `web/src/layout/AppShell.tsx:1-8, 50-60`, `web/src/i18n/dict/comun.ts` (înainte de `} as const`), `web/src/styles/global.css:56`, `web/verifica_ui.py`

**Interfaces:**
- Consumes: `useTema()`, `type Tema` din `web/src/tema` (Task 1); helperii din `web/verifica_ui.py` (Task 1).
- Produces: în meniu, `nav .picior .comutatoare` cu `.limba` (RO/EN) și `.tema` (Segmented cu 3 opțiuni, în ordinea luminos, intunecat, sistem). Verificatorul `comutator`.

- [ ] **Step 1: Verificarea `comutator` (pică)**

În `web/verifica_ui.py`, înainte de `VERIFICARI`:

```python
def v_comutator(b: Browser, url: str) -> None:
    pg = deschide(b, url, sistem='light')
    asteapta(pg, "!!document.querySelector('nav .picior .tema')", 15000)
    opt = pg.locator('nav .picior .tema .ant-segmented-item')
    verifica(opt.count() == 3, f'comutatorul are 3 opțiuni (am {opt.count()})')
    if opt.count() != 3:
        inchide(pg)
        return
    verifica(pg.evaluate("document.documentElement.dataset.theme") == 'light', 'implicit: ca sistemul (aici luminos)')
    pg.evaluate("window.__fara_reincarcare = 1")
    opt.nth(1).click()
    verifica(asteapta(pg, "document.documentElement.dataset.theme === 'dark'"), 'clic pe Întunecat: tema se schimbă')
    verifica(pg.evaluate("window.__fara_reincarcare === 1"), 'fără reîncărcarea paginii')
    verifica(pg.evaluate("localStorage.getItem('mcc-tema')") == 'intunecat', 'alegerea se salvează')
    pg.reload()
    asteapta(pg, "!!document.querySelector('nav .picior .tema')", 15000)
    verifica(pg.evaluate("document.documentElement.dataset.theme") == 'dark', 'după reîncărcare rămâne întunecat')
    pg.set_viewport_size({'width': 1440, 'height': 720})
    nav = pg.evaluate("(() => { const n = document.querySelector('nav'); return [n.scrollHeight, n.clientHeight] })()")
    verifica(nav[0] <= nav[1], f'meniul încape fără derulare la 720 px (conținut {nav[0]}, loc {nav[1]})')
    opt.nth(2).click()
    verifica(asteapta(pg, "document.documentElement.dataset.theme === 'light'"), 'Ca sistemul: revine la tema sistemului')
    inchide(pg)
```

și în `VERIFICARI`: `'comutator': v_comutator,`.

Run: `PYTHONIOENCODING=utf-8 /c/Users/robert.postolache/AppData/Local/Programs/Python/Python314/python.exe web/verifica_ui.py --url http://localhost:5174 --doar comutator`
Expected: `PICĂ  comutatorul are 3 opțiuni (am 0)`, exit 1.

- [ ] **Step 2: Textele**

În `web/src/i18n/dict/comun.ts`, înainte de `} as const`:

```ts
  "comun.tema.eticheta": ["Tema", "Theme"],
  "comun.tema.luminos": ["Luminos", "Light"],
  "comun.tema.intunecat": ["Întunecat", "Dark"],
  "comun.tema.sistem": ["Ca sistemul", "System"],
```

- [ ] **Step 3: Comutatorul**

În `web/src/layout/AppShell.tsx`:
- importuri: `import { DesktopOutlined, MoonOutlined, SunOutlined } from '@ant-design/icons'` și `import { useTema, type Tema } from '../tema'`;
- în componentă, după `useLang()`: `const { tema, setTema } = useTema()`;
- comentariul componentei: `/** Bara laterală, titlul paginii, comutatoarele de limbă și de temă. */`;
- `<div className="limba">…</div>` (rândurile 50-60) devine:

```tsx
          {/* limba și tema pe același rând: meniul trebuie să încapă fără derulare la 720 px */}
          <div className="comutatoare">
            <div className="limba">
              <Segmented<Lang>
                size="small"
                value={lang}
                onChange={setLang}
                options={[
                  { label: 'RO', value: 'ro' },
                  { label: 'EN', value: 'en' },
                ]}
              />
            </div>
            <div className="tema">
              <Segmented<Tema>
                size="small"
                value={tema}
                onChange={setTema}
                aria-label={t('comun.tema.eticheta')}
                options={[
                  { value: 'luminos', title: t('comun.tema.luminos'), label: <SunOutlined aria-label={t('comun.tema.luminos')} /> },
                  { value: 'intunecat', title: t('comun.tema.intunecat'), label: <MoonOutlined aria-label={t('comun.tema.intunecat')} /> },
                  { value: 'sistem', title: t('comun.tema.sistem'), label: <DesktopOutlined aria-label={t('comun.tema.sistem')} /> },
                ]}
              />
            </div>
          </div>
```

(Dacă `typecheck` respinge `title` pe opțiune sau `aria-label` pe `Segmented`, scoate doar proprietatea respinsă și păstrează `aria-label` de pe icoane; notează în raport.)

În `web/src/styles/global.css`, `nav .picior .limba { margin-top: 8px }` devine:

```css
nav .picior .comutatoare { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px }
```

- [ ] **Step 4: Verifică**

Run: `npm run typecheck && npm run build`, apoi verificatorul cu `--doar tema,comutator`.
Expected: toate `ok`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add web/src/layout/AppShell.tsx web/src/i18n/dict/comun.ts web/src/styles/global.css web/verifica_ui.py
git commit -m "web: comutatorul de temă în meniu, lângă RO/EN"
```

---

### Task 3: Paleta verificată în `typecheck`

**Files:**
- Create: `web/scripts/verifica_tema.mjs`
- Modify: `web/package.json` (`scripts.build`, `scripts.typecheck`)

**Interfaces:**
- Consumes: blocurile `:root {` și `:root[data-theme="dark"] {` din `global.css` (Task 1); `const LUMINOS = {…}` și `const INTUNECAT = {…}` din `theme.ts`.
- Produces: `node web/scripts/verifica_tema.mjs` iese cu 1 și listează diferențele dacă paletele nu coincid.

- [ ] **Step 1: Scriptul**

`web/scripts/verifica_tema.mjs`:

```js
// Paleta stă în două locuri: src/theme.ts (Ant Design) și src/styles/global.css (variabilele
// CSS). Scriptul verifică, în ambele teme, că sunt aceleași culori; rulează în
// `npm run typecheck` și în `npm run build`, deci o culoare schimbată într-un singur loc oprește build-ul.
import { readFileSync } from 'node:fs'

const citeste = (f) => readFileSync(new URL(f, import.meta.url), 'utf8')
const ts = citeste('../src/theme.ts')
const css = citeste('../src/styles/global.css')

// cheia din theme.ts → variabila din global.css
const VARIABILE = {
  bg: '--bg', surface: '--surface', ink: '--ink', muted: '--muted', line: '--line', line2: '--line-2',
  warn: '--warn', ok: '--ok', accent: '--accent', accentTint: '--accent-tint', onAccent: '--on-accent',
}

function paletaTs(nume) {
  const m = ts.match(new RegExp(`const ${nume} = \\{([^}]*)\\}`))
  if (!m) throw new Error(`theme.ts: nu găsesc paleta ${nume}`)
  return Object.fromEntries([...m[1].matchAll(/(\w+):\s*'([^']*)'/g)].map(([, k, v]) => [k, v.toLowerCase()]))
}

function blocCss(selector) {
  const i = css.indexOf(`${selector} {`)
  if (i < 0) throw new Error(`global.css: nu găsesc blocul „${selector} {”`)
  const corp = css.slice(i, css.indexOf('}', i))
  return Object.fromEntries([...corp.matchAll(/(--[\w-]+):\s*([^;]+);/g)].map(([, k, v]) => [k, v.trim().toLowerCase()]))
}

const luminos = blocCss(':root')
// în tema întunecată, ce nu e redefinit se moștenește din :root
const intunecat = { ...luminos, ...blocCss(':root[data-theme="dark"]') }
const diferente = []
for (const [nume, paletaCss] of [['LUMINOS', luminos], ['INTUNECAT', intunecat]]) {
  const p = paletaTs(nume)
  for (const [cheie, variabila] of Object.entries(VARIABILE)) {
    if (p[cheie] !== paletaCss[variabila]) diferente.push(`${nume}.${cheie} = ${p[cheie]}, dar ${variabila} = ${paletaCss[variabila]}`)
  }
}
if (diferente.length) {
  console.error('Paleta din theme.ts nu e aceeași cu cea din global.css:\n  ' + diferente.join('\n  '))
  process.exit(1)
}
console.log('paleta: theme.ts și global.css au aceleași culori')
```

- [ ] **Step 2: Arată că prinde o diferență**

În `web/src/theme.ts`, schimbă temporar `bg: '#1b1517'` (INTUNECAT) în `bg: '#1b1518'`.
Run: `cd /c/Users/robert.postolache/Downloads/mip-tema && node web/scripts/verifica_tema.mjs; echo "exit $?"`
Expected: `INTUNECAT.bg = #1b1518, dar --bg = #1b1517`, `exit 1`. Pune valoarea înapoi (`#1b1517`) și rulează din nou: `paleta: theme.ts și global.css au aceleași culori`, `exit 0`. `git diff web/src/theme.ts` nu arată nimic.

- [ ] **Step 3: Legat de typecheck și build**

În `web/package.json`:

```json
    "build": "tsc --noEmit && node scripts/verifica_tema.mjs && vite build",
    "typecheck": "tsc --noEmit && node scripts/verifica_tema.mjs",
```

Run: `npm run typecheck && npm run build`
Expected: trec; în ieșire apare `paleta: theme.ts și global.css au aceleași culori`.

- [ ] **Step 4: Commit**

```bash
git add web/scripts/verifica_tema.mjs web/package.json
git commit -m "web: verificarea că paleta din theme.ts e aceeași cu cea din global.css"
```

---

### Task 4: Harta urmează tema din mers

**Files:**
- Modify: `web/src/pages/harta/Mapa.tsx:13-29, 67-79, 137-193`, `web/verifica_ui.py`

**Interfaces:**
- Consumes: `useTema()` (Task 1); comutatorul `nav .picior .tema .ant-segmented-item` (Task 2).
- Produces: în dezvoltare (`import.meta.env.DEV`), `window.__harta` = instanța MapLibre, doar pentru verificator. Verificatorul `harta`.

- [ ] **Step 1: Verificarea `harta` (pică)**

În `web/verifica_ui.py`:

```python
def v_harta(b: Browser, url: str) -> None:
    cereri: list[str] = []
    pg = deschide(b, url + '/#/harta', tema='luminos', cereri=cereri)
    STRATURI = "!!(window.__harta && window.__harta.getSource('locatii') && window.__harta.getLayer('atm') && window.__harta.getLayer('sucursala'))"
    verifica(asteapta(pg, STRATURI, 30000), 'harta s-a încărcat, cu sursa și straturile băncilor')
    verifica(any('positron' in u for u in cereri), 'tema luminoasă: fundalul positron')
    pg.evaluate("window.__fara_reincarcare = 1")
    pg.locator('nav .picior .tema .ant-segmented-item').nth(1).click()
    verifica(asteapta(pg, "document.documentElement.dataset.theme === 'dark'"), 'comutat pe întunecat')
    for _ in range(60):
        if any('dark-matter' in u for u in cereri):
            break
        pg.wait_for_timeout(250)
    verifica(any('dark-matter' in u for u in cereri), 'tema întunecată: harta cere fundalul dark-matter')
    pg.wait_for_timeout(1000)
    verifica(asteapta(pg, STRATURI, 30000), 'după comutare, sursa și straturile sunt la loc')
    verifica(pg.evaluate("window.__fara_reincarcare === 1"), 'harta s-a schimbat fără reîncărcarea paginii')
    verifica(pg.locator('.ht-diag').count() == 0, 'fără mesaj de eroare pe hartă (dacă pică: CARTO e blocat din rețea?)')
    inchide(pg)
```

și `'harta': v_harta,` în `VERIFICARI`.

Run: verificatorul cu `--doar harta`.
Expected: `PICĂ  harta s-a încărcat…` (nu există `__harta`), exit 1.

- [ ] **Step 2: Stilurile, după temă**

În `web/src/pages/harta/Mapa.tsx`, rândurile 13-29 (constanta `intunecat`, `STIL_CARTO`, `STIL_REZERVA`) devin:

```ts
const stilCarto = (intunecat: boolean) => intunecat
  ? 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
  : 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
const stilRezerva = (intunecat: boolean): StyleSpecification => ({
  version: 8,
  sources: {
    osm: {
      type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  layers: [
    { id: 'fundal', type: 'background', paint: { 'background-color': intunecat ? '#161113' : '#f3efea' } },
    { id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-saturation': -0.6 } },
  ],
})
```

și importul `import { useTema } from '../../tema'`.

- [ ] **Step 3: Starea în componentă**

În `Mapa`, după `const { t, locale } = useLang()`:

```ts
  const { intunecat } = useTema()
  /* tema cu care e desenată harta acum și dacă a căzut pe fondul de rezervă:
     la comutarea temei se cere același fel de fond, în varianta cealaltă */
  const temaHarta = useRef(intunecat)
  const peRezerva = useRef(false)
```

În efectul de creare (rândurile 137-193):
- comentariul `// harta se creează o singură dată; fundalul se alege după tema sistemului, ca în pagina veche` devine `// harta se creează o singură dată, cu tema de acum; schimbarea temei o tratează efectul de mai jos`;
- `style: STIL_CARTO` → `style: stilCarto(temaHarta.current)`;
- după `harta.current = map`: `if (import.meta.env.DEV) (window as unknown as { __harta?: HartaGL }).__harta = map  // doar pentru web/verifica_ui.py`;
- `let cazutPeRezerva = false` se șterge; în handlerul de eroare, `!cazutPeRezerva` → `!peRezerva.current`, `cazutPeRezerva = true` → `peRezerva.current = true`, `map.setStyle(STIL_REZERVA, { diff: false })` → `map.setStyle(stilRezerva(temaHarta.current), { diff: false })`;
- în funcția de curățare, după `harta.current = null`: `if (import.meta.env.DEV) delete (window as unknown as { __harta?: HartaGL }).__harta`.

- [ ] **Step 4: Efectul de comutare**

După efectul de creare, adaugă:

```ts
  // tema schimbată din meniu: alt fond, fără reîncărcare. `diff: false` reconstruiește stilul,
  // deci vine „style.load”, iar efectul de mai jos pune la loc texturile, sursa și straturile
  useEffect(() => {
    const map = harta.current
    if (!map || temaHarta.current === intunecat) return
    temaHarta.current = intunecat
    stilIncarcat.current = false
    setGata(false)
    curataGrupe()
    map.setStyle(peRezerva.current ? stilRezerva(intunecat) : stilCarto(intunecat), { diff: false })
  }, [intunecat])
```

- [ ] **Step 5: Verifică**

Run: `npm run typecheck && npm run build`, apoi verificatorul cu `--doar harta`.
Expected: toate `ok`, exit 0. Deschide și manual http://localhost:5174/#/harta, comută de câteva ori: punctele și grupurile reapar de fiecare dată.

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/harta/Mapa.tsx web/verifica_ui.py
git commit -m "web: harta își schimbă fondul odată cu tema, fără reîncărcare"
```

---

### Task 5: Logo-uri și culori fixe lizibile pe fundal închis

**Files:**
- Modify: `web/src/components/comune.tsx:15`, `web/src/pages/Banca.tsx:122`, `web/src/pages/versus/CardBanca.tsx:31`, `web/src/components/BareStele.tsx:5-6`, `web/src/styles/global.css` (blocurile de culori, `.cap-d`, regulă nouă), `web/src/styles/retea.css:34-41`, `web/verifica_ui.py`

**Interfaces:**
- Consumes: `data-theme` pe `<html>` (Task 1).
- Produces: clasa `.sigla` pe orice `<img>` cu logo de bancă în afara hărții; variabilele `--stele-4`, `--stele-2`. Verificatorul `sigle`.

- [ ] **Step 1: Verificarea `sigle` (pică)**

În `web/verifica_ui.py`:

```python
JS_SIGLE = r"""() => {
  const imgs = [...document.querySelectorAll('img')].filter(i => /\/logos\//.test(i.src) && !i.closest('.ht-zona, .ht-panou, .maplibregl-popup'))
  const r = imgs[0] ? imgs[0].getBoundingClientRect() : null
  return { total: imgs.length, fara_sigla: imgs.filter(i => !i.classList.contains('sigla')).length,
           fundal: imgs[0] ? getComputedStyle(imgs[0]).backgroundColor : null,
           marime: r ? [Math.round(r.width), Math.round(r.height)] : null }
}"""


def v_sigle(b: Browser, url: str) -> None:
    for pagina in ('produse', 'banca', 'versus'):
        rez = {}
        for tema in ('luminos', 'intunecat'):
            pg = deschide(b, f'{url}/#/{pagina}', tema=tema)
            incarcata(pg)
            rez[tema] = pg.evaluate(JS_SIGLE)
            inchide(pg)
        l, i = rez['luminos'], rez['intunecat']
        verifica(i['total'] > 0, f'{pagina}: are logo-uri ({i["total"]})')
        verifica(i['fara_sigla'] == 0, f'{pagina}: toate logo-urile au clasa .sigla ({i["fara_sigla"]} fără)')
        verifica(i['fundal'] == 'rgb(255, 255, 255)', f'{pagina}, întunecat: logo pe alb ({i["fundal"]})')
        verifica(l['fundal'] == 'rgba(0, 0, 0, 0)', f'{pagina}, luminos: logo fără fundal, ca azi ({l["fundal"]})')
        verifica(l['marime'] == i['marime'], f'{pagina}: logo-ul ocupă același loc în ambele teme ({l["marime"]} / {i["marime"]})')
```

și `'sigle': v_sigle,` în `VERIFICARI`.

Run: verificatorul cu `--doar sigle`. Expected: `PICĂ` la „toate logo-urile au clasa .sigla” și „logo pe alb”, exit 1.

- [ ] **Step 2: Clasa `.sigla`**

- `web/src/components/comune.tsx:15`: `{logo && <img src={logo} alt="" />}` → `{logo && <img className="sigla" src={logo} alt="" />}`
- `web/src/pages/Banca.tsx:122`: `className="bk-logo"` → `className="bk-logo sigla"`
- `web/src/pages/versus/CardBanca.tsx:31`: `<img src={m.logo[b]} alt={nume} />` → `<img className="sigla" src={m.logo[b]} alt={nume} />`

În `web/src/styles/global.css`, după regula `.cl-banca img { … }`:

```css
/* siglele pe fundal închis: multe sunt negre sau bleumarin, fără fundal propriu (BRD, CEC, UniCredit, Libra,
   Raiffeisen, ING…). În tema întunecată stau pe alb, ca pe hartă; culorile băncii nu se ating. Albul e
   desenat cu umbră, nu cu padding: logo-ul ocupă același loc în ambele teme, iar tabelele nu sar la comutare. */
:root[data-theme="dark"] img.sigla { background: #fff; box-shadow: 0 0 0 3px #fff; border-radius: 2px }
```

- [ ] **Step 3: Culorile fixe**

`web/src/components/BareStele.tsx:6`: `const CULORI = ['var(--ok)', '#7fb893', 'var(--muted)', '#d9a441', 'var(--warn)']` → `const CULORI = ['var(--ok)', 'var(--stele-4)', 'var(--muted)', 'var(--stele-2)', 'var(--warn)']`, iar comentariul de deasupra primește la final: ` Culorile vin din temă (global.css).`

În `web/src/styles/global.css`, în `:root {`: `--stele-4: #7fb893; --stele-2: #d9a441;`; în `:root[data-theme="dark"] {`: `--stele-4: #4e9466; --stele-2: #c08a3e;`.

`.cap-d` (descrierea din capul tabelului): scoate `opacity: .85;` (în tema luminoasă dădea 4,20:1, sub pragul de 4,5:1).

`web/src/styles/retea.css`: în `.ht-lg-suc, .ht-lg-atm { … }` și în `.ht-grup { … }`, `color: #fff` → `color: var(--on-accent)` (pe accentul roz al temei întunecate, albul dădea 2,05:1). Chenarele `#fff` rămân (copiază insignele de pe hartă). Deasupra regulii `.ht-lg-suc` adaugă: `/* textul insignelor: --on-accent, lizibil pe accent în ambele teme; chenarul alb rămâne, ca pe hartă */`.

- [ ] **Step 4: Verifică**

Run: `npm run typecheck && npm run build`, apoi verificatorul cu `--doar tema,sigle`.
Expected: toate `ok`, exit 0.

- [ ] **Step 5: Commit**

```bash
git add web/src/components/comune.tsx web/src/pages/Banca.tsx web/src/pages/versus/CardBanca.tsx web/src/components/BareStele.tsx web/src/styles/global.css web/src/styles/retea.css web/verifica_ui.py
git commit -m "web: siglele pe alb în tema întunecată, culorile fixe din temă, contrast la cap și legendă"
```

---

### Task 6: Capul tabelului lipit sub bara de filtre

**Files:**
- Create: `web/src/components/lipire.tsx`
- Modify: `web/src/components/Tabel.tsx`, `web/src/styles/global.css` (după `.cap-d`), `web/src/pages/campanii/Google.tsx:445-466`, `lipit={false}` în: `web/src/pages/rate_mobil/android/Aplicatii.tsx:67`, `…/android/Functionalitati.tsx:71`, `…/android/Portofele.tsx:46`, `…/android/TrackerePermisiuni.tsx:79` și `:87`, `…/android/Detaliu.tsx:87`, `web/src/pages/Istoric.tsx:248`, `web/src/pages/banca/Catalog.tsx:61`; `web/verifica_ui.py`

**Interfaces:**
- Produces: `useSusCap(el: HTMLElement | null): number`; `propsLipit<R>(sus: number): Pick<TableProps<R>, 'sticky' | 'scroll' | 'tableLayout'>`; `RandFantoma({ capuri }: { capuri: { cheie: string; cap: ReactNode; sortabil: boolean }[] })`; `Tabel` primește `lipit?: boolean` (implicit `true`). Verificatorul `capete`.

- [ ] **Step 1: Verificarea `capete` (pică)**

În `web/verifica_ui.py`:

```python
CAPETE = ['produse', 'rate', 'mobil', 'coada', 'surse', 'overview', 'campanii']

JS_CAPETE = r"""async () => {
  const main = document.getElementById('principal')
  const tabel = [...document.querySelectorAll('#principal .ant-table-wrapper.t')]
    .find(w => w.getBoundingClientRect().height > main.clientHeight * 0.9)
  if (!tabel) return { lung: false }
  const cap = tabel.querySelector('.ant-table-header')
  if (!cap) return { lung: true, lipit: false }
  main.scrollTop += tabel.getBoundingClientRect().top - main.getBoundingClientRect().top + 300
  await new Promise(r => setTimeout(r, 400))
  const bare = [...document.querySelectorAll('#principal .bara-fixa')]
    .filter(b => b.compareDocumentPosition(tabel) & Node.DOCUMENT_POSITION_FOLLOWING)
  const bara = bare[bare.length - 1]
  const sub = bara ? bara.getBoundingClientRect().bottom : main.getBoundingClientRect().top
  const r = (e) => e.getBoundingClientRect()
  const ths = [...cap.querySelectorAll('thead > tr > th')].filter(th => !th.classList.contains('ant-table-cell-scrollbar'))
  const tds = [...tabel.querySelector('.ant-table-tbody > tr.ant-table-row').querySelectorAll(':scope > td')]
  const nealiniate = ths.filter((th, i) => !tds[i] || Math.abs(r(th).left - r(tds[i]).left) > 1.5
    || Math.abs(r(th).width - r(tds[i]).width) > 1.5).length
  return { lung: true, lipit: true, dif: Math.round(r(cap).top - sub), nealiniate, coloane: ths.length }
}"""

JS_ORIZONTAL = r"""async () => {
  const tabel = document.querySelector('#principal .ant-table-wrapper.t')
  const corp = tabel && tabel.querySelector('.ant-table-body')
  if (!corp || corp.scrollWidth <= corp.clientWidth) return { lat: false }
  const td = tabel.querySelector('.ant-table-tbody > tr.ant-table-row > td')
  const inainte = td.getBoundingClientRect().left
  corp.scrollLeft = 200
  await new Promise(r => setTimeout(r, 300))
  const libra = tabel.querySelector('.ant-table-tbody > tr.libra > td')
  return { lat: true, mutat: Math.round(td.getBoundingClientRect().left - inainte),
           fundal_libra: libra ? getComputedStyle(libra).backgroundColor : null }
}"""


def v_capete(b: Browser, url: str) -> None:
    for lat, inalt in ((1440, 900), (1000, 760)):
        for pagina in CAPETE:
            pg = deschide(b, f'{url}/#/{pagina}', lat=lat, inalt=inalt)
            incarcata(pg)
            r = pg.evaluate(JS_CAPETE)
            if not r['lung']:
                print(f'  —   {pagina} @{lat}: niciun tabel mai înalt decât ecranul, nimic de verificat')
            elif verifica(r['lipit'], f'{pagina} @{lat}: tabelul lung are capul lipit'):
                verifica(abs(r['dif']) <= 2, f'{pagina} @{lat}: capul stă imediat sub bara de filtre (diferență {r["dif"]} px)')
                verifica(r['nealiniate'] == 0, f'{pagina} @{lat}: capul e aliniat cu coloanele ({r["nealiniate"]} din {r["coloane"]} nealiniate)')
            inchide(pg)
    # prima coloană fixă când tabelul e mai lat decât ecranul
    pg = deschide(b, f'{url}/#/produse', lat=1000, inalt=760)
    incarcata(pg)
    r = pg.evaluate(JS_ORIZONTAL)
    if verifica(r['lat'], 'produse @1000: tabelul derulează pe orizontală (precondiție)'):
        verifica(r['mutat'] == 0, f'produse @1000: prima coloană rămâne pe loc la derularea la dreapta (mutată {r["mutat"]} px)')
        verifica(r['fundal_libra'] not in (None, 'rgba(0, 0, 0, 0)'), f'rândul Libra are fundal opac în coloana fixă ({r["fundal_libra"]})')
    inchide(pg)
    # sortarea din capul lipit
    pg = deschide(b, f'{url}/#/produse')
    incarcata(pg)
    th = pg.locator('#principal .ant-table-header th.ant-table-column-has-sorters').last
    inainte = th.get_attribute('aria-sort')
    th.click()
    pg.wait_for_timeout(400)
    verifica(th.get_attribute('aria-sort') != inainte, f'sortarea din capul lipit merge (aria-sort {inainte} → {th.get_attribute("aria-sort")})')
    # căutare fără rezultat: tabelul gol nu strică pagina
    pg.locator('#principal .bara-fixa input.ant-input').first.fill('zzzzzzzz')
    pg.wait_for_timeout(600)
    verifica(pg.locator('#principal .ant-table-wrapper.t').count() == 0 and pg.locator('#principal p.note').count() > 0,
             'căutare fără rezultat: mesajul „nimic de afișat”, fără tabel')
    inchide(pg)
    # tabelele din chenare cu derulare proprie rămân cum erau
    pg = deschide(b, f'{url}/#/istoric')
    incarcata(pg)
    r = pg.evaluate("""() => { const w = document.querySelector('.ci-tabel'); if (!w) return null
      const c = w.querySelector('.ant-table-content')
      return { lipit: !!w.querySelector('.ant-table-header'), chenar: !!c && getComputedStyle(c).maxHeight !== 'none' } }""")
    if r is None:
        print('  —   istoric: nicio schimbare afișată, chenarul nu se poate verifica')
    else:
        verifica(not r['lipit'] and r['chenar'], f'istoric: tabelul rămâne în chenarul lui, fără lipire pe pagină ({r})')
    inchide(pg)
```

și `'capete': v_capete,` în `VERIFICARI`.

Run: verificatorul cu `--doar capete`.
Expected: `PICĂ  produse @1440: tabelul lung are capul lipit` (și la celelalte pagini cu tabele lungi), exit 1.

- [ ] **Step 2: `lipire.tsx`**

`web/src/components/lipire.tsx`:

```tsx
import { useEffect, useState, type ReactNode } from 'react'
import { Table, type TableProps } from 'antd'

/** Marginea de sus a lui <main> (global.css: `main { padding: 26px … }`); bara de filtre o acoperă cu `top: -26px`. */
const SUS_MAIN = 26

/**
 * Cât de jos se lipește capul unui tabel la derularea paginii: sub ultima bară de filtre
 * (`.bara-fixa`) de dinaintea tabelului, oricât de înaltă e (se rupe pe rânduri la ferestre
 * înguste, deci se măsoară); fără bară, sus de tot. Valoarea e față de marginea conținutului
 * lui <main>, deci fără bară e -26.
 */
export function useSusCap(el: HTMLElement | null): number {
  const [sus, setSus] = useState(-SUS_MAIN)
  useEffect(() => {
    if (!el) return
    const bare = [...document.querySelectorAll<HTMLElement>('#principal .bara-fixa')]
      .filter((b) => b.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING)
    const bara = bare[bare.length - 1]
    if (!bara) {
      setSus(-SUS_MAIN)
      return
    }
    const masoara = () => setSus(bara.offsetHeight - SUS_MAIN)
    masoara()
    const obs = new ResizeObserver(masoara)
    obs.observe(bara)
    return () => obs.disconnect()
  }, [el])
  return sus
}

/**
 * Capul lipit pe pagină (varianta aleasă prin proba din 06.10.2026): `sticky` desparte capul
 * de corp în două tabele; `scroll.x: '100%'` cu `tableLayout: 'auto'` păstrează lățimea de azi
 * (textul se rupe pe rânduri în loc să împingă tabelul în lateral); tabelul capului ia exact
 * lățimile măsurate în corp (global.css, `.ant-table-header > table`).
 */
export function propsLipit<R>(sus: number): Pick<TableProps<R>, 'sticky' | 'scroll' | 'tableLayout'> {
  return {
    sticky: { offsetHeader: sus, getContainer: () => document.getElementById('principal') ?? window },
    scroll: { x: '100%' },
    tableLayout: 'auto',
  }
}

/**
 * Rândul fantomă: AntD dă capului lipit lățimile măsurate în corp, iar un cap lung peste
 * cifre scurte („Administrare cont”, cu descrierea, peste „0 lei”) s-ar înghesui. Rândul
 * acesta pune textul capului și în corp, invizibil și de înălțime zero, deci coloanele ies
 * cel puțin cât capul; locul săgeților de sortare e rezervat alături (`.fantoma-sort`).
 */
export function RandFantoma({ capuri }: { capuri: { cheie: string; cap: ReactNode; sortabil: boolean }[] }) {
  return (
    <Table.Summary.Row className="cap-fantoma">
      {capuri.map((c, i) => (
        <Table.Summary.Cell key={c.cheie} index={i}>
          <div className="fantoma" aria-hidden="true">
            <span>{c.cap}</span>
            {c.sortabil && <span className="fantoma-sort" />}
          </div>
        </Table.Summary.Cell>
      ))}
    </Table.Summary.Row>
  )
}
```

- [ ] **Step 3: `Tabel` cu cap lipit**

În `web/src/components/Tabel.tsx`:
- import: `import { propsLipit, RandFantoma, useSusCap } from './lipire'`;
- la comentariul de sus, după „rândul Libra rămâne primul…”, adaugă rândul: ` *  - capul rămâne lipit sub bara de filtre la derulare, iar prima coloană la derularea pe orizontală (`lipit`);`
- în `Coloana<R>` nu se schimbă nimic; în props adaugă, după `onRand`:

```ts
  /** capul lipit la derularea paginii (implicit); `false` în chenarele cu derulare proprie și în sertare */
  lipit?: boolean
```

  și `lipit = true,` în destructurare;
- după `const [sort, setSort] = …`:

```ts
  const [el, setEl] = useState<HTMLDivElement | null>(null)
  const sus = useSusCap(lipit ? el : null)
```

- în `coloane.map((c) => ({` → `coloane.map((c, i) => ({`, cu primul câmp nou `fixed: lipit && i === 0 ? ('left' as const) : undefined,`;
- `return ( <Table<R> … /> )` devine:

```tsx
  return (
    <div ref={setEl}>
      <Table<R>
        className="t"
        size="small"
        columns={cols}
        dataSource={lista}
        rowKey={cheieRand}
        pagination={false}
        {...(lipit ? propsLipit<R>(sus) : {})}
        summary={lipit ? () => <RandFantoma capuri={coloane.map((c) => ({ cheie: c.cheie, cap: c.cap, sortabil: !!c.s }))} /> : undefined}
        rowClassName={…neschimbat…}
        onRow={…neschimbat…}
        onChange={…neschimbat…}
      />
    </div>
  )
```

În `web/src/styles/global.css`, după regula `.cap-d { … }`:

```css
/* capul lipit (components/lipire.tsx): tabelul capului ia exact lățimile măsurate în corp, iar rândul
   fantomă (textul capului, invizibil, de înălțime zero) face coloanele din corp cel puțin cât capul */
.ant-table-wrapper.t .ant-table-header > table { table-layout: fixed !important; width: 1px !important }
.ant-table-wrapper.t tr.cap-fantoma > td { padding-top: 0 !important; padding-bottom: 0 !important; border: 0 !important; height: 0;
  font-family: var(--mono); font-size: 10.5px; text-transform: uppercase; letter-spacing: .03em; font-weight: 500 }
.fantoma { display: flex; height: 0; overflow: hidden; visibility: hidden }
.fantoma-sort { flex: none; width: 22px }
```

- [ ] **Step 4: Chenarele și sertarul rămân cum erau**

Adaugă `lipit={false}` pe `<Tabel …>` în: `rate_mobil/android/Aplicatii.tsx:67`, `Functionalitati.tsx:71`, `Portofele.tsx:46`, `TrackerePermisiuni.tsx:79` și `:87` (în `.an-tabel`, chenar de 70vh), `Detaliu.tsx:87` (în sertar), `pages/Istoric.tsx:248` (`.ci-tabel`), `pages/banca/Catalog.tsx:61` (`.bk-catalog-wrap`). Verifică: `grep -rn "lipit={false}" web/src | wc -l` → `8`.

- [ ] **Step 5: Tabelul Google (AntD direct)**

În `web/src/pages/campanii/Google.tsx`, în componenta care randează `<Table<ReclamaGoogle>` (rândul 449), la începutul ei (înainte de orice `return` timpuriu):

```ts
  const [elTabel, setElTabel] = useState<HTMLDivElement | null>(null)
  const sus = useSusCap(elTabel)
```

cu `import { propsLipit, RandFantoma, useSusCap } from '../../components/lipire'` (și `useState`, `type ReactNode` din `react`, dacă lipsesc). Tabelul devine:

```tsx
      <div ref={setElTabel}>
        <Table<ReclamaGoogle>
          className="t"
          size="small"
          columns={coloane.map((c, i) => (i === 0 ? { ...c, fixed: 'left' as const } : c))}
          dataSource={d.randuri}
          rowKey={(r) => `${r.advertiser_id}/${r.creative_id}`}
          pagination={false}
          {...propsLipit<ReclamaGoogle>(sus)}
          summary={() => (
            <RandFantoma capuri={coloane.map((c, i) => ({ cheie: String(c.key ?? i), cap: c.title as ReactNode, sortabil: !!c.sorter }))} />
          )}
          rowClassName={(r) => (r.banca === 'libra' ? 'libra' : '')}
          onChange={…neschimbat…}
        />
      </div>
```

(Dacă `c.title` e funcție în vreo coloană, `typecheck` o prinde: atunci folosește `typeof c.title === 'function' ? null : c.title`.)

- [ ] **Step 6: Verifică**

Run: `npm run typecheck && npm run build`, apoi verificatorul cu `--doar capete,tema`.
Expected: toate `ok` (paginile fără tabel lung apar cu `—`), exit 0. Deschide manual http://localhost:5174/#/produse și derulează: capul cu descrierile stă sub filtre; comută tema: capul își schimbă culoarea odată cu tabelul.

- [ ] **Step 7: Commit**

```bash
git add web/src/components/lipire.tsx web/src/components/Tabel.tsx web/src/styles/global.css web/src/pages web/verifica_ui.py
git commit -m "web: capul tabelelor lipit sub bara de filtre, prima coloană fixă la derularea pe orizontală"
```

---

### Task 7: Contrast verificat pe toate paginile, capturi, corecturi

**Files:**
- Modify: `web/package.json` + `package-lock.json` (devDependency), `web/verifica_ui.py`, `.gitignore`; apoi ce cer corecturile (`web/src/theme.ts` și `web/src/styles/*.css`)

**Interfaces:**
- Consumes: tot ce e mai sus.
- Produces: verificările `contrast` și `capturi`; zero încălcări de contrast în ambele teme (sau excepții listate cu motiv în raport).

- [ ] **Step 1: axe-core, doar pentru dezvoltare**

Run: `export PATH="/c/Program Files/nodejs:$PATH" && cd /c/Users/robert.postolache/Downloads/mip-tema && npm install -D -w web axe-core@4.14.0 --save-exact --no-audit --no-fund`
Expected: `web/package.json` are `"axe-core": "4.14.0"` în `devDependencies`; fișierul `node_modules/axe-core/axe.min.js` există. Nimic nu se aprobă la scripturi de instalare (axe-core n-are).

În `.gitignore`, la final: `web/.capturi/`

- [ ] **Step 2: Verificările `contrast` și `capturi`**

În `web/verifica_ui.py`:

```python
PAGINI = ['overview', 'produse', 'rate', 'mobil', 'campanii', 'retea', 'context', 'versus', 'banca',
          'istoric', 'surse', 'coada', 'harta']
AXE = [AICI / 'node_modules' / 'axe-core' / 'axe.min.js', AICI.parent / 'node_modules' / 'axe-core' / 'axe.min.js']
JS_AXE = """() => axe.run(document, { runOnly: { type: 'rule', values: ['color-contrast'] } })
  .then(r => r.violations.flatMap(v => v.nodes.map(n => n.target.join(' ') + ' · ' + (n.any[0] ? n.any[0].message : ''))))"""


def v_contrast(b: Browser, url: str) -> None:
    axe = next((c for c in AXE if c.exists()), None)
    if not verifica(axe is not None, 'axe-core instalat (npm install)'):
        return
    for tema in ('luminos', 'intunecat'):
        for pagina in PAGINI:
            pg = deschide(b, f'{url}/#/{pagina}', tema=tema)
            incarcata(pg)
            pg.add_script_tag(path=str(axe))
            noduri = pg.evaluate(JS_AXE)
            verifica(not noduri, f'contrast {pagina}, {tema}: {len(noduri)} elemente sub prag')
            for n in noduri[:12]:
                print(f'        {n}')
            inchide(pg)


def v_capturi(b: Browser, url: str) -> None:
    out = AICI / '.capturi'
    out.mkdir(exist_ok=True)
    for tema in ('luminos', 'intunecat'):
        for pagina in PAGINI:
            pg = deschide(b, f'{url}/#/{pagina}', tema=tema)
            incarcata(pg)
            pg.screenshot(path=str(out / f'{tema}_{pagina}.png'))
            inchide(pg)
    print(f'  capturile: {out}')
```

și în `VERIFICARI`: `'contrast': v_contrast, 'capturi': v_capturi,`.

- [ ] **Step 3: Rulează și citește**

Run: verificatorul cu `--doar contrast`.
Expected la prima rulare: probabil câteva `PICĂ`; fiecare listează elementele (selector · mesajul axe cu raportul și culorile).

- [ ] **Step 4: Corectează, în ordinea asta**

1. Dacă problema e o culoare a paletei (același element pică pe mai multe pagini), schimbă valoarea în AMBELE locuri: `theme.ts` și `global.css` (`npm run typecheck` verifică că se potrivesc). Ajustează doar luminozitatea, păstrând nuanța. Dacă schimbi `--bg`, actualizează și valorile `rgb(...)` din `v_tema` (pasul 2 al ei).
2. Dacă e o regulă locală (o culoare fixă, o opacitate), corecteaz-o în fișierul CSS al paginii.
3. Excepții acceptabile, de listat în raport cu motivul: text decorativ dezactivat (`disabled`), logo-uri și imagini, elemente pe care axe le raportează greșit peste gradientul din meniu (verifică manual raportul cu un calculator WCAG). Nimic altceva.

Repetă pasul 3 până la zero `PICĂ` sau doar excepțiile de la punctul 3.

- [ ] **Step 5: Toate verificările, plus capturile**

Run: verificatorul fără `--doar` (toate) și apoi `--doar capturi`.
Expected: „toate verificările au trecut”, exit 0; 26 de capturi în `web/.capturi/`. Uită-te la capturile întunecate pentru: logo-uri lizibile, nimic alb pe alb sau negru pe negru, capul tabelelor opac. Notează în raport orice observație.

- [ ] **Step 6: Commit**

```bash
git add web/package.json package-lock.json web/verifica_ui.py .gitignore web/src
git commit -m "web: contrast verificat cu axe pe toate paginile, în ambele teme; corecturile găsite"
```

---

## După ultimul task (controller)

1. Review final al întregii ramuri (cel mai capabil model), pe diff-ul `main..tema-intunecata`.
2. Skill-ul `security-audit` pe același diff, apoi `superpowers:requesting-code-review` și `superpowers:finishing-a-development-branch` — fără push, fără merge pe `main` până nu spune Robert.
3. Robert primește: ce s-a făcut, cum testează pe http://localhost:5174, capturile din `web/.capturi/`.
