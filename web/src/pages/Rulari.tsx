import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Select } from 'antd'
import { Rulari as RulariSchema, type ComandaRulare, type RulareCurenta, type Rulari as RulariT } from '@mcc/shared'
import { api, apiPost, SERVER_OPRIT } from '../api/client'
import type { Meta } from '../api/meta'
import { Pill, Pliat } from '../components/comune'
import { T, useLang } from '../i18n'
import { deLaServer } from '../i18n/server'

/**
 * Rulări manuale (Overview): scripturile de colectare care ar rula automat,
 * pornite la cerere. Doar pe laptopul cu MIP_PERMITE_RULARI=1; altfel butoanele
 * rămân dezactivate. Lista e fixă, pe server (app/rulari.py): din pagină pleacă
 * doar id-ul comenzii și, unde se poate, banca. Un singur proces odată.
 * Cât rulează ceva, starea se cere la 2 s, ca în aplicația veche.
 */
export default function Rulari({ m }: { m: Meta }) {
  const { t, lang } = useLang()
  const rq = useQuery({
    queryKey: ['rulari'],
    queryFn: () => api('/api/rulari', RulariSchema),
    refetchInterval: (q) => (q.state.data?.curenta ? 2000 : false),
  })
  const d = rq.data
  return (
    <Pliat
      deschis={!!d?.curenta}
      titlu={<>{t('rulari.titlu')} {d && (d.activ ? <Pill tip="ok">{t('rulari.pornite_laptop')}</Pill> : <Pill>{t('rulari.oprite_server')}</Pill>)}</>}
    >
      <section>
        {rq.error ? (
          <p className="note" style={{ color: 'var(--warn)' }}>{(rq.error as Error).message === SERVER_OPRIT ? t('comun.server_oprit') : t('rulari.eroare_stare', { eroare: deLaServer((rq.error as Error).message, lang) })}</p>
        ) : d ? (
          <Corp d={d} m={m} />
        ) : (
          <p className="note">{t('comun.se_incarca')}</p>
        )}
      </section>
    </Pliat>
  )
}

function useDurata() {
  const { t } = useLang()
  return (s: number | null | undefined) => {
    if (s === null || s === undefined) return '—'
    s = Math.round(s)
    if (s < 60) return t('rulari.durata_s', { s })
    if (s < 3600) return t('rulari.durata_min', { min: Math.round(s / 60) })
    const h = Math.floor(s / 3600)
    const mn = Math.round((s % 3600) / 60)
    return mn ? t('rulari.durata_h_min', { h, min: mn }) : t('rulari.durata_h', { h })
  }
}

/** estimarea pentru banca aleasă: mediana ei din istoric, altfel cea pe orice bancă */
function est(c: ComandaRulare, banca: string): number | undefined {
  if (!banca) return c.estimare_s ?? c.estimare_banca_s
  return c.estimari_banca?.[banca] ?? c.estimare_banca_s
}

