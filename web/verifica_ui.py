"""Verificările interfeței React în browser, cu Playwright: tema, capetele de tabel lipite, derularea laterală.

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


def v_harta(b: Browser, url: str) -> None:
    cereri: list[str] = []
    # pagina hărții e pe tot ecranul, fără meniu: tema se schimbă din sistem, pe „Ca sistemul”
    pg = deschide(b, url + '/#/harta', tema='sistem', sistem='light', cereri=cereri)
    straturi = ("!!(window.__harta && window.__harta.getSource('locatii') && window.__harta.getLayer('atm')"
                " && window.__harta.getLayer('sucursala'))")
    verifica(asteapta(pg, straturi, 30000), 'harta s-a încărcat, cu sursa și straturile băncilor')
    verifica(any('positron' in u for u in cereri), 'tema luminoasă: fundalul positron')
    pg.evaluate("window.__fara_reincarcare = 1")
    pg.emulate_media(color_scheme='dark')
    verifica(asteapta(pg, "document.documentElement.dataset.theme === 'dark'"), 'comutat pe întunecat')
    for _ in range(60):
        if any('dark-matter' in u for u in cereri):
            break
        pg.wait_for_timeout(250)
    verifica(any('dark-matter' in u for u in cereri), 'tema întunecată: harta cere fundalul dark-matter')
    pg.wait_for_timeout(1000)
    verifica(asteapta(pg, straturi, 30000), 'după comutare, sursa și straturile sunt la loc')
    verifica(pg.evaluate("window.__fara_reincarcare === 1"), 'harta s-a schimbat fără reîncărcarea paginii')
    verifica(pg.locator('.ht-diag').count() == 0, 'fără mesaj de eroare pe hartă (dacă pică: CARTO e blocat din rețea?)')
    inchide(pg)


JS_SIGLE = r"""() => {
  // sigla în cutia standard `.sg`; excepții: harta (are propria zonă) și iconița aplicației (.as-icon: pătrat alb fix)
  const imgs = [...document.querySelectorAll('img')].filter(i => /\/logos\//.test(i.src) && !i.closest('.ht-zona, .ht-panou, .maplibregl-popup, .as-icon'))
  const cutii = imgs.map(i => i.parentElement).filter(c => c && c.classList.contains('sg'))
  const incarcate = cutii.filter(c => c.firstElementChild.complete && c.firstElementChild.naturalWidth > 0)
  const dim = (c) => { const r = c.getBoundingClientRect(); return Math.round(r.width) + 'x' + Math.round(r.height) }
  const dupa = {}
  cutii.forEach(c => { const m = [...c.classList].find(x => x.startsWith('sg-')); (dupa[m] = dupa[m] || new Set()).add(dim(c)) })
  return { total: imgs.length, fara_cutie: imgs.length - cutii.length,
           fundal: cutii[0] ? getComputedStyle(cutii[0]).backgroundColor : null,
           marimi: Object.fromEntries(Object.entries(dupa).map(([k, v]) => [k, [...v].sort().join(',')])),
           incarcate: incarcate.length }
}"""


def v_sigle(b: Browser, url: str) -> None:
    for pagina in ('produse', 'banca?b=bcr', 'versus', 'concurenta', 'mobil'):
        rez = {}
        for tema in ('luminos', 'intunecat'):
            pg = deschide(b, f'{url}/#/{pagina}', tema=tema)
            incarcata(pg)
            asteapta(pg, "[...document.images].some(i => /\\/logos\\//.test(i.src) && i.complete && i.naturalWidth > 0)", 15000)
            rez[tema] = pg.evaluate(JS_SIGLE)
            inchide(pg)
        l, i = rez['luminos'], rez['intunecat']
        if i['total'] == 0 and pagina == 'concurenta':
            # fără produse descoperite (products_discovery gol) pagina nu desenează nicio siglă: nu e ce verifica
            print('  —   concurenta: niciun produs în baza de date, nicio siglă de verificat')
            continue
        verifica(i['total'] > 0, f'{pagina}: are logo-uri ({i["total"]})')
        verifica(i['fara_cutie'] == 0, f'{pagina}: toate logo-urile sunt în cutia standard .sg ({i["fara_cutie"]} fără)')
        verifica(all(len(v.split(',')) == 1 for v in i['marimi'].values()),
                 f'{pagina}: într-un context, toate cutiile au aceeași mărime ({i["marimi"]})')
        verifica(i['fundal'] == 'rgb(255, 255, 255)', f'{pagina}, întunecat: cutia e albă ({i["fundal"]})')
        verifica(l['fundal'] == 'rgba(0, 0, 0, 0)', f'{pagina}, luminos: cutia fără fundal ({l["fundal"]})')
        verifica(l['marimi'] == i['marimi'], f'{pagina}: cutia are aceeași mărime în ambele teme ({l["marimi"]} / {i["marimi"]})')


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

JS_CHENAR_ISTORIC = """() => { const w = document.querySelector('.ci-tabel'); if (!w) return null
  const c = w.querySelector('.ant-table-content')
  return { lipit: !!w.querySelector('.ant-table-header'), chenar: !!c && getComputedStyle(c).maxHeight !== 'none' } }"""


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
                verifica(r['nealiniate'] == 0,
                         f'{pagina} @{lat}: capul e aliniat cu coloanele ({r["nealiniate"]} din {r["coloane"]} nealiniate)')
            inchide(pg)
    # prima coloană fixă: pe prima pagină unde tabelul chiar e mai lat decât ecranul la 1000 px
    for pagina in ('produse', 'mobil', 'campanii', 'coada', 'surse'):
        pg = deschide(b, f'{url}/#/{pagina}', lat=1000, inalt=760)
        incarcata(pg)
        r = pg.evaluate(JS_ORIZONTAL)
        inchide(pg)
        if r['lat']:
            verifica(r['mutat'] == 0, f'{pagina} @1000: prima coloană rămâne pe loc la derularea la dreapta (mutată {r["mutat"]} px)')
            if r['fundal_libra'] is not None:
                verifica(r['fundal_libra'] != 'rgba(0, 0, 0, 0)', f'{pagina}: rândul Libra are fundal opac în coloana fixă ({r["fundal_libra"]})')
            break
    else:
        print('  —   niciun tabel mai lat decât ecranul la 1000 px: coloana fixă nu se poate verifica')
    pg = deschide(b, f'{url}/#/produse')
    incarcata(pg)
    th = pg.locator('#principal .ant-table-header th.ant-table-column-has-sorters').last
    inainte = th.get_attribute('aria-sort')
    th.click()
    pg.wait_for_timeout(400)
    verifica(th.get_attribute('aria-sort') != inainte, f'sortarea din capul lipit merge (aria-sort {inainte} → {th.get_attribute("aria-sort")})')
    pg.locator('#principal .bara-fixa input.ant-input').first.fill('zzzzzzzz')
    pg.wait_for_timeout(600)
    verifica(pg.locator('#principal .ant-table-wrapper.t').count() == 0 and pg.locator('#principal p.note').count() > 0,
             'căutare fără rezultat: mesajul „nimic de afișat”, fără tabel')
    inchide(pg)
    pg = deschide(b, f'{url}/#/istoric')
    incarcata(pg)
    r = pg.evaluate(JS_CHENAR_ISTORIC)
    if r is None:
        print('  —   istoric: nicio schimbare afișată, chenarul nu se poate verifica')
    else:
        verifica(not r['lipit'] and r['chenar'], f'istoric: tabelul rămâne în chenarul lui, fără lipire pe pagină ({r})')
    inchide(pg)


PAGINI = ['overview', 'produse', 'rate', 'mobil', 'campanii', 'retea', 'context', 'versus', 'banca',
          'istoric', 'surse', 'coada', 'harta', 'concurenta', 'logging', 'rulare']
AXE = [AICI / 'node_modules' / 'axe-core' / 'axe.min.js', AICI.parent / 'node_modules' / 'axe-core' / 'axe.min.js']
JS_AXE = """() => axe.run(document, { runOnly: { type: 'rule', values: ['color-contrast'] } })
  .then(r => r.violations.flatMap(v => v.nodes.map(n => n.target.join(' ') + ' · ' + (n.any[0] ? n.any[0].message : ''))))"""


LATERAL = [f'campanii?s={x}' for x in ('site', 'comunicate', 'google', 'bing', 'youtube', 'retele')] + [
    'produse', 'rate?categorie=credite', 'coada', 'surse']
JS_LATERAL = """() => {
  const m = document.querySelector('#principal')
  const rau = []
  for (const e of [m, ...m.querySelectorAll('.ant-table-body, .ant-table-content, .ant-table-sticky-scroll')]) {
    if (e.scrollWidth > e.clientWidth + 1) rau.push((e.id || e.className).slice(0, 40) + ' ' + e.scrollWidth + '>' + e.clientWidth)
  }
  return rau
}"""


def v_scroll_lateral(b: Browser, url: str) -> None:
    """Nicio derulare pe orizontală la 1280 px și la 1440 px: nici pagina (<main>), nici tabelele."""
    for lat, inalt in ((1440, 900), (1280, 800)):
        for pagina in LATERAL:
            pg = deschide(b, f'{url}/#/{pagina}', lat=lat, inalt=inalt)
            incarcata(pg)
            pg.wait_for_timeout(1000)
            rau = pg.evaluate(JS_LATERAL)
            verifica(not rau, f'{pagina} @{lat}: fără derulare pe orizontală{" (" + "; ".join(rau) + ")" if rau else ""}')
            inchide(pg)


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


VERIFICARI: dict[str, Callable[[Browser, str], None]] = {
    'tema': v_tema,
    'comutator': v_comutator,
    'harta': v_harta,
    'sigle': v_sigle,
    'capete': v_capete,
    'lateral': v_scroll_lateral,
    'contrast': v_contrast,
    'capturi': v_capturi,
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
