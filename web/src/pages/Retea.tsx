import { Button } from 'antd'
import { Link, useHref } from 'react-router-dom'
import { useMeta } from '../api/meta'
import { useLocatii } from '../api/retea'
import { Despre, EtichetaBanca, Eroare, SeIncarca } from '../components/comune'
import { Tabel } from '../components/Tabel'
import { T, useLang } from '../i18n'
import { num } from '../util/format'
import '../styles/retea.css'

/**
 * 2.5 Rețea & operațional: patru cifre-cheie și rețeaua fiecărei bănci, cu
 * trimitere spre hartă (toate băncile sau doar una).
 */
export default function Retea() {
  const { t, locale } = useLang()
  const meta = useMeta()
  const q = useLocatii()
  const hrefHarta = useHref('/harta')
  if (q.error) return <Eroare e={q.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (!q.data || !meta.data) return <SeIncarca />
  const m = meta.data

  /* Sortat după REȚEAUA PROPRIE, nu după total: totalul include ATM-urile
     partenere, iar Patria ieșea prima cu 617 locații, din care 572 ATM-uri
     Euronet. Rețeaua proprie răspunde la „cine are cea mai mare prezență”. */
  const b = q.data.banci.map((x) => ({ ...x, proprie: x.sucursale + x.atm }))
  const suma = (k: 'sucursale' | 'atm' | 'atm_parteneri') => b.reduce((s, x) => s + x[k], 0)

  return (
    <>
      <div className="kpi">
        <div>
          <div className="e">{t('retea.kpi_banci_cu_locatii')}</div>
          <div className="n">{num(b.length, locale, 0)}<span className="gri" style={{ fontSize: 15 }}> / 30</span></div>
          <div className="l">{t('retea.kpi_banci_cu_locatii_nota')}</div>
        </div>
        <div>
          <div className="e">{t('retea.sucursale')}</div>
          <div className="n">{num(suma('sucursale'), locale, 0)}</div>
          <div className="l">{t('retea.kpi_sucursale_nota')}</div>
        </div>
        <div>
          <div className="e">{t('retea.atm_proprii')}</div>
          <div className="n">{num(suma('atm'), locale, 0)}</div>
          <div className="l">{t('retea.kpi_atm_proprii_nota')}</div>
        </div>
        <div>
          <div className="e">{t('retea.atm_partenere')}</div>
          <div className="n">{num(suma('atm_parteneri'), locale, 0)}</div>
          <div className="l">{t('retea.kpi_atm_partenere_nota')}</div>
        </div>
      </div>
      <section>
        <div className="rt-cap">
          <h2>{t('retea.titlu_reteaua_bancilor')}</h2>
          <Button type="primary" href={hrefHarta}>{t('retea.deschide_harta')}</Button>
        </div>
        <Tabel
          randuri={b}
          cheieRand={(r) => r.slug}
          libra={(r) => r.slug}
          implicit={['proprie', 'descend']}
          coloane={[
            { cheie: 'banca', cap: t('retea.banca'), s: (r) => r.nume, val: (r) => <EtichetaBanca slug={r.slug} m={m} fisa tag /> },
            { cheie: 'proprie', cap: t('retea.retea_proprie'), titlu: t('retea.retea_proprie_titlu'), num: true,
              s: (r) => r.proprie, val: (r) => <b>{num(r.proprie, locale, 0)}</b> },
            { cheie: 'sucursale', cap: t('retea.sucursale'), num: true, s: (r) => r.sucursale, val: (r) => num(r.sucursale, locale, 0) },
            { cheie: 'atm', cap: t('retea.atm_proprii'), num: true, s: (r) => r.atm, val: (r) => num(r.atm, locale, 0) },
            { cheie: 'atm_parteneri', cap: t('retea.atm_partenere'), num: true, s: (r) => r.atm_parteneri,
              val: (r) => <span className="gri">{r.atm_parteneri ? num(r.atm_parteneri, locale, 0) : '—'}</span> },
            { cheie: 'harta', cap: t('retea.pe_harta'),
              val: (r) => <Link className="sursa" to={`/harta?banca=${encodeURIComponent(r.slug)}`}>{t('retea.vezi_pe_harta')}</Link> },
          ]}
        />
        <Despre>
          <T k="retea.despre" />
        </Despre>
      </section>
    </>
  )
}
