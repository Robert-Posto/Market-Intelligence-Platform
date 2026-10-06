#!/usr/bin/env node
/**
 * Statisticile unei aplicații din Google Play, cu `google-play-scraper` (npm): primește
 * slug-ul băncii (`ing`) sau id-ul aplicației (`ro.ing.mobile.banking.android.activity`).
 *
 * DOAR `gplay.app()`: e singura funcție a pachetului care cere o adresă permisă de robots.txt
 * (`/store/apps/details`). Celelalte au fost verificate în sursa v10.1.3 la 06.10.2026 și cad:
 *   reviews, permissions, suggest, list  → `/_/PlayStoreUi/data/batchexecute`  (Disallow: /_)
 *   datasafety                           → `/store/apps/datasafety`            (Disallow explicit)
 *   search, similar, developer           → paginarea trece tot prin batchexecute
 * Pentru permisiuni există analiza APK (2.3 Android).
 *
 * RECENZIILE vin din aceeași pagină `/store/apps/details`, nu din `reviews()`: pagina conține
 * cele 20 de recenzii pe care Google le afișează (cele mai relevante, nu cele mai noi), cu nota,
 * data, versiunea, voturile „util” și răspunsul băncii. `app()` le căuta în ds:8 / ds:9 și
 * întorcea 0; pe 06.10.2026 stăteau în ds:10. Aici blocul se caută după formă, nu după număr.
 * HTML-ul se ia din hook-ul `afterResponse` al lui `got`, deci nicio cerere în plus.
 * Autorul NU se păstrează: doar `autor_hash` = sha256(MIP_SALT|nume)[:32], ca în load_mobil.py;
 * fără MIP_SALT, `--salveaza` refuză să ruleze.
 *
 * Aceleași reguli ca `ingest/transport.py`: originea marcată BLOCAT în `loguri/origini_blocate.jsonl`
 * nu primește nicio cerere (pachetul ăsta ar fi „alt canal”, interzis de flux.marcheaza_blocat);
 * un 429 / 403 o marchează BLOCAT și oprește rularea; fără reîncercări (`got` reîncerca 429 de 2 ori);
 * o cerere la 3 s; UA-ul cu nume și contact din crawler/__init__.py.
 *
 * Rulare:
 *   node ingest/google_play_app.mjs ing                    # raport lizibil
 *   node ingest/google_play_app.mjs ing libra revolut      # mai multe
 *   node ingest/google_play_app.mjs com.revolut.revolut    # după id
 *   node ingest/google_play_app.mjs --toate                # toate băncile cu aplicație Android
 *   node ingest/google_play_app.mjs ing --json             # tot ce întoarce app(), ca JSON
 *   node ingest/google_play_app.mjs ing --lang en          # textele în engleză (implicit ro)
 *   node ingest/google_play_app.mjs --toate --salveaza     # scrie date/google_play.json, citit de 2.3
 *
 * `--salveaza` scrie `date/google_play.json` și `date/google_play_recenzii.json` (în .gitignore,
 * ca restul rezultatelor din date/): pagina 2.3 le citește la build. O rulare pe câteva bănci
 * păstrează celelalte bănci; recenziile se acumulează după id (Google arată alte 20 peste o lună).
 */
import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import gplay from 'google-play-scraper'

const RADACINA = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const JURNAL_BLOCAT = path.join(RADACINA, 'loguri', 'origini_blocate.jsonl')
const FISIER_PLAY = path.join(RADACINA, 'date', 'google_play.json')
const FISIER_RECENZII = path.join(RADACINA, 'date', 'google_play_recenzii.json')
const ORIGINE = 'https://play.google.com'
const PAUZA_MS = 3000
const UA = 'LibraBank-MarketIntel-Test/0.1 (test personal, doar date publice; contact: robert.postolache@librabank.ro)'

function argumente(argv) {
  const a = { tinte: [], json: false, toate: false, salveaza: false, lang: 'ro', tara: 'ro' }
  for (let i = 0; i < argv.length; i++) {
    const x = argv[i]
    if (x === '--json') a.json = true
    else if (x === '--toate') a.toate = true
    else if (x === '--salveaza') a.salveaza = true
    else if (x === '--lang') a.lang = argv[++i]
    else if (x === '--tara') a.tara = argv[++i]
    else if (x === '-h' || x === '--help') a.ajutor = true
    else if (x.startsWith('-')) a.necunoscut = x
    else a.tinte.push(x)
  }
  return a
}

