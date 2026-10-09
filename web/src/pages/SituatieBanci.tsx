import { useMemo } from 'react'
import { Select, Tooltip as Tip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { BancaSituatie, IndicatoriSituatie, SituatiiBanci } from '@mcc/shared'
import { useMeta, type Meta } from '../api/meta'
import { useSituatiiBanci } from '../api/situatii_banci'
import { Despre, EtichetaBanca, Eroare, Pill, SeIncarca } from '../components/comune'
import { Comutator } from '../components/Comutator'
import { Tabel, type Coloana } from '../components/Tabel'
import { T, useLang, type DictKey } from '../i18n'
import { num } from '../util/format'
import '../styles/situatie_banci.css'

type Disponibil = Extract<SituatiiBanci, { disponibil: true }>
type Indicator = keyof Pick<IndicatoriSituatie, 'active' | 'credite' | 'datorii' | 'numerar' | 'capital_social' | 'profit_net' | 'profit_brut'>

const INDICATORI: Indicator[] = ['active', 'credite', 'datorii', 'numerar', 'capital_social', 'profit_net', 'profit_brut']
/** profitul și capitalul se citesc în milioane; restul, în miliarde (BT are ~150 mld lei active, Libra ~14) */
const IN_MILIOANE: Indicator[] = ['capital_social', 'profit_net', 'profit_brut']
const LIBRA_CUI = 8119644
/** Libra + cel mult 7: atâtea culori categoriale trec validarea de contrast și daltonism (paleta din CSS) */
const MAX_ALESE = 7
const PRESETATE = [5022670, 361757, 361579] // BT, BCR, BRD: prima vedere are cu cine compara

/**
 * Situația băncilor: bilanțul și profitul fiecărei instituții de credit din 2012 încoace, din
 * situațiile financiare depuse la MF (ingest/situatii_financiare_mf.py). Libra e mereu pe grafic;
 * celelalte bănci, indicatorul și modul (valoare sau cotă de piață) stau în adresă. Valoarea se vede
 * pe ani (linii); cota de piață, ca parte din sector într-un singur an (donut), anul stând tot în adresă.
 */
export default function SituatieBanci() {
  const q = useSituatiiBanci()
  const meta = useMeta()
  if (q.error) return <Eroare e={q.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (!q.data || !meta.data) return <SeIncarca />
  if (!q.data.disponibil) return <section><p className="note"><T k="sb.nedisponibil" params={{ motiv: q.data.motiv }} /></p></section>
  return <Vedere d={q.data} m={meta.data} />
}

function Vedere({ d, m }: { d: Disponibil; m: Meta }) {
  const { t, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const ind = (INDICATORI as string[]).includes(sp.get('ind') ?? '') ? (sp.get('ind') as Indicator) : 'active'
  const mod = sp.get('mod') === 'cota' ? 'cota' : 'valoare'
  const anCota = d.ani.map(String).includes(sp.get('an') ?? '') ? sp.get('an')! : String(d.ani[d.ani.length - 1])
  const ent = sp.get('vezi') === 'active' || sp.get('vezi') === 'toate' ? sp.get('vezi')! : 'monitorizate'
  const pe = useMemo(() => new Map(d.banci.map((b) => [b.cui, b])), [d.banci])
  const alese = (sp.get('banci') !== null ? (sp.get('banci') ?? '').split(',').filter(Boolean).map(Number) : PRESETATE)
    .filter((c) => c !== LIBRA_CUI && pe.has(c)).slice(0, MAX_ALESE)
  const mergi = (o: Record<string, string>) => setSp((p) => {
    const n = new URLSearchParams(p)
    for (const [k, v] of Object.entries(o)) n.set(k, v)
    return n
  }, { replace: true })

  const ani = d.ani
  const ultim = String(ani[ani.length - 1])
  const nume = (b: BancaSituatie) => (b.slug && m.nume[b.slug]) || b.nume
  const val = (b: BancaSituatie, an: number | string, i: Indicator = ind) => b.valori[String(an)]?.[i] ?? null
  const cota = (b: BancaSituatie, an: number | string, i: Indicator = ind) => {
    const v = val(b, an, i)
    const tot = d.total[String(an)]?.[i]
    return v === null || !tot ? null : (100 * v) / tot
  }
  const mil = IN_MILIOANE.includes(ind)
  const unitate = mod === 'cota' ? '%' : t(mil ? 'sb.u.mil' : 'sb.u.mld')
  const scala = (v: number | null) => (v === null ? null : mod === 'cota' ? v : v / (mil ? 1e6 : 1e9))
  const fmt = (v: number | null | undefined) =>
    v === null || v === undefined ? '—' : `${num(v, locale, mod === 'cota' ? 2 : mil ? 1 : 2)}${mod === 'cota' ? '%' : ' ' + unitate}`

  // graficul: un rând pe an, o coloană pe bancă (cheia e CUI-ul: băncile istorice n-au slug)
  const libra = pe.get(LIBRA_CUI)!
  const serii = [libra, ...alese.map((c) => pe.get(c)!)]
  const date = ani.map((an) => Object.fromEntries([['an', an], ...serii.map((b) => [String(b.cui), scala(mod === 'cota' ? cota(b, an) : val(b, an))])]))

  // donutul cotei pe anul ales: Libra, băncile alese (culoarea după poziția în listă, ca pe linii;
  // o bancă fără date în acel an lipsește) și restul sectorului. O cotă negativă (bancă pe pierdere)
  // nu încape într-un cerc: atunci rămân liniile, cu o notă.
  const felii = serii.map((b, i) => ({ cheie: String(b.cui), nume: nume(b), i, cota: cota(b, anCota), valoare: val(b, anCota) }))
    .filter((f): f is typeof f & { cota: number; valoare: number } => f.cota !== null && f.valoare !== null)
  const restCota = 100 - felii.reduce((s, f) => s + f.cota, 0)
  const restN = d.banci.filter((b) => val(b, anCota) !== null).length - felii.length
  const pie = mod === 'cota' && felii.every((f) => f.cota >= 0) && restCota >= -0.005
  const fmtValoare = (v: number) => `${num(v / (mil ? 1e6 : 1e9), locale, mil ? 1 : 2)} ${t(mil ? 'sb.u.mil' : 'sb.u.mld')}`

  // reperele Libra pe ultimul an: active, cotă și loc, profit, creștere față de piață pe 5 ani
  const activeUltim = d.banci.filter((b) => val(b, ultim, 'active') !== null)
    .sort((a, b) => (val(b, ultim, 'active') ?? 0) - (val(a, ultim, 'active') ?? 0))
  const loc = activeUltim.findIndex((b) => b.cui === LIBRA_CUI) + 1
  const an5 = String(Number(ultim) - 5)
  const cagr = (v0: number | null | undefined, v1: number | null | undefined, n: number) =>
    v0 && v1 && v0 > 0 && v1 > 0 && n > 0 ? 100 * ((v1 / v0) ** (1 / n) - 1) : null
  const crLibra = cagr(val(libra, an5, 'active'), val(libra, ultim, 'active'), 5)
  const crPiata = cagr(d.total[an5]?.active, d.total[ultim]?.active, 5)

  // tabelul de evoluție: băncile alese din filtru, cu valorile pe ani în indicatorul și modul curent
  const randuri = d.banci.filter((b) => ent === 'toate' || (ent === 'monitorizate' ? !!b.slug && b.ultimul_an === Number(ultim)
    : b.ultimul_an === Number(ultim) && b.tip !== 'cooperativa'))
  const primAn = (b: BancaSituatie) => String(Math.max(b.primul_an, ani[0]!))
  const colEvolutie: Coloana<BancaSituatie>[] = [
    { cheie: 'banca', cap: t('sb.col.banca'), s: nume, val: (b) => <NumeBanca b={b} m={m} /> },
    ...ani.map((an) => ({
      cheie: String(an), cap: String(an), num: true,
      s: (b: BancaSituatie) => (mod === 'cota' ? cota(b, an) : val(b, an)),
      // doar cifra: unitatea stă o dată deasupra tabelului, nu în fiecare din cele ~400 de celule
      val: (b: BancaSituatie) => {
        const x = scala(mod === 'cota' ? cota(b, an) : val(b, an))
        return <span className="mono">{x === null ? '—' : num(x, locale, mod === 'cota' ? 2 : mil ? 1 : 2)}</span>
      },
    })),
    {
      cheie: 'cagr', cap: t('sb.col.cagr'), titlu: t('sb.col.cagr_titlu'), num: true,
      s: (b) => cagr(val(b, primAn(b)), val(b, b.ultimul_an), b.ultimul_an - Number(primAn(b))),
      val: (b) => {
        const x = cagr(val(b, primAn(b)), val(b, b.ultimul_an), b.ultimul_an - Number(primAn(b)))
        return <span className="mono">{x === null ? '—' : `${num(x, locale, 1)}%`}</span>
      },
    },
    {
      cheie: 'dcota', cap: t('sb.col.dcota'), titlu: t('sb.col.dcota_titlu'), num: true,
      s: (b) => { const a = cota(b, primAn(b)); const z = cota(b, b.ultimul_an); return a === null || z === null ? null : z - a },
      val: (b) => {
        const a = cota(b, primAn(b))
        const z = cota(b, b.ultimul_an)
        if (a === null || z === null) return '—'
        const x = z - a
        return <span className={`mono ${x > 0 ? 'sb-plus' : x < 0 ? 'sb-minus' : ''}`}>{x > 0 ? '+' : ''}{num(x, locale, 2)} pp</span>
      },
    },
  ]
  const colMapare: Coloana<BancaSituatie>[] = [
    { cheie: 'cui', cap: t('sb.col.cui'), s: (b) => b.cui, val: (b) => <span className="mono">{b.cui}</span> },
    { cheie: 'denumire', cap: t('sb.col.denumire'), s: (b) => b.nume, val: (b) => b.nume },
    { cheie: 'monitorizata', cap: t('sb.col.monitorizata'), s: (b) => b.slug ?? '', val: (b) => (b.slug ? <EtichetaBanca slug={b.slug} m={m} fisa /> : <span className="gri">—</span>) },
    { cheie: 'tip', cap: t('sb.col.tip'), s: (b) => b.tip, val: (b) => t(`sb.tip.${b.tip}` as DictKey) },
    { cheie: 'ani', cap: t('sb.col.ani'), s: (b) => b.primul_an, val: (b) => <span className="mono">{b.primul_an}–{b.ultimul_an}</span> },
    {
      cheie: 'stare', cap: t('sb.col.stare'), s: (b) => b.ultimul_an,
      val: (b) => (b.ultimul_an === Number(ultim) ? <Pill tip="ok">{t('sb.stare.activa')}</Pill> : <Pill>{t('sb.stare.iesita', { an: b.ultimul_an })}</Pill>),
    },
  ]
  const optiuni = d.banci.filter((b) => b.cui !== LIBRA_CUI && b.ultimul_an >= Number(ultim) - 1)
    .sort((a, b) => (val(b, ultim, 'active') ?? 0) - (val(a, ultim, 'active') ?? 0))
    .map((b) => ({ value: b.cui, label: nume(b) }))

  return (
    <>
      <div className="bara-fixa">
        <div className="filtre sb-filtre">
          <Comutator<string> value={mod} onChange={(v) => mergi({ mod: v })}
            options={[{ value: 'valoare', label: t('sb.mod.valoare') }, { value: 'cota', label: t('sb.mod.cota') }]} />
          <label className="f">{t('sb.filtru.indicator')}
            <Select value={ind} onChange={(v) => mergi({ ind: v })} style={{ minWidth: 230 }} popupMatchSelectWidth={false}
              options={INDICATORI.map((i) => ({ value: i, label: t(`sb.ind.${i}` as DictKey) }))} />
          </label>
          {mod === 'cota' && (
            <label className="f">{t('sb.filtru.an')}
              <Select value={anCota} onChange={(v) => mergi({ an: v })} style={{ minWidth: 96 }}
                options={[...ani].reverse().map((a) => ({ value: String(a), label: String(a) }))} />
            </label>
          )}
          <label className="f sb-banci">{t('sb.filtru.banci')}
            <Select<number[]> mode="multiple" value={alese} allowClear showSearch optionFilterProp="label" maxCount={MAX_ALESE}
              placeholder={t('sb.filtru.banci_placeholder', { n: MAX_ALESE })} options={optiuni}
              onChange={(v) => mergi({ banci: v.join(',') })} />
          </label>
        </div>
      </div>

      <div className="kpi sb-kpi">
        <div>
          <div className="e">{t('sb.kpi.active', { an: ultim })}</div>
          <div className="n">{num((val(libra, ultim, 'active') ?? 0) / 1e9, locale, 2)} <span className="gri sb-u">{t('sb.u.mld')}</span></div>
          <div className="l">{t('sb.kpi.cota', { cota: num(cota(libra, ultim, 'active') ?? 0, locale, 2) })}</div>
        </div>
        <div>
          <div className="e">{t('sb.kpi.loc_titlu')}</div>
          <div className="n">{loc}<span className="gri sb-u"> / {activeUltim.length}</span></div>
          <div className="l">{t('sb.kpi.loc_desc', { an: ultim })}</div>
        </div>
        <div>
          <div className="e">{t('sb.kpi.profit', { an: ultim })}</div>
          <div className="n">{num((val(libra, ultim, 'profit_net') ?? 0) / 1e6, locale, 1)} <span className="gri sb-u">{t('sb.u.mil')}</span></div>
          <div className="l">{t('sb.kpi.cota', { cota: num(cota(libra, ultim, 'profit_net') ?? 0, locale, 2) })}</div>
        </div>
        <div>
          <div className="e">{t('sb.kpi.crestere', { de_la: an5, pana_la: ultim })}</div>
          <div className="n">{crLibra === null ? '—' : `${num(crLibra, locale, 1)}%`}<span className="gri sb-u"> {t('sb.kpi.pe_an')}</span></div>
          <div className="l">{t('sb.kpi.crestere_desc', { piata: crPiata === null ? '—' : num(crPiata, locale, 1) })}</div>
        </div>
      </div>

      <section>
        <h2 className="sb-titlu">{t(`sb.ind.${ind}` as DictKey)} <span className="gri">· {mod === 'cota' ? t('sb.grafic_cota') : unitate} · {pie ? anCota : `${ani[0]}–${ultim}`}</span></h2>
        <p className="note sb-nota">{t(`sb.ind_titlu.${ind}` as DictKey)}</p>
        {pie
          ? <GraficCota felii={felii} rest={{ cota: Math.max(restCota, 0), n: restN }} an={anCota} fmtValoare={fmtValoare} />
          : <>
              {mod === 'cota' && <p className="note sb-nota">{t('sb.pie.negativ', { an: anCota, indicator: t(`sb.ind.${ind}` as DictKey).toLowerCase() })}</p>}
              <Grafic date={date} serii={serii} nume={nume} fmt={fmt} />
            </>}
        {Object.entries(d.goluri ?? {}).filter(([an]) => !pie || an === anCota).map(([an, l]) => (
          <div key={an} className="callout warn sb-gol">
            {t('sb.gol_an', { an, banci: l.map((x) => `${x.nume} (~${num(x.cota_estimata, locale, 1)}%)`).join(', ') })}
          </div>
        ))}
      </section>

      <section>
        <div className="sb-cap-tabel">
          <h2>{t('sb.tab.evolutie')}</h2>
          <Comutator<string> value={ent} onChange={(v) => mergi({ vezi: v })}
            options={(['monitorizate', 'active', 'toate'] as const).map((k) => ({ value: k, label: t(`sb.ent.${k}` as DictKey) }))} />
        </div>
        <div className="sb-scroll">
          <p className="note sb-unitate">{t('sb.tabel_unitate', { unitate: mod === 'cota' ? t('sb.grafic_cota') : unitate, indicator: t(`sb.ind.${ind}` as DictKey) })}</p>
          {/* derulare orizontală proprie (14 ani): capul lipit de pagină s-ar suprapune peste rânduri */}
          <Tabel<BancaSituatie> randuri={randuri} cheieRand={(b) => String(b.cui)} libra={(b) => b.slug ?? ''}
            implicit={[ultim, 'descend']} gol={t('sb.gol')} coloane={colEvolutie} lipit={false} />
        </div>
      </section>

      <section>
        <h2>{t('sb.tab.mapare')}</h2>
        <p className="note sb-nota">{t('sb.mapare_nota', { n: d.banci.length, m: d.banci.filter((b) => b.slug).length })}</p>
        <Tabel<BancaSituatie> randuri={d.banci} cheieRand={(b) => String(b.cui)} libra={(b) => b.slug ?? ''}
          implicit={['monitorizata', 'descend']} coloane={colMapare} />
        <Despre>
          <T k="sb.despre.sursa" params={{ generat: d.generat_la.slice(0, 10) }} />{' '}
          <T k="sb.despre.forme" />{' '}
          <T k="sb.despre.indicatori" />{' '}
          <T k="sb.despre.cote" />
        </Despre>
      </section>
    </>
  )
}

function NumeBanca({ b, m }: { b: BancaSituatie; m: Meta }) {
  // în tabelul de evoluție: doar sigla, mărită (numele e în tooltip); fără siglă rămâne numele
  if (b.slug) return <EtichetaBanca slug={b.slug} m={m} fisa tag doarLogo />
  return <Tip title={`CUI ${b.cui}`}><span>{b.nume}</span></Tip>
}

const culoare = (i: number) => (i === 0 ? 'var(--sb-libra)' : `var(--sb-${i})`)

/**
 * Cota de piață într-un an: donut cu Libra pornind de la ora 12, apoi băncile alese în ordinea
 * listei și restul sectorului în gri. Cota Libra stă în centru; lista alăturată dă cifrele, ca
 * identitatea feliilor să nu depindă doar de culoare.
 */
function GraficCota({ felii, rest, an, fmtValoare }: {
  felii: { cheie: string; nume: string; i: number; cota: number; valoare: number }[]
  rest: { cota: number; n: number }
  an: string
  fmtValoare: (v: number) => string
}) {
  const { t, locale } = useLang()
  const pct = (v: number) => `${num(v, locale, 2)}%`
  const restNume = t('sb.pie.rest', { n: rest.n })
  const date = [...felii.map((f) => ({ cheie: f.cheie, nume: f.nume, cota: f.cota, fill: culoare(f.i) })),
    { cheie: 'rest', nume: restNume, cota: rest.cota, fill: 'var(--sb-rest)' }]
  const libra = felii.find((f) => f.i === 0)
  return (
    <div className="sb-cota">
      <div className="sb-donut">
        <ResponsiveContainer width="100%" height={320}>
          <PieChart>
            <Pie data={date} dataKey="cota" nameKey="nume" innerRadius="58%" outerRadius="92%" startAngle={90} endAngle={-270}
              stroke="var(--surface)" strokeWidth={2} isAnimationActive={false}>
              {date.map((x) => <Cell key={x.cheie} fill={x.fill} />)}
            </Pie>
            <Tooltip isAnimationActive={false}
              contentStyle={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 8, fontSize: 12 }}
              itemStyle={{ color: 'var(--ink)' }} formatter={(v, n) => [pct(typeof v === 'number' ? v : 0), String(n)]} />
          </PieChart>
        </ResponsiveContainer>
        {libra && (
          <div className="sb-centru" aria-hidden>
            <div className="n">{pct(libra.cota)}</div>
            <div className="gri">{t('sb.pie.centru', { an })}</div>
          </div>
        )}
      </div>
      <table className="sb-lista">
        <thead><tr><th>{t('sb.col.banca')}</th><th className="num">{t('sb.mod.cota')}</th><th className="num">{t('sb.mod.valoare')}</th></tr></thead>
        <tbody>
          {felii.map((f) => (
            <tr key={f.cheie} className={f.i === 0 ? 'libra' : ''}>
              <td><span className="sb-bulina" style={{ background: culoare(f.i) }} />{f.nume}</td>
              <td className="num mono">{pct(f.cota)}</td>
              <td className="num mono">{fmtValoare(f.valoare)}</td>
            </tr>
          ))}
          <tr className="rest">
            <td><span className="sb-bulina" style={{ background: 'var(--sb-rest)' }} />{restNume}</td>
            <td className="num mono">{pct(rest.cota)}</td>
            <td className="num mono gri">—</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

/**
 * Linii pe ani: Libra în roșul paletei (validat, nu culoarea de marcă #7a1e2c, prea închisă pentru o
 * linie), mai groasă; celelalte bănci în ordinea fixă a paletei, după poziția în listă. Un an fără
 * valoare rupe linia (banca nu exista sau nu a raportat), nu se unește peste gol.
 */
function Grafic({ date, serii, nume, fmt }: {
  date: Record<string, number | null>[]
  serii: BancaSituatie[]
  nume: (b: BancaSituatie) => string
  fmt: (v: number | null | undefined) => string
}) {
  const { locale } = useLang()
  // Legenda și tooltip-ul Recharts mai randează o dată cheia unei bănci tocmai scoase din listă:
  // căutarea directă întorcea undefined și pagina cădea (ecran negru la „x” pe o bancă).
  const etichete = new Map(serii.map((b) => [String(b.cui), nume(b)]))
  const eticheta = (k: unknown) => etichete.get(String(k)) ?? String(k)
  return (
    <div className="sb-grafic">
      <ResponsiveContainer width="100%" height={380}>
        <LineChart data={date} margin={{ top: 10, right: 24, bottom: 4, left: 8 }}>
          <CartesianGrid vertical={false} stroke="var(--line)" />
          <XAxis dataKey="an" tick={{ fill: 'var(--muted)', fontSize: 11 }} tickLine={false} axisLine={{ stroke: 'var(--line)' }} />
          <YAxis tick={{ fill: 'var(--muted)', fontSize: 11 }} tickLine={false} axisLine={false} width={64}
            tickFormatter={(v: number) => num(v, locale, v !== 0 && Math.abs(v) < 10 ? 1 : 0)} />
          <Tooltip isAnimationActive={false} cursor={{ stroke: 'var(--line-2)' }}
            contentStyle={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 8, fontSize: 12 }}
            labelStyle={{ color: 'var(--ink)', fontWeight: 600 }} itemStyle={{ color: 'var(--ink)' }}
            formatter={(v, k) => [fmt(typeof v === 'number' ? v : null), eticheta(k)]} />
          <Legend formatter={(k: string) => <span className="sb-leg">{eticheta(k)}</span>} />
          {serii.map((b, i) => (
            <Line key={b.cui} dataKey={String(b.cui)} name={String(b.cui)} type="linear" stroke={culoare(i)}
              strokeWidth={i === 0 ? 3 : 2} dot={{ r: i === 0 ? 4 : 3, strokeWidth: 0, fill: culoare(i) }}
              activeDot={{ r: 6, stroke: 'var(--surface)', strokeWidth: 2 }} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
