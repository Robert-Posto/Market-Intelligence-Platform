import { Modal, Select } from 'antd'
import type { Meta } from '../../../api/meta'
import { EtichetaBanca } from '../../../components/comune'
import { useLang } from '../../../i18n'
import { num } from '../../../util/format'
import { googlePlay } from '../dateLocale'
import { Galerie, RezumatAi, Stele } from '../Piese'

type AplicatiePlay = NonNullable<typeof googlePlay>['aplicatii'][string]

/**
 * Libra lângă o altă bancă, așezate ca pagina aplicației din Google Play: perechea modalului
 * de la iOS (ComparaLibra), din `date/google_play.json`. Pe bancă e aplicația principală
 * (cheia din google_play.json), aceeași pe care o rezumă și analiza AI a recenziilor.
 */
export default function ComparaPlay({ deschis, vs, m, alege, onClose }: {
  deschis: boolean
  vs: string
  m: Meta
  alege: (banca: string) => void
  onClose: () => void
}) {
  const { t } = useLang()
  const aplicatii = googlePlay?.aplicatii ?? {}
  const libra = aplicatii.libra
  const alta = vs && vs !== 'libra' ? aplicatii[vs] : undefined
  const optiuni = Object.keys(aplicatii)
    .filter((b) => b !== 'libra')
    .map((b) => ({ value: b, nume: m.nume[b] ?? b, label: <EtichetaBanca slug={b} m={m} /> }))
    .sort((a, b) => a.nume.localeCompare(b.nume))
  const titlu = alta ? t('mobil.compara_titlu_play', { banca: m.nume[vs] ?? vs }) : t('mobil.compara_titlu_gol_play')

  return (
    <Modal open={deschis} onCancel={onClose} footer={null} centered width="min(1380px, 96vw)" destroyOnHidden className="as-modal"
      title={<span className="sertar-titlu">{titlu}</span>}>
      <div className="as-alege">
        <span className="gri">{t('mobil.compara_alege')}</span>
        <Select showSearch value={alta ? vs : undefined} onChange={alege} options={optiuni} optionFilterProp="nume" style={{ width: 280 }}
          placeholder={t('mobil.compara_alege')} />
      </div>
      <div className="as-coloane">
        {libra ? <PaginaPlay banca="libra" p={libra} m={m} /> : <div className="as-gol gri">{t('mobil.compara_fara_libra_play')}</div>}
        {alta ? <PaginaPlay banca={vs} p={alta} m={m} /> : <div className="as-gol gri">{t('mobil.compara_gol')}</div>}
      </div>
      <p className="note" style={{ margin: '12px 0 0' }}>{t('mobil.compara_nota_play')}</p>
    </Modal>
  )
}

/** O coloană în ordinea paginii din Google Play: antet, note, descărcări, ce spun recenziile, capturi. */
function PaginaPlay({ banca, p, m }: { banca: string; p: AplicatiePlay; m: Meta }) {
  const { t, locale } = useLang()
  const dist = (p.distributie_stele ?? []).map(Number)
  const tot = dist.reduce((s, x) => s + x, 0)
  const numeBanca = m.nume[banca] ?? banca
  const icon = p.icon ?? m.logo[banca]
  const capturi = p.capturi ?? []
  return (
    <section className="as-pagina">
      <header className="as-antet">
        <div className={['as-icon', p.icon ? 'real' : ''].join(' ').trim()}>
          {icon ? <img src={icon} alt="" referrerPolicy="no-referrer" /> : <span>{numeBanca.slice(0, 1)}</span>}
        </div>
        <div className="as-antet-txt">
          {/* numele aplicației vine din Google Play: nu se traduce */}
          <h3>{p.nume ?? numeBanca}</h3>
          <div className="gri">{p.nume ? numeBanca : 'Android'}{p.versiune ? ` · ${t('mobil.as_versiune', { v: p.versiune })}` : ''}</div>
          <a className="as-buton" href={p.url} target="_blank" rel="noopener">{t('mobil.as_deschide_play')}</a>
        </div>
      </header>

      <div className="as-sectiune">
        <h4>{t('mobil.as_evaluari')}</h4>
        <div className="as-note">
          <div className="as-nota-mare">
            <b>{p.nota === null ? '—' : num(p.nota, locale, 1)}</b>
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
        <Stele nota={p.nota} marime={30} />
        <div className="mb-volum as-volum-mare">
          <b>{num(p.evaluari, locale, 0)}</b>
          <span>{t('mobil.note_google_play')}</span>
        </div>
        <div className="mb-volum as-volum-mare">
          <b>{num(p.descarcari, locale, 0)}</b>
          <span>{t('mobil.descarcari_play_compara', { prag: p.prag_descarcari ?? '—' })}</span>
        </div>
      </div>

      <div className="as-sectiune">
        <RezumatAi banca={banca} compact sursa="play" />
      </div>

      <div className="as-sectiune">
        <h4>{t('mobil.as_previzualizare')}</h4>
        {capturi.length
          ? <Galerie urls={capturi} inaltime={360} clasa="as-capturi" titlu={t('mobil.capturi_titlu_play', { banca: numeBanca })} />
          : <div className="as-gol gri">{t('mobil.fara_capturi_play')}</div>}
      </div>
    </section>
  )
}
