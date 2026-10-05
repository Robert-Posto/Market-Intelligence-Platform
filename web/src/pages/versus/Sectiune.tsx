import type { ReactNode } from 'react'
import { Collapse, Tooltip } from 'antd'
import type { CerereSertar } from '../../components/Sertar'
import { etDesc, etNume, unitTxt } from '../../components/valori'
import { useLang } from '../../i18n'
import { deLaServer } from '../../i18n/server'
import { num } from '../../util/format'
import { REFERINTA, type CelulaVs, type SectiuneExtra, type SectiunePret } from './model'

interface Comun {
  coloane: string[]
  /** numele scurte, în ordinea coloanelor */
  nume: Record<string, string>
}

/**
 * Secțiune pliabilă cu capul fix la derulare (revamp 25.09): cu 4 bănci și ~25
 * de rânduri pe pagină, fără cap fix nu se mai știa a cui e coloana a treia.
 */
function Pliabila({ cap, children }: { cap: ReactNode; children: ReactNode }) {
  return <Collapse className="vs-sec" ghost defaultActiveKey={['s']} items={[{ key: 's', showArrow: false, label: cap, children }]} />
}

function CapSectiune({ titlu, sens, coloane, nume }: Comun & { titlu: string; sens: string }) {
  const { t } = useLang()
  return (
    <div className="vs-sec-cap">
      <div className="t">{titlu}<span>{t(sens === 'mare_bun' ? 'versus.sens_mare_bun' : 'versus.sens_mic_bun')}</span></div>
      {coloane.map((b) => <div key={b} className={b === REFERINTA ? 'c ref' : 'c'}>{nume[b]}</div>)}
    </div>
  )
}

function EtichetaRand({ et, desc, cate, total }: { et: string; desc: string; cate: number; total: number }) {
  const { t } = useLang()
  return (
    <div className="vs-lab">
      <b>{et}</b>
      {desc && <span>{desc}</span>}
      {cate < total && <em>{t('versus.date_doar_la', { cate, total })}</em>}
    </div>
  )
}

/** Libra e cea mai slabă pe rând: o etichetă cu contur, pereche cu „cel mai bun” (plină). */
function Marcaje({ bun, pierde }: { bun: boolean; pierde: boolean }) {
  const { t } = useLang()
  return (
    <>
      {bun && <span className="eticheta-best">{t('versus.cel_mai_bun')}</span>}
      {pierde && <span className="vs-slab">{t('comun.css.cea_mai_slaba')}</span>}
    </>
  )
}

function Gol({ title }: { title: string }) {
  return (
    <Tooltip title={title}>
      <div className="vs-cel gol">—</div>
    </Tooltip>
  )
}

/** Textul de sub cifră: frecvența, serviciul și condiția, tăiate scurt (celula e îngustă). */
function contextScurt(c: CelulaVs, maxLen = 26): string {
  const taie = (s: string) => (s.length > maxLen ? s.slice(0, maxLen - 1) + '…' : s)
  return [c.frecventa, c.serviciu && taie(c.serviciu), c.conditie && taie(c.conditie)].filter(Boolean).join(' · ')
}

/**
 * Cifra afișată e mediana valorilor din bancă, nu minimul: la minim, 80% din
 * celule arătau „0 lei”, fiindcă fiecare bancă are cel puțin o variantă
 * gratuită. Mediana e cât costă de obicei și se poate compara.
 */
