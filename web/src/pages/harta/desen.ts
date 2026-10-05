/**
 * Culoarea de brand și insignele de pe hartă, desenate pe canvas.
 *
 * Logourile intră AICI, nu în DOM: se desenează o dată per bancă, apoi harta
 * mută doar texturi pe GPU. De aceea numărul de puncte nu mai contează.
 *
 * Două variante per tip, comutate după zoom:
 *   „punct” — la depărtare: cerc/pătrat plin, doar culoarea băncii. Curat,
 *             fără aglomerare de text.
 *   „chip”  — la apropiere: card alb cu bara de brand și LOGOUL real, lizibil,
 *             fiindcă acolo există lățime.
 */

export type TipLocatie = 'sucursala' | 'atm'

/** Codul băncii scris pe punct; celelalte primesc primele trei litere din slug. */
export const COD: Record<string, string> = {
  bcr: 'BCR', brd: 'BRD', 'banca-transilvania': 'BT', raiffeisen: 'RAI', ing: 'ING',
  unicredit: 'UC', cec: 'CEC', garanti: 'GAR', libra: 'LIB', patria: 'PAT', salt: 'SALT',
}
export const codBanca = (slug: string) => COD[slug] ?? slug.slice(0, 3).toUpperCase()

/** Culorile pentru băncile fără logo sau cu logo fără culoare dominantă. */
export const CULOARE_REZERVA = ['#1d6f6f', '#b5651d', '#3b6fb6', '#7a3b8f', '#2f7a4f', '#b03a48',
  '#0f766e', '#a8720f', '#4f46a5', '#5b7c99', '#8b5cf6']

export function incarcaImagine(src: string): Promise<HTMLImageElement> {
  return new Promise((rez, resp) => {
    const img = new Image()
    img.crossOrigin = 'anonymous'
    img.onload = () => rez(img)
    img.onerror = () => resp(new Error(`nu s-a putut încărca ${src}`))
    img.src = src
  })
}

export function culoareDominanta(img: HTMLImageElement): string | null {
  const N = 48
  const c = document.createElement('canvas')
  c.width = c.height = N
  const ctx = c.getContext('2d', { willReadFrequently: true })
  if (!ctx) return null
  // logourile late se desenează încadrate, ca să nu se piardă zona colorată
  const r = Math.min(N / (img.naturalWidth || N), N / (img.naturalHeight || N))
  const w = (img.naturalWidth || N) * r
  const h = (img.naturalHeight || N) * r
  ctx.drawImage(img, (N - w) / 2, (N - h) / 2, w, h)
  const px = ctx.getImageData(0, 0, N, N).data
  const cos: Record<string, { n: number; R: number; G: number; B: number }> = {}
  for (let i = 0; i < px.length; i += 4) {
    const R = px[i]!, G = px[i + 1]!, B = px[i + 2]!, A = px[i + 3]!
    if (A < 200) continue
    const max = Math.max(R, G, B), min = Math.min(R, G, B)
    const lum = (max + min) / 2
    const sat = max === min ? 0 : (max - min) / (255 - Math.abs(max + min - 255))
    if (sat < 0.25 || lum < 28 || lum > 235) continue // ignoră gri, alb, negru
    const k = `${R >> 4},${G >> 4},${B >> 4}` // cuantizare
    const x = (cos[k] ??= { n: 0, R: 0, G: 0, B: 0 })
    x.n++; x.R += R; x.G += G; x.B += B
  }
  let best: { n: number; R: number; G: number; B: number } | null = null
  for (const k in cos) if (!best || cos[k]!.n > best.n) best = cos[k]!
  if (!best) return null
  const b = best
  const f = (v: number) => Math.round(v / b.n)
  return `rgb(${f(b.R)}, ${f(b.G)}, ${f(b.B)})`
}

function contur(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  if (ctx.roundRect) { ctx.roundRect(x, y, w, h, r); return }
  ctx.moveTo(x + r, y) // fallback Safari < 16.4
  ctx.arcTo(x + w, y, x + w, y + h, r)
  ctx.arcTo(x + w, y + h, x, y + h, r)
  ctx.arcTo(x, y + h, x, y, r)
  ctx.arcTo(x, y, x + w, y, r)
  ctx.closePath()
}

function panza(w: number, h: number, ratie: number) {
  const c = document.createElement('canvas')
  c.width = Math.round(w * ratie)
  c.height = Math.round(h * ratie)
  const ctx = c.getContext('2d')!
  ctx.scale(ratie, ratie)
  return { c, ctx }
}

function umbra(ctx: CanvasRenderingContext2D, on: boolean) {
  ctx.shadowColor = on ? 'rgba(16,24,32,.30)' : 'transparent'
  ctx.shadowBlur = on ? 5 : 0
  ctx.shadowOffsetY = on ? 1.5 : 0
}

const rgb = (text: string) => (text.match(/\d+/g) ?? ['90', '110', '125']).map(Number)

// alb pe fundal închis, aproape-negru pe fundal deschis — altfel codul se
// pierde pe brandurile luminoase (galben, portocaliu deschis)
function textPeste(rgbText: string): string {
  const [r = 90, g = 110, b = 125] = rgb(rgbText)
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return lum > 0.62 ? '#15202b' : '#ffffff'
}

