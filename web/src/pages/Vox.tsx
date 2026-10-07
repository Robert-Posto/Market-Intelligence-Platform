import { useEffect, useRef, useState } from 'react'
import { Button, Input, Tooltip } from 'antd'
import { ArrowRightOutlined } from '@ant-design/icons'
import type { Interpretare, RaspunsBanca, RaspunsIntrebare, ValoareDovada } from '@mcc/shared'
import { SERVER_OPRIT } from '../api/client'
import { trimiteIntrebarea, useStareVox } from '../api/vox'
import { useMeta, type Meta } from '../api/meta'
import { EtichetaBanca, Eroare, Pill, SeIncarca } from '../components/comune'
import { LinkSursa } from '../components/Dovezi'
import { VoxBula, VoxInsigna } from '../components/LogoVox'
import Sertar, { type CerereSertar } from '../components/Sertar'
import { etNume, unitTxt } from '../components/valori'
import { areCheie, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { num } from '../util/format'
import '../styles/vox.css'

/**
 * Vox: o întrebare despre o valoare a unei bănci. Modelul (app/vox.py) doar
 * traduce textul în banca și conceptul căutat; cifrele, citatele și documentele vin din bază, prin
 * aceeași funcție ca Sertar-ul din 2.1, deci fișa nu conține niciun număr scris de model.
 * Conversația stă doar în memoria paginii, nu în adresă: un link deschis ar porni un apel plătit
 * (abatere asumată de la „filtrele stau în adresă”, specificația din 06.10.2026).
 * Așezarea de chat (întrebarea jos, cea mai nouă tură deasupra ei) e macheta aprobată pe 07.10.2026.
 */

interface Mesaj {
  id: number
  intrebare: string
  raspuns?: RaspunsIntrebare
  eroare?: string
}

type Tr = (k: DictKey, p?: Record<string, string | number>) => string

const EXEMPLE: { tip: DictKey; text: DictKey }[] = [
  { tip: 'vox.exemplu_tip.1', text: 'vox.exemplu.1' },
  { tip: 'vox.exemplu_tip.2', text: 'vox.exemplu.2' },
  { tip: 'vox.exemplu_tip.3', text: 'vox.exemplu.3' },
]
// plăcile de rezumat spun deja intervalul; tabelul arată doar câteva rânduri ca exemplu (macheta)
const PRIMELE = 3

/** O întrebare costă miimi de dolar: `usd` din Logging ar arăta orice sub un cent ca „< $0,01”. */
const dolari = (v: number, locale: string) => '$' + num(v, locale, 4)

/** Eticheta unei chei din vocabular; o cheie nouă, fără traducere, apare cum vine, nu dispare. */
function eticheta(k: string, rezerva: string, t: Tr): string {
  return areCheie(k) ? t(k) : rezerva
}

export default function Vox() {
  const { t, lang, locale } = useLang()
  const meta = useMeta()
  const stare = useStareVox()
  const [text, setText] = useState('')
  const [mesaje, setMesaje] = useState<Mesaj[]>([])
  const [seTrimite, setSeTrimite] = useState(false)
  const [cerere, setCerere] = useState<CerereSertar | null>(null)
  // tura nouă apare jos, deasupra câmpului fix: pagina coboară după ea
  const capat = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (mesaje.length) capat.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [mesaje])

  const err = meta.error ?? stare.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !stare.data) return <SeIncarca />
  const m = meta.data
  const st = stare.data
  const poate = st.activ && !seTrimite
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

  const intreaba = (q: string) => {
    setText(q)
    void trimite(q)
  }

  return (
    <div className="vox">
      {!st.activ && <div className="callout warn">{t('vox.oprit')}</div>}
      {mesaje.length === 0 && <BunVenit banci={Object.keys(m.nume).length} poate={poate} onExemplu={intreaba} />}
      {mesaje.map((x) => (
        <div key={x.id} className="vox-tura">
          <p className="vox-q">{x.intrebare}</p>
          <div className="vox-r">
            <span className="vox-avatar"><VoxBula size={20} /></span>
            {!x.raspuns && !x.eroare && (
              <div className="vox-bula vox-gandeste">
                <span className="vox-puncte" aria-hidden="true"><i /><i /><i /></span>
                {t('vox.se_gandeste')}
              </div>
            )}
            {x.eroare && <div className="vox-bula vox-eroare">{x.eroare}</div>}
            {x.raspuns && <Raspuns r={x.raspuns} m={m} poate={poate} onDovezi={setCerere} onExemplu={intreaba} />}
          </div>
        </div>
      ))}
      <div ref={capat} className="vox-capat" />
      <div className="vox-compune">
        <div className="vox-cutie">
          <Input.TextArea
            variant="borderless"
            aria-label={t('vox.eticheta_camp')}
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={500}
            autoSize={{ minRows: 1, maxRows: 5 }}
            placeholder={t('vox.placeholder')}
            disabled={!st.activ}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault()
                void trimite(text)
              }
            }}
          />
          <Button
            type="primary"
            className="vox-trimite"
            icon={<ArrowRightOutlined />}
            iconPosition="end"
            onClick={() => void trimite(text)}
            loading={seTrimite}
            disabled={!st.activ || !text.trim()}
          >
            {t('vox.trimite')}
          </Button>
        </div>
        <div className="vox-cutie-jos">
          <span>{t('vox.tastatura')}</span>
          <span>
            {mesaje.length > 0
              ? t('vox.subsol_sesiune', { model: st.model, cost: dolari(cost, locale) })
              : t('vox.subsol_gol', { model: st.model })}
          </span>
        </div>
      </div>
      <Sertar cerere={cerere} onClose={() => setCerere(null)} />
    </div>
  )
}

