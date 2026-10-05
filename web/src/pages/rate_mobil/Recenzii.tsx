import { useState } from 'react'
import { Button, Select } from 'antd'
import type { Sentiment } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { EtichetaBanca, Pill } from '../../components/comune'
import { useLang } from '../../i18n'
import { formatZi, num } from '../../util/format'

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

/** O recenzie: textul și răspunsul băncii rămân cum le-a scris omul, netraduse. */
function Recenzie({ r, m }: { r: Sentiment['recente'][number]; m: Meta }) {
  const { t, locale } = useLang()
  const n = Math.max(0, Math.min(5, r.rating ?? 0))
  return (
    <div className="rec">
      <div className="rec-cap">
        <span className={`rec-stele${n >= 4 ? ' bun' : n <= 2 ? ' rau' : ''}`}>{'★'.repeat(n)}{'☆'.repeat(5 - n)}</span>
        <EtichetaBanca slug={r.banca} m={m} />
        <Pill>{r.storefront}</Pill>
        {r.versiune && <Pill>v{r.versiune}</Pill>}
        <span className="mono gri rec-data">{r.postat_la ? formatZi(r.postat_la, locale) : ''}</span>
      </div>
      <div className="rec-txt">{r.text || t('mobil.fara_text')}</div>
      {r.raspuns_banca && (
        <div className="rec-txt rec-raspuns"><b>{t('mobil.raspunsul_bancii')}</b> {r.raspuns_banca}</div>
      )}
    </div>
  )
}
