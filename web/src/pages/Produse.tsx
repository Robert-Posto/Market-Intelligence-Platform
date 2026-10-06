import { useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Input, Segmented, Select } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { Matrice } from '@mcc/shared'
import { api } from '../api/client'
import { useMeta } from '../api/meta'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../components/comune'
import Sertar, { type CerereSertar } from '../components/Sertar'
import { Tabel } from '../components/Tabel'
import { etDesc, etNume } from '../components/valori'
import { T, useLang, type DictKey } from '../i18n'
import { faraDiacritice, num } from '../util/format'
import ComparatieLibra from './produse/ComparatieLibra'

const GRUPURI: [string, DictKey][] = [
  ['cont_curent', 'produse.grup_cont_curent'],
  ['carduri', 'produse.grup_carduri'],
  ['transferuri', 'produse.grup_transferuri'],
]
const SEGMENTE: [string, DictKey][] = [
  ['toate', 'produse.segment_toate'],
  ['pf', 'produse.segment_pf'],
  ['pj', 'produse.segment_pj'],
  ['pfa', 'produse.segment_pfa'],
]

/**
 * 2.1 Produse & prețuri, cu două vederi: „Comparație cu Libra” (implicită, ca în
 * aplicația veche de pe george-branch) și matricea „Comisioane pe bănci”.
 * Linkurile vechi spre matrice (`#/produse?grup=…`) nu aveau `vedere`, deci un
 * `grup` în adresă deschide tot matricea.
 */
export default function Produse() {
  const { t } = useLang()
  const [sp, setSp] = useSearchParams()
  const vedere = sp.get('vedere') ?? (sp.get('grup') ? 'matrice' : 'libra')
  // filtrele unei vederi nu au sens în cealaltă: la comutare adresa pornește de la zero
  const comutator = (
    <Segmented value={vedere} onChange={(v) => setSp(v === 'matrice' ? { vedere: 'matrice' } : {})}
      options={[{ value: 'libra', label: t('produse.vedere_libra') }, { value: 'matrice', label: t('produse.vedere_matrice') }]} />
  )
  return vedere === 'matrice' ? <MatriceComisioane comutator={comutator} /> : <ComparatieLibra comutator={comutator} />
}

/**
 * Vederea „Comisioane pe bănci”: matrice bancă × serviciu, o privire în loc de cinci
 * clasamente. Celula nu arată o singură cifră (un comision are pachete, praguri,
 * monede — o cifră ar induce în eroare), ci câte prețuri avem, între ce valori
 * și câte sunt gratuite. Clic pe celulă = toate prețurile, cu citat și link.
 */
