import { useState } from 'react'
import { Button, Input, Tooltip } from 'antd'
import type { Interpretare, RaspunsBanca, RaspunsIntrebare, ValoareDovada } from '@mcc/shared'
import { SERVER_OPRIT } from '../api/client'
import { trimiteIntrebarea, useStareIntrebari } from '../api/intreaba'
import { useMeta, type Meta } from '../api/meta'
import { EtichetaBanca, Eroare, Pill, SeIncarca } from '../components/comune'
import { LinkSursa } from '../components/Dovezi'
import Sertar, { type CerereSertar } from '../components/Sertar'
import { etNume, unitTxt } from '../components/valori'
import { areCheie, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { num } from '../util/format'
import '../styles/intreaba.css'

/**
 * „Întreabă datele”: o întrebare despre o valoare a unei bănci. Modelul (app/intreaba.py) doar
 * traduce textul în banca și conceptul căutat; cifrele, citatele și documentele vin din bază, prin
 * aceeași funcție ca Sertar-ul din 2.1, deci fișa nu conține niciun număr scris de model.
 * Conversația stă doar în memoria paginii, nu în adresă: un link deschis ar porni un apel plătit
 * (abatere asumată de la „filtrele stau în adresă”, specificația din 06.10.2026).
 */

interface Mesaj {
  id: number
  intrebare: string
  raspuns?: RaspunsIntrebare
  eroare?: string
}

type Tr = (k: DictKey, p?: Record<string, string | number>) => string

const EXEMPLE: DictKey[] = ['intreaba.exemplu.1', 'intreaba.exemplu.2', 'intreaba.exemplu.3']
const PRIMELE = 5

/** O întrebare costă miimi de dolar: `usd` din Logging ar arăta orice sub un cent ca „< $0,01”. */
const dolari = (v: number, locale: string) => '$' + num(v, locale, 4)

/** Eticheta unei chei din vocabular; o cheie nouă, fără traducere, apare cum vine, nu dispare. */
function eticheta(k: string, rezerva: string, t: Tr): string {
  return areCheie(k) ? t(k) : rezerva
}

export default function Intreaba() {
  const { t, lang, locale } = useLang()
  const meta = useMeta()
  const stare = useStareIntrebari()
  const [text, setText] = useState('')
  const [mesaje, setMesaje] = useState<Mesaj[]>([])
  const [seTrimite, setSeTrimite] = useState(false)
  const [cerere, setCerere] = useState<CerereSertar | null>(null)

  const err = meta.error ?? stare.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !stare.data) return <SeIncarca />
  const m = meta.data
  const st = stare.data
  const cost = mesaje.reduce((s, x) => s + (x.raspuns?.cost_usd ?? 0), 0)

  async function trimite(intrebare: string) {
    const q = intrebare.trim()
    if (!q || seTrimite || !st.activ) return
    // „și la BRD?” continuă ultima căutare reușită, nu o clarificare sau o eroare
    const anterior = [...mesaje].reverse().find((x) => x.raspuns?.interpretare.tip === 'cautare')?.raspuns?.interpretare ?? null
    const id = Date.now()
    setMesaje((x) => [...x, { id, intrebare: q }])
    setSeTrimite(true)
    try {
      const r = await trimiteIntrebarea(q, anterior, st.token ?? '')
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, raspuns: r } : y)))
      setText('')
    } catch (e) {
      const mesaj = (e as Error).message
      const afisat = mesaj === SERVER_OPRIT ? t('comun.server_oprit') : deLaServer(mesaj, lang)
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, eroare: afisat } : y)))
      // serverul repornit are alt token: îl ia din nou, întrebarea rămâne în câmp
      if (mesaj.includes('token')) void stare.refetch()
    } finally {
      setSeTrimite(false)
    }
  }

  return (
    <>
      {!st.activ && <div className="callout warn intreaba-oprit">{t('intreaba.oprit')}</div>}
      <section className="intreaba-intrebare">
        <Input.TextArea
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={500}
          autoSize={{ minRows: 2, maxRows: 5 }}
          placeholder={t('intreaba.placeholder')}
          disabled={!st.activ}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault()
              void trimite(text)
            }
          }}
        />
        <div className="intreaba-butoane">
          <Button type="primary" onClick={() => void trimite(text)} loading={seTrimite} disabled={!st.activ || !text.trim()}>
            {t('intreaba.trimite')}
          </Button>
          {EXEMPLE.map((k) => (
            <Button key={k} size="small" disabled={!st.activ || seTrimite} onClick={() => { setText(t(k)); void trimite(t(k)) }}>
              {t(k)}
            </Button>
          ))}
        </div>
        <p className="note">
          {t('intreaba.model', { model: st.model })}
          {mesaje.length > 0 && ` · ${t('intreaba.cost_total', { cost: dolari(cost, locale) })}`}
        </p>
      </section>
      {/* stilul global desenează orice `section` ca un card: fără mesaje ar rămâne o casetă goală */}
      {mesaje.length > 0 && <section className="intreaba-mesaje">
        {mesaje.map((x) => (
          <article key={x.id} className="intreaba-mesaj">
            <p className="intreaba-q">{x.intrebare}</p>
            {!x.raspuns && !x.eroare && <p className="note">{t('intreaba.se_gandeste')}</p>}
            {x.eroare && <p className="note intreaba-eroare">{x.eroare}</p>}
            {x.raspuns && <Raspuns r={x.raspuns} m={m} onDovezi={setCerere} onExemplu={(q) => void trimite(q)} />}
          </article>
        ))}
      </section>}
      <Sertar cerere={cerere} onClose={() => setCerere(null)} />
    </>
  )
}

