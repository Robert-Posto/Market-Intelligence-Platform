import { useState } from 'react'
import { Button, Select } from 'antd'
import type { Sentiment } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { Pill } from '../../components/comune'
import { useLang } from '../../i18n'
import { formatZi, num } from '../../util/format'
import { Stele } from './Piese'

/** Primele 15 la vedere, restul la cerere: serverul trimite până la 120 (LIMIT în /api/sentiment). */
const VIZIBILE = 15

export interface FiltruRecenzii {
  banca: string
  nota: string
  storefront: string
}

/**
 * Recenziile din App Store (fosta pagină 2.7 Sentiment, mutată aici pe 25.09:
 * „ce notă are aplicația și de ce se plâng oamenii” sunt aceeași întrebare).
 * Bara rămâne sus la derulare; `id="recenzii"` e ținta lui `?la=recenzii`.
 */
export function BaraRecenzii({ s, f, schimba, sterge }: {
  s: Sentiment
  f: FiltruRecenzii
  schimba: (o: Partial<FiltruRecenzii>) => void
  sterge: () => void
}) {
  const { t, locale } = useLang()
  const banci = s.sumar.slice().sort((a, b) => a.nume.localeCompare(b.nume, locale))
  return (
    <div className="bara-fixa" id="recenzii">
      <div className="filtre">
        <b className="mb-bara-titlu">{t('mobil.recenzii')}</b>
        <label className="f">{t('rate.banca')}
          <Select value={f.banca} onChange={(v) => schimba({ banca: v })} style={{ minWidth: 200 }} popupMatchSelectWidth={false}
            options={[
              { value: '', label: t('mobil.toate_bancile') },
              ...banci.map((x) => ({ value: x.banca, label: `${x.nume} (${num(x.review_uri, locale, 0)})` })),
            ]} />
        </label>
        <label className="f">{t('mobil.nota')}
          <Select value={f.nota} onChange={(v) => schimba({ nota: v })} style={{ minWidth: 140 }} popupMatchSelectWidth={false}
            options={[
              { value: '', label: t('mobil.toate_notele') },
              ...[5, 4, 3, 2, 1].map((n) => ({ value: String(n), label: '★'.repeat(n) })),
            ]} />
        </label>
        <label className="f">{t('mobil.magazin')}
          <Select value={f.storefront} onChange={(v) => schimba({ storefront: v })} style={{ minWidth: 140 }} popupMatchSelectWidth={false}
            options={[
              { value: '', label: t('mobil.toate') },
              ...s.storefronts.map((x) => ({ value: x.storefront ?? '', label: `${x.storefront ?? ''} (${num(x.n, locale, 0)})` })),
            ]} />
        </label>
        {(f.banca || f.nota || f.storefront) && <Button onClick={sterge}>{t('mobil.sterge_filtrele')}</Button>}
        <span className="note" style={{ marginLeft: 'auto' }}>{t('mobil.in_filtrul_curent', { n: num(s.total_filtrat, locale, 0) })}</span>
      </div>
    </div>
  )
}

/** Lista; „arată toate” se uită la schimbarea filtrului (pagina o remontează cu altă cheie). */
export function ListaRecenzii({ s, f, m }: { s: Sentiment; f: FiltruRecenzii; m: Meta }) {
  const { t } = useLang()
  const [toate, setToate] = useState(false)
  const lista = toate ? s.recente : s.recente.slice(0, VIZIBILE)
  return (
    <section>
      <h2>{f.banca ? t('mobil.titlu_rec_banca', { banca: m.nume[f.banca] ?? f.banca }) : t('mobil.titlu_rec_toate')}</h2>
      {s.recente.length ? lista.map((r, i) => <Recenzie key={i} r={r} m={m} />) : <p className="note">{t('mobil.nicio_recenzie')}</p>}
      {!toate && s.recente.length > VIZIBILE && (
        <Button onClick={() => setToate(true)}>{t('mobil.arata_toate', { n: s.recente.length })}</Button>
      )}
    </section>
  )
}

/** O recenzie din App Store, în cardul comun cu Google Play. */
function Recenzie({ r, m }: { r: Sentiment['recente'][number]; m: Meta }) {
  return (
    <CardRecenzie banca={r.banca} m={m} nota={r.rating} data={r.postat_la} versiune={r.versiune} magazin={r.storefront}
      text={r.text} raspuns={r.raspuns_banca} />
  )
}

/**
 * Antetul: sigla (fără nume: „Banca Transilvania” se suprapunea cu eticheta vitrinei) și
 * stelele sub ea; în dreapta vitrina, versiunea și data. Textul și răspunsul băncii rămân
 * cum le-a scris omul, netraduse.
 */
export function CardRecenzie({ banca, m, nota, data, versiune, magazin, text, raspuns, raspunsData, utile }: {
  banca: string
  m: Meta
  nota: number | null
  data: string | null
  versiune?: string | null
  magazin?: string | null
  text: string | null
  raspuns?: string | null
  raspunsData?: string | null
  utile?: number | null
}) {
  const { t, tn, locale } = useLang()
  const nume = m.nume[banca] ?? banca
  const logo = m.logo[banca]
  return (
    <div className="rec">
      <div className="rec-cap">
        <div className="rec-banca">
          {logo ? <img className="rec-sigla" src={logo} alt={nume} title={nume} /> : <b className="nm">{nume}</b>}
          <Stele nota={nota} marime={16} />
        </div>
        <div className="rec-meta">
          {magazin && <Pill>{magazin}</Pill>}
          {versiune && <Pill>v{versiune}</Pill>}
          {!!utile && <span className="gri rec-utile">{tn('mobil.n_utile', utile)}</span>}
          <span className="mono gri rec-data">{data ? formatZi(data, locale) : ''}</span>
        </div>
      </div>
      <div className="rec-txt">{text || t('mobil.fara_text')}</div>
      {raspuns && (
        <div className="rec-txt rec-raspuns">
          <b>{t('mobil.raspunsul_bancii')}</b> {raspuns}
          {raspunsData && <span className="mono gri"> · {formatZi(raspunsData, locale)}</span>}
        </div>
      )}
    </div>
  )
}
