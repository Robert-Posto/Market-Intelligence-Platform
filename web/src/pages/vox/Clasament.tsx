import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { BlocClasament, Clasament as ClasamentT, RandClasament } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { EtichetaBanca } from '../../components/comune'
import type { CerereSertar } from '../../components/Sertar'
import { etNume, etSegment, unitTxt } from '../../components/valori'
import { areCheie, useLang, type DictKey } from '../../i18n'
import { num } from '../../util/format'

/**
 * Clasamentul unei întrebări din Vox (app/vox.py, `clasa`), cu celulele din 2.1 / 2.2: aceleași cifre
 * ca paginile. Primele 10 rânduri plus Libra și băncile numite; „Arată toate” pentru restul (cel mult
 * 15 bănci cu date pe un concept, mip_merge, 07.10.2026).
 */
const PRIMELE = 10

function eticheta(k: string, rezerva: string, t: (k: DictKey) => string): string {
  return areCheie(k) ? t(k) : rezerva
}

/** Titlul blocului cu valorile la care sursa nu spune termenul sau tipul de credit. */
function titluNespecificat(b: BlocClasament, t: (k: DictKey) => string): string {
  return t(b.termen && b.produs ? 'vox.clasament.bloc.ambele' : b.termen ? 'vox.clasament.bloc.termen' : 'vox.clasament.bloc.produs')
}

export default function Clasament({ c, m, onDovezi }: { c: ClasamentT; m: Meta; onDovezi: (q: CerereSertar) => void }) {
  const { t, tn } = useLang()
  if (c.neclasabil || !c.blocuri) {
    const ce = c.concept ? etNume(c.concept, t) : t('vox.text_chip', { text: c.text ?? '' })
    return <p className="vox-nota"><span className="vox-punct" />{t('vox.clasament.neclasabil', { concept: ce })}</p>
  }
  const primul = c.blocuri[0]!
  const cap = [
    c.concept ? etNume(c.concept, t) : '',
    c.sursa === 'matrice' && c.segment ? etSegment(c.segment, t) : '',
    c.termen ? eticheta(`vox.termen.${c.termen}`, c.termen, t) : '',
    c.produs ? eticheta(`vox.produs.${c.produs}`, c.produs, t) : '',
    t(`vox.clasament.metrica.${c.metrica ?? 'mediana'}` as DictKey),
  ].filter(Boolean)
  // Libra poate sta doar în blocul „nespecificat” (depozitul de 12 luni: locul 7 din 9): locul ei se spune
  // acolo, nu „n-are valori”
  const blocLibra = c.libra?.bloc === 'nespecificat' ? c.blocuri.find((b) => b.tip === 'nespecificat') : undefined
  const libra = !c.libra
    ? t('vox.clasament.libra_lipsa')
    : blocLibra
      ? t(c.libra.loc === c.libra.loc_pana ? 'vox.clasament.libra_nespecificat' : 'vox.clasament.libra_nespecificat_egal',
          { loc: c.libra.loc, pana: c.libra.loc_pana, din: c.libra.din, bloc: titluNespecificat(blocLibra, t) })
      : c.libra.loc === c.libra.loc_pana
        ? t('vox.clasament.libra', { loc: c.libra.loc, din: c.libra.din })
        : t('vox.clasament.libra_egal', { loc: c.libra.loc, pana: c.libra.loc_pana, din: c.libra.din })
  // băncile cu date din toate blocurile, ca împreună cu „Fără date” să dea toate băncile
  const cuDate = new Set(c.blocuri.flatMap((b) => b.randuri.map((r) => r.banca))).size
  const pagina = c.sursa === 'matrice'
    ? `/produse?grup=${c.grup}&segment=${c.segment ?? 'pf'}`
    : `/rate?categorie=${c.grup}${primul.termen ? `&termen=${primul.termen}` : ''}${primul.produs ? `&produs=${primul.produs}` : ''}`
  return (
    <div className="vox-fisa">
      <div className="vox-clas-antet">
        <b>{cap.join(' · ')}</b>
        <span className="vox-meta">{t('vox.clasament.sens')} · {tn('vox.clasament.n_banci', cuDate)}</span>
      </div>
      <p className="vox-nota"><span className="vox-punct gri" />{libra}</p>
      {c.blocuri.map((b, k) => <Bloc key={k} b={b} c={c} m={m} onDovezi={onDovezi} />)}
      <FaraDate c={c} m={m} />
      <Link className="vox-link vox-clas-pagina" to={pagina}>{t(c.sursa === 'matrice' ? 'vox.clasament.deschide_21' : 'vox.clasament.deschide_22')}</Link>
    </div>
  )
}

