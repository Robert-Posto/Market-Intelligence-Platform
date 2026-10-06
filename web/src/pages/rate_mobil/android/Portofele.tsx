import type { AplicatieAndroid } from '@mcc/shared'
import { Tabel, type Coloana } from '../../../components/Tabel'
import { T, useLang, type DictKey } from '../../../i18n'
import { Bifa, CelulaApp, Note } from './comune'
import { SEMNALE_PORTOFEL, type PropsSectiune } from './model'

/**
 * Semnalele de portofel din APK. NU răspund la „banca acceptă Google Pay / Apple
 * Pay?”: un card se adaugă și direct din Google Wallet, fără nimic în aplicația
 * băncii (Capcane, punctul 1, în pachet). De aceea avertismentul stă deasupra
 * tabelului, nu în „Despre”, iar coloanele sunt ordonate de la sigur la slab.
 */
export default function Portofele({ ix, apps, m, deschide }: PropsSectiune) {
  const { t, tn } = useLang()

  const coloane: Coloana<AplicatieAndroid>[] = [
    { cheie: 'aplicatie', cap: t('mobil.android_col_aplicatie'), s: (a) => m.nume[a.banca] ?? a.banca,
      val: (a) => <CelulaApp a={a} m={m} /> },
    ...SEMNALE_PORTOFEL.map(({ k, tip }) => ({
      cheie: k,
      cap: (
        <>
          {t(`mobil.android_port.${k}` as DictKey)}
          <span className={`cap-d an-semnal ${tip}`}>{t(`mobil.android_semnal.${tip}` as DictKey)}</span>
        </>
      ),
      titlu: t(`mobil.android_port_d.${k}` as DictKey),
      s: (a: AplicatieAndroid) => ix.portofel[a.package]?.[k] ?? null,
      td: () => ({ className: 'an-c' }),
      val: (a: AplicatieAndroid) => {
        const v = ix.portofel[a.package]?.[k]
        if (v === null || v === undefined) return <span className="gri">?</span>
        // HCE: câte servicii de plată declară aplicația (BT Pay are 4); restul sunt 0/1
        return k === 'hce_servicii' && v > 0
          ? <span title={tn('mobil.android_n_servicii_hce', v)}><Bifa da /></span>
          : <Bifa da={v > 0} />
      },
    })),
  ]

  return (
    <section className="an-sec">
      <h2>{t('mobil.android_titlu_portofele')}</h2>
      <div className="callout warn an-avert"><T k="mobil.android_portofele_avertisment" /></div>
      <div className="an-tabel an-mx">
        <Tabel randuri={apps} coloane={coloane} cheieRand={(a) => a.package} libra={(a) => a.banca} onRand={(a) => deschide(a.package)}
          gol={t('mobil.android_gol_filtru')} />
      </div>
      <Note ix={ix} m={m}>
        <T k="mobil.android_cum_portofele" />
      </Note>
    </section>
  )
}
