import { Tooltip } from 'antd'
import type { ValoareDovada } from '@mcc/shared'
import { useLang } from '../i18n'
import { Pill } from './comune'

/**
 * Dovada din spatele unei cifre, folosită de sertar, de coada de verificare, de
 * istoric și de fișa băncii: legătura spre sursă, citatul cu cifra marcată.
 */

/**
 * Adresa vizualizatorului propriu de PDF, la pagina și cu citatul de evidențiat.
 * Un singur loc: era `/pdf.html?…` în aplicația veche și e `#/document?…` acum.
 */
export function linkDocument(url: string, pagina: number, citat: string): string {
  return `#/document?u=${encodeURIComponent(url)}&p=${pagina}&q=${encodeURIComponent(citat)}`
}

/** Motivele din bază (vederea coada_verificare) -> cheia explicației în dicționar. */
export const MOTIV_CHEIE: Record<string, string> = {
  'antet de coloana pierdut': 'antet_coloana_pierdut',
  'prag de suma pierdut': 'prag_suma_pierdut',
  'sumă implauzibilă': 'suma_implauzibila',
  'procent implauzibil': 'procent_implauzibil',
  'extras de LLM: tipul și produsul de confirmat': 'extras_llm',
  'încredere scăzută': 'incredere_scazuta',
  'validator: SUSPECT': 'validator_suspect',
  'peste pragul de plauzibilitate': 'peste_prag_plauzibilitate',
  'ambiguu, motiv nenotat': 'ambiguu_motiv_nenotat',
}

/** Citatul merită arătat doar dacă spune ceva în plus față de cifră (la 2.378 de rânduri din PDF, `citat` era chiar valoarea). */
export function citatUtil(r: ValoareDovada): string | null {
  const c = (r.citat || '').trim()
  if (!c) return null
  return /^[0-9][0-9.,\s]*(lei|euro|eur|usd|ron|%)?$/i.test(c) ? null : c
}

/**
 * Citatul cu cifra evidențiată: se marchează exact numărul observației, cu
 * marginile verificate, ca „20” să nu se marcheze în „2024”. Altfel citatul
 * rămâne neatins. Citatul e textul documentului și nu se traduce.
 */
export function CitatEvidentiat({ r }: { r: ValoareDovada }) {
  const c = r.citat ?? ''
  const t = c.length > 260 ? c.slice(0, 259) + '…' : c
  if (r.valoare === null || r.valoare === undefined) return <>{t}</>
  const v = Number(r.valoare)
  const forme = [...new Set([String(v), v.toFixed(2), v.toFixed(2).replace('.', ',')])]
  for (const f of forme) {
    const i = t.indexOf(f)
    if (i < 0) continue
    const inainte = i > 0 ? t[i - 1]! : ' '
    const dupa = t[i + f.length] ?? ' '
    if (/[0-9]/.test(inainte) || /[0-9.,]/.test(dupa)) continue
    return <>{t.slice(0, i)}<mark>{f}</mark>{t.slice(i + f.length)}</>
  }
  return <>{t}</>
}

/**
 * Trei nivele de dovadă, arătate diferit fiindcă nu sunt același lucru:
 *   ↗ document   linkul duce la cifra însăși (PDF-ul exact sau pagina web)
 *   ⌂ pagină     pagina de pe care banca publică documentul — NU e documentul
 *   (fără link)  numele fișierului și pagina din PDF, verificabile manual
 * La PDF se deschide vizualizatorul propriu (#/document), nu fișierul brut:
 * Chrome ignoră `search=`, iar extensia Adobe pierde `#page=`.
 */
export function LinkSursa({ r }: { r: ValoareDovada }) {
  const { t } = useLang()
  if (r.metoda_extractie === 'catalog') {
    return <Pill title={t('sertar.sursa.catalog_tooltip')}>{t('sertar.sursa.catalog_intern', { fisier: r.fisier || r.sursa || '' })}</Pill>
  }
  const pg = r.pagina ? t('sertar.sursa.pagina_abrev', { pagina: r.pagina }) : ''
  const scurta = (s: string | null) => {
    const x = String(s || '').replace(/^https?:\/\/(www\.)?/, '')
    return x.length > 44 ? x.slice(0, 43) + '…' : x
  }
  if (r.link) {
    if (r.tip_sursa === 'document') {
      const u = linkDocument(r.link, r.pagina || 1, r.citat || '')
      return (
        <Tooltip title={t('sertar.sursa.document_tooltip', { pagina: r.pagina || 1 })}>
          <a className="sursa" href={u} target="_blank" rel="noopener">↗ {scurta(r.fisier || r.sursa)}{pg} ⤷</a>
        </Tooltip>
      )
    }
    return (
      <Tooltip title={t('sertar.sursa.pagina_web_tooltip', { link: r.link })}>
        <a className="sursa" href={`${r.link}${r.ancora || ''}`} target="_blank" rel="noopener">↗ {scurta(r.sursa)}{r.ancora ? ' ⤷' : ''}</a>
      </Tooltip>
    )
  }
  const fisier = <Pill title={t('sertar.sursa.fisier_tooltip')}>{scurta(r.fisier || r.sursa)}{pg}</Pill>
  if (r.link_pagina) {
    return (
      <>
        {fisier}{' '}
        <Tooltip title={t('sertar.sursa.pagina_banca_tooltip', { motiv: r.pagina_documente_motiv || '' })}>
          <a className="sursa pagina" href={r.link_pagina} target="_blank" rel="noopener">{t('sertar.sursa.pagina_banca')}</a>
        </Tooltip>
      </>
    )
  }
  return fisier
}