function Raspuns({ r, m, onDovezi, onExemplu }: {
  r: RaspunsIntrebare; m: Meta; onDovezi: (c: CerereSertar) => void; onExemplu: (q: string) => void
}) {
  const { t, locale } = useLang()
  const i = r.interpretare
  const tk = r.tokeni
  const subsol = (
    <p className="note intreaba-subsol">
      {t('intreaba.subsol', {
        model: r.model,
        intrare: num(tk.intrare + tk.citire_cache + tk.scriere_cache, locale, 0),
        iesire: num(tk.iesire, locale, 0),
        cost: r.cost_usd === null ? t('intreaba.cost_necunoscut') : dolari(r.cost_usd, locale),
      })}
    </p>
  )
  if (i.tip === 'in_afara') {
    return (
      <>
        <p>{t('intreaba.in_afara')}</p>
        <div className="intreaba-butoane">
          {EXEMPLE.map((k) => <Button key={k} size="small" onClick={() => onExemplu(t(k))}>{t(k)}</Button>)}
        </div>
        {subsol}
      </>
    )
  }
  if (i.tip === 'neclar') {
    return (
      <>
        {i.clarificare
          ? <p><Pill title={t('intreaba.clarificare_tooltip')}>{t('intreaba.clarificare_eticheta')}</Pill> {i.clarificare}</p>
          : <p>{t('intreaba.neclar')}</p>}
        {subsol}
      </>
    )
  }
  return (
    <>
      <p className="intreaba-inteles">
        {t('intreaba.am_inteles')} <b>{i.banci.map((b) => m.nume[b] ?? b).join(', ')}</b>
        {' · '}{i.concept ? etNume(i.concept, t) : t('intreaba.text', { text: i.text_cautat ?? '' })}
        {i.categorie && <> · {eticheta(`intreaba.categorie.${i.categorie}`, i.categorie, t)}</>}
        {i.termen && <> · {eticheta(`intreaba.termen.${i.termen}`, i.termen, t)}</>}
        {i.produs_credit && <> · {eticheta(`intreaba.produs.${i.produs_credit}`, i.produs_credit, t)}</>}
      </p>
      {r.ignorate.length > 0 && <p className="note">{t('intreaba.ignorate', { banci: r.ignorate.map((b) => m.nume[b] ?? b).join(', ') })}</p>}
      {r.raspunsuri.map((rb) => <FisaBanca key={rb.banca} rb={rb} i={i} m={m} onDovezi={onDovezi} />)}
      {subsol}
    </>
  )
}