/** Ce vede cine deschide pagina: ce face Vox și trei întrebări care chiar găsesc valori. */
function BunVenit({ banci, poate, onExemplu }: { banci: number; poate: boolean; onExemplu: (q: string) => void }) {
  const { t } = useLang()
  return (
    <section className="vox-bun-venit">
      <VoxInsigna className="vox-insigna" size={64} />
      <h2>{t('vox.bun_venit.titlu')}</h2>
      <p>{t('vox.bun_venit.text', { n: banci })}</p>
      <div className="vox-exemple">
        {EXEMPLE.map((e) => (
          <button key={e.text} type="button" className="vox-exemplu" disabled={!poate} onClick={() => onExemplu(t(e.text))}>
            <span className="tip">{t(e.tip)}</span>
            <span className="txt">{t(e.text)}</span>
            <span className="sag">{t('vox.intreaba_sageata')}</span>
          </button>
        ))}
      </div>
      <p className="vox-limite">{t('vox.bun_venit.limite')}</p>
    </section>
  )
}

function Raspuns({ r, m, poate, onDovezi, onExemplu }: {
  r: RaspunsIntrebare; m: Meta; poate: boolean; onDovezi: (c: CerereSertar) => void; onExemplu: (q: string) => void
}) {
  const { t, locale } = useLang()
  const i = r.interpretare
  const tk = r.tokeni
  const subsol = (
    <span className="vox-meta">
      {t('vox.subsol', {
        model: r.model,
        tokeni: num(tk.intrare + tk.citire_cache + tk.scriere_cache + tk.iesire, locale, 0),
        cost: r.cost_usd === null ? t('vox.cost_necunoscut') : dolari(r.cost_usd, locale),
      })}
    </span>
  )
  if (i.tip === 'in_afara') {
    return (
      <div className="vox-bula">
        <p>{t('vox.in_afara')}</p>
        <div className="vox-sugestii">
          {EXEMPLE.map((e) => (
            <button key={e.text} type="button" className="vox-sugestie" disabled={!poate} onClick={() => onExemplu(t(e.text))}>
              {t(e.text)}
            </button>
          ))}
        </div>
        {subsol}
      </div>
    )
  }
  if (i.tip === 'neclar') {
    return (
      <div className="vox-bula">
        {i.clarificare
          ? <p><Pill title={t('vox.clarificare_tooltip')}>{t('vox.clarificare_eticheta')}</Pill> {i.clarificare}</p>
          : <p>{t('vox.neclar')}</p>}
        {subsol}
      </div>
    )
  }
  const filtre = [
    i.categorie && eticheta(`vox.categorie.${i.categorie}`, i.categorie, t),
    i.termen && eticheta(`vox.termen.${i.termen}`, i.termen, t),
    i.produs_credit && eticheta(`vox.produs.${i.produs_credit}`, i.produs_credit, t),
  ].filter((x): x is string => !!x)
  return (
    <article className="vox-card">
      <div className="vox-inteles">
        <span className="vox-et">{t('vox.am_inteles')}</span>
        {i.banci.map((b) => <span key={b} className="vox-chip banca">{m.nume[b] ?? b}</span>)}
        <span className="vox-chip">{i.concept ? etNume(i.concept, t) : t('vox.text_chip', { text: i.text_cautat ?? '' })}</span>
        {filtre.map((f) => <span key={f} className="vox-chip">{f}</span>)}
      </div>
      {r.ignorate.length > 0 && (
        <p className="vox-nota"><span className="vox-punct" />{t('vox.ignorate', { banci: r.ignorate.map((b) => m.nume[b] ?? b).join(', ') })}</p>
      )}
      {r.raspunsuri.map((rb) => <FisaBanca key={rb.banca} rb={rb} i={i} m={m} onDovezi={onDovezi} />)}
      <div className="vox-card-jos">{subsol}</div>
    </article>
  )
}

