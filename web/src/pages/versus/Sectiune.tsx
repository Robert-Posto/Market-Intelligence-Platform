import type { ReactNode } from 'react'
import { Collapse, Tooltip } from 'antd'
import { SEGMENT_VERSUS } from '../../api/versus'
import type { CerereSertar } from '../../components/Sertar'
import { etDesc, etNume, unitTxt } from '../../components/valori'
import { useLang } from '../../i18n'
import { DataValorii } from '../../components/DataValorii'
import { deLaServer } from '../../i18n/server'
import { num } from '../../util/format'
import { numeCategorie } from '../produse/logica'
import { REFERINTA, UNITATI_LIBRA, type CelulaVs, type RandLibra, type SectiuneExtra, type SectiuneLibra, type SectiunePret } from './model'

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

/** `sub`: textul mic de lângă titlu în locul sensului (la produsele Libra sensul e pe rând). */
function CapSectiune({ titlu, sens, sub, coloane, nume }: Comun & { titlu: string; sens: string; sub?: string }) {
  const { t } = useLang()
  return (
    <div className="vs-sec-cap">
      <div className="t">{titlu}<span>{sub ?? t(sens === 'mare_bun' ? 'versus.sens_mare_bun' : 'versus.sens_mic_bun')}</span></div>
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
                  onClick={() => deschide({ banca: b, camp: r.camp, unitate: g.unitate, scenariu: g.api === 'rate' ? g.cheie : '', segment: g.api === 'matrice' ? SEGMENT_VERSUS : undefined })}>
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

/**
 * Un produs Libra din fluxul comparației: valoarea băncii pe câmpul produsului echivalent
 * (mediana, dacă documentul are mai multe variante). Citatul stă în tooltip, iar clic pe
 * valoare deschide documentul băncii (nu sertarul: valorile nu vin din `observations`).
 */
export function SectiuneLibraVs({ s, coloane, nume }: Comun & { s: SectiuneLibra }) {
  const { t, locale } = useLang()
  const unitate = (u: string) => {
    const k = UNITATI_LIBRA[u]
    return k === undefined ? unitTxt(u, t) : k ? t(k) : ''
  }
  const sub = [t('versus.libra_produs'), s.segment, s.categorie && numeCategorie(s.categorie, t)].filter(Boolean).join(' · ')
  // același câmp în două unități („Administrare lunară” în lei și în %): unitatea intră în etichetă
  const repetate = new Set(s.randuri.map((r) => r.camp).filter((c, i, a) => a.indexOf(c) !== i))
  const eticheta = (r: RandLibra) => (r.nume !== r.camp ? r.nume : etNume(r.camp, t)) + (repetate.has(r.camp) ? ` (${unitate(r.unitate).trim() || r.unitate})` : '')
  return (
    <Pliabila cap={<CapSectiune titlu={s.titlu} sens="" sub={sub} coloane={coloane} nume={nume} />}>
      {s.randuri.map((r, k) => (
        <div key={`${r.camp}|${r.unitate}`} className={k % 2 ? 'vs-rand alt' : 'vs-rand'}>
          <EtichetaRand et={eticheta(r)} desc={t(r.sens === 'mare_bun' ? 'versus.sens_mare_bun' : 'versus.sens_mic_bun')}
            cate={r.prezente} total={coloane.length} />
          {coloane.map((b) => {
            const c = r.celule[b]
            if (!c) return <Gol key={b} title={t('versus.celula_goala_title')} />
            const bun = r.prezente > 1 && c.valoare === r.celMaiBun
            const pierde = b === REFERINTA && r.stare === 'pierde'
            const u = unitate(r.unitate)
            const variante = c.variante ?? []
            // tooltip-ul: citatul, apoi de ce cifra asta, celelalte cifre la conflict și variantele
            const titlu = (
              <div className="vs-libra-tip">
                {c.citat && <div>„{c.citat}”</div>}
                {c.motiv && <div className="gri">{c.motiv}</div>}
                {c.stare === 'conflict' && !!c.alternative?.length && (
                  <div>{t('versus.libra_alternative')}: {c.alternative.map((a) => `${num(a.valoare_num, locale)}${unitate(a.unitate ?? '')}`).join(', ')}</div>
                )}
                {variante.length > 0 && (
                  <div>
                    <b>{t('versus.libra_variante_titlu')}</b>
                    {variante.map((v, i) => <div key={i}>{v.eticheta}: {num(v.valoare_num, locale)}{unitate(v.unitate ?? '')}</div>)}
                  </div>
                )}
                {c.link && <div className="gri">{t('versus.libra_clic_sursa')}</div>}
              </div>
            )
            return (
              <div key={b} className={['vs-cel', bun && 'best', pierde && 'pierde'].filter(Boolean).join(' ')}>
                <Tooltip title={titlu}>
                  <a className="celula vs-libra" href={c.link ?? undefined} target="_blank" rel="noopener noreferrer">
                    <span className="v-num">{num(c.valoare, locale)}{u}</span>
                    {c.stare === 'aproximativ' && <span className="v-ctx">{t('versus.libra_aproximativ')}</span>}
                    {c.stare === 'conflict' && <span className="v-ctx vs-de-verificat">{t('versus.libra_conflict')}</span>}
                    {variante.length > 0 && <span className="v-ctx">{t('versus.libra_variante', { n: variante.length })}</span>}
                    <DataValorii d={c} className="v-ctx" />
                  </a>
                </Tooltip>
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
