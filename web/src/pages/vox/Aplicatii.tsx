import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Tooltip } from 'antd'
import type { Aplicatii as AplicatiiT, CardNote as CardNoteT, ClasamentNote, ColoanaAplicatie, Diferenta } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { BareStele } from '../../components/BareStele'
import { EtichetaBanca } from '../../components/comune'
import { areCheie, useLang, type DictKey } from '../../i18n'
import { formatZi, num } from '../../util/format'
import { Verdict } from '../rate_mobil/android/comune'
import { FUNCTII } from '../rate_mobil/android/model'
import '../../styles/android.css'

/**
 * Aplicațiile băncilor în Vox (app/vox.py, `Vox._aplicatii_raspuns`): o funcție la toate băncile, aplicațiile băncilor
 * numite, notele din magazine sau o funcție neanalizată. Verdictele, etichetele și ordinea funcțiilor sunt ale paginii
 * Android, ca să nu existe a doua listă. Primele 10 rânduri ale unui clasament de note, plus Libra și băncile numite,
 * ca în `Clasament.tsx`: 22 de aplicații în Google Play, 19 în App Store (08.10.2026).
 */
const PRIMELE = 10
type T = ReturnType<typeof useLang>['t']

function etFunctie(f: string, t: T, scurt = false): string {
  const k = `mobil.android_${scurt ? 'fs' : 'f'}.${f}`
  return areCheie(k) ? t(k) : f
}

/** Ordinea paginii Android; o funcție nouă din bază, fără loc în listă, la final. */
function rang(f: string): number {
  const i = FUNCTII.indexOf(f)
  return i === -1 ? FUNCTII.length : i
}

function Dovada({ aplicatie, surse, dovada }: { aplicatie: string | null; surse: string[]; dovada: string | null }) {
  const { t } = useLang()
  const etSursa = (s: string) => {
    const k = `mobil.android_sursa.${s}`
    return areCheie(k) ? t(k) : s
  }
  return (
    <span className="vox-apl-dovada">
      {aplicatie && <b>{aplicatie}</b>}
      {surse.length > 0 && <span>{t('mobil.android_surse', { surse: surse.map(etSursa).join(', ') })}</span>}
      {dovada && <span>{t('mobil.android_dovada', { dovada })}</span>}
    </span>
  )
}

export default function Aplicatii({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t, locale } = useLang()
  const note = a.vedere === 'note' || a.vedere === 'aplicatii'
  const surse = [
    a.vedere !== 'note' && a.analiza_la ? t('vox.aplicatii.sursa_analiza', { data: formatZi(a.analiza_la, locale) }) : '',
    note && a.app_store_la ? t('vox.aplicatii.sursa_app_store', { data: formatZi(a.app_store_la, locale) }) : '',
    note ? (a.play_la ? t('vox.aplicatii.sursa_play', { data: formatZi(a.play_la, locale) }) : t('vox.aplicatii.play_lipsa')) : '',
  ].filter(Boolean)
  return (
    <div className="vox-fisa vox-apl">
      {a.vedere === 'functie' && <VedereFunctie a={a} m={m} />}
      {a.vedere === 'aplicatii' && <VedereAplicatii a={a} m={m} />}
      {a.vedere === 'note' && <VedereNote a={a} m={m} />}
      {a.vedere === 'neanalizata' && <Neanalizata a={a} />}
      {a.vedere !== 'aplicatii' && a.banci_fara_aplicatie.length > 0 && (
        <p className="vox-nota">
          <span className="vox-punct gri" />
          {t('vox.aplicatii.fara_aplicatie', {
            n: a.banci_fara_aplicatie.length, banci: a.banci_fara_aplicatie.map((b) => m.nume[b] ?? b).join(', '),
          })}
        </p>
      )}
      <div className="vox-fisa-jos">
        <span className="vox-meta">{surse.join(' · ')}</span>
        <Link className="vox-link" to={a.vedere === 'note' ? '/mobil' : '/mobil?platforma=android&s=functionalitati'}>
          {t(a.vedere === 'note' ? 'vox.aplicatii.deschide_mobil' : 'vox.aplicatii.deschide_android')}
        </Link>
      </div>
    </div>
  )
}

