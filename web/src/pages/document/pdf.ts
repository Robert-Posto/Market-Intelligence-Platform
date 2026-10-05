import { getDocument, GlobalWorkerOptions, TextLayer, Util, type PDFDocumentLoadingTask, type PDFDocumentProxy, type PageViewport } from 'pdfjs-dist'
import type { TextContent, TextItem } from 'pdfjs-dist/types/src/display/api'
import urlWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
// stilul stratului de text (.textLayer) vine din pachet, aceeași versiune ca biblioteca
import 'pdfjs-dist/web/pdf_viewer.css'
import { faraDiacritice } from '../../util/format'

/* PDF.js din npm, cu worker-ul servit de Vite de pe aceeași origine: pdf.html
   îl lua din cdnjs, deci vizualizatorul nu mergea fără internet chiar când
   documentul era în Bronze. */
GlobalWorkerOptions.workerSrc = urlWorker

/**
 * Documentul vine prin serverul nostru, nu direct de la bancă: un `fetch`
 * către CDN-ul băncii cade pe CORS, iar PDF.js are nevoie de octeți. Ruta
 * `/pdf` servește doar adresele înregistrate în `surse` (altfel ar fi proxy
 * deschis) și ia fișierul din Bronze când există.
 */
export function incarcaDocument(url: string): PDFDocumentLoadingTask {
  return getDocument(`/pdf?u=${encodeURIComponent(url)}`)
}

/* Normalizare pentru potrivire: PDF-urile despart des cuvintele în glife
   separate, cu spații care nu există în text, și folosesc diacritice
   inconsistent. Se compară fără spații și fără diacritice — altfel citatul
   „Lunar: 20 Lei” nu se regăsește într-un text extras ca „Lunar : 20 Lei”. */
const strans = (s: string) => faraDiacritice(s).replace(/\s+/g, '')

export interface Dreptunghi {
  left: number
  top: number
  width: number
  height: number
}

/**
 * Găsește citatul în textul paginii și întoarce dreptunghiurile lui.
 * PDF.js dă fiecare fragment de text cu transformarea lui; se caută secvența
 * de fragmente care, lipite, conțin citatul. Nu e o căutare vizuală, sunt
 * coordonatele glifelor.
 */
export function marcaje(tc: TextContent, viewport: PageViewport, citat: string): Dreptunghi[] {
  if (!citat) return []
  const cauta = strans(citat)
  if (cauta.length < 4) return []
  // un citat lung poate trece de 14 fragmente: atunci ajung primele 18 caractere
  const contine = (s: string) => s.includes(cauta) || (cauta.length > 18 && s.includes(cauta.slice(0, 18)))
  const it = tc.items.filter((i): i is TextItem => 'str' in i && !!i.str.trim())
  const lipite = it.map((x) => strans(x.str))
  // se încearcă ferestre de fragmente consecutive
  for (let i = 0; i < it.length; i++) {
    let acc = ''
    for (let j = i; j < Math.min(i + 14, it.length); j++) {
      acc += lipite[j]
      if (contine(acc)) {
        /* Fereastra pornește de la primul fragment încercat, deci prindea și
           până la ~140 de caractere dinaintea citatului: în pdf.html, la
           „Lunar: 20 Lei, în echivalent” (BCR, cont în valută, 05.10.2026) se
           colorau 14 fragmente, cu fraza de deasupra tabelului și antetul lui;
           citatul are 5. Se strânge de la stânga cât timp restul îl conține. */
        let k = i
        while (k < j && contine(lipite.slice(k + 1, j + 1).join(''))) k++
        return it.slice(k, j + 1).map((x) => {
          const t = Util.transform(viewport.transform, x.transform) as number[]
          const h = Math.hypot(t[2]!, t[3]!) || x.height
          return { left: t[4]!, top: t[5]! - h, width: x.width * viewport.scale, height: h * 1.18 }
        })
      }
      if (acc.length > cauta.length + 140) break
    }
  }
  return []
}

/**
 * Randează o pagină în `cutie`: pânza, stratul de text (textul se poate
 * selecta și copia) și evidențierea citatului. Întoarce câte dreptunghiuri
 * s-au marcat, sau null dacă între timp s-a cerut altă vedere (`viu()` fals):
 * o pagină începută nu mai ajunge în ecranul nou.
 */
export async function randeazaPagina(
  doc: PDFDocumentProxy,
  nr: number,
  cutie: HTMLElement,
  citat: string,
  latime: number,
  viu: () => boolean,
): Promise<number | null> {
  const pag = await doc.getPage(nr)
  if (!viu()) return null
  const v1 = pag.getViewport({ scale: 1 })
  const viewport = pag.getViewport({ scale: Math.max(0.6, latime / v1.width) })

  const foaie = document.createElement('div')
  foaie.className = 'doc-foaie'
  foaie.style.width = `${viewport.width}px`
  foaie.style.height = `${viewport.height}px`
  // stratul de text din PDF.js 4 își calculează pozițiile din variabila asta
  foaie.style.setProperty('--scale-factor', String(viewport.scale))
  const canvas = document.createElement('canvas')
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.floor(viewport.width * dpr)
  canvas.height = Math.floor(viewport.height * dpr)
  canvas.style.width = `${viewport.width}px`
  canvas.style.height = `${viewport.height}px`
  foaie.appendChild(canvas)
  cutie.appendChild(foaie)

  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.scale(dpr, dpr)
  await pag.render({ canvasContext: ctx, viewport }).promise
  if (!viu()) return null

  const tc = await pag.getTextContent()
  if (!viu()) return null
  const strat = document.createElement('div')
  strat.className = 'textLayer'
  foaie.appendChild(strat)
  await new TextLayer({ textContentSource: tc, container: strat, viewport }).render()
  if (!viu()) return null

  const m = marcaje(tc, viewport, citat)
  for (const r of m) {
    const d = document.createElement('div')
    d.className = 'doc-marcaj'
    d.style.left = `${r.left}px`
    d.style.top = `${r.top}px`
    d.style.width = `${Math.max(r.width, 6)}px`
    d.style.height = `${r.height}px`
    foaie.appendChild(d)
  }
  return m.length
}
