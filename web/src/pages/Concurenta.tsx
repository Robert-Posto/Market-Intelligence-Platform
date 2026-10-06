import { useCallback, useMemo, useState } from 'react'
import { Checkbox, Input, Segmented, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { ProdusConcurenta } from '@mcc/shared'
import { useProduseConcurenta } from '../api/comparatie_libra'
import { useMeta } from '../api/meta'
import { Despre, Eroare, Pill, SeIncarca } from '../components/comune'
import { T, useLang, type DictKey } from '../i18n'
import { faraDiacritice, formatZi } from '../util/format'
import { SCURT } from './produse/logica'
import '../styles/produse_libra.css'

const CATEGORII = ['conturi', 'carduri', 'credite', 'depozite_economii', 'investitii', 'asigurari', 'pensii', 'leasing',
  'plati_digitale', 'schimb_valutar', 'trade_finance', 'acceptare_plati', 'altele'] as const
const SEGMENTE: [string, DictKey][] = [['toate', 'pl.segment_toate'], ['PF', 'pl.segment_pf'], ['PJ', 'pl.segment_pj']]
const PENTRU = ['PF', 'PJ', 'PF+PJ']

/** O categorie necunoscută (clasificatorul adaugă una nouă) intră la „Altele”, nu dispare. */
const categoria = (p: ProdusConcurenta) => ((CATEGORII as readonly string[]).includes(p.categorie ?? '') ? p.categorie! : 'altele')

/**
 * Descoperă concurența: produsele concurenței fără echivalent în catalogul Libra,
 * din products_discovery, grupate pe categorie; filtrele stau în adresă. Un rând
 * cu banca Libra = produs de pe librabank.ro care nu e printre cele 57. Portată din
 * aplicația Next.js (components/concurenta/ProduseConcurenta.jsx).
 */
export default function Concurenta() {
  const { t, tn, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const stare = useMemo(() => Object.fromEntries(sp.entries()), [sp])
  const [cauta, setCauta] = useState('')
  const q = useProduseConcurenta()
  const meta = useMeta()

  const mergi = useCallback((k: Record<string, string>) => setSp((p) => {
    const n = new URLSearchParams(p)
    for (const [c, v] of Object.entries(k)) {
      if (v) n.set(c, v)
      else n.delete(c)
    }
    return n
  }, { replace: true }), [setSp])

  if (q.error) return <Eroare e={q.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (!q.data || !meta.data) return <SeIncarca />
  if (!q.data.disponibil) return <section><p className="note"><T k="pc.nedisponibil" /></p></section>

  const m = meta.data
  const toate = q.data.produse
  const seg = stare.segment || 'toate'
  const cat = stare.cat || ''
  const banca = stare.banca || ''
  const c = faraDiacritice(cauta.trim())
  const peSeg = toate.filter((p) => seg === 'toate' || p.segment === seg || p.segment === 'PF+PJ')
  const nrCat: Record<string, number> = {}
  const nrBanca: Record<string, number> = {}
  for (const p of peSeg) {
    nrCat[categoria(p)] = (nrCat[categoria(p)] ?? 0) + 1
    nrBanca[p.banca] = (nrBanca[p.banca] ?? 0) + 1
  }
  const vizibile = peSeg.filter((p) => (!cat || categoria(p) === cat) && (!banca || p.banca === banca)
    && (stare.noi !== '1' || p.nou)
    && (!c || faraDiacritice(`${p.denumire_produs} ${p.descriere_produs ?? ''}`).includes(c)))
  const peCat: Record<string, ProdusConcurenta[]> = {}
  for (const p of vizibile) (peCat[categoria(p)] ??= []).push(p)
  const nume = (b: string) => SCURT[b] ?? m.nume[b] ?? b
  const nrBanci = (l: ProdusConcurenta[]) => new Set(l.map((p) => p.banca)).size

  return (
    <>
      <div className="pl-filtre">
        <Segmented value={seg} onChange={(s) => mergi({ segment: s === 'toate' ? '' : s })}
          options={SEGMENTE.map(([s, k]) => ({ value: s, label: t(k) }))} />
        <Input className="cauta" allowClear placeholder={t('pc.cauta_placeholder')} value={cauta} onChange={(e) => setCauta(e.target.value)} />
        <Checkbox checked={stare.noi === '1'} onChange={() => mergi({ noi: stare.noi === '1' ? '' : '1' })}>{t('pc.bifa_noi')}</Checkbox>
      </div>

      <div className="pl-chipuri">
        <button type="button" className={`pl-chip ${!cat ? 'activ' : ''}`} onClick={() => mergi({ cat: '' })}>
          {t('pc.toate')}<span>{peSeg.length}</span>
        </button>
        {CATEGORII.filter((k) => nrCat[k]).map((k) => (
          <button type="button" key={k} className={`pl-chip ${k === cat ? 'activ' : ''}`} onClick={() => mergi({ cat: k })}>
            {t(`pc.categorie.${k}` as DictKey)}<span>{nrCat[k]}</span>
          </button>
        ))}
      </div>
      <div className="pl-chipuri">
        <button type="button" className={`pl-chip ${!banca ? 'activ' : ''}`} onClick={() => mergi({ banca: '' })}>{t('pc.toate_bancile')}</button>
        {Object.keys(nrBanca).sort((a, b) => nrBanca[b]! - nrBanca[a]!).map((b) => (
          <button type="button" key={b} className={`pl-chip ${b === banca ? 'activ' : ''}`} onClick={() => mergi({ banca: b })}>
            {nume(b)}<span>{nrBanca[b]}</span>
          </button>
        ))}
      </div>

      {!toate.length ? (
        <section><p className="note"><T k="pc.niciun_produs" /></p></section>
      ) : !vizibile.length ? (
        <section><p className="note">{t('pc.niciun_filtre')}</p></section>
      ) : CATEGORII.filter((k) => peCat[k]).map((k) => (
        <section key={k} className="pc-sec">
          <h2>
            {t(`pc.categorie.${k}` as DictKey)}{' '}
            <span className="gri" style={{ fontSize: 13, fontWeight: 400 }}>
              {t('pc.sectiune', { produse: tn('pc.n_produse', peCat[k]!.length), banci: tn('pc.n_banci', nrBanci(peCat[k]!)) })}
            </span>
          </h2>
          <div className="pc-lista">
            {peCat[k]!.map((p) => (
              <a key={p.id} className="pc-produs" href={p.link} target="_blank" rel="noopener noreferrer">
                <span className="pc-banca">{m.logo[p.banca] && <img src={m.logo[p.banca]} alt="" />}{nume(p.banca)}</span>
                {/* denumirea și descrierea vin de pe site-ul băncii: nu se traduc */}
                <span className="pc-nume">
                  {p.denumire_produs}
                  {p.nou && <Pill tip="ok">{t('pc.nou')}</Pill>}
                  {p.retras && <Tooltip title={t('pc.retras_tooltip', { zi: formatZi(p.vazut_la, locale) })}><span><Pill tip="amb">{t('pc.retras')}</Pill></span></Tooltip>}
                  {p.banca === 'libra' && <Pill tip="amb">{t('pc.libra_catalog')}</Pill>}
                </span>
                {p.descriere_produs && <span className="pc-desc">{p.descriere_produs}</span>}
                <span className="pc-jos">
                  {p.segment && PENTRU.includes(p.segment) ? t(`pc.pentru.${p.segment}` as DictKey) : (p.segment ?? '')}
                  {' · '}{t('pc.vazut', { zi: formatZi(p.vazut_la, locale) })}
                </span>
              </a>
            ))}
          </div>
        </section>
      ))}

      <section>
        <Despre>
          <T k="pc.despre_ce" />
          <T k="pc.despre_etichete" />
          <T k="pc.despre_de_unde" />
        </Despre>
      </section>
    </>
  )
}
