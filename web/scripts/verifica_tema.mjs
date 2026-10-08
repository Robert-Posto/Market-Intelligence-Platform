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
  warn: '--warn', ok: '--ok', accent: '--accent', accentTint: '--accent-tint', onAccent: '--on-accent', capTabel: '--cap-tabel',
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
