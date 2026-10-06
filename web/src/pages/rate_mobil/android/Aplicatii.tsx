import type { AplicatieAndroid } from '@mcc/shared'
import { Pill } from '../../../components/comune'
import { Tabel, type Coloana } from '../../../components/Tabel'
import { T, useLang } from '../../../i18n'
import { formatZi, num } from '../../../util/format'
import { Captura, CelulaApp, Note } from './comune'
import { cheie, eticheta, type PropsSectiune } from './model'

/**
 * Aplicațiile, câte un rând pe `package`. Cifrele (permisiuni, trackere, biblioteci,
 * librării native) sunt ale versiunii celei mai noi; dedesubtul versiunii apare
 * cea analizată când diferă, fiindcă funcționalitățile și profilul stau pe ea.
 */
export default function Aplicatii({ ix, apps, m, deschide }: PropsSectiune) {
  const { t, tn, locale } = useLang()
  const nr = (v: number | null) => num(v, locale, 0)
  const banci = new Set(apps.map((a) => a.banca)).size

  const coloane: Coloana<AplicatieAndroid>[] = [
    { cheie: 'banca', cap: t('rate.banca'), s: (a) => m.nume[a.banca] ?? a.banca,
      val: (a) => <CelulaApp a={a} m={m} /> },
    { cheie: 'rol', cap: t('mobil.android_col_rol'), titlu: t('mobil.android_col_rol_title'), s: (a) => eticheta(t, 'rol', a.rol),
      val: (a) => <Pill>{eticheta(t, 'rol', a.rol)}</Pill> },
    { cheie: 'versiune', cap: t('mobil.versiune'), titlu: t('mobil.android_col_versiune_title'), td: () => ({ className: 'mono an-nowrap' }),
      val: (a) => (
        <>
          {a.versiune_cea_mai_noua ?? '—'}
          {a.versiune_analizata && a.versiune_analizata !== a.versiune_cea_mai_noua && (
            <span className="sub">{t('mobil.android_analizata', { v: a.versiune_analizata })}</span>
          )}
          {a.data_extragere && <span className="sub">{t('mobil.android_extrasa', { data: formatZi(a.data_extragere, locale) })}</span>}
        </>
      ) },
    { cheie: 'framework', cap: t('mobil.android_framework'), titlu: t('mobil.android_col_framework_title'), s: (a) => eticheta(t, 'fw', a.framework),
      val: (a) => (
        <>
          {eticheta(t, 'fw', a.framework)}
          <span className="sub">{t('mobil.android_platforma', { p: eticheta(t, 'plat', a.platforma_tehnica) })}</span>
        </>
      ) },
    // o coloană, nu două: tabelul trecea de chenar la 1440 px cu ~220 px
    { cheie: 'sdk', cap: t('mobil.android_d_sdk'), titlu: t('mobil.android_col_sdk_title'), num: true, s: (a) => a.min_sdk,
      td: () => ({ className: 'an-nowrap' }), val: (a) => `${nr(a.min_sdk)} → ${nr(a.target_sdk)}` },
    { cheie: 'permisiuni', cap: t('mobil.android_col_permisiuni'), titlu: t('mobil.android_col_permisiuni_title'), num: true, s: (a) => a.nr_permisiuni,
      val: (a) => nr(a.nr_permisiuni) },
    { cheie: 'trackere', cap: t('mobil.android_col_trackere'), titlu: t('mobil.android_col_trackere_title'), num: true, s: (a) => a.nr_trackere,
      val: (a) => nr(a.nr_trackere) },
    { cheie: 'biblioteci', cap: t('mobil.android_col_biblioteci'), titlu: t('mobil.android_col_biblioteci_title'), num: true, s: (a) => a.nr_biblioteci,
      val: (a) => nr(a.nr_biblioteci) },
    { cheie: 'native', cap: t('mobil.android_col_native'), titlu: t('mobil.android_col_native_title'), num: true, s: (a) => a.nr_librarii_native,
      val: (a) => nr(a.nr_librarii_native) },
    { cheie: 'captura', cap: t('mobil.android_col_captura'), titlu: t('mobil.android_col_captura_title'), s: (a) => eticheta(t, 'captura', a.captura),
      val: (a) => <Captura v={a.captura} simplu /> },
  ]

  return (
    <section className="an-sec">
      <h2>{t('mobil.android_titlu_aplicatii')}</h2>
      <p className="note" style={{ margin: '0 0 10px' }}>
        <T k="mobil.android_nota_aplicatii" params={{
          aplicatii: tn('mobil.android_n_aplicatii', apps.length),
          banci: tn('mobil.android_n_banci', banci),
          total: num(Object.keys(m.nume).length, locale, 0),
        }} />
      </p>
      <div className="an-tabel">
        <Tabel randuri={apps} coloane={coloane} cheieRand={(a) => a.package} libra={(a) => a.banca} onRand={(a) => deschide(a.package)}
          gol={t('mobil.android_gol_filtru')} />
      </div>
      <Note ix={ix} m={m}>
        <T k="mobil.android_cum_aplicatii" />
        <br />
        {['ok', 'negru_text', 'negru_nimic', 'blocat'].map((v) => {
          const k = cheie('captura_d', v)
          return (
            <span key={v} className="an-leg-r">
              <Pill>{eticheta(t, 'captura', v)}</Pill> {k ? t(k) : ''}
            </span>
          )
        })}
      </Note>
    </section>
  )
}
