import { useState } from 'react'
import { Button, Tooltip } from 'antd'
import { DownloadOutlined } from '@ant-design/icons'
import { useSearchParams } from 'react-router-dom'
import type { AplicatieAndroid } from '@mcc/shared'
import { BareStele } from '../../../components/BareStele'
import { T, useLang } from '../../../i18n'
import { num } from '../../../util/format'
import { googlePlay, playDupaPachet, recenziiPlay } from '../dateLocale'
import { CeENou, Galerie, RezumatAi, Stele } from '../Piese'
import { Captura } from './comune'
import ComparaPlay from './ComparaPlay'
import { eticheta, type PropsSectiune } from './model'
import RecenziiPlay from './RecenziiPlay'

/**
 * Google Play: aceleași carduri ca la iOS (notă, evaluări, descărcări, capturi), din
 * `date/google_play.json` (ingest/google_play_app.mjs), cu rezumatul analizei APK dedesubt.
 * Până la 06.10.2026 secțiunea Android avea doar APK-urile: nicio cifră de magazin.
 */
export default function Magazin({ apps, m, deschide }: PropsSectiune) {
  const { t } = useLang()
  const [recenzii, setRecenzii] = useState<AplicatieAndroid | null>(null)
  // ca la iOS: banca aleasă stă în adresă (`?vs=ing`), deci o comparație se poate trimite
  const [sp, setSp] = useSearchParams()
  const [compara, setCompara] = useState(false)
  const vs = sp.get('vs') || ''
  const alegeVs = (b: string) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      if (b) n.set('vs', b)
      else n.delete('vs')
      return n
    })
  // ca `Tabel`: Libra prima, apoi după descărcări; aplicațiile fără date din Play la coadă
  const ordonate = [...apps].sort((a, b) => {
    if ((a.banca === 'libra') !== (b.banca === 'libra')) return a.banca === 'libra' ? -1 : 1
    return (playDupaPachet(b.package)?.descarcari ?? -1) - (playDupaPachet(a.package)?.descarcari ?? -1)
  })
  const cuDate = apps.filter((a) => playDupaPachet(a.package)).length

  return (
    <section className="an-sec">
      <div className="mb-lista-cap">
        <h2>{t('mobil.android_titlu_magazin')}</h2>
        {googlePlay && (
          <Button type="primary" className="mb-btn-compara" onClick={() => setCompara(true)}>{t('mobil.compara_buton')}</Button>
        )}
      </div>
      <p className="note" style={{ margin: '0 0 12px' }}>
        <T k="mobil.android_nota_magazin" params={{
          n: cuDate, total: apps.length,
          data: googlePlay ? googlePlay.colectat_la.slice(0, 10) : '—',
        }} />
      </p>
      <div className="mb-carduri">
        {ordonate.map((a) => (
          <CardPlay key={a.package} a={a} m={m} deschide={deschide} onRecenzii={() => setRecenzii(a)} />
        ))}
      </div>
      {!googlePlay && <div className="gol-stare">{t('mobil.raport_lipsa')}</div>}
      <RecenziiPlay pachet={recenzii?.package ?? null} banca={recenzii?.banca ?? ''} m={m} onClose={() => setRecenzii(null)} />
      <ComparaPlay deschis={compara || !!vs} vs={vs} m={m} alege={alegeVs} onClose={() => { setCompara(false); alegeVs('') }} />
    </section>
  )
}

