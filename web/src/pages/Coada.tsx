import { Fragment } from 'react'
import { Button, Checkbox, Select } from 'antd'
import { useMeta } from '../api/meta'
import { useCoadaVerificare } from '../api/surse_coada'
import { Despre, EtichetaBanca, Eroare, Pliat, SeIncarca } from '../components/comune'
import { Paginare } from '../components/Paginare'
import { Tabel, type Coloana } from '../components/Tabel'
import { T, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { num } from '../util/format'
import { useFiltreAdresa } from './surse_coada/adresa'
import { GrupeCoada } from './surse_coada/GrupeCoada'
import { useMotive } from './surse_coada/motive'
import '../styles/surse_coada.css'

const CHEI = ['motiv', 'banca', 'produs', 'context'] as const
const LIM = 100

/** Același text ca la Istoric („Bancă”, „toate băncile”…): extragerea din 02.10 a păstrat o singură cheie pe text. */
const K_BANCA: DictKey = 'istoric.banca'
const K_TOATE_BANCILE: DictKey = 'istoric.toate_bancile'
const K_STERGE: DictKey = 'istoric.sterge_filtrele'

interface RandMatrice {
  banca: string
  nume: string
  tot: number
  n: Record<string, number>
}

/*
 * Coada de verificare. Revamp 25.09 în aplicația veche: tabel bancă × motiv (cât
 * e de verificat, dintr-o privire), explicația motivului o singură dată, rânduri
 * pe o linie, paginare reală — înainte se vedeau doar primele 150 de rânduri din 5.263.
 */
export default function Coada() {
  const { t, lang, locale } = useLang()
  const a = useFiltreAdresa(CHEI)
  const { f } = a
  const meta = useMeta()
  const q = useCoadaVerificare(a.parametri(LIM))
  const mot = useMotive()

  const err = q.error ?? meta.error
  if (err) return <Eroare e={err} />
  if (!q.data || !meta.data) return <SeIncarca />
  const d = q.data
  const m = meta.data
  const c = d.context

  // matricea bancă × motiv, cu motivele în ordinea mărimii lor (pe_motiv vine sortat de server)
  const motive = d.pe_motiv.map((x) => x.motiv)
  const mat: Record<string, RandMatrice> = {}
  for (const x of d.matrice) {
    const r = (mat[x.banca] ??= { banca: x.banca, nume: x.banca_nume || x.banca, tot: 0, n: {} })
    r.n[x.motiv] = x.n
    r.tot += x.n
  }
  const coloane: Coloana<RandMatrice>[] = [
    { cheie: 'banca', cap: t(K_BANCA), s: (r) => r.nume, val: (r) => <EtichetaBanca slug={r.banca} m={m} tag /> },
    ...motive.map((mo): Coloana<RandMatrice> => ({
      cheie: `m:${mo}`,
      cap: mot.scurt(mo),
      titlu: mot.explicatie(mo) || mot.nume(mo),
      num: true,
      s: (r) => r.n[mo] || 0,
      td: (r) => (r.n[mo]
        ? { className: `mc${r.banca === f.banca && mo === f.motiv ? ' best' : ''}`, title: `${r.nume} · ${mot.nume(mo)}`,
            onClick: () => a.mergi({ banca: r.banca, motiv: mo }) }
        : { className: 'gol' }),
      val: (r) => (r.n[mo] ? <b>{num(r.n[mo], locale, 0)}</b> : '·'),
    })),
    { cheie: 'total', cap: t('coada.col_total'), num: true, s: (r) => r.tot, val: (r) => <b>{num(r.tot, locale, 0)}</b>,
      td: (r) => ({ className: 'mc', onClick: () => a.mergi({ banca: r.banca, motiv: '' }) }) },
  ]

  const banci = d.pe_banca.slice().sort((x, y) => (x.banca_nume || x.banca).localeCompare(y.banca_nume || y.banca, locale))
  const procent = num((100 * c.in_coada) / Math.max(c.observatii_total, 1), locale, 1)

  return (
    <div className="sc" style={{ opacity: q.isPlaceholderData ? 0.45 : 1 }}>
      <section>
        <div className="callout warn">
          <T k="coada.callout" params={{ in_coada: num(c.in_coada, locale, 0), total: num(c.observatii_total, locale, 0), procent }} />
        </div>
      </section>

      {/* un filtru pe bancă sau pe motiv pliază matricea: rândurile alese sunt dedesubt */}
      <Pliat key={f.banca || f.motiv ? 'inchis' : 'deschis'} deschis={!(f.banca || f.motiv)}
        titlu={<>{t('coada.matrice_titlu')} <span className="note">{t('coada.matrice_nota')}</span></>}>
        <section className="sc-matrice">
          <Tabel randuri={Object.values(mat)} coloane={coloane} cheieRand={(r) => r.banca} libra={(r) => r.banca} implicit={['total', 'descend']} />
          <Despre titlu="coada.despre_titlu">
            {motive.map((mo, i) => (
              <Fragment key={mo}>
                {i > 0 && <br />}
                <b>{mot.scurt(mo)}</b> — {mot.explicatie(mo) || mot.nume(mo)}
              </Fragment>
            ))}
          </Despre>
        </section>
      </Pliat>

      <div className="bara-fixa">
        <div className="filtre">
          <label className="f">{t('coada.motiv')}
            <Select value={f.motiv} onChange={(v: string) => a.mergi({ motiv: v })} style={{ minWidth: 200 }} popupMatchSelectWidth={false}
              options={[
                { value: '', label: t('coada.toate_motivele') },
                ...d.pe_motiv.map((x) => ({ value: x.motiv, label: `${mot.scurt(x.motiv)} (${num(x.n, locale, 0)})` })),
              ]} />
          </label>
          <label className="f">{t(K_BANCA)}
            <Select value={f.banca} onChange={(v: string) => a.mergi({ banca: v })} style={{ minWidth: 320 }} popupMatchSelectWidth={false}
              options={[
                { value: '', label: t(K_TOATE_BANCILE) },
                ...banci.map((x) => ({ value: x.banca, label: `${x.banca_nume || x.banca} (${num(x.n, locale, 0)})` })),
              ]} />
          </label>
          <label className="f">{t('coada.produs')}
            {/* produsul e un cod din bază (`comisioane`, `dobanda-nominala`): rămâne cod în adresă, tradus doar la afișare */}
            <Select value={f.produs} onChange={(v: string) => a.mergi({ produs: v })} style={{ minWidth: 180 }} popupMatchSelectWidth={false}
              options={[
                { value: '', label: t('coada.toate_produsele') },
                ...d.pe_produs.map((x) => ({ value: x.produs ?? '', label: `${deLaServer(x.produs, lang)} (${num(x.n, locale, 0)})` })),
              ]} />
          </label>
          {/* la jumătate din rânduri citatul e chiar cifra („349 RON”) și nu ajută la decizie */}
          <Checkbox className="sc-bifa" checked={f.context === '1'} onChange={(e) => a.mergi({ context: e.target.checked ? '1' : '' })}>
            {t('coada.doar_cu_context')}
          </Checkbox>
          {a.activ && <Button onClick={a.sterge}>{t(K_STERGE)}</Button>}
          <span className="note sc-n">
            {d.total === 1 ? t('coada.numar_filtru_1', { n: 1 }) : t('coada.numar_filtru', { n: num(d.total, locale, 0) })}
          </span>
        </div>
      </div>

      {f.motiv && (
        <div className="callout" style={{ marginBottom: 14 }}>
          <b>{mot.nume(f.motiv)}.</b> {mot.explicatie(f.motiv)}
        </div>
      )}

      <section>
        {d.randuri.length ? (
          <GrupeCoada d={d} motivAles={f.motiv} mot={mot} />
        ) : (
          <div className="gol-stare">
            <b>{t('coada.gol_titlu')}</b>
            {t('coada.gol_text')}
          </div>
        )}
        <Paginare total={d.total} offset={d.offset} limit={d.limit} onChange={a.pagina} />
      </section>
    </div>
  )
}
