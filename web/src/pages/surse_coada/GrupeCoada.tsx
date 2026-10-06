import { useState } from 'react'
import { Collapse, Tooltip } from 'antd'
import type { CoadaVerificare, ValoareCoada, ValoareDovada } from '@mcc/shared'
import { Pill } from '../../components/comune'
import { CitatEvidentiat, citatUtil, LinkSursa } from '../../components/Dovezi'
import { etNume, unitTxt } from '../../components/valori'
import { useLang } from '../../i18n'
import { deLaServer } from '../../i18n/server'
import { num } from '../../util/format'
import type { Motive } from './motive'

/**
 * Rândul din coadă în forma dovezii din sertar, ca legătura spre sursă și citatul
 * marcat să fie aceleași peste tot (Dovezi.tsx). Coada trimite `valoare_num`, nu `valoare`.
 */
function caDovada(r: ValoareCoada): ValoareDovada {
  return {
    valoare: r.valoare_num,
    valoare_text: null,
    unitate: r.unitate,
    cod_scenariu: null,
    citat: r.citat,
    confidence: r.confidence,
    ambiguu: r.ambiguu ?? true,
    motiv_ambiguu: r.motiv_ambiguu,
    metoda_extractie: r.metoda_extractie,
    serviciu: r.serviciu,
    sectiune: null,
    conditie: null,
    frecventa: null,
    detaliu: null,
    pagina: r.pagina,
    nr_aparitii: null,
    sursa: r.sursa,
    tip_sursa: r.tip_sursa,
    link: r.link,
    link_pagina: r.link_pagina,
    pagina_documente_motiv: null,
    fisier: r.fisier,
    ancora: r.ancora,
  }
}

/**
 * Rândurile grupate pe (bancă, serviciu), fiecare valoare pe o linie. Revamp
 * 25.09 în aplicația veche: înainte se vedeau doar primele 150 de rânduri din
 * 5.263, câte un card mare. Până la 12 grupe pe pagină stau deschise.
 */
export function GrupeCoada({ d, motivAles, mot }: { d: CoadaVerificare; motivAles: string; mot: Motive }) {
  const { t, lang } = useLang()
  const g = new Map<string, ValoareCoada[]>()
  for (const r of d.randuri) {
    const k = `${r.banca}|${r.camp}|${r.serviciu || ''}`
    if (!g.has(k)) g.set(k, [])
    g.get(k)!.push(r)
  }
  const lista = [...g]
  // pagina nouă (alt filtru, altă pagină) reface grupele, cu deschiderea implicită a ei
  const cheie = `${d.total}|${d.offset}|${d.randuri[0]?.id ?? ''}|${d.randuri.length}`
  return (
    <Collapse
      key={cheie}
      className="grupe"
      defaultActiveKey={lista.length <= 12 ? lista.map(([k]) => k) : []}
      items={lista.map(([k, rs]) => {
        const r0 = rs[0]!
        // Valorile-frate: același serviciu la aceeași bancă, TOATE, nu doar cele din coadă. Așa se vede
        // dacă cifra face parte dintr-o serie de tranșe (1, 3, 5, 15 lei) sau e singura.
        const frati = d.fratii[`${r0.banca}|${r0.camp}|${r0.serviciu}`]
        const inCoada = new Set(rs.map((x) => x.valoare_num))
        return {
          key: k,
          label: (
            <div className="g-cap">
              <span className="gn">
                {r0.serviciu || etNume(r0.camp, t)}
                <span className="sub">{r0.banca_nume || r0.banca} · {etNume(r0.camp, t)} · {deLaServer(r0.produs, lang)}</span>
              </span>
              <span className="gi" />
              <span className="gc">{t('coada.grup_de_verificat', { n: rs.length })}</span>
            </div>
          ),
          children: (
            <>
              {frati && frati.n > 1 && <Serie valori={frati.valori} n={frati.n} inCoada={inCoada} unitate={r0.unitate} />}
              {rs.map((r) => <RandCoada key={r.id} r={r} motivAles={motivAles} mot={mot} />)}
            </>
          ),
        }
      })}
    />
  )
}

function Serie({ valori, n, inCoada, unitate }: { valori: number[]; n: number; inCoada: Set<number | null>; unitate: string | null }) {
  const { t, locale } = useLang()
  return (
    <div className="sc-serie">
      <span className="et">{t('coada.serie_titlu')}</span>
      {valori.map((v, i) => {
        const aici = inCoada.has(v)
        return (
          <Tooltip key={i} title={t(aici ? 'coada.valoare_in_coada_title' : 'coada.valoare_trece_title')}>
            <span className={`v${aici ? ' aici' : ''}`}>{num(v, locale)}{unitTxt(unitate, t)}</span>
          </Tooltip>
        )
      })}
      {n > valori.length && <span className="et">+{num(n - valori.length, locale, 0)}</span>}
    </div>
  )
}

/** O valoare pe o linie; clic = metoda de extracție și motivul întreg (nu și pe legătura spre document). */
function RandCoada({ r, motivAles, mot }: { r: ValoareCoada; motivAles: string; mot: Motive }) {
  const { t, locale } = useLang()
  const [des, setDes] = useState(false)
  const dov = caDovada(r)
  const explicatie = mot.explicatie(r.motiv)
  return (
    <div className={`r${des ? ' des' : ''}`} onClick={(e) => { if (!(e.target as HTMLElement).closest('a')) setDes(!des) }}>
      <div className="rv">{num(r.valoare_num, locale)}{unitTxt(r.unitate, t)}</div>
      <div className="rc">
        {citatUtil(dov)
          ? <CitatEvidentiat r={dov} />
          : <span className="gri" style={{ fontStyle: 'italic' }}>{t('coada.citat_doar_cifra')}</span>}
        {/* cu un motiv ales, el e scris o dată deasupra; pe fiecare rând ar fi doar zgomot */}
        {!motivAles && <Pill tip="amb" title={explicatie || undefined}>{mot.scurt(r.motiv)}</Pill>}
        {r.confidence !== null && r.confidence < 0.7 && <Pill>{t('coada.pill_incredere', { valoare: num(r.confidence, locale) })}</Pill>}
      </div>
      <div className="rs"><LinkSursa r={dov} /></div>
      <div className="rx">
        <div className="meta">
          <Pill>{r.metoda_extractie || '?'}</Pill>
          <Pill>{mot.nume(r.motiv)}</Pill>
        </div>
      </div>
    </div>
  )
}