function VedereFunctie({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t } = useLang()
  const grupuri = a.grupuri ?? []
  return (
    <>
      <div className="vox-clas-antet">
        <b>{a.functie ? etFunctie(a.functie, t) : ''}</b>
        <span className="vox-meta">{t('vox.aplicatii.n_aplicatii', { n: grupuri.reduce((s, g) => s + g.aplicatii.length, 0) })}</span>
      </div>
      <div className="vox-apl-grupe">
        {grupuri.map((g) => (
          <section key={g.verdict} className="vox-apl-grupa">
            <div className="vox-apl-grupa-cap">
              <Verdict v={g.verdict} />
              <b>{t(`mobil.android_verdict.${g.verdict}` as DictKey)}</b>
              <span className="vox-meta">
                {t('vox.aplicatii.n_aplicatii', { n: g.aplicatii.length })} · {t(`mobil.android_verdict_d.${g.verdict}` as DictKey)}
              </span>
            </div>
            {g.aplicatii.length > 0 && (
              <div className="vox-apl-banci">
                {g.aplicatii.map((x) => (
                  <Tooltip key={x.banca} title={<Dovada aplicatie={x.aplicatie} surse={x.surse} dovada={x.dovada_text} />}>
                    <span className={x.evidentiata ? 'vox-apl-banca evidentiata' : 'vox-apl-banca'}>
                      <EtichetaBanca slug={x.banca} m={m} tag />
                    </span>
                  </Tooltip>
                ))}
              </div>
            )}
          </section>
        ))}
      </div>
      <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.nota_bifa')}</p>
    </>
  )
}

/** „Are X, n-are Y: …”, din diferențe și din verdictul lui X (sigur sau probabil), cu etichetele scurte. */
function propozitie(x: ColoanaAplicatie, y: ColoanaAplicatie, dif: Diferenta[], t: T): string | null {
  const ale = dif.filter((d) => d.au.includes(x.banca) && d.n_au.includes(y.banca)).sort((p, q) => rang(p.functie) - rang(q.functie))
  if (!ale.length) return null
  const sigure = ale.filter((d) => x.functii[d.functie]?.verdict === 'sigur').map((d) => etFunctie(d.functie, t, true))
  const probabile = ale.filter((d) => x.functii[d.functie]?.verdict === 'probabil').map((d) => etFunctie(d.functie, t, true))
  const parti = [sigure.join(', ')]
  if (probabile.length) parti.push(t(sigure.length ? 'vox.aplicatii.probabil_si' : 'vox.aplicatii.probabil', { lista: probabile.join(', ') }))
  return t('vox.aplicatii.are_nu', { x: x.aplicatie ?? x.banca, y: y.aplicatie ?? y.banca, lista: parti.filter(Boolean).join('; ') })
}

function NoteScurte({ c }: { c: ColoanaAplicatie }) {
  const { t, locale } = useLang()
  const parti = (['play', 'app_store'] as const).flatMap((k) => {
    const n = c[k]
    return n && n.nota !== null
      ? [`${t(`vox.aplicatii.magazin.${k}` as DictKey)} ${num(n.nota, locale, 1)} (${num(n.evaluari, locale, 0)})`]
      : []
  })
  return parti.length ? <span className="sub">★ {parti.join(' · ')}</span> : null
}

