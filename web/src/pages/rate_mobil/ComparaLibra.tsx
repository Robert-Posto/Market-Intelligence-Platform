import { Modal, Select } from 'antd'
import type { Mobil as MobilT, Sentiment } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { EtichetaBanca } from '../../components/comune'
import { useLang } from '../../i18n'
import { num } from '../../util/format'
import { googlePlay } from './dateLocale'
import { Galerie, RezumatAi, Stele } from './Piese'

export type RandAplicatie = MobilT['versiuni'][number] & { rec: Sentiment['sumar'][number] | null }

/**
 * Libra lângă o altă bancă, așezate ca pagina aplicației din App Store: întrebarea venea
 * cu capturile deschise în două sertare pe rând, deci comparația se făcea din memorie.
 * Numele și iconița vin din Google Play: app_release are doar app_id (06.10.2026); fără Play,
 * titlul e numele băncii și iconița e sigla ei.
 */
export default function ComparaLibra({ deschis, vs, aplicatii, capturiPe, m, alege, onClose }: {
  deschis: boolean
  vs: string
  aplicatii: RandAplicatie[]
  capturiPe: Record<string, string[]>
  m: Meta
  alege: (banca: string) => void
  onClose: () => void
}) {
  const { t } = useLang()
  const libra = aplicatii.find((r) => r.banca === 'libra')
  const alta = aplicatii.find((r) => r.banca === vs && r.banca !== 'libra')
  const optiuni = aplicatii
    .filter((r) => r.banca !== 'libra')
    .map((r) => ({ value: r.banca, nume: m.nume[r.banca] ?? r.banca, label: <EtichetaBanca slug={r.banca} m={m} /> }))
    .sort((a, b) => a.nume.localeCompare(b.nume))
  const titlu = alta ? t('mobil.compara_titlu', { banca: m.nume[alta.banca] ?? alta.banca }) : t('mobil.compara_titlu_gol')

  return (
    <Modal open={deschis} onCancel={onClose} footer={null} centered width="min(1380px, 96vw)" destroyOnHidden className="as-modal"
      title={<span className="sertar-titlu">{titlu}</span>}>
      <div className="as-alege">
        <span className="gri">{t('mobil.compara_alege')}</span>
        <Select showSearch value={alta?.banca} onChange={alege} options={optiuni} optionFilterProp="nume" style={{ width: 280 }}
          placeholder={t('mobil.compara_alege')} />
      </div>
      <div className="as-coloane">
        {libra ? <PaginaStore r={libra} urls={capturiPe.libra ?? []} m={m} /> : <div className="as-gol gri">{t('mobil.compara_fara_libra')}</div>}
        {alta ? <PaginaStore r={alta} urls={capturiPe[alta.banca] ?? []} m={m} /> : <div className="as-gol gri">{t('mobil.compara_gol')}</div>}
      </div>
      <p className="note" style={{ margin: '12px 0 0' }}>{t('mobil.compara_nota_nume')}</p>
    </Modal>
  )
}

/** O coloană în ordinea paginii din App Store: antet, note, ce spun recenziile, previzualizare. */
function PaginaStore({ r, urls, m }: { r: RandAplicatie; urls: string[]; m: Meta }) {
  const { t, locale } = useLang()
  const nota = r.rating_agregat === null ? null : Number(r.rating_agregat)
  const dist = (r.distributie_stele ?? []).map(Number)
  const tot = dist.reduce((s, x) => s + x, 0)
  const play = googlePlay?.aplicatii[r.banca]
  const banca = m.nume[r.banca] ?? r.banca
  // iconița și numele reale vin din Google Play; App Store nu le are colectate
  const icon = play?.icon ?? m.logo[r.banca]
  return (
    <section className="as-pagina">
      <header className="as-antet">
        <div className={['as-icon', play?.icon ? 'real' : ''].join(' ').trim()}>
          {icon ? <img src={icon} alt="" referrerPolicy="no-referrer" /> : <span>{banca.slice(0, 1)}</span>}
        </div>
        <div className="as-antet-txt">
          <h3>{play?.nume ?? banca}</h3>
          <div className="gri">{play?.nume ? banca : 'iOS'}{r.versiune ? ` · ${t('mobil.as_versiune', { v: r.versiune })}` : ''}</div>
          {r.app_id && (
            <a className="as-buton" href={`https://apps.apple.com/ro/app/id${r.app_id}`} target="_blank" rel="noopener">{t('mobil.as_deschide')}</a>
          )}
        </div>
      </header>

      <div className="as-sectiune">
        <h4>{t('mobil.as_evaluari')}</h4>
        <div className="as-note">
          <div className="as-nota-mare">
            <b>{nota === null ? '—' : num(nota, locale, 1)}</b>
            <span className="gri">{t('mobil.as_din_5')}</span>
          </div>
          <div className="as-histograma">
            {tot > 0 && dist.map((x, i) => (
              <div key={i} className="as-rand-stea">
                <span className="as-stele-mici">{'★'.repeat(5 - i)}</span>
                <span className="as-bara"><span style={{ width: `${(100 * x) / tot}%` }} /></span>
              </div>
            ))}
          </div>
        </div>
        <Stele nota={nota} marime={30} />
        <div className="mb-volum as-volum-mare">
          <b>{num(r.volum_rating, locale, 0)}</b>
          <span>{t('mobil.note_app_store')}</span>
        </div>
      </div>

      <div className="as-sectiune">
        <RezumatAi banca={r.banca} compact />
      </div>

      <div className="as-sectiune">
        <h4>{t('mobil.as_previzualizare')}</h4>
        {urls.length
          ? <Galerie urls={urls} inaltime={360} clasa="as-capturi" titlu={t('mobil.capturi_titlu', { banca })} />
          : <div className="as-gol gri">{t('mobil.fara_capturi')}</div>}
      </div>
    </section>
  )
}
