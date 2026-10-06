import { Tooltip } from 'antd'
import type { AplicatieAndroid } from '@mcc/shared'
import { Pill } from '../../../components/comune'
import { Tabel, type Coloana } from '../../../components/Tabel'
import { T, useLang, type DictKey } from '../../../i18n'
import { num } from '../../../util/format'
import { Bifa, CelulaApp, Note } from './comune'
import { categorii, GRUPURI_PERMISIUNI, LOCATIE_FUNDAL, permScurt, type PropsSectiune } from './model'

/**
 * Trackerele și permisiunile sensibile, pe versiunea cea mai nouă a fiecărei
 * aplicații. Fără clasament separat („cele mai multe trackere”): numărul rămâne
 * coloană sortabilă, lângă numele lor, ca să se vadă ce sunt, nu doar câte.
 */
export default function TrackerePermisiuni({ ix, apps, m, deschide }: PropsSectiune) {
  const { t, locale } = useLang()
  const ver = (a: AplicatieAndroid) => ix.ultima[a.package] ?? null
  const trk = (a: AplicatieAndroid) => ix.trackere[a.package] ?? []
  const perm = (a: AplicatieAndroid) => ix.perm[a.package] ?? []

  const colTrackere: Coloana<AplicatieAndroid>[] = [
    { cheie: 'aplicatie', cap: t('mobil.android_col_aplicatie'), s: (a) => m.nume[a.banca] ?? a.banca,
      val: (a) => <CelulaApp a={a} m={m} versiune={ver(a)} /> },
    { cheie: 'n', cap: t('mobil.android_col_trackere'), titlu: t('mobil.android_col_trackere_title'), num: true, s: (a) => trk(a).length,
      val: (a) => num(trk(a).length, locale, 0) },
    { cheie: 'lista', cap: t('mobil.android_col_care'),
      val: (a) => {
        const l = trk(a)
        if (!l.length) return <span className="gri">{t('mobil.android_niciun_tracker')}</span>
        return (
          <span className="an-pills">
            {l.map((x) => {
              const cat = categorii(x, t)
              return (
                <Pill key={x.tracker} title={[cat, x.dovada && t('mobil.android_gasit_ca', { dovada: x.dovada })].filter(Boolean).join(' · ') || undefined}>
                  {x.tracker}
                </Pill>
              )
            })}
          </span>
        )
      } },
  ]

  const colPermisiuni: Coloana<AplicatieAndroid>[] = [
    { cheie: 'aplicatie', cap: t('mobil.android_col_aplicatie'), s: (a) => m.nume[a.banca] ?? a.banca,
      val: (a) => <CelulaApp a={a} m={m} versiune={ver(a)} /> },
    { cheie: 'total', cap: t('mobil.android_col_toate_perm'), titlu: t('mobil.android_col_toate_perm_title'), num: true, s: (a) => perm(a).length,
      val: (a) => num(perm(a).length, locale, 0) },
    ...GRUPURI_PERMISIUNI.map((g) => {
      const are = (a: AplicatieAndroid) => perm(a).filter((p) => g.perm.includes(p) || (!!g.prefix && p.startsWith(g.prefix)))
      return {
        cheie: g.k,
        cap: t(`mobil.android_perm.${g.k}` as DictKey),
        titlu: t(`mobil.android_perm_d.${g.k}` as DictKey),
        s: (a: AplicatieAndroid) => (are(a).length ? 1 : 0),
        td: () => ({ className: 'an-c' }),
        val: (a: AplicatieAndroid) => {
          const l = are(a)
          if (!l.length) return <Bifa da={false} />
          return (
            <Tooltip title={l.map(permScurt).join(', ')}>
              <span>
                <Bifa da>{g.k === 'locatie' && l.includes(LOCATIE_FUNDAL) && <span className="an-fundal"> {t('mobil.android_perm_fundal')}</span>}</Bifa>
              </span>
            </Tooltip>
          )
        },
      }
    }),
  ]

  return (
    <>
      <section className="an-sec">
        <h2>{t('mobil.android_titlu_trackere')}</h2>
        <p className="note" style={{ margin: '0 0 10px' }}><T k="mobil.android_nota_trackere" /></p>
        <div className="an-tabel">
          <Tabel randuri={apps} coloane={colTrackere} cheieRand={(a) => a.package} libra={(a) => a.banca} onRand={(a) => deschide(a.package)}
            gol={t('mobil.android_gol_filtru')} />
        </div>
      </section>
      <section className="an-sec">
        <h2>{t('mobil.android_titlu_permisiuni')}</h2>
        <p className="note" style={{ margin: '0 0 10px' }}><T k="mobil.android_nota_permisiuni" /></p>
        <div className="an-tabel an-mx">
          <Tabel randuri={apps} coloane={colPermisiuni} cheieRand={(a) => a.package} libra={(a) => a.banca} onRand={(a) => deschide(a.package)}
            gol={t('mobil.android_gol_filtru')} />
        </div>
        <Note ix={ix} m={m}>
          <T k="mobil.android_cum_trackere" />
          <br />
          <T k="mobil.android_cum_permisiuni" />
        </Note>
      </section>
    </>
  )
}
