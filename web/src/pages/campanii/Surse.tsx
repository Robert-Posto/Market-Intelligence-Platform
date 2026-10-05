import type { ReactNode } from 'react'
import { Collapse } from 'antd'
import { Link } from 'react-router-dom'
import { useCampanii, useComunicate } from '../../api/campanii'
import { faraRutaYoutube, useYoutube } from '../../api/youtube_retele'
import { Pill } from '../../components/comune'
import { Tabel } from '../../components/Tabel'
import { useLang } from '../../i18n'
import { deLaServer } from '../../i18n/server'
import { formatZi, num } from '../../util/format'

interface Sursa {
  nume: string
  ce: string
  nevoie: string
  ok: boolean
  /** secțiunea 2.4 cu datele sursei; fără ea, numele nu e link */
  s?: string
}

/**
 * 2.4: toate sursele posibile și ce cere fiecare, pliat la coada fiecărei
 * secțiuni. Numele surselor externe sunt nume proprii (Meta Ad Library, YouTube
 * Data API v3…) și nu se traduc.
 */
export default function Surse() {
  const { t, lang, locale } = useLang()
  const camp = useCampanii()
  const com = useComunicate()
  const yt = useYoutube()
  if (!camp.data || !com.data || (!yt.data && !yt.error)) return null

  const zi = (x: string | null | undefined) => formatZi(String(x || '').slice(0, 10), locale)
  const rulare = camp.data.rulare
  const nCamp = camp.data.randuri.length
  const nBanciCamp = new Set(camp.data.randuri.map((r) => r.banca)).size
  const nBanciCom = new Set(com.data.map((r) => r.banca)).size
  // un server pornit înainte de ruta nouă răspunde 404 (useYoutube dă atunci obiectul de rezervă):
  // rândul spune asta, în limba aleasă, iar restul tabelului merge; la fel la orice altă eroare, ca în aplicația veche
  const y = yt.data ?? { data_extragerii: null, sterge_la: null, banci: {}, motiv: null }
  const motivYt = !yt.data || faraRutaYoutube(yt.data) ? t('campanii.youtube.motiv_fara_ruta') : y.motiv ? deLaServer(y.motiv, lang) : ''
  const nCanale = Object.keys(y.banci).length

  const surse: Sursa[] = [
    {
      nume: t('campanii.surse.landing.nume'),
      ce: t('campanii.surse.landing.ce_aduce'),
      nevoie: t('campanii.surse.landing.stare', { n_campanii: num(nCamp, locale, 0), n_banci: nBanciCamp, data: zi(rulare?.campanii) }),
      ok: true,
      s: 'site',
    },
    {
      nume: t('campanii.surse.newsroom.nume'),
      ce: t('campanii.surse.newsroom.ce_aduce'),
      nevoie: t('campanii.surse.newsroom.stare', { n_comunicate: num(com.data.length, locale, 0), n_banci: nBanciCom, data: zi(rulare?.comunicate) }),
      ok: true,
      s: 'comunicate',
    },
    { nume: 'Microsoft Ad Library (Bing)', ce: t('campanii.surse.bing.ce_aduce'), nevoie: t('campanii.surse.bing.stare'), ok: true, s: 'bing' },
    { nume: 'Meta Ad Library', ce: t('campanii.surse.meta.ce_aduce'), nevoie: t('campanii.surse.meta.stare'), ok: false },
    { nume: 'TikTok Commercial Content Library', ce: t('campanii.surse.tiktok.ce_aduce'), nevoie: t('campanii.surse.tiktok.stare'), ok: false },
    {
      nume: 'YouTube Data API v3',
      ce: t('campanii.surse.youtube.ce_aduce'),
      nevoie: y.data_extragerii
        ? t('campanii.surse.youtube.stare', { n_canale: num(nCanale, locale, 0), data_extragerii: zi(y.data_extragerii), sterge_la: zi(y.sterge_la) })
        : t('campanii.surse.youtube.stare_fara', { motiv: motivYt || t('campanii.surse.youtube.motiv_implicit') }),
      ok: !!y.data_extragerii && nCanale > 0,
      s: 'youtube',
    },
    { nume: 'Google Ads Transparency Center', ce: t('campanii.surse.google.ce_aduce'), nevoie: t('campanii.surse.google.stare'), ok: true, s: 'google' },
  ]

  const corp: ReactNode = (
    <>
      <p className="note" style={{ margin: '0 0 8px' }}>{t('campanii.surse.nota')}</p>
      <Tabel
        randuri={surse}
        cheieRand={(r) => r.nume}
        coloane={[
          { cheie: 'sursa', cap: t('campanii.surse.col_sursa'), val: (r) => (r.s ? <Link to={`/campanii?s=${r.s}`}>{r.nume}</Link> : r.nume) },
          { cheie: 'ce', cap: t('campanii.surse.col_ce_aduce'), val: (r) => r.ce },
          { cheie: 'nevoie', cap: t('campanii.surse.col_ce_e_nevoie'), val: (r) => <Pill tip={r.ok ? 'ok' : undefined}>{r.nevoie}</Pill> },
        ]}
      />
    </>
  )
  return (
    <Collapse
      ghost
      className="despre cs-surse"
      items={[{ key: 's', label: <span className="despre-cap">ⓘ {t('campanii.surse.titlu')}</span>, children: corp }]}
    />
  )
}