function ValoarePret({ c, sens, unitate }: { c: CelulaVs; sens: string; unitate: string }) {
  const { t, tn, locale } = useLang()
  const v = c.valoare !== null ? c.valoare : sens === 'mare_bun' ? c.maxim : c.minim
  const multe = c.n > 1 && c.minim !== c.maxim
  const ctx = contextScurt(c)
  const u = unitTxt(unitate, t)
  const extrem = sens === 'mare_bun'
    ? t('comun.valoare.cea_mai_mare', { valoare: num(c.maxim, locale), unitate: u })
    : t('comun.valoare.cea_mai_mica', { valoare: num(c.minim, locale), unitate: u })
  return (
    <>
      {multe && <span className="v-pref">{t('comun.valoare.de_obicei')}</span>}
      <span className="v-num">{num(v, locale)}{u}</span>
      {ctx && <span className="v-ctx">{ctx}</span>}
      {c.gratuite > 0 && <span className="v-ctx v-gratis">{tn('comun.valoare.variante_gratuite', c.gratuite, { n: num(c.gratuite, locale, 0) })}</span>}
      {c.n > 1 && (
        <Tooltip title={t('comun.valoare.tooltip_variante', { n: num(c.n, locale, 0), extrem })}>
          <span className="v-n">+{num(c.n - 1, locale, 0)}</span>
        </Tooltip>
      )}
    </>
  )
}

/** Comisioane și dobânzi: clic pe o valoare = sertarul cu toate valorile din spate, cu citat și link. */
export function SectiunePretVs({ s, coloane, nume, deschide }: Comun & { s: SectiunePret; deschide: (c: CerereSertar) => void }) {
  const { t, lang } = useLang()
  const g = s.grup
  return (
    <Pliabila cap={<CapSectiune titlu={deLaServer(s.titlu, lang)} sens={s.sens} coloane={coloane} nume={nume} />}>
      {s.randuri.map((r, k) => (
        <div key={r.camp} className={k % 2 ? 'vs-rand alt' : 'vs-rand'}>
          <EtichetaRand et={etNume(r.camp, t)} desc={etDesc(r.camp, t)} cate={r.prezente} total={coloane.length} />
          {coloane.map((b) => {
            const c = r.celule[b]
            if (!c) return <Gol key={b} title={t('versus.celula_goala_title')} />
            const bun = r.prezente > 1 && c.valoare === r.celMaiBun
            const pierde = b === REFERINTA && r.stare === 'pierde'
            return (
              <div key={b} className={['vs-cel', bun && 'best', pierde && 'pierde'].filter(Boolean).join(' ')}>
                <span className="celula"
                  onClick={() => deschide({ banca: b, camp: r.camp, unitate: g.unitate, scenariu: g.api === 'rate' ? g.cheie : '' })}>
                  <ValoarePret c={c} sens={s.sens} unitate={g.unitate} />
                </span>
                <Marcaje bun={bun} pierde={pierde} />
              </div>
            )
          })}
        </div>
      ))}
    </Pliabila>
  )
}

/** Aplicația, rețeaua și recenziile: aceleași marcaje, fără sertar (nu au dovezi pe valoare). */
export function SectiuneExtraVs({ s, coloane, nume }: Comun & { s: SectiuneExtra }) {
  const { t } = useLang()
  return (
    <Pliabila cap={<CapSectiune titlu={t(s.titlu)} sens={s.sens} coloane={coloane} nume={nume} />}>
      {s.randuri.map((r, k) => (
        <div key={r.eticheta} className={k % 2 ? 'vs-rand alt' : 'vs-rand'}>
          <EtichetaRand et={t(r.eticheta)} desc={t(r.desc)} cate={coloane.filter((b) => r.valori[b]).length} total={coloane.length} />
          {coloane.map((b) => {
            const x = r.valori[b]
            if (!x) return <Gol key={b} title={t('versus.celula_goala_extra_title')} />
            const bun = r.best !== null && x.n === r.best
            const pierde = b === REFERINTA && r.stare === 'pierde'
            return (
              <div key={b} className={['vs-cel', bun && 'best', pierde && 'pierde'].filter(Boolean).join(' ')}>
                <span className="v-num">{x.t}</span>
                {x.sub && <span className="v-ctx">{x.sub}</span>}
                <Marcaje bun={bun} pierde={pierde} />
              </div>
            )
          })}
        </div>
      ))}
    </Pliabila>
  )
}
