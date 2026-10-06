import { Tooltip } from 'antd'
import type { AplicatieAndroid } from '@mcc/shared'
import { Tabel, type Coloana } from '../../../components/Tabel'
import { areCheie, T, useLang } from '../../../i18n'
import { CelulaApp, Note, Verdict } from './comune'
import { bucati, cheie, eticheta, rangVerdict, VERDICTE, type PropsSectiune } from './model'

/**
 * Matricea aplicație × funcționalitate, pe versiunea analizată. Fără total pe
 * rând: „neconcludent” (aplicație web, textul pe server) nu e „absent”, deci o
 * sumă de bife ar pune alături lucruri care nu se compară. Sortarea pe coloană
 * rămâne: arată cine are o anumită funcție.
 */
export default function Functionalitati({ ix, apps, m, deschide }: PropsSectiune) {
  const { t, lang } = useLang()

  // titlul vine din bază, în română; în engleză, perechea din dicționar, dacă există
  const titlu = (functie: string, ro: string) => {
    const k = `mobil.android_f.${functie}`
    return lang === 'ro' || !areCheie(k) ? ro : t(k)
  }
  const scurt = (functie: string, ro: string) => {
    const k = `mobil.android_fs.${functie}`
    return areCheie(k) ? t(k) : titlu(functie, ro)
  }

  const coloane: Coloana<AplicatieAndroid>[] = [
    { cheie: 'aplicatie', cap: t('mobil.android_col_aplicatie'), s: (a) => m.nume[a.banca] ?? a.banca,
      val: (a) => <CelulaApp a={a} m={m} versiune={a.versiune_analizata} /> },
    ...ix.coloaneFunctii.map(({ functie, titlu: ro }) => ({
      cheie: functie,
      cap: scurt(functie, ro),
      titlu: titlu(functie, ro),
      s: (a: AplicatieAndroid) => rangVerdict(ix.functii[a.package]?.[functie]?.verdict),
      td: () => ({ className: 'an-c' }),
      val: (a: AplicatieAndroid) => {
        const f = ix.functii[a.package]?.[functie]
        if (!f) return <span className="gri">—</span>
        const surse = bucati(f.surse).map((s) => eticheta(t, 'sursa', s)).join(', ')
        return (
          <Tooltip title={
            <>
              <b>{titlu(functie, ro)}</b>: {eticheta(t, 'verdict', f.verdict)}
              {surse && <><br />{t('mobil.android_surse', { surse })}</>}
              {/* dovada e textul găsit în aplicație: rămâne netradus */}
              {f.dovada_text && <><br />{t('mobil.android_dovada', { dovada: f.dovada_text })}</>}
            </>
          }>
            <span><Verdict v={f.verdict} /></span>
          </Tooltip>
        )
      },
    })),
  ]

  return (
    <section className="an-sec">
      <h2>{t('mobil.android_titlu_functionalitati')}</h2>
      <p className="note" style={{ margin: '0 0 8px' }}><T k="mobil.android_nota_functionalitati" /></p>
      <div className="an-leg">
        {VERDICTE.map((v) => {
          const k = cheie('verdict_d', v)
          return (
            <span key={v}>
              <Verdict v={v} /> <b>{eticheta(t, 'verdict', v)}</b> {k ? t(k) : ''}
            </span>
          )
        })}
      </div>
      <div className="an-tabel an-mx">
        <Tabel randuri={apps} coloane={coloane} cheieRand={(a) => a.package} libra={(a) => a.banca} onRand={(a) => deschide(a.package)}
          gol={t('mobil.android_gol_filtru')} />
      </div>
      <Note ix={ix} m={m}>
        <T k="mobil.android_cum_functionalitati" />
        <br />
        <T k="mobil.android_cum_functionalitati_wallet" />
        <br />
        <T k="mobil.android_cum_functionalitati_total" />
      </Note>
    </section>
  )
}