function Corp({ d, m }: { d: RulariT; m: Meta }) {
  const { t, lang, locale } = useLang()
  const { modal } = App.useApp()
  const durata = useDurata()
  const qc = useQueryClient()
  const [alese, setAlese] = useState<Record<string, string>>({})
  const blocat = !d.activ || !!d.curenta
  const numeBanca = (b: string) => m.nume[b] ?? b
  const banci = d.banci.slice().sort((a, b) => numeBanca(a).localeCompare(numeBanca(b), locale))
  const ora = (x: string | null | undefined) =>
    x ? new Date(x).toLocaleString(locale, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

  const estHtml = (c: ComandaRulare, banca: string) => {
    const peBanca = !!banca || c.estimare_s === undefined
    const masurat = peBanca ? c.estimari_banca?.[banca] !== undefined || c.estimare_banca_sursa === 'istoric' : c.estimare_sursa === 'istoric'
    const s = durata(est(c, banca))
    return (
      <>
        {!banca && peBanca ? t('rulari.estimare_pe_banca', { durata: s }) : `~${s}`}
        <span className="sub">{masurat ? t('rulari.estimare_masurata') : t('rulari.estimare_initiala')}</span>
      </>
    )
  }

  const porneste = (c: ComandaRulare) => {
    const banca = alese[c.id] ?? ''
    if (c.banca === 'obligatoriu' && !banca) {
      modal.warning({ content: t('rulari.alege_intai_banca') })
      return
    }
    const nume = deLaServer(c.nume, lang)
    const e = est(c, banca) ?? 0
    const pleaca = async () => {
      const r = await apiPost('/api/rulari/porneste', { id: c.id, banca: banca || null }, d.token ?? '')
      if (r.eroare) modal.error({ content: t('rulari.nu_a_pornit', { eroare: deLaServer(r.eroare, lang) }) })
      await qc.invalidateQueries({ queryKey: ['rulari'] })
    }
    if (e <= 600) return void pleaca()
    const p = { nume, durata: durata(e), banca: numeBanca(banca) }
    const k = banca
      ? c.internet ? 'rulari.confirma_pornire_banca_internet' : 'rulari.confirma_pornire_banca'
      : c.internet ? 'rulari.confirma_pornire_internet' : 'rulari.confirma_pornire'
    modal.confirm({ content: t(k, p), onOk: pleaca })
  }

  const opreste = (cur: RulareCurenta) => {
    modal.confirm({
      content: t('rulari.confirma_oprire', { nume: deLaServer(cur.nume, lang) }),
      onOk: async () => {
        const r = await apiPost('/api/rulari/opreste', {}, d.token ?? '')
        if (r.eroare) modal.error({ content: t('rulari.nu_s_a_oprit', { eroare: deLaServer(r.eroare, lang) }) })
        await qc.invalidateQueries({ queryKey: ['rulari'] })
      },
    })
  }

  const ultima = (u: ComandaRulare['ultima']) => {
    if (!u) return <span className="gri">{t('rulari.niciodata')}</span>
    const rez = u.oprit ? <Pill tip="amb">{t('rulari.oprita')}</Pill>
      : u.cod === 0 ? <Pill tip="ok">{t('rulari.reusita')}</Pill>
        : u.cod === null ? <Pill title={t('rulari.cod_necunoscut_tooltip')}>{t('rulari.cod_necunoscut')}</Pill>
          : <Pill tip="amb">{t('rulari.eroare_cod', { cod: u.cod })}</Pill>
    return (
      <>
        <span title={(u.ultimele || []).join('\n')}>{ora(u.sfarsit)} · {durata(u.durata_s)}{u.banca ? ' · ' + numeBanca(u.banca) : ''}</span> {rez}
      </>
    )
  }

  const cur = d.curenta
  return (
    <>
      {!d.activ && <div className="callout warn" style={{ marginBottom: 14 }}><T k="rulari.oprite_callout" /></div>}
      {cur && (() => {
        const e = cur.estimare_s || 0
        const p = e ? cur.scurs_s / e : 0
        return (
          <div className="rl-curenta">
            <div className="rl-cap">
              <b>{t('rulari.ruleaza_acum', { nume: deLaServer(cur.nume, lang) })}{cur.banca ? ' · ' + numeBanca(cur.banca) : ''}</b>
              <span className="note">{cur.dupa_repornire ? t('rulari.pornita_la_repornire', { ora: ora(cur.inceput) }) : t('rulari.pornita_la', { ora: ora(cur.inceput) })}</span>
              <span style={{ marginLeft: 'auto' }}>
                <Button onClick={() => opreste(cur)} disabled={cur.oprit}>{cur.oprit ? t('rulari.se_opreste') : t('rulari.opreste')}</Button>
              </span>
            </div>
            <div className={`rl-bara${p > 1 ? ' peste' : ''}`}><i style={{ width: `${Math.min(100, Math.round(p * 100))}%` }} /></div>
            <div className="note">
              {t('rulari.progres', { scurs: durata(cur.scurs_s), estimat: durata(e) })}
              {p > 1 && <> · <T k="rulari.peste_estimare" /></>}
              {' · '}<T k="rulari.jurnal" params={{ log: cur.log }} />
            </div>
            <pre className="rl-jurnal">{(cur.jurnal || []).join('\n') || t('rulari.se_porneste')}</pre>
          </div>
        )
      })()}
      <p className="note" style={{ margin: '0 0 10px' }}>{t('rulari.nota')}</p>
      <table className="t rl">
        <thead>
          <tr>
            <th>{t('rulari.col_ce_ruleaza')}</th><th>{t('rulari.col_retea')}</th><th>{t('overview.col_banca')}</th>
            <th className="num">{t('rulari.col_dureaza')}</th><th>{t('rulari.col_ultima')}</th><th />
          </tr>
        </thead>
        <tbody>
          {d.comenzi.map((c) => (
            <tr key={c.id}>
              <td><b>{deLaServer(c.nume, lang)}</b><span className="sub" style={{ maxWidth: '62ch' }}>{deLaServer(c.ce, lang)}</span></td>
              <td className="rl-n">{c.internet ? <Pill tip="amb">{t('rulari.cu_internet')}</Pill> : <Pill tip="ok">{t('rulari.fara_internet')}</Pill>}</td>
              <td>
                {!c.banca ? <span className="gri">—</span> : (
                  <Select style={{ width: 200 }} disabled={!d.activ} value={alese[c.id] ?? ''}
                    onChange={(v) => setAlese({ ...alese, [c.id]: v })}
                    options={[{ value: '', label: c.banca === 'obligatoriu' ? t('rulari.alege_banca') : t('rulari.toate_bancile') },
                      ...banci.map((b) => ({ value: b, label: numeBanca(b) }))]} />
                )}
              </td>
              <td className="num rl-n">{estHtml(c, alese[c.id] ?? '')}</td>
              <td className="rl-u">{ultima(c.ultima)}</td>
              <td><Button type="primary" disabled={blocat} onClick={() => porneste(c)}>{t('rulari.ruleaza_buton')}</Button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}
