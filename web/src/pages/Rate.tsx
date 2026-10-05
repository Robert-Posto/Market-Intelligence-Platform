import { useMemo, useState, type ReactNode } from 'react'
import { Input, Segmented, Select } from 'antd'
import { Link, useSearchParams } from 'react-router-dom'
import type { Indici, Rate as RateT } from '@mcc/shared'
import { useMeta } from '../api/meta'
import { useIndici, useRate } from '../api/rate_mobil'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../components/comune'
import Sertar, { type CerereSertar } from '../components/Sertar'
import { Tabel, type Coloana } from '../components/Tabel'
import { etDesc, etNume } from '../components/valori'
import { T, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { faraDiacritice, num } from '../util/format'
import '../styles/rate_mobil.css'

type CelulaRata = RateT['celule'][number]

const CATEGORII: [string, DictKey][] = [
  ['depozite', 'rate.tab_depozite'],
  ['credite', 'rate.tab_credite'],
  ['conturi_carduri', 'rate.tab_conturi_carduri'],
]

/**
 * Cea mai bună valoare pe coloană: doar un câștigător UNIC cu cel puțin
 * MIN_VALORI valori colectate. Altfel „cel mai bun” ar fi banca despre care
 * știm cel mai puțin.
 */
const MIN_VALORI = 3

/**
 * 2.2 Rate & indicatori: dobânda tipică a fiecărei bănci (mediana), pe categorie,
 * cu termenul (depozite) și produsul (credite) ca filtre — fără ele, mediana
 * amestecă 4 luni cu 12 luni și un ipotecar cu rate în magazine.
 */
export default function Rate() {
  const { t, tn, lang, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const cat = sp.get('categorie') || 'depozite'
  const termen = sp.get('termen') || ''
  const produs = sp.get('produs') || ''
  const [cauta, setCauta] = useState('')
  const [sertar, setSertar] = useState<CerereSertar | null>(null)
  const meta = useMeta()
  const q = useRate(cat, termen, produs)
  const indici = useIndici()

  const pe = useMemo(() => {
    const o: Record<string, Record<string, CelulaRata>> = {}
    for (const c of q.data?.celule ?? []) (o[c.banca] ??= {})[c.camp] = c
    return o
  }, [q.data])

  if (q.error) return <Eroare e={q.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (indici.error) return <Eroare e={indici.error} />
  if (!q.data || !meta.data || !indici.data) return <SeIncarca />
  const d = q.data
  const m = meta.data
  const mare = d.sens === 'mare_bun'
  const banci = Object.keys(pe)
  const campuri = d.campuri.filter((cp) => banci.some((b) => pe[b]![cp]))

  const best: Record<string, string> = {}
  for (const cp of campuri) {
    const cel = banci.map((b) => pe[b]![cp]).filter((c): c is CelulaRata => !!c && c.valoare !== null)
    if (!cel.length) continue
    const vals = cel.map((c) => c.valoare!)
    const ext = mare ? Math.max(...vals) : Math.min(...vals)
    const egali = cel.filter((c) => c.valoare === ext)
    if (egali.length === 1 && egali[0]!.n >= MIN_VALORI) best[cp] = egali[0]!.banca
  }

  /* Frecvența e text liber din sursă („pe 30 ani”, „primii 3 ani”): se arată
     cum vine, nu se traduce într-un termen care ar putea minți. */
  const termenTxt = (c: CelulaRata) =>
    c.luni
      ? c.luni % 12 === 0 && c.luni >= 12 ? tn('rate.termen_ani', c.luni / 12) : tn('rate.termen_luni', c.luni)
      : c.frecventa || ''

  // filtrele datelor afișate, nu ale adresei: cât vine răspunsul nou, pe ecran e încă cel vechi
  const deschide = (b: string, cp: string) =>
    setSertar({ banca: b, camp: cp, unitate: 'procent', scenariu: d.categorie, termen: d.termen, produs: d.produs })

  const eticheta = <span className="rt-best">{t('rate.cea_mai_buna')}</span>
  const colBanca: Coloana<string> = {
    cheie: 'banca', cap: t('rate.banca'), s: (b) => m.nume[b] ?? b, val: (b) => <EtichetaBanca slug={b} m={m} fisa tag />,
  }
  const cp0 = campuri[0]
  /* Un singur tip de dobândă (la depozite doar nominala: DAE și marja peste
     IRCC țin de credite): matricea ar avea o singură coloană de cifre, cu tot
     contextul înghesuit sub ea și gol în dreapta. Aici fiecare informație are
     coloana ei — dobânda, termenul, oferta, intervalul — pe toată lățimea. */
  const plat = campuri.length === 1 && cp0 !== undefined

  let tabel: ReactNode
  if (!banci.length) {
    tabel = (
      <div className="gol-stare">
        <b>{t('rate.gol_titlu')}</b>
        {termen ? `${t('rate.gol_termen_absent')} ` : ''}{t('rate.gol_incearca_toate')}
      </div>
    )
  } else if (plat) {
    // tot rândul deschide sertarul: clicul stă pe fiecare celulă; numele băncii (fișa) îl oprește
    const rand = (b: string) => ({ onClick: () => deschide(b, cp0) })
    const c = (b: string) => pe[b]![cp0]!
    const coloane: Coloana<string>[] = [
      { ...colBanca, td: rand },
      {
        cheie: cp0, num: true,
        cap: <>{etNume(cp0, t)}<span className="cap-d">{t('rate.cap_tipica_mediana')}</span></>,
        s: (b) => c(b).valoare,
        td: (b) => ({ ...rand(b), className: best[cp0] === b ? 'mc best' : 'mc' }),
        val: (b) => <><b>{num(c(b).valoare, locale)}%</b>{best[cp0] === b && eticheta}</>,
      },
      {
        cheie: 'termen', cap: t('rate.termen'), s: (b) => c(b).luni, td: rand,
        val: (b) => termenTxt(c(b)) || <span className="gri" title={t('rate.termen_nespecificat_title')}>{t('rate.nespecificat')}</span>,
      },
      {
        cheie: 'oferta', cap: t('rate.oferta'), s: (b) => c(b).serviciu, td: rand,
        val: (b) => <>{c(b).serviciu || '—'}{c(b).conditie && <span className="sub">{c(b).conditie!.slice(0, 110)}</span>}</>,
      },
      {
        cheie: 'interval', cap: t('rate.interval'), num: true, s: (b) => c(b).maxim, td: rand,
        val: (b) => (
          <span style={{ whiteSpace: 'nowrap' }}>
            {c(b).minim === c(b).maxim ? `${num(c(b).minim, locale)}%` : `${num(c(b).minim, locale)}–${num(c(b).maxim, locale)}%`}
          </span>
        ),
      },
      { cheie: 'valori', cap: t('rate.valori'), num: true, s: (b) => c(b).n, td: rand, val: (b) => num(c(b).n, locale, 0) },
    ]
    tabel = <TabelRate key={`plat|${d.categorie}|${d.termen}|${d.produs}`} banci={banci} m={m} cauta={cauta} coloane={coloane} implicit={[cp0, mare ? 'descend' : 'ascend']} clic />
  } else {
    const coloane: Coloana<string>[] = [
      colBanca,
      ...campuri.map((cp): Coloana<string> => ({
        cheie: cp,
        cap: <>{etNume(cp, t)}<span className="cap-d">{etDesc(cp, t)}</span></>,
        s: (b) => pe[b]![cp]?.valoare,
        td: (b) => {
          const x = pe[b]![cp]
          return x
            ? { className: best[cp] === b ? 'mc best' : 'mc', title: tn('rate.celula_title', x.n), onClick: () => deschide(b, cp) }
            : { className: 'gol' }
        },
        val: (b) => {
          const x = pe[b]![cp]
          if (!x) return '—'
          const serv = x.serviciu ? (x.serviciu.length > 34 ? x.serviciu.slice(0, 33) + '…' : x.serviciu) : ''
          const ctx = [termenTxt(x), serv].filter(Boolean).join(' · ')
          return (
            <>
              <b>{num(x.valoare, locale)}%</b>
              {best[cp] === b && eticheta}
              {ctx && <span className="sub ctx">{ctx}</span>}
              <span className="sub">
                {x.n > 1
                  ? t('rate.interval_valori_n', { minim: num(x.minim, locale), maxim: num(x.maxim, locale), n: num(x.n, locale, 0) })
                  : t('rate.interval_valori_1')}
              </span>
            </>
          )
        },
      })),
    ]
    tabel = <TabelRate key={`matrice|${d.categorie}|${d.termen}|${d.produs}`} banci={banci} m={m} cauta={cauta} coloane={coloane}
      implicit={cp0 ? [cp0, mare ? 'descend' : 'ascend'] : undefined} />
  }

  // pe categorie nouă, termenul și produsul se golesc: țin de categoria veche
  const mergi = (p: Record<string, string>) => setSp(Object.fromEntries(Object.entries(p).filter(([, v]) => v)))
  const necunoscut = d.termene.find((x) => x.cheie === 'necunoscut')?.n ?? 0
  const sens = <T k={mare ? 'rate.sens_mare' : 'rate.sens_mic'} />

  return (
    <>
      <div className="bara-fixa">
        <div className="filtre">
          <Segmented value={cat} onChange={(v) => mergi({ categorie: v })} options={CATEGORII.map(([v, k]) => ({ value: v, label: t(k) }))} />
          {cat === 'depozite' && (
            <label className="f">{t('rate.termen')}
              <Select value={termen} onChange={(v) => mergi({ categorie: cat, termen: v })} style={{ minWidth: 200 }} popupMatchSelectWidth={false}
                options={[
                  { value: '', label: t('rate.toate_termenele') },
                  ...d.termene.map((x) => ({ value: x.cheie, label: `${deLaServer(x.eticheta, lang)} (${num(x.n, locale, 0)})`, disabled: !x.n })),
                ]} />
            </label>
          )}
          {cat === 'credite' && (
            <label className="f">{t('rate.produs')}
              <Select value={produs} onChange={(v) => mergi({ categorie: cat, produs: v })} style={{ minWidth: 240 }} popupMatchSelectWidth={false}
                options={[
                  { value: '', label: t('rate.toate_produsele') },
                  ...d.produse.map((x) => ({ value: x.cheie, label: `${deLaServer(x.eticheta, lang)} (${num(x.n, locale, 0)})`, disabled: !x.n })),
                ]} />
            </label>
          )}
          <label className="f">{t('rate.cauta_banca')}
            <Input className="cauta" allowClear placeholder={t('rate.cauta_placeholder')} value={cauta} onChange={(e) => setCauta(e.target.value)} />
          </label>
          <Reper indici={indici.data} />
        </div>
      </div>
      <section style={{ opacity: q.isPlaceholderData ? 0.45 : 1 }}>
        <p className="note" style={{ margin: '0 0 10px' }}>
          <T k={plat ? (banci.length === 1 ? 'rate.nota_intro_plat_1' : 'rate.nota_intro_plat') : (banci.length === 1 ? 'rate.nota_intro_matrice_1' : 'rate.nota_intro_matrice')}
            params={{ n: banci.length, sens }} />{' '}
          {t(plat ? 'rate.clic_rand' : 'rate.clic_celula')}
          {cat === 'depozite' && !termen && <>{' '}<T k="rate.alege_termen" /></>}
          {cat === 'credite' && !produs && <>{' '}<T k="rate.alege_produs" /></>}
        </p>
        {tabel}
        <Despre>
          <T k="rate.despre_mediana" />
          <T k="rate.despre_termen" params={{ n: num(necunoscut, locale, 0) }} />
          <T k="rate.despre_produs" />
          {d.excluse_implauzibile > 0 && <T k="rate.despre_implauzibile" params={{ n: num(d.excluse_implauzibile, locale, 0), prag: num(d.prag, locale) }} />}
          {d.provenienta.length > 0 && (
            <T k="rate.colectat_de" params={{
              lista: d.provenienta.map((p) => (
                <Pill key={p.metoda}>{t('rate.provenienta_pill', { metoda: p.metoda, valori: num(p.valori, locale, 0), banci: num(p.banci, locale, 0) })}</Pill>
              )),
            }} />
          )}
        </Despre>
      </section>
      <Sertar cerere={sertar} onClose={() => setSertar(null)} />
    </>
  )
}

/**
 * Căutarea filtrează rândurile pe loc, fără cerere nouă (ca `cautaInTabel` din aplicația veche).
 * Cheia de deasupra (categoria, termenul și produsul datelor primite) reface tabelul la fiecare filtru, cu sortarea
 * implicită: la credite „mai mic e mai bine”, iar sortarea de la depozite ar fi pus dobânzile mari sus.
 */
function TabelRate({ banci, m, cauta, coloane, implicit, clic }: {
  banci: string[]
  m: { nume: Record<string, string> }
  cauta: string
  coloane: Coloana<string>[]
  implicit?: [string, 'ascend' | 'descend']
  clic?: boolean
}) {
  const c = faraDiacritice(cauta.trim())
  const vizibile = c ? banci.filter((b) => faraDiacritice(`${m.nume[b] ?? ''} ${b}`).includes(c)) : banci
  return (
    <Tabel randuri={vizibile} cheieRand={(b) => b} libra={(b) => b} implicit={implicit} coloane={coloane}
      clasaRand={clic ? () => 'clic' : undefined} />
  )
}

/** Indicii BNR sunt pe pagina 2.6; aici doar reperul pentru credite și depozite. */
function Reper({ indici }: { indici: Indici }) {
  const { t, locale } = useLang()
  const zi = (x: string | null) => String(x ?? '').slice(0, 10)
  const robor = indici.filter((x) => x.indice === 'robor')
  const ultimaZi = robor.map((x) => zi(x.valabil_din)).sort().pop()
  const r3 = robor.find((x) => x.scadenta === '3M' && zi(x.valabil_din) === ultimaZi)
  const azi = new Date().toISOString().slice(0, 10)
  const ircc = indici.filter((x) => x.indice === 'ircc' && zi(x.valabil_din) <= azi && (!x.valabil_pana || zi(x.valabil_pana) >= azi))[0]
  const v = (x: Indici[number]) => `${num(x.valoare === null ? null : Number(x.valoare), locale)}%`
  return (
    <span className="note rt-reper">
      {r3 && <>ROBOR 3M <b>{v(r3)}</b></>}
      {ircc && <>{r3 ? ' · ' : ''}IRCC <b>{v(ircc)}</b></>}
      {' '}<Link to="/context">{t('rate.link_indici_bnr')}</Link>
    </span>
  )
}
