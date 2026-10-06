import { useState } from 'react'
import { Tooltip } from 'antd'
import type { ValoareLibra } from '@mcc/shared'
import { Pill } from '../../components/comune'
import { useLang } from '../../i18n'
import { num } from '../../util/format'
import { Eticheta } from './Iconita'
import { etichete, rang, valoare, vizibila, type Stare } from './logica'

const VIZIBILE = 3

function Valoare({ v, deschide, implicit = false, mare = false }: {
  v: ValoareLibra
  deschide: (v: ValoareLibra) => void
  implicit?: boolean
  mare?: boolean
}) {
  const { t, tn, locale } = useLang()
  const e = etichete(v.scenariu, v, t, tn, locale, implicit)
  // „altele” poartă în valoare_text ce este cifra („comision transfer”); fără ea, 0,4% nu spune nimic
  const ce = v.camp === 'altele' && v.valoare !== null ? v.valoare_text : null
  return (
    <Tooltip title={t('pl.v_tooltip')} mouseEnterDelay={0.6}>
      <button type="button" className={`pl-v${mare ? ' mare' : ''}`} onClick={() => deschide(v)}>
        {/* eticheta vine din document: nu se traduce */}
        {ce && <span className="ce">{ce}</span>}
        <span className="val">{valoare(v, t, locale)}</span>
        {v.ambiguu && <Pill tip="amb">{t('pl.neclar')}</Pill>}
        {v.incredere != null && v.incredere < 0.85 && <Pill>{t('pl.incredere', { n: num(v.incredere, locale) })}</Pill>}
        {e.length > 0 && <span className="sc">{e.map((x, i) => <Eticheta key={i} e={x} />)}</span>}
      </button>
    </Tooltip>
  )
}

const potrivire = (v: ValoareLibra) => v.scenariu?.referinta?.potrivire
const aceeasi = (a: ValoareLibra, b: ValoareLibra) =>
  a.valoare === b.valoare && a.valoare_text === b.valoare_text && a.unitate === b.unitate

/**
 * O celulă bancă × câmp. Când câmpul depinde de scenariul de referință, celula răspunde
 * întâi la întrebarea comparației: cifra pe referință, mare, o singură dată; restul
 * (alte trepte, alte valute, oferte condiționate) se numără pe o linie și se deschid la clic.
 * Altfel: primele 3 valori, restul la „+ încă N”.
 */
export default function Celula({ lista, stare, deschide }: {
  lista: ValoareLibra[] | undefined
  stare: Stare
  deschide: (v: ValoareLibra) => void
}) {
  const { t, tn } = useLang()
  const [toate, setToate] = useState(false)
  const l = (lista ?? []).filter((v) => vizibila(v, stare)).sort((a, b) => rang(a) - rang(b))
  if (!l.length) {
    if (lista?.length) return <span className="pl-gol">{t(stare.ref === '1' ? 'pl.doar_alt_exemplu' : 'pl.ascuns_filtre')}</span>
    return <span className="pl-gol">—</span>
  }
  const cuReferinta = l.some((v) => v.scenariu?.referinta)

  if (cuReferinta && !toate) {
    const exacte = l.filter((v) => potrivire(v) === 'exact')
    const aprox = l.filter((v) => potrivire(v) === 'aproximativ')
    const baza = exacte.length ? exacte : aprox.length ? aprox : l.slice(0, 1)
    // aceeași cifră din două documente se arată o dată
    const principale = baza.filter((v, i) => baza.findIndex((x) => aceeasi(x, v)) === i)
    const rest = l.filter((v) => !principale.includes(v))
    const valuta = principale[0]?.scenariu?.valuta
    const alteValute = rest.filter((v) => v.scenariu?.valuta && valuta && v.scenariu.valuta !== valuta).length
    const conditionate = rest.filter((v) => potrivire(v) === 'aproximativ').length
    const alte = rest.length - alteValute - conditionate
    const parti = [
      alteValute > 0 && tn('pl.c.valute', alteValute),
      conditionate > 0 && tn('pl.c.conditionate', conditionate),
      alte > 0 && tn('pl.c.alte', alte),
    ].filter(Boolean)
    return (
      <>
        {!exacte.length && <span className="pl-gol">{t('pl.c.fara_referinta')}</span>}
        {principale.map((v, i) => (
          <Valoare key={i} v={v} deschide={deschide} implicit={potrivire(v) === 'exact'} mare={exacte.length > 0} />
        ))}
        {rest.length > 0 && (
          <button type="button" className="pl-mai pl-rest" onClick={() => setToate(true)}>
            {tn('pl.c.rest', rest.length)}
            {parti.length > 0 && <small>{parti.join(' · ')}</small>}
          </button>
        )}
      </>
    )
  }

  const arata = toate ? l : l.slice(0, VIZIBILE)
  return (
    <>
      {arata.map((v, i) => <Valoare key={i} v={v} deschide={deschide} />)}
      {!toate && l.length > VIZIBILE && (
        <button type="button" className="pl-mai" onClick={() => setToate(true)}>{t('pl.mai_multe', { n: l.length - VIZIBILE })}</button>
      )}
      {toate && cuReferinta && (
        <button type="button" className="pl-mai" onClick={() => setToate(false)}>{t('pl.c.restrange')}</button>
      )}
    </>
  )
}