function FisaBanca({ rb, i, m, onDovezi }: { rb: RaspunsBanca; i: Interpretare; m: Meta; onDovezi: (c: CerereSertar) => void }) {
  const { t, tn, locale } = useLang()
  const [toate, setToate] = useState(false)
  const cap = (
    <div className="vox-banca">
      <EtichetaBanca slug={rb.banca} m={m} fisa />
      {rb.mod === 'text' && (
        <Tooltip title={t('vox.mod_text_tooltip')}>
          <span><Pill tip="amb">{t('vox.mod_text')}</Pill></span>
        </Tooltip>
      )}
      {rb.total > 0 && <span className="vox-n">{tn('vox.n_valori', rb.total)}</span>}
    </div>
  )
  if (rb.total === 0) {
    const concept = i.concept ? etNume(i.concept, t) : t('vox.text', { text: i.text_cautat ?? '' })
    // filtrele intră în mesaj: „nu avem dobânda nominală la ING” era fals, ING avea 2, fără termen citit
    const filtre = [
      i.termen && eticheta(`vox.termen.${i.termen}`, i.termen, t),
      i.produs_credit && eticheta(`vox.produs.${i.produs_credit}`, i.produs_credit, t),
    ].filter(Boolean).join(' · ')
    return (
      <div className="vox-fisa">
        {cap}
        <div className="vox-gol">
          <p>
            <b>{t('vox.zero', { concept: filtre ? `${concept} · ${filtre}` : concept, banca: m.nume[rb.banca] ?? rb.banca })}</b>
            {rb.stare_banca && <> {t(rb.stare_banca === 'blocata' ? 'vox.stare.blocata' : 'vox.stare.fara_surse')}</>}
            {!!rb.fara_filtre && <> {tn('vox.fara_filtre', rb.fara_filtre)}</>}
          </p>
          {!!rb.fara_filtre && i.concept && (
            <button type="button" className="vox-link avertizare" onClick={() => onDovezi({
              banca: rb.banca, camp: i.concept!, unitate: '', scenariu: i.categorie ?? '', termen: '', produs: '',
            })}>
              {tn('vox.vezi_le', rb.fara_filtre)}
            </button>
          )}
        </div>
      </div>
    )
  }
  const vizibile = toate ? rb.randuri : rb.randuri.slice(0, PRIMELE)
  // categoria spune ceva doar când grupele diferă (dobândă de depozit vs. de credit)
  const multeCategorii = new Set(rb.rezumat.map((g) => g.categorie)).size > 1
  return (
    <div className="vox-fisa">
      {cap}
      {rb.rezumat.length > 0 && (
        <div className="vox-kpis">
          {rb.rezumat.map((g) => {
            const unitate = unitTxt(g.unitate, t).trim()
            const egal = g.minim === g.maxim
            return (
              <div key={`${g.unitate}|${g.categorie}`} className="vox-kpi">
                <span className="v">
                  {egal ? num(g.minim, locale) : `${num(g.minim, locale)} – ${num(g.maxim, locale)}`}
                  {unitate && <small> {unitate}</small>}
                </span>
                <span className="l">
                  {egal && g.n > 1 ? tn('vox.kpi_egal', g.n) : tn('vox.kpi', g.n)}
                  {g.gratuite > 0 && <> · {tn('vox.gratuite', g.gratuite)}</>}
                  {multeCategorii && <> · {eticheta(`vox.categorie.${g.categorie}`, g.categorie, t)}</>}
                </span>
                {rb.mod === 'concept' && i.concept && (
                  <button type="button" className="vox-link" onClick={() => onDovezi({
                    banca: rb.banca, camp: i.concept!, unitate: g.unitate, scenariu: g.categorie,
                    termen: i.termen ?? '', produs: i.produs_credit ?? '',
                  })}>
                    {t('vox.vezi_dovezi')}
                  </button>
                )}
              </div>
            )
          })}
        </div>
      )}
      {/* la căutarea după text SQL-ul se oprește la 50: rezumatul e pe ele, nu pe toate */}
      {rb.limitat && <p className="vox-nota"><span className="vox-punct" />{t('vox.din_primele', { n: rb.randuri.length })}</p>}
      {rb.ambigue > 0 && <p className="vox-nota"><span className="vox-punct" />{tn('vox.ambigue', rb.ambigue)}</p>}
      {rb.fara_cifra > 0 && <p className="vox-nota"><span className="vox-punct gri" />{tn('vox.fara_cifra', rb.fara_cifra)}</p>}
      <div className="vox-tabel-cutie">
        <table className="vox-tabel">
          <thead>
            <tr>
              <th>{t('vox.col.serviciu')}</th>
              <th className="dr">{t('vox.col.valoare')}</th>
              <th>{t('vox.col.document')}</th>
            </tr>
          </thead>
          <tbody>{vizibile.map((v, k) => <Rand key={k} v={v} />)}</tbody>
        </table>
      </div>
      {(rb.randuri.length > PRIMELE || rb.limitat) && (
        <div className="vox-fisa-jos">
          {rb.randuri.length > PRIMELE && (
            <button type="button" className="vox-link" onClick={() => setToate(!toate)}>
              {toate
                ? t('vox.arata_mai_putine')
                // BCR · Administrare cont are 570 de valori, din care răspunsul aduce 50: „toate (50)” ar minți
                : rb.total > rb.randuri.length
                  ? t('vox.arata_primele', { n: rb.randuri.length, total: rb.total })
                  : tn('vox.arata_toate', rb.randuri.length)}
            </button>
          )}
          {rb.limitat && <span className="vox-meta">{t('vox.limitat', { n: rb.randuri.length })}</span>}
        </div>
      )}
    </div>
  )
}

/** Un rând: serviciul și condiția băncii (date, netraduse), valoarea, dovada. */
function Rand({ v }: { v: ValoareDovada }) {
  const { t, locale } = useLang()
  const valoare = v.valoare !== null ? num(v.valoare, locale) + unitTxt(v.unitate, t) : (v.valoare_text ?? '—')
  return (
    <tr className={v.ambiguu ? 'ambiguu' : undefined}>
      <td>{v.serviciu ?? '—'}{v.conditie && <span className="sub">{v.conditie}</span>}</td>
      <td className="dr val">{valoare}{v.frecventa && <span className="sub">{v.frecventa}</span>}</td>
      <td>
        {v.ambiguu && <><Pill tip="amb" title={v.motiv_ambiguu ?? undefined}>{t('vox.ambiguu')}</Pill>{' '}</>}
        <LinkSursa r={v} />
      </td>
    </tr>
  )
}