function MatriceComisioane({ comutator }: { comutator: ReactNode }) {
  const { t, tn, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const grup = sp.get('grup') || 'cont_curent'
  const seg = sp.get('segment') || 'toate'
  const [cauta, setCauta] = useState('')
  const [sertar, setSertar] = useState<CerereSertar | null>(null)
  const meta = useMeta()
  const q = useQuery({
    queryKey: ['matrice', grup, seg],
    queryFn: () => api('/api/matrice', Matrice, { grup, segment: seg, unitate: 'lei' }),
    placeholderData: (p) => p,
  })

  const pe = useMemo(() => {
    const o: Record<string, Record<string, Matrice['celule'][number]>> = {}
    for (const c of q.data?.celule ?? []) (o[c.banca] ??= {})[c.camp] = c
    return o
  }, [q.data])

  if (q.error) return <Eroare e={q.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (!q.data || !meta.data) return <SeIncarca />
  const d = q.data
  const m = meta.data
  const toate = Object.keys(pe)
  const c = faraDiacritice(cauta.trim())
  const banci = c ? toate.filter((b) => faraDiacritice(`${m.nume[b] ?? ''} ${b}`).includes(c)) : toate
  const total = (b: string) => d.campuri.reduce((s, cp) => s + (pe[b]![cp]?.n ?? 0), 0)
  const schimba = (k: string, v: string) => setSp((p) => { const n = new URLSearchParams(p); n.set(k, v); return n })

  return (
    <>
      <div className="bara-fixa">
        <div className="filtre">
          {comutator}
          <Segmented value={grup} onChange={(v) => schimba('grup', v)} options={GRUPURI.map(([v, k]) => ({ value: v, label: t(k) }))} />
          <label className="f">{t('produse.filtru_segment')}
            <Select value={seg} onChange={(v) => schimba('segment', v)} style={{ minWidth: 220 }}
              options={SEGMENTE.map(([v, k]) => ({ value: v, label: t(k) }))} />
          </label>
          <label className="f">{t('produse.filtru_cauta')}
            <Input className="cauta" allowClear placeholder={t('produse.cauta_placeholder')} value={cauta} onChange={(e) => setCauta(e.target.value)} />
          </label>
        </div>
      </div>
      <section style={{ opacity: q.isPlaceholderData ? 0.45 : 1 }}>
        <p className="note" style={{ margin: '0 0 10px' }}><T k="produse.nota_matrice" params={{ n: toate.length }} /></p>
        <Tabel
          randuri={banci}
          cheieRand={(b) => b}
          libra={(b) => b}
          implicit={['total', 'descend']}
          gol={t('produse.fara_date')}
          coloane={[
            { cheie: 'banca', cap: t('produse.col_banca'), s: (b) => m.nume[b] ?? b, val: (b) => <EtichetaBanca slug={b} m={m} fisa tag /> },
            ...d.campuri.map((cp) => ({
              cheie: cp,
              cap: <>{etNume(cp, t)}<span className="cap-d">{etDesc(cp, t)}</span></>,
              s: (b: string) => pe[b]![cp]?.n,
              td: (b: string) => pe[b]![cp]
                ? { className: 'mc', title: t('produse.tooltip_celula', { banca: m.nume[b] ?? b, serviciu: etNume(cp, t) }),
                    onClick: () => setSertar({ banca: b, camp: cp, unitate: 'lei', scenariu: '' }) }
                : { className: 'gol' },
              val: (b: string) => {
                const x = pe[b]![cp]
                if (!x) return '—'
                const interval = x.minim === x.maxim
                  ? t('banca.suma_lei', { suma: num(x.minim, locale) })
                  : t('banca.interval_lei', { minim: num(x.minim, locale), maxim: num(x.maxim, locale) })
                return (
                  <>
                    <b>{num(x.n, locale, 0)}</b> <span className="gri" style={{ fontSize: 11 }}>{t(x.n === 1 ? 'produse.celula_pret_1' : 'produse.celula_pret_n')}</span>
                    <span className="sub">{interval}</span>
                    {x.gratuite > 0 && <span className="g">{tn('produse.celula_gratuite', x.gratuite)}</span>}
                  </>
                )
              },
            })),
            { cheie: 'total', cap: t('produse.col_total'), num: true, s: total, val: (b) => num(total(b), locale, 0) },
          ]}
        />
        <Despre>
          <T k="produse.despre_o_cifra" />
          <T k="produse.despre_segment" />{' '}
          {d.segmente.map((s) => <Pill key={s.seg}>{s.seg}: {num(s.n, locale, 0)}</Pill>)}
          <br />
          {/* frazele sunt texte separate; spațiul dintre ele îl pune pagina, nu dicționarul */}
          {d.excluse_ambigue > 0 && <><T k="produse.despre_ambigue" params={{ n: num(d.excluse_ambigue, locale, 0) }} />{' '}</>}
          {d.excluse_implauzibile > 0 && (
            <><T k="produse.despre_implauzibile" params={{ n: num(d.excluse_implauzibile, locale, 0), prag: num(d.prag_plauzibil, locale, 0) }} />{' '}</>
          )}
          <T k="produse.despre_coada" />
        </Despre>
      </section>
      <Sertar cerere={sertar} onClose={() => setSertar(null)} />
    </>
  )
}
