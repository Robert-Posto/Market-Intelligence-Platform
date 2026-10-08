import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Button, Drawer, Input, Tooltip } from 'antd'
import { ArrowRightOutlined, HistoryOutlined } from '@ant-design/icons'
import type { GrupaRezumat, Interpretare, RaspunsBanca, RaspunsIntrebare, ValoareDovada } from '@mcc/shared'
import { ApiError, SERVER_OPRIT } from '../api/client'
import {
  CHEIE_CONVERSATII,
  citesteConversatia,
  redenumesteConversatia,
  stergeConversatia,
  trimiteIntrebarea,
  useConversatii,
  useStareVox,
} from '../api/vox'
import { useMeta, type Meta } from '../api/meta'
import { EtichetaBanca, Eroare, Pill, PillSegment, SeIncarca } from '../components/comune'
import { LinkSursa } from '../components/Dovezi'
import { VoxBula, VoxInsigna } from '../components/LogoVox'
import Sertar, { type CerereSertar } from '../components/Sertar'
import { etNume, etSegment, unitTxt } from '../components/valori'
import { areCheie, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { formatZi, num } from '../util/format'
import Clasament from './vox/Clasament'
import Conversatii, { cand } from './vox/Conversatii'
import '../styles/vox.css'

/**
 * Vox: o întrebare despre o valoare a unei bănci. Modelul (app/vox.py) doar
 * traduce textul în banca și conceptul căutat; cifrele, citatele și documentele vin din bază, prin
 * aceeași funcție ca Sertar-ul din 2.1, deci fișa nu conține niciun număr scris de model.
 * Conversațiile se păstrează pe laptop (loguri/vox/conversatii/, prin server) și se redeschid din
 * coloana „Conversații”; cea deschisă stă în adresă (`?c=`), fiindcă redeschiderea citește fișierul
 * și nu cheamă modelul.
 * Așezarea de chat (întrebarea jos, cea mai nouă tură deasupra ei) e macheta aprobată pe 07.10.2026.
 */

interface Mesaj {
  id: number
  intrebare: string
  /** ora întrebării (ISO): din fișier la o conversație redeschisă, a laptopului la una nouă */
  data: string
  raspuns?: RaspunsIntrebare
  eroare?: string
}

type Tr = (k: DictKey, p?: Record<string, string | number>) => string
type Tn = ReturnType<typeof useLang>['tn']

// șase pe pagina goală (pe un ecran de 1033px, trei lăsau cardul pe jumătate gol); primele trei și sub refuz
const EXEMPLE: { tip: DictKey; text: DictKey }[] = [
  { tip: 'vox.exemplu_tip.1', text: 'vox.exemplu.1' },
  { tip: 'vox.exemplu_tip.2', text: 'vox.exemplu.2' },
  { tip: 'vox.exemplu_tip.3', text: 'vox.exemplu.3' },
  { tip: 'vox.exemplu_tip.4', text: 'vox.exemplu.4' },
  { tip: 'vox.exemplu_tip.5', text: 'vox.exemplu.5' },
  { tip: 'vox.exemplu_tip.6', text: 'vox.exemplu.6' },
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
  const { t, tn, lang, locale } = useLang()
  const qc = useQueryClient()
  const [sp, setSp] = useSearchParams()
  const c = sp.get('c')
  const cauta = sp.get('cauta') ?? ''
  const meta = useMeta()
  const stare = useStareVox()
  const conversatii = useConversatii()
  const [text, setText] = useState('')
  const [mesaje, setMesaje] = useState<Mesaj[]>([])
  const [seTrimite, setSeTrimite] = useState(false)
  const [seIncarca, setSeIncarca] = useState(false)
  const [lipsa, setLipsa] = useState(false)
  const [eroareConv, setEroareConv] = useState<string | null>(null)
  const [sertarConv, setSertarConv] = useState(false)
  const [cerere, setCerere] = useState<CerereSertar | null>(null)
  // conversația creată chiar acum de prima întrebare: e deja în `mesaje`, nu se recitește
  const creata = useRef<string | null>(null)
  // conversația afișată acum, pentru un răspuns care sosește după un „Înapoi”: fără ea, răspunsul unei
  // conversații noi muta adresa pe ea, cu turele altei conversații pe ecran (revizia, 07.10.2026)
  const afisata = useRef(c)
  afisata.current = c
  const capat = useRef<HTMLDivElement>(null)

  const mergi = (k: Record<string, string | null>, inIstoric = false) =>
    setSp((p) => {
      const n = new URLSearchParams(p)
      for (const [cheie, v] of Object.entries(k)) {
        if (v) n.set(cheie, v)
        else n.delete(cheie)
      }
      return n
    }, { replace: !inIstoric })

  // tura nouă apare jos, deasupra câmpului fix: pagina coboară după ea
  useEffect(() => {
    if (mesaje.length) capat.current?.scrollIntoView({ block: 'end', behavior: 'smooth' })
  }, [mesaje])

  // conversația din adresă (clic în coloană, link, înapoi/înainte): se citește din fișier, fără model
  useEffect(() => {
    if (c && c === creata.current) {
      creata.current = null
      return
    }
    setMesaje([])
    setEroareConv(null)
    setSeIncarca(false)
    if (!c) return
    let anulat = false
    setLipsa(false)
    setSeIncarca(true)
    citesteConversatia(c)
      .then((conv) => {
        if (!anulat) setMesaje(conv.ture.map((x, i) => ({ id: i + 1, intrebare: x.intrebare, data: x.data, raspuns: x.raspuns })))
      })
      .catch((e: unknown) => {
        if (anulat) return
        if (e instanceof ApiError && e.status === 404) {
          setLipsa(true)
          mergi({ c: null })
          return
        }
        const mesaj = (e as Error).message
        setEroareConv(mesaj === SERVER_OPRIT ? t('comun.server_oprit') : deLaServer(mesaj, lang))
      })
      .finally(() => {
        if (!anulat) setSeIncarca(false)
      })
    return () => {
      anulat = true
    }
  }, [c])

  const err = meta.error ?? stare.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !stare.data) return <SeIncarca />
  const m = meta.data
  const st = stare.data
  const poate = st.activ && !seTrimite && !seIncarca
  const cost = mesaje.reduce((s, x) => s + (x.raspuns?.cost_usd ?? 0), 0)
  const raspunse = mesaje.filter((x) => x.raspuns).length
  const titlu = conversatii.data?.find((x) => x.id === c)?.titlu ?? mesaje[0]?.intrebare ?? ''

  async function trimite(intrebare: string) {
    const q = intrebare.trim()
    if (!q || seTrimite || seIncarca || !st.activ) return
    // „și la BRD?” continuă ultima căutare reușită, nu o clarificare sau o eroare
    // și din clasamente: „și pentru firme?” continuă clasamentul de dinainte
    const anterior = [...mesaje].reverse().find((x) => ['cautare', 'clasament'].includes(x.raspuns?.interpretare.tip ?? ''))?.raspuns?.interpretare ?? null
    const id = Date.now()
    setLipsa(false)
    setMesaje((x) => [...x, { id, intrebare: q, data: new Date().toISOString() }])
    setSeTrimite(true)
    try {
      const r = await trimiteIntrebarea(q, anterior, c, st.token ?? '')
      // între timp s-a deschis altă conversație: răspunsul e în fișierul lui, lista îl arată
      if (afisata.current !== c) return
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, raspuns: r } : y)))
      setText('')
      if (r.conversatie && r.conversatie !== c) {
        creata.current = r.conversatie
        mergi({ c: r.conversatie })
      }
    } catch (e) {
      if (afisata.current !== c) return
      const mesaj = (e as Error).message
      const afisat = mesaj === SERVER_OPRIT ? t('comun.server_oprit') : deLaServer(mesaj, lang)
      setMesaje((x) => x.map((y) => (y.id === id ? { ...y, eroare: afisat } : y)))
      // serverul repornit are alt token: îl ia din nou, întrebarea rămâne în câmp
      if (mesaj.includes('token')) void stare.refetch()
    } finally {
      setSeTrimite(false)
      void qc.invalidateQueries({ queryKey: CHEIE_CONVERSATII })
    }
  }

  const intreaba = (q: string) => {
    setText(q)
    void trimite(q)
  }
  const deschide = (id: string) => {
    setSertarConv(false)
    if (id !== c) mergi({ c: id }, true)
  }
  const noua = () => {
    setSertarConv(false)
    setText('')
    setMesaje([])
    setLipsa(false)
    if (c) mergi({ c: null }, true)
  }
  const redenumeste = async (id: string, titluNou: string) => {
    await redenumesteConversatia(id, titluNou, st.token ?? '')
    await qc.invalidateQueries({ queryKey: CHEIE_CONVERSATII })
  }
  const sterge = async (id: string) => {
    await stergeConversatia(id, st.token ?? '')
    if (id === c) noua()
    await qc.invalidateQueries({ queryKey: CHEIE_CONVERSATII })
  }
  const coloana = (inSertar: boolean) => (
    <Conversatii
      lista={conversatii.data}
      eroare={!!conversatii.error}
      deschisa={c}
      cauta={cauta}
      blocat={seTrimite}
      poateModifica={!!st.token}
      inSertar={inSertar}
      onCauta={(q) => mergi({ cauta: q || null })}
      onDeschide={deschide}
      onNoua={noua}
      onRedenumeste={redenumeste}
      onSterge={sterge}
    />
  )

  return (
    <div className="vox">
      {coloana(false)}
      <div className="vox-chat">
        {!st.activ && <div className="callout warn">{t('vox.oprit')}</div>}
        <Button className="vox-istoric-btn" icon={<HistoryOutlined />} onClick={() => setSertarConv(true)}>
          {t('vox.conv.istoric_btn', { n: conversatii.data?.length ?? 0 })}
        </Button>
        {lipsa && <div className="callout warn">{t('vox.conv.lipsa')}</div>}
        {eroareConv && <div className="callout warn">{eroareConv}</div>}
        {c && mesaje.length > 0 && (
          <div className="vox-conv-cap">
            <b>{titlu}</b>
            <span>
              {tn('vox.conv.n_intrebari', raspunse)} · {dolari(cost, locale)} · {cand(mesaje[0]!.data, 'vox.conv.inceputa', t, locale)}
            </span>
          </div>
        )}
        {seIncarca && <div className="vox-bula vox-gandeste">{t('vox.conv.se_incarca')}</div>}
        {!seIncarca && mesaje.length === 0 && <BunVenit banci={Object.keys(m.nume).length} poate={poate} onExemplu={intreaba} />}
        {mesaje.map((x) => (
          <div key={x.id} className="vox-tura">
            <span className="vox-ora">{cand(x.data, 'vox.conv.ora', t, locale)}</span>
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
              placeholder={t(mesaje.length ? 'vox.placeholder_continua' : 'vox.placeholder')}
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
                ? t('vox.subsol_conversatie', { model: st.model, cost: dolari(cost, locale) })
                : t('vox.subsol_gol', { model: st.model })}
            </span>
          </div>
        </div>
      </div>
      <Drawer open={sertarConv} onClose={() => setSertarConv(false)} placement="left" width={320} title={t('vox.conv.titlu_coloana')}>
        {coloana(true)}
      </Drawer>
      <Sertar cerere={cerere} onClose={() => setCerere(null)} />
    </div>
  )
}

/** Ce vede cine deschide pagina: ce face Vox și câteva întrebări care chiar găsesc valori. */
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
          {EXEMPLE.slice(0, 3).map((e) => (
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
    i.segment && etSegment(i.segment, t),
    i.metrica === 'cea_mai_buna' && t('vox.clasament.metrica.cea_mai_buna'),
  ].filter((x): x is string => !!x)
  const inteles = (
    <div className="vox-inteles">
      <span className="vox-et">{t('vox.am_inteles')}</span>
      {i.tip === 'clasament' && <span className="vox-chip">{t('vox.clasament.chip')}</span>}
      {i.banci.map((b) => <span key={b} className="vox-chip banca">{m.nume[b] ?? b}</span>)}
      <span className="vox-chip">{i.concept ? etNume(i.concept, t) : t('vox.text_chip', { text: i.text_cautat ?? '' })}</span>
      {filtre.map((f) => <span key={f} className="vox-chip">{f}</span>)}
    </div>
  )
  if (i.tip === 'clasament') {
    return (
      <article className="vox-card">
        {inteles}
        {r.clasament && <Clasament c={r.clasament} m={m} onDovezi={onDovezi} />}
        <div className="vox-card-jos">{subsol}</div>
      </article>
    )
  }
  return (
    <article className="vox-card">
      {inteles}
      {r.ignorate.length > 0 && (
        <p className="vox-nota"><span className="vox-punct" />{t('vox.ignorate', { banci: r.ignorate.map((b) => m.nume[b] ?? b).join(', ') })}</p>
      )}
      {r.raspunsuri.map((rb) => <FisaBanca key={rb.banca} rb={rb} i={i} m={m} onDovezi={onDovezi} />)}
      <div className="vox-card-jos">{subsol}</div>
    </article>
  )
}

function FisaBanca({ rb, i, m, onDovezi }: { rb: RaspunsBanca; i: Interpretare; m: Meta; onDovezi: (c: CerereSertar) => void }) {
  const { t, tn } = useLang()
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
    const motiv = !rb.stare_banca && rb.blocaje ? textBlocaje(rb.blocaje, tn, !!rb.fara_filtre) : ''
    return (
      <div className="vox-fisa">
        {cap}
        <div className="vox-gol">
          <p>
            <b>{t('vox.zero', { concept: filtre ? `${concept} · ${filtre}` : concept, banca: m.nume[rb.banca] ?? rb.banca })}</b>
            {rb.stare_banca && <> {t(rb.stare_banca === 'blocata' ? 'vox.stare.blocata' : 'vox.stare.fara_surse')}</>}
            {motiv && <> {motiv}</>}
            {!!rb.fara_filtre && <> {tn('vox.fara_filtre', rb.fara_filtre)}</>}
            {' '}{t('vox.lipsa_nu_inseamna')}
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
  const relaxate = rb.filtre_relaxate ?? []
  // sertarul cere filtrele pe care s-au găsit rândurile: cu termenul cerut de om, după o cădere pe
  // „termen nespecificat”, s-ar deschide gol
  const termen = relaxate.includes('termen') ? 'necunoscut' : (i.termen ?? '')
  const produs = relaxate.includes('produs') ? 'altele' : (i.produs_credit ?? '')
  const nota = notaRelaxata(relaxate, rb.total, i, t, tn)
  // segmentul se arată doar când sursele îl spun: la dobânzi niciun rând nu-l are, iar „fără segment
  // în sursă” pe fiecare răspuns ar fi zgomot
  const cuSegmente = rb.rezumat.some((g) => g.segment) || rb.randuri.some((v) => v.segment)
  // categoria spune ceva doar când grupele diferă (dobândă de depozit vs. de credit)
  const multeCategorii = new Set(rb.rezumat.map((g) => g.categorie)).size > 1
  const vizibile = toate ? rb.randuri : rb.randuri.slice(0, PRIMELE)
  const alte = rb.alte ?? []
  // „Vezi dovezile” de pe o grupă: aceeași bancă, concept, unitate și tip; la dobânzi, și moneda grupei
  const dovezi = (g: GrupaRezumat) => (rb.mod === 'concept' && i.concept ? () => onDovezi({
    banca: rb.banca, camp: i.concept!, unitate: g.unitate, scenariu: g.categorie, termen, produs,
    ...(cuSegmente ? { segment: g.segment ?? 'nemarcat', strict: true } : {}),
    ...(g.moneda !== undefined ? { valuta: g.moneda ?? 'nespusa' } : {}),
  }) : undefined)
  return (
    <div className="vox-fisa">
      {cap}
      {nota && <p className="vox-nota"><span className="vox-punct" />{nota}</p>}
      {peSegmente(rb.rezumat).map(([s, grupe]) => (
        <div key={s ?? '-'} className="vox-segment">
          {cuSegmente && <span className="vox-segment-cap">{etSegment(s, t)}</span>}
          <div className="vox-kpis">
            {grupe.map((g) => (
              <PlacaRezumat key={`${g.unitate}|${g.categorie}|${g.moneda ?? ''}`} g={g} multeCategorii={multeCategorii} onDovezi={dovezi(g)} />
            ))}
          </div>
        </div>
      ))}
      {!rb.rezumat.length && alte.length > 0 && (
        <p className="vox-nota"><span className="vox-punct" />{textDoarAlte(alte, i, t)}</p>
      )}
      {alte.length > 0 && (
        <div className="vox-segment vox-alte">
          <span className="vox-segment-cap">{t('vox.alte.titlu')}</span>
          <div className="vox-kpis">
            {/* Garanti · schimbarea PIN-ului: cele două carduri „limită” (6 PF, 1 IMM) nu se deosebeau (mip_merge, 08.10.2026) */}
            {alte.map((g) => (
              <PlacaRezumat key={`${g.segment ?? ''}|${g.unitate}|${g.categorie}`} g={g} multeCategorii tip
                segment={cuSegmente ? g.segment : undefined} onDovezi={dovezi(g)} />
            ))}
          </div>
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


/** Grupele rezumatului, pe segmente consecutive: serverul le trimite deja în ordinea PF, PFA, IMM, PJ,
 * fără segment. În conversațiile vechi grupele n-au `segment`, deci ies toate într-un singur bloc. */
function peSegmente(rezumat: GrupaRezumat[]): [string | null, GrupaRezumat[]][] {
  const blocuri: [string | null, GrupaRezumat[]][] = []
  for (const g of rezumat) {
    const s = g.segment ?? null
    const ultim = blocuri[blocuri.length - 1]
    if (ultim && ultim[0] === s) ultim[1].push(g)
    else blocuri.push([s, [g]])
  }
  return blocuri
}

/** Ce filtru a căzut pe „nespecificat în sursă” și câte valori au rămas (app/vox.py, `_raspuns`). */
function notaRelaxata(relaxate: string[], n: number, i: Interpretare, t: Tr, tn: Tn): string | null {
  const termen = i.termen ? eticheta(`vox.termen.${i.termen}`, i.termen, t) : ''
  const produs = i.produs_credit ? eticheta(`vox.produs.${i.produs_credit}`, i.produs_credit, t) : ''
  if (relaxate.length === 2) return tn('vox.relaxat.ambele', n, { termen, produs })
  if (relaxate[0] === 'termen') return tn('vox.relaxat.termen', n, { termen })
  if (relaxate[0] === 'produs') return tn('vox.relaxat.produs', n, { produs })
  return null
}

/** De ce n-are banca valori, cu cifrele din `surse` (app/server.py, `_stare_banca_vox`). */
function textBlocaje(b: NonNullable<RaspunsBanca['blocaje']>, tn: Tn, cuValoriFaraFiltre: boolean): string {
  const parti = [
    b.robots > 0 ? tn('vox.blocaje.robots', b.robots, { surse: b.surse }) : '',
    b.refuzate > 0 ? tn('vox.blocaje.refuzate', b.refuzate, { surse: b.surse }) : '',
    b.pdf > 0 ? tn('vox.blocaje.pdf', b.pdf) : '',
  ].filter(Boolean)
  if (parti.length) return parti.join(' ')
  // cu valori fără filtru, „valoarea n-a apărut în sursele colectate” contrazicea propoziția următoare,
  // care le numără: Raiffeisen · depozit 1–3 luni, 3 valori pe alte termene (mip_merge, 07.10.2026)
  return cuValoriFaraFiltre ? '' : tn('vox.blocaje.niciuna', b.surse)
}

/** „Nicio valoare de comision; am găsit doar limite (7).”: Garanti · schimbarea PIN-ului (mip_merge, 08.10.2026). */
function textDoarAlte(alte: GrupaRezumat[], i: Interpretare, t: Tr): string {
  const n = alte.reduce((s, g) => s + g.n, 0)
  const tipuri = [...new Set(alte.map((g) => g.categorie))].map((c) => eticheta(`vox.alte.tipuri.${c}`, c, t)).join(', ')
  return t('vox.alte.doar', { ce: t(i.categorie ? 'vox.alte.ce_dobanda' : 'vox.alte.ce_comision'), tipuri, n })
}

/** Eticheta unei frecvențe din date („lunar”, „pe tranzacție”); una necunoscută rămâne cum e în date. */
function etFrecventa(f: string | null, t: Tr): string {
  if (!f) return t('vox.frecventa.fara')
  const k = f.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim().replace(/\s+/g, '_')
  return eticheta(`vox.frecventa.${k}`, f, t)
}

function PlacaRezumat({ g, multeCategorii, tip, segment, onDovezi }: {
  g: GrupaRezumat; multeCategorii: boolean; tip?: boolean; segment?: string | null; onDovezi?: () => void
}) {
  const { t, tn, locale } = useLang()
  const unitate = unitTxt(g.unitate, t).trim()
  const egal = g.minim === g.maxim
  const interval = (a: number, b: number) => (a === b ? num(a, locale) : `${num(a, locale)} – ${num(b, locale)}`)
  return (
    <div className="vox-kpi">
      {g.frecvente?.length
        ? (
          // BCR · administrare cont PF: „0 – 1.200 lei” punea 6 sume anuale lângă 16 lunare (08.10.2026)
          <span className="vox-frecvente">
            {g.frecvente.map((f) => (
              <span key={f.frecventa ?? '-'}>
                <b>{interval(f.minim, f.maxim)}{unitate && <small> {unitate}</small>}</b>
                {' '}{etFrecventa(f.frecventa, t)} · {tn('vox.kpi', f.n)}
              </span>
            ))}
          </span>
        )
        : (
          <span className="v">
            {interval(g.minim, g.maxim)}
            {unitate && <small> {unitate}</small>}
          </span>
        )}
      <span className="l">
        {egal && g.n > 1 ? tn('vox.kpi_egal', g.n) : tn('vox.kpi', g.n)}
        {g.gratuite > 0 && <> · {tn('vox.gratuite', g.gratuite)}</>}
        {g.moneda !== undefined && <> · {eticheta(`vox.moneda.${g.moneda ?? 'nespusa'}`, g.moneda ?? '', t)}</>}
        {(multeCategorii || tip) && <> · {eticheta(tip ? `vox.tip.${g.categorie}` : `vox.categorie.${g.categorie}`, g.categorie, t)}</>}
        {segment && <> · {segment.toUpperCase()}</>}
      </span>
      {onDovezi && <button type="button" className="vox-link" onClick={onDovezi}>{t('vox.vezi_dovezi')}</button>}
    </div>
  )
}

/** Un rând: serviciul și condiția băncii (date, netraduse), valoarea, dovada. */
function Rand({ v }: { v: ValoareDovada }) {
  const { t, locale } = useLang()
  const valoare = v.valoare !== null ? num(v.valoare, locale) + unitTxt(v.unitate, t) : (v.valoare_text ?? '—')
  return (
    <tr className={v.ambiguu ? 'ambiguu' : undefined}>
      <td>
        {v.serviciu ?? '—'}{v.conditie && <span className="sub">{v.conditie}</span>}
        {v.segment && <span className="vox-seg"><PillSegment segment={v.segment} /></span>}
        {v.tip_alt && <span className="vox-seg"><Pill>{eticheta(`vox.tip.${v.tip_alt}`, v.tip_alt, t)}</Pill></span>}
      </td>
      <td className="dr val">
        {valoare}{v.frecventa && <span className="sub">{v.frecventa}</span>}
        {v.data_vigoare && <span className="sub">{t('vox.din_data', { data: formatZi(v.data_vigoare, locale) })}</span>}
      </td>
      <td>
        {v.ambiguu && <><Pill tip="amb" title={v.motiv_ambiguu ?? undefined}>{t('vox.ambiguu')}</Pill>{' '}</>}
        <LinkSursa r={v} />
      </td>
    </tr>
  )
}