function Bloc({ b, c, m, onDovezi }: { b: BlocClasament; c: ClasamentT; m: Meta; onDovezi: (q: CerereSertar) => void }) {
  const { t, locale } = useLang()
  const [toate, setToate] = useState(false)
  const u = unitTxt(c.unitate, t)
  const titlu = b.tip === 'nespecificat' ? titluNespecificat(b, t) : null
  const vizibile = toate ? b.randuri : b.randuri.filter((r, i) => i < PRIMELE || r.evidentiata)
  // sertarul cere exact celula: la comisioane regula din 2.1 (segmentul plus rândurile nemarcate, fără
  // `strict`), la dobânzi categoria, termenul și tipul de credit ale blocului
  const cerere = (r: RandClasament): CerereSertar => c.sursa === 'matrice'
    ? { banca: r.banca, camp: c.concept!, unitate: 'lei', scenariu: '', segment: c.segment ?? 'pf' }
    : { banca: r.banca, camp: c.concept!, unitate: 'procent', scenariu: c.grup ?? '', termen: b.termen, produs: b.produs }
  if (!b.randuri.length) return <p className="vox-nota"><span className="vox-punct gri" />{titlu ? `${titlu}: ` : ''}{t('vox.clasament.gol')}</p>
  return (
    <div className="vox-clas-bloc">
      {titlu && <span className="vox-segment-cap">{titlu}</span>}
      <div className="vox-tabel-cutie">
        <table className="vox-tabel vox-clas">
          <thead>
            <tr>
              <th>{t('vox.clasament.col.loc')}</th>
              <th>{t('vox.clasament.col.banca')}</th>
              <th className="dr">{t('vox.clasament.col.valoare')}</th>
              <th className="dr">{t('vox.clasament.col.interval')}</th>
              <th className="dr">{t('vox.clasament.col.valori')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {vizibile.map((r) => (
              <tr key={r.banca} className={r.evidentiata ? 'evidentiata' : undefined}>
                <td className="loc">{r.loc === r.loc_pana ? r.loc : `${r.loc}–${r.loc_pana}`}</td>
                <td><EtichetaBanca slug={r.banca} m={m} fisa tag /></td>
                <td className="dr val">
                  <span className="nr">{num(r.valoare, locale)}{u}</span>
                  {r.serviciu && <span className="sub">{r.serviciu}{r.frecventa ? ` · ${r.frecventa}` : ''}</span>}
                </td>
                <td className="dr">{r.minim === r.maxim ? '—' : `${num(r.minim, locale)} – ${num(r.maxim, locale)}`}</td>
                <td className="dr">{r.n}</td>
                <td><button type="button" className="vox-link" onClick={() => onDovezi(cerere(r))}>{t('vox.clasament.dovezi')}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {b.randuri.length > vizibile.length && (
        <button type="button" className="vox-link vox-clas-toate" onClick={() => setToate(true)}>
          {t('vox.clasament.arata_toate', { n: b.randuri.length })}
        </button>
      )}
    </div>
  )
}

/** Băncile fără nicio valoare, grupate pe motiv (app/server.py, `_stare_banci_vox`). */
function FaraDate({ c, m }: { c: ClasamentT; m: Meta }) {
  const { t } = useLang()
  const fara = c.fara_date ?? []
  if (!fara.length) return null
  const grupe = new Map<string, string[]>()
  for (const f of fara) {
    const motiv = f.stare === 'blocata' ? 'blocata' : f.stare === 'fara_surse' ? 'fara_surse'
      : (f.robots ?? 0) > 0 ? 'robots' : (f.refuzate ?? 0) > 0 ? 'refuzate' : 'fara_valoare'
    grupe.set(motiv, [...(grupe.get(motiv) ?? []), m.nume[f.banca] ?? f.banca])
  }
  return (
    <p className="vox-nota vox-clas-fara">
      <span className="vox-punct gri" />
      <span>
        {t('vox.clasament.fara_date', { n: fara.length })}{' '}
        {[...grupe].map(([motiv, banci]) => `${banci.join(', ')} (${t(`vox.clasament.motiv.${motiv}` as DictKey)})`).join(' · ')}
      </span>
    </p>
  )
}