/** Culoarea amestecată cu alb: `alfa` din culoare, restul alb. */
function amesteca(rgbText: string, alfa: number): string {
  return `rgb(${rgb(rgbText).slice(0, 3).map((v) => Math.round(v * alfa + 255 * (1 - alfa))).join(',')})`
}

export function badgePunct(cod: string, culoare: string, tip: TipLocatie, ratie: number): ImageData {
  const D = tip === 'sucursala' ? 36 : 28 // diametru/latură
  const P = 7 // spațiu pentru umbră
  const S = D + P * 2
  const { c, ctx } = panza(S, S, ratie)

  umbra(ctx, true)
  ctx.beginPath()
  if (tip === 'sucursala') contur(ctx, P, P, D, D, 9)
  else ctx.arc(S / 2, S / 2, D / 2, 0, Math.PI * 2)
  ctx.fillStyle = culoare
  ctx.fill()
  umbra(ctx, false)

  ctx.lineWidth = tip === 'sucursala' ? 3 : 2.5
  ctx.strokeStyle = 'rgba(255,255,255,.95)'
  ctx.stroke()

  // codul băncii, ca să se știe cine e și la depărtare, când nu încape logoul
  const dim = tip === 'sucursala'
    ? (cod.length >= 4 ? 11 : cod.length === 3 ? 13 : 15)
    : (cod.length >= 4 ? 8.5 : cod.length === 3 ? 10 : 12)
  ctx.fillStyle = textPeste(culoare)
  ctx.font = `700 ${dim}px "IBM Plex Sans", system-ui, sans-serif`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(cod, S / 2, S / 2 + 0.5)

  return ctx.getImageData(0, 0, c.width, c.height)
}

export function badgeChip(img: HTMLImageElement | undefined, culoare: string, tip: TipLocatie, ratie: number, eticheta: string): ImageData {
  const H = tip === 'sucursala' ? 44 : 34
  const W = tip === 'sucursala' ? 140 : 112
  const P = 8
  const { c, ctx } = panza(W + P * 2, H + P * 2, ratie)
  const x = P, y = P, r = tip === 'sucursala' ? 11 : 9
  const bara = tip === 'sucursala' ? 6 : 5

  umbra(ctx, true)
  ctx.beginPath()
  contur(ctx, x, y, W, H, r)
  // sucursala: alb, prezență puternică. ATM: fundal ușor colorat, mai discret.
  ctx.fillStyle = tip === 'sucursala' ? '#ffffff' : amesteca(culoare, 0.12)
  ctx.fill()
  umbra(ctx, false)

  ctx.lineWidth = tip === 'sucursala' ? 2 : 1.25
  ctx.strokeStyle = amesteca(culoare, 0.55)
  ctx.stroke()

  // bara de brand pe muchia stângă, tăiată pe forma chipului
  ctx.save()
  ctx.beginPath()
  contur(ctx, x, y, W, H, r)
  ctx.clip()
  ctx.fillStyle = culoare
  ctx.fillRect(x, y, bara, H)
  ctx.restore()

  // logoul, încadrat în spațiul rămas
  if (img) {
    const padX = 9, padY = tip === 'sucursala' ? 9 : 7
    const zonaW = W - bara - padX * 2, zonaH = H - padY * 2
    const iw = img.naturalWidth || 100, ih = img.naturalHeight || 40
    const k = Math.min(zonaW / iw, zonaH / ih)
    const lw = iw * k, lh = ih * k
    ctx.drawImage(img, x + bara + padX + (zonaW - lw) / 2, y + padY + (zonaH - lh) / 2, lw, lh)
  }

  // eticheta „ATM”, ca tipul să fie explicit și fără legendă
  if (tip === 'atm') {
    ctx.fillStyle = culoare
    ctx.font = '700 8px "IBM Plex Mono", monospace'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'bottom'
    ctx.fillText(eticheta, x + W - 5, y + H - 3)
  }

  return ctx.getImageData(0, 0, c.width, c.height)
}

export interface Sigle {
  culori: Record<string, string>
  imagini: Record<string, HTMLImageElement>
}

/**
 * Culoarea fiecărei bănci, din logoul ei; imaginile încărcate se refolosesc
 * apoi la desenarea chip-urilor, ca să nu le cerem de două ori.
 */
export async function pregatesteSigle(banci: string[], logo: Record<string, string>): Promise<Sigle> {
  const culori: Record<string, string> = {}
  const imagini: Record<string, HTMLImageElement> = {}
  await Promise.all(banci.map(async (slug, i) => {
    const rezerva = CULOARE_REZERVA[i % CULOARE_REZERVA.length]!
    const src = logo[slug]
    if (!src) { culori[slug] = rezerva; return }
    try {
      const img = await incarcaImagine(src)
      imagini[slug] = img
      culori[slug] = culoareDominanta(img) ?? rezerva
    } catch {
      culori[slug] = rezerva
    }
  }))
  // codurile de pe puncte se desenează pe canvas: fără fontul încărcat, primele
  // texturi ar ieși cu fontul de sistem și ar rămâne așa (se desenează o dată)
  try {
    await Promise.all([document.fonts.load('700 13px "IBM Plex Sans"'), document.fonts.load('700 8px "IBM Plex Mono"')])
  } catch {
    /* fără fonturi: rămâne fontul de rezervă din `ctx.font` */
  }
  return { culori, imagini }
}