function VedereAplicatii({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t } = useLang()
  const coloane = a.coloane ?? []
  const dif = a.diferente ?? []
  const peFunctie = new Map(dif.map((d) => [d.functie, d]))
  const cu = coloane.filter((c) => !c.fara_aplicatie)
  const randuri = [...new Set(coloane.flatMap((c) => Object.keys(c.functii)))]
    .sort((x, y) => (x === a.functie ? -1 : y === a.functie ? 1 : rang(x) - rang(y)))
  const necomparabile = randuri.filter((f) => !peFunctie.has(f) && cu.some((c) => c.functii[f]?.verdict === 'neconcludent'))
  const fraze = cu.length === 2
    ? [propozitie(cu[0]!, cu[1]!, dif, t), propozitie(cu[1]!, cu[0]!, dif, t)].filter((x): x is string => !!x)
    : []
  return (
    <>
      {a.text_cautat && !a.functie && (
        <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.neanalizata_banca', { text: a.text_cautat })}</p>
      )}
      {cu.length === 2 && (
        <p className="vox-apl-propozitie">
          {fraze.length ? fraze.join(' ') : t('vox.aplicatii.nicio_diferenta', { n: randuri.length })}
          {necomparabile.length > 0 && ` ${t('vox.aplicatii.necomparabile', { n: necomparabile.length })}`}
        </p>
      )}
      <div className="vox-tabel-cutie">
        <table className="vox-tabel vox-apl-tabel">
          <thead>
            <tr>
              <th>{t('vox.aplicatii.col.functie')}</th>
              {coloane.map((c) => (
                <th key={c.banca} className="vox-apl-col">
                  <EtichetaBanca slug={c.banca} m={m} tag />
                  {c.fara_aplicatie
                    ? <span className="sub">{t('vox.aplicatii.fara_apk')}</span>
                    : (
                      <span className="sub">
                        {[c.aplicatie, c.versiune_analizata && t('vox.aplicatii.versiune', { v: c.versiune_analizata }), c.framework]
                          .filter(Boolean).join(' · ')}
                      </span>
                    )}
                  <NoteScurte c={c} />
                  {c.secundare.length > 0 && <span className="sub">{t('vox.aplicatii.secundare', { nume: c.secundare.join(', ') })}</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {randuri.map((f) => {
              const d = peFunctie.get(f)
              const necomp = necomparabile.includes(f)
              const cls = [f === a.functie ? 'evidentiata' : '', d ? `dif-${d.nivel}` : necomp ? 'necomparabil' : ''].filter(Boolean).join(' ')
              return (
                <tr key={f} className={cls || undefined}>
                  <td>
                    {etFunctie(f, t)}
                    {d && <span className="sub">{t(d.nivel === 'sigur' ? 'vox.aplicatii.dif_sigura' : 'vox.aplicatii.dif_probabila')}</span>}
                    {!d && necomp && <span className="sub">{t('vox.aplicatii.necomparabil')}</span>}
                  </td>
                  {coloane.map((c) => {
                    const v = c.functii[f]
                    return (
                      <td key={c.banca} className="vox-apl-v">
                        {v
                          ? (
                            <Tooltip title={(
                              <span className="vox-apl-dovada">
                                <b>{t(`mobil.android_verdict.${v.verdict}` as DictKey)}</b>
                                <span>{t(`mobil.android_verdict_d.${v.verdict}` as DictKey)}</span>
                                <Dovada aplicatie={null} surse={v.surse} dovada={v.dovada_text} />
                              </span>
                            )}>
                              <span><Verdict v={v.verdict} /></span>
                            </Tooltip>
                          )
                          : <span className="gri">—</span>}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}

function VedereNote({ a, m }: { a: AplicatiiT; m: Meta }) {
  const { t, locale } = useLang()
  const p = a.putine_note
  const magazin = (k: 'play' | 'app_store') => t(`vox.aplicatii.magazin.${k}` as DictKey)
  return (
    <>
      <div className="vox-clas-antet">
        <b>{t('vox.aplicatii.note_titlu')}</b>
        <span className="vox-meta">{t('vox.aplicatii.dupa_nota')}</span>
      </div>
      {p && (
        <p className="vox-nota vox-apl-prag">
          <span className="vox-punct" />
          {t(p.primul.loc === p.primul.loc_pana ? 'vox.aplicatii.intreaba_prag' : 'vox.aplicatii.intreaba_prag_egal', {
            magazin: magazin(p.primul.magazin), banca: m.nume[p.primul.banca] ?? p.primul.banca,
            loc: p.primul.loc, pana: p.primul.loc_pana, evaluari: num(p.primul.evaluari, locale, 0),
            prag: num(p.prag, locale, 0), n_app_store: p.app_store ?? 0, n_play: p.play ?? 0,
          })}
        </p>
      )}
      {a.prag != null && (
        <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.prag_activ', { prag: num(a.prag, locale, 0) })}</p>
      )}
      {(a.carduri ?? []).length > 0 && (
        <div className="vox-apl-carduri">
          {(a.carduri ?? []).map((c) => <CardNote key={c.banca} c={c} m={m} />)}
        </div>
      )}
      {(['play', 'app_store'] as const).map((k) => (
        <TabelNote key={k} titlu={magazin(k)} c={a.clasamente?.[k] ?? null} m={m} />
      ))}
    </>
  )
}

function CardNote({ c, m }: { c: CardNoteT; m: Meta }) {
  const { t, locale } = useLang()
  return (
    <article className="vox-apl-card">
      <EtichetaBanca slug={c.banca} m={m} tag />
      {c.fara_aplicatie
        ? <span className="vox-meta">{t('vox.aplicatii.fara_apk')}</span>
        : (
          <>
            {c.aplicatie && <b>{c.aplicatie}</b>}
            {(['play', 'app_store'] as const).map((k) => {
              const n = c[k]
              const numeMagazin = t(`vox.aplicatii.magazin.${k}` as DictKey)
              if (!n) return <span key={k} className="vox-meta">{t('vox.aplicatii.fara_magazin', { magazin: numeMagazin })}</span>
              const loc = n.sub_prag
                ? t('vox.aplicatii.card_sub_prag')
                : n.loc == null
                  ? ''
                  : n.loc === n.loc_pana
                    ? t('vox.aplicatii.card_loc', { loc: n.loc, din: n.din ?? 0 })
                    : t('vox.aplicatii.card_loc_egal', { loc: n.loc, pana: n.loc_pana ?? n.loc, din: n.din ?? 0 })
              return (
                <div key={k} className="vox-apl-magazin">
                  <span className="vox-et">{numeMagazin}</span>
                  <span className="nr">{n.nota !== null ? num(n.nota, locale, 1) : '—'}</span>
                  <span className="vox-meta">{t('vox.aplicatii.nr_note', { n: num(n.evaluari, locale, 0) })}{loc ? ` · ${loc}` : ''}</span>
                  <BareStele dist={n.distributie_stele} latime={160} />
                  {n.url && <a className="vox-link" href={n.url} target="_blank" rel="noopener noreferrer">{t('vox.aplicatii.deschide_magazin')}</a>}
                </div>
              )
            })}
          </>
        )}
    </article>
  )
}

function TabelNote({ titlu, c, m }: { titlu: string; c: ClasamentNote | null; m: Meta }) {
  const { t, locale } = useLang()
  const [toate, setToate] = useState(false)
  if (!c) return <p className="vox-nota"><span className="vox-punct gri" />{titlu}: {t('vox.aplicatii.play_lipsa')}</p>
  const vizibile = toate ? c.randuri : c.randuri.filter((r, i) => i < PRIMELE || r.evidentiata)
  const lista = (rs: ClasamentNote['sub_prag']) => rs
    .map((r) => `${m.nume[r.banca] ?? r.banca} (${r.nota_afisata !== null ? num(r.nota_afisata, locale, 1) : '—'}; ${num(r.evaluari, locale, 0)})`)
    .join(', ')
  return (
    <div className="vox-clas-bloc">
      <span className="vox-segment-cap">{titlu}</span>
      <div className="vox-tabel-cutie">
        <table className="vox-tabel vox-clas vox-apl-note">
          <thead>
            <tr>
              <th>{t('vox.clasament.col.loc')}</th>
              <th>{t('vox.clasament.col.banca')}</th>
              <th>{t('vox.aplicatii.col.aplicatia')}</th>
              <th className="dr">{t('vox.aplicatii.col.nota')}</th>
              <th className="dr">{t('vox.aplicatii.col.evaluari')}</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {vizibile.map((r) => (
              <tr key={r.banca} className={r.evidentiata ? 'evidentiata' : undefined}>
                <td className="loc">{r.loc === r.loc_pana ? r.loc : `${r.loc}–${r.loc_pana}`}</td>
                <td><EtichetaBanca slug={r.banca} m={m} tag /></td>
                <td>{r.aplicatie ?? '—'}</td>
                <td className="dr val">
                  <Tooltip title={r.nota !== null ? num(r.nota, locale) : ''}>
                    <span className="nr">{r.nota_afisata !== null ? num(r.nota_afisata, locale, 1) : '—'}</span>
                  </Tooltip>
                </td>
                <td className="dr">{num(r.evaluari, locale, 0)}</td>
                <td>{r.url && <a className="vox-link" href={r.url} target="_blank" rel="noopener noreferrer">{t('vox.aplicatii.deschide_magazin')}</a>}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {c.randuri.length > vizibile.length && (
        <button type="button" className="vox-link vox-clas-toate" onClick={() => setToate(true)}>
          {t('vox.clasament.arata_toate', { n: c.randuri.length })}
        </button>
      )}
      {c.sub_prag.length > 0 && (
        <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.sub_prag', { n: c.sub_prag.length, lista: lista(c.sub_prag) })}</p>
      )}
      {c.fara_nota.length > 0 && (
        <p className="vox-nota"><span className="vox-punct gri" />{t('vox.aplicatii.fara_nota', { n: c.fara_nota.length, lista: lista(c.fara_nota) })}</p>
      )}
    </div>
  )
}

function Neanalizata({ a }: { a: AplicatiiT }) {
  const { t } = useLang()
  const lista = [...(a.functii ?? [])].sort((x, y) => rang(x) - rang(y))
  return (
    <>
      <p className="vox-nota"><span className="vox-punct" />{t('vox.aplicatii.neanalizata', { text: a.text_cautat ?? '' })}</p>
      <ul className="vox-apl-lista">{lista.map((f) => <li key={f}>{etFunctie(f, t)}</li>)}</ul>
    </>
  )
}