function CardPlay({ a, m, deschide, onRecenzii }: {
  a: AplicatieAndroid
  m: PropsSectiune['m']
  deschide: (pachet: string) => void
  onRecenzii: () => void
}) {
  const { t, tn, locale } = useLang()
  const p = playDupaPachet(a.package)
  const nume = m.nume[a.banca] ?? a.banca
  const logo = m.logo[a.banca]
  const capturi = p?.capturi ?? []
  const nRec = recenziiPlay(a.package).length
  return (
    <article className="mb-card">
      <div className="mb-card-sus">
        <div className="mb-card-info">
          {logo ? <Tooltip title={nume}><img className="mb-sigla" src={logo} alt={nume} /></Tooltip> : <span className="mb-sigla-txt">{nume}</span>}
          {p ? (
            <>
              {/* nota și evaluările un singur bloc: 4,59 fără „din 3.081” nu spune cât cântărește */}
              <div className="mb-rating">
                <div className="mb-nota">
                  <Stele nota={p.nota} marime={26} />
                  {p.nota !== null && <span className="mb-nota-cifra">{num(p.nota, locale)}</span>}
                </div>
                <div className="mb-volum"><b>{num(p.evaluari, locale, 0)}</b><span>{t('mobil.note_google_play')}</span></div>
              </div>
              <Tooltip title={t('mobil.descarcari_title', { prag: p.prag_descarcari ?? '—' })}>
                <div className="an-descarcari">
                  <DownloadOutlined aria-hidden />
                  <b>{num(p.descarcari, locale, 0)}</b>
                  <span>{t('mobil.descarcari')}</span>
                </div>
              </Tooltip>
              <Tooltip title={t('mobil.distributia_title_play')}>
                <span className="mb-stele"><BareStele dist={p.distributie_stele} latime={230} /></span>
              </Tooltip>
              <div className="mb-versiune">
                <span className="gri">{t('mobil.versiune')}</span> <b className="mono">{p.versiune ?? a.versiune_cea_mai_noua ?? '—'}</b>
                {p.actualizat_la && <span className="gri"> · {t('mobil.actualizata', { data: p.actualizat_la })}</span>}
              </div>
              <CeENou text={p.ce_e_nou ?? null} />
            </>
          ) : (
            <p className="gri" style={{ fontSize: 12, margin: 0 }}>{t('mobil.play_lipsa_app')}</p>
          )}
          <div className="an-butoane">
            {nRec > 0 && <Button size="small" type="primary" onClick={onRecenzii}>{t('mobil.rec_play_buton', { n: nRec })}</Button>}
            <Button size="small" onClick={() => deschide(a.package)}>{t('mobil.detalii_apk')}</Button>
          </div>
        </div>
        <div className="mb-card-capturi">
          {capturi.length
            ? <>
                <Galerie urls={capturi} inaltime={270} clasa="mb-banda" titlu={t('mobil.capturi_titlu_play', { banca: nume })} />
                <span className="sub mb-banda-nota">{tn('mobil.n_capturi', capturi.length)} · {t('mobil.clic_marire')}</span>
              </>
            : <div className="mb-fara-capturi gri">{t('mobil.fara_capturi_play')}</div>}
        </div>
      </div>
      <div className="mb-card-jos">
        {/* rezumatele sunt pe bancă, ale aplicației principale: MyBRD și Avantaj ar fi primit rezumatul YOU BRD / monet */}
        <RezumatAi banca={a.rol === 'secundar' ? '' : a.banca} sursa="play" />
      </div>
      <div className="mb-card-apk">
        <div className="an-apk">
          <div className="ap-eticheta">{t('mobil.din_apk')}</div>
          <dl className="an-apk-cifre">
            <div><dt>{t('mobil.android_framework')}</dt><dd>{eticheta(t, 'fw', a.framework)}</dd></div>
            <div><dt>{t('mobil.android_d_sdk')}</dt><dd>{num(a.min_sdk, locale, 0)} → {num(a.target_sdk, locale, 0)}</dd></div>
            <div><dt>{t('mobil.android_col_permisiuni')}</dt><dd>{num(a.nr_permisiuni, locale, 0)}</dd></div>
            <div><dt>{t('mobil.android_col_trackere')}</dt><dd>{num(a.nr_trackere, locale, 0)}</dd></div>
            <div><dt>{t('mobil.android_col_biblioteci')}</dt><dd>{num(a.nr_biblioteci, locale, 0)}</dd></div>
            <div><dt>{t('mobil.android_col_captura')}</dt><dd><Captura v={a.captura} simplu /></dd></div>
          </dl>
          <span className="sub">{t('mobil.android_analizata', { v: a.versiune_analizata ?? '—' })}</span>
        </div>
      </div>
    </article>
  )
}