function FisaBanca({ rb, i, m, onDovezi }: { rb: RaspunsBanca; i: Interpretare; m: Meta; onDovezi: (c: CerereSertar) => void }) {
  const { t, tn, locale } = useLang()
  const [toate, setToate] = useState(false)
  const concept = i.concept ? etNume(i.concept, t) : t('intreaba.text', { text: i.text_cautat ?? '' })
  if (rb.total === 0) {
    return (
      <div className="intreaba-fisa">
        <EtichetaBanca slug={rb.banca} m={m} fisa />
        <p>
          {t('intreaba.zero', { concept, banca: m.nume[rb.banca] ?? rb.banca })}
          {rb.stare_banca && <> {t(rb.stare_banca === 'blocata' ? 'intreaba.stare.blocata' : 'intreaba.stare.fara_surse')}</>}
        </p>
      </div>
    )
  }
  const vizibile = toate ? rb.randuri : rb.randuri.slice(0, PRIMELE)
  const cuUnitate = (v: number, u: string) => num(v, locale) + unitTxt(u, t)
  return (
    <div className="intreaba-fisa">
      <div className="intreaba-fisa-cap">
        <EtichetaBanca slug={rb.banca} m={m} fisa />
        {rb.mod === 'text' && (
          <Tooltip title={t('intreaba.mod_text_tooltip')}>
            <span><Pill tip="amb">{t('intreaba.mod_text')}</Pill></span>
          </Tooltip>
        )}
      </div>
      <ul className="intreaba-rezumat">
        {rb.rezumat.map((g) => (
          <li key={`${g.unitate}|${g.categorie}`}>
            {g.minim === g.maxim
              ? tn('intreaba.rezumat_egal', g.n, { val: cuUnitate(g.minim, g.unitate) })
              : tn('intreaba.rezumat', g.n, { min: cuUnitate(g.minim, g.unitate), max: cuUnitate(g.maxim, g.unitate) })}
            {g.gratuite > 0 && <> · {tn('intreaba.gratuite', g.gratuite)}</>}
            {rb.rezumat.length > 1 && <> · <span className="note">{eticheta(`intreaba.categorie.${g.categorie}`, g.categorie, t)}</span></>}
            {rb.mod === 'concept' && i.concept && (
              <Button size="small" type="link" onClick={() => onDovezi({
                banca: rb.banca, camp: i.concept!, unitate: g.unitate, scenariu: g.categorie,
                termen: i.termen ?? '', produs: i.produs_credit ?? '',
              })}>
                {t('intreaba.vezi_dovezi')}
              </Button>
            )}
          </li>
        ))}
      </ul>
      {rb.ambigue > 0 && <p className="note">{tn('intreaba.ambigue', rb.ambigue)}</p>}
      <table className="intreaba-valori">
        <tbody>{vizibile.map((v, k) => <Rand key={k} v={v} />)}</tbody>
      </table>
      {rb.randuri.length > PRIMELE && (
        <Button size="small" type="link" onClick={() => setToate(!toate)}>
          {toate ? t('intreaba.arata_mai_putine') : tn('intreaba.arata_toate', rb.randuri.length)}
        </Button>
      )}
      {rb.limitat && <p className="note">{t('intreaba.limitat', { n: rb.randuri.length })}</p>}
    </div>
  )
}

/** Un rând: serviciul și condiția băncii (date, netraduse), valoarea, dovada. */
function Rand({ v }: { v: ValoareDovada }) {
  const { t, locale } = useLang()
  const valoare = v.valoare !== null ? num(v.valoare, locale) + unitTxt(v.unitate, t) : (v.valoare_text ?? '—')
  return (
    <tr className={v.ambiguu ? 'ambiguu' : undefined}>
      <td>{v.serviciu ?? '—'}{v.conditie && <div className="note">{v.conditie}</div>}</td>
      <td className="valoare">{valoare}{v.frecventa && <div className="note">{v.frecventa}</div>}</td>
      <td>
        {v.ambiguu && <Pill tip="amb" title={v.motiv_ambiguu ?? undefined}>{t('intreaba.ambiguu')}</Pill>}{' '}
        <LinkSursa r={v} />
      </td>
    </tr>
  )
}
