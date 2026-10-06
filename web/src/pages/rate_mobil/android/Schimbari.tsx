import type { SchimbareAndroid } from '@mcc/shared'
import { EtichetaBanca } from '../../../components/comune'
import { Tabel } from '../../../components/Tabel'
import { T, useLang } from '../../../i18n'
import { ListaScurta, Note } from './comune'
import { bucati, eticheta, intervalVersiuni, type PropsSectiune } from './model'

/** „androidx.activity 1.11.0->1.12.0”: săgeata scrisă ca săgeată. */
const element = (x: string) => x.replace(/\s*->\s*/g, ' → ')

/**
 * Diferențele dintre două versiuni consecutive ale aceleiași aplicații. Doar
 * aplicațiile cu cel puțin două versiuni extrase au ce compara (Libra, Raiffeisen
 * și Revolut pe 05.10.2026); una fără diferențe apare totuși, ca să nu pară uitată.
 */
export default function Schimbari({ ix, apps, m, deschide }: PropsSectiune) {
  const { t } = useLang()
  const cuVersiuni = apps.filter((a) => (ix.versiuni[a.package]?.length ?? 0) > 1)
  return (
    <section className="an-sec">
      <h2>{t('mobil.android_titlu_schimbari')}</h2>
      <p className="note" style={{ margin: '0 0 12px' }}><T k="mobil.android_nota_schimbari" /></p>
      {cuVersiuni.length === 0 && <p className="note">{t('mobil.android_fara_versiuni_multiple')}</p>}
      {cuVersiuni.map((a) => (
        <div key={a.package} className="an-sch">
          <div className="an-sch-cap clic" onClick={() => deschide(a.package)}>
            <EtichetaBanca slug={a.banca} m={m} fisa tag />
            <b>{a.aplicatie}</b>
            <span className="mono">{intervalVersiuni(ix, a)}</span>
          </div>
          <ListaSchimbari randuri={ix.schimbari[a.package] ?? []} />
        </div>
      ))}
      <Note ix={ix} m={m}>
        <T k="mobil.android_cum_schimbari" />
      </Note>
    </section>
  )
}

/** Tabelul diferențelor; îl folosește și detaliul aplicației. */
export function ListaSchimbari({ randuri }: { randuri: SchimbareAndroid[] }) {
  const { t } = useLang()
  return (
    <Tabel
      randuri={randuri}
      cheieRand={(s) => `${s.de_la}|${s.la}|${s.camp}`}
      gol={t('mobil.android_fara_diferente')}
      coloane={[
        { cheie: 'camp', cap: t('mobil.android_col_camp'), td: () => ({ className: 'an-nowrap' }),
          val: (s) => (
            <>
              {eticheta(t, 'camp', s.camp)}
              <span className="sub mono">{s.de_la} → {s.la}</span>
            </>
          ) },
        { cheie: 'adaugat', cap: t('mobil.android_col_adaugat'), val: (s) => <ListaScurta items={bucati(s.adaugat)} render={element} /> },
        { cheie: 'eliminat', cap: t('mobil.android_col_eliminat'), val: (s) => <ListaScurta items={bucati(s.eliminat)} render={element} /> },
      ]}
    />
  )
}