/** MIP_SALT din mediu sau din `.env` (același fișier pe care îl citește config.py). */
function sare() {
  if (process.env.MIP_SALT) return process.env.MIP_SALT
  const env = path.join(RADACINA, '.env')
  if (!fs.existsSync(env)) return null
  const m = fs.readFileSync(env, 'utf8').match(/^\s*MIP_SALT\s*=\s*(.+?)\s*$/m)
  return m ? m[1].replace(/^["']|["']$/g, '') : null
}

const hashAutor = (nume, s) => crypto.createHash('sha256').update(`${s}|${nume ?? ''}`, 'utf8').digest('hex').slice(0, 32)

/**
 * Recenziile din pagină: blocul `AF_initDataCallback` al cărui `data[0]` e o listă de recenzii
 * ([id, [autor, …], notă 1–5, null, text, [secunde, nanos], utile, [null, răspuns, [secunde]], …, versiune]).
 */
function recenziiDinPagina(html, s) {
  const re = /AF_initDataCallback\(\{key: 'ds:\d+'.*?data:([\s\S]*?), sideChannel: \{\}\}\);<\/script>/g
  for (const m of html.matchAll(re)) {
    let d
    try { d = JSON.parse(m[1]) } catch { continue }
    const lista = Array.isArray(d) && Array.isArray(d[0]) ? d[0] : null
    const eRecenzie = (r) => Array.isArray(r) && typeof r[0] === 'string' && Array.isArray(r[1])
      && Number.isInteger(r[2]) && r[2] >= 1 && r[2] <= 5 && Array.isArray(r[5])
    if (!lista?.length || !lista.every(eRecenzie)) continue
    const zi = (sec) => (sec ? new Date(sec * 1000).toISOString().slice(0, 10) : null)
    return lista.map((r) => ({
      id: r[0],
      autor_hash: hashAutor(r[1]?.[0], s),
      nota: r[2],
      text: r[4] ?? null,
      data: zi(r[5]?.[0]),
      utile: r[6] ?? 0,
      raspuns_banca: r[7]?.[1] ?? null,
      raspuns_data: zi(r[7]?.[2]?.[0]),
      versiune: r[10] ?? null,
    }))
  }
  return []
}

/** Motivul, dacă play.google.com e BLOCAT în jurnalul comun cu transport.py; altfel null. */
function motivBlocat() {
  if (!fs.existsSync(JURNAL_BLOCAT)) return null
  let motiv = null
  for (const linie of fs.readFileSync(JURNAL_BLOCAT, 'utf8').split('\n')) {
    if (!linie.trim()) continue
    const e = JSON.parse(linie)
    if (e.origine !== ORIGINE) continue
    motiv = e.actiune === 'DEBLOCAT' ? null : e.motiv
  }
  return motiv
}

function marcheazaBlocat(motiv) {
  fs.mkdirSync(path.dirname(JURNAL_BLOCAT), { recursive: true })
  const data = new Date().toISOString().replace(/\.\d+Z$/, 'Z')
  fs.appendFileSync(JURNAL_BLOCAT, JSON.stringify({ data, origine: ORIGINE, actiune: 'BLOCAT', banca: 'google-play', motiv }) + '\n')
  process.stderr.write(`  BLOCAT ${ORIGINE}: ${motiv} — fără alte cereri, fără alt canal\n`)
}

/**
 * Slug → id de aplicație: aplicația principală (și Libra, rol `reper`) din `android_aplicatii`,
 * prin API-ul pornit (`app/server.py`); fără server, din `date/google_play.json`.
 */
async function harta() {
  const port = process.env.MIP_PORT || 8765
  try {
    const r = await fetch(`http://localhost:${port}/api/android`, { signal: AbortSignal.timeout(5000) })
    const d = await r.json()
    return Object.fromEntries(d.aplicatii.filter((x) => x.rol !== 'secundar').map((x) => [x.banca, x.package]))
  } catch {
    if (!fs.existsSync(FISIER_PLAY)) return {}
    const d = JSON.parse(fs.readFileSync(FISIER_PLAY, 'utf8'))
    return Object.fromEntries(Object.entries(d.aplicatii).map(([banca, x]) => [banca, x.package]))
  }
}

/** Ce păstrează fișierul: câmpurile citite de 2.3, cu numele din restul proiectului (fără descrierea HTML). */
function pentruFisier(a) {
  const h = a.histogram || {}
  return {
    package: a.appId,
    url: `https://play.google.com/store/apps/details?id=${a.appId}`,
    nume: a.title ?? null,
    icon: a.icon ?? null,
    nota: typeof a.score === 'number' ? Math.round(a.score * 100) / 100 : null,
    evaluari: a.ratings ?? null,
    recenzii_scrise: a.reviews ?? null,
    prag_descarcari: a.installs ?? null,
    descarcari_min: a.minInstalls ?? null,
    descarcari: a.maxInstalls ?? null,
    // de la 5★ la 1★, ca app_release.distributie_stele
    distributie_stele: [5, 4, 3, 2, 1].map((k) => h[k] ?? 0),
    versiune: a.version ?? null,
    actualizat_la: a.updated ? new Date(a.updated).toISOString().slice(0, 10) : null,
    lansat: a.released ?? null,
    ce_e_nou: a.recentChanges ? a.recentChanges.replace(/<br\s*\/?>/g, '\n').trim() : null,
    android_minim: a.androidVersionText ?? null,
    // Play repetă uneori aceeași captură (telefon și tabletă): BCR avea 21, dintre care 14 distincte (06.10.2026)
    capturi: [...new Set(a.screenshots ?? [])],
    banner: a.headerImage ?? null,
    video: a.video ?? null,
    rezumat: a.summary ?? null,
    dezvoltator: a.developer ?? null,
    clasificare: a.contentRating ?? null,
    reclame: a.adSupported ?? null,
  }
}

function salveaza(rezultate) {
  const vechi = fs.existsSync(FISIER_PLAY) ? JSON.parse(fs.readFileSync(FISIER_PLAY, 'utf8')).aplicatii ?? {} : {}
  const aplicatii = { ...vechi }
  for (const r of rezultate) if (r.banca) aplicatii[r.banca] = pentruFisier(r)
  fs.mkdirSync(path.dirname(FISIER_PLAY), { recursive: true })
  const acum = new Date().toISOString().replace(/\.\d+Z$/, 'Z')
  fs.writeFileSync(FISIER_PLAY, JSON.stringify({
    colectat_la: acum,
    sursa: 'play.google.com/store/apps/details',
    colector: 'ingest/google_play_app.mjs (google-play-scraper, doar app())',
    aplicatii,
  }, null, 2) + '\n')
  process.stderr.write(`\n${Object.keys(aplicatii).length} aplicații în ${path.relative(RADACINA, FISIER_PLAY)}\n`)

  // recenziile se acumulează: o recenzie văzută o dată nu dispare pentru că Google arată acum alte 20
  const vechiRec = fs.existsSync(FISIER_RECENZII) ? JSON.parse(fs.readFileSync(FISIER_RECENZII, 'utf8')).aplicatii ?? {} : {}
  const rec = { ...vechiRec }
  let noi = 0
  for (const r of rezultate) {
    if (!r.banca) continue
    const dupaId = Object.fromEntries((vechiRec[r.banca]?.recenzii ?? []).map((x) => [x.id, x]))
    for (const x of r.recenzii) {
      if (!dupaId[x.id]) noi++
      dupaId[x.id] = { ...x, vazuta_ultima: acum.slice(0, 10) }
    }
    rec[r.banca] = { package: r.appId, recenzii: Object.values(dupaId).sort((a, b) => (b.data ?? '').localeCompare(a.data ?? '')) }
  }
  fs.writeFileSync(FISIER_RECENZII, JSON.stringify({
    colectat_la: acum,
    sursa: 'play.google.com/store/apps/details (recenziile afișate pe pagină, ~20 pe aplicație)',
    pseudonimizare: 'autor_hash = sha256(MIP_SALT|nume)[:32], ca app_review.autor_hash; numele nu se păstrează',
    aplicatii: rec,
  }, null, 2) + '\n')
  const tot = Object.values(rec).reduce((n, x) => n + x.recenzii.length, 0)
  process.stderr.write(`${tot} recenzii (${noi} noi) în ${path.relative(RADACINA, FISIER_RECENZII)}\n`)
}

const nr = (x) => (x === null || x === undefined ? '—' : Number(x).toLocaleString('ro-RO'))
const zi = (ms) => (ms ? new Date(ms).toISOString().slice(0, 10) : '—')

function raport(slug, a) {
  const h = a.histogram || {}
  const tot = [1, 2, 3, 4, 5].reduce((s, k) => s + (h[k] || 0), 0)
  const bara = (k) => {
    const p = tot ? (h[k] || 0) / tot : 0
    return `${k}★ ${'█'.repeat(Math.round(p * 30)).padEnd(30, '·')} ${String(Math.round(p * 100)).padStart(3)}%  ${nr(h[k])}`
  }
  const linii = [
    `━━ ${a.title} ${slug ? `(${slug})` : ''}`,
    `   ${a.appId} · ${a.developer} · ${a.genre}`,
    `   ${a.url.split('&')[0]}`,
    '',
    `   Notă              ${a.scoreText ?? '—'} ★  (${a.score?.toFixed(3) ?? '—'})`,
    `   Evaluări          ${nr(a.ratings)}`,
    `   Recenzii scrise   ${nr(a.reviews)}`,
    `   Descărcări        ${nr(a.maxInstalls)}  (afișat ${a.installs}, prag minim ${nr(a.minInstalls)})`,
    '',
    ...[5, 4, 3, 2, 1].map((k) => `   ${bara(k)}`),
    '',
    `   Versiune          ${a.version ?? '—'}  · actualizată ${zi(a.updated)} · lansată ${a.released ?? '—'}`,
    `   Android minim     ${a.androidVersionText ?? '—'}`,
    `   Clasificare       ${a.contentRating ?? '—'} · reclame: ${a.adSupported ? 'da' : 'nu'} · cumpărături în aplicație: ${a.offersIAP ? `da (${a.IAPRange ?? '?'})` : 'nu'}`,
    `   Preț              ${a.free ? 'gratuită' : a.priceText}`,
    `   Imagini           ${a.screenshots?.length ?? 0} capturi · iconiță ${a.icon ? 'da' : 'nu'} · banner ${a.headerImage ? 'da' : 'nu'} · video ${a.video ? 'da' : 'nu'}`,
    `   Dezvoltator       ${a.developerEmail ?? '—'} · ${a.developerWebsite ?? '—'}`,
    `   Rezumat           ${a.summary ?? '—'}`,
  ]
  if (a.recentChanges) linii.push(`   Ce e nou          ${a.recentChanges.replace(/<br>/g, ' ').replace(/\s+/g, ' ').slice(0, 200)}`)
  return linii.join('\n')
}

async function main() {
  const a = argumente(process.argv.slice(2))
  if (a.ajutor || (!a.tinte.length && !a.toate)) {
    process.stdout.write(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').match(/\/\*\*([\s\S]*?)\*\//)[1].replace(/^ \* ?/gm, ''))
    return a.ajutor ? 0 : 1
  }
  // o opțiune greșită nu trebuie să devină o „bancă” și să pornească cereri (--salvează, --all)
  if (a.necunoscut) {
    process.stderr.write(`opțiune necunoscută: ${a.necunoscut} (vezi --help)\n`)
    return 1
  }
  const s = sare()
  if (a.salveaza && !s) {
    process.stderr.write('MIP_SALT nu e setat. Opresc: fără sare, hash-urile autorilor ar fi reversibile prin dicționar de nume.\n')
    return 1
  }
  const motiv = motivBlocat()
  if (motiv) {
    process.stderr.write(`${ORIGINE} e BLOCAT în ${path.relative(RADACINA, JURNAL_BLOCAT)} (${motiv}): nicio cerere până la o deblocare decisă de om.\n`)
    return 1
  }

  const banci = await harta()
  // un id de aplicație are puncte (`com.revolut.revolut`); un slug de bancă nu
  const tinte = (a.toate ? Object.keys(banci) : a.tinte).map((x) => (x.includes('.') ? { slug: null, id: x } : { slug: x, id: banci[x] }))
  const rezultate = []
  let cod = 0
  for (const [i, t] of tinte.entries()) {
    if (!t.id) {
      process.stderr.write(`${t.slug}: bancă fără aplicație Android cunoscută (${Object.keys(banci).join(', ')})\n`)
      cod = 1
      continue
    }
    if (i > 0) await new Promise((r) => setTimeout(r, PAUZA_MS))
    try {
      let html = ''
      const app = await gplay.app({
        appId: t.id, lang: a.lang, country: a.tara,
        requestOptions: {
          retry: { limit: 0 }, headers: { 'User-Agent': UA }, timeout: { request: 20000 },
          // aceeași pagină pe care o citește app(): recenziile din ea, fără a doua cerere
          hooks: { afterResponse: [(r) => { html = String(r.body); return r }] },
        },
      })
      const recenzii = recenziiDinPagina(html, s ?? '')
      rezultate.push({ banca: t.slug, ...app, recenzii })
      if (a.salveaza) {
        process.stderr.write(`${(t.slug ?? t.id).padEnd(20)} ${String(app.installs).padStart(12)} · ${app.scoreText} ★ · ${nr(app.ratings)} evaluări · ${app.screenshots?.length ?? 0} capturi · ${recenzii.length} recenzii · v${app.version}\n`)
      } else if (!a.json) process.stdout.write(raport(t.slug, app) + '\n\n')
    } catch (e) {
      process.stderr.write(`${t.slug ?? t.id}: ${e.message}\n`)
      cod = 1
      if ([401, 403, 407, 429, 451].includes(e.status)) {
        marcheazaBlocat(`HTTP ${e.status}`)
        break
      }
    }
  }
  if (a.salveaza) salveaza(rezultate)
  if (a.json) process.stdout.write(JSON.stringify(a.toate || tinte.length > 1 ? rezultate : rezultate[0] ?? null, null, 2) + '\n')
  return cod
}

process.exitCode = await main()
