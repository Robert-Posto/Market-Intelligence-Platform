import { Segmented, Select, Switch, Tooltip } from 'antd'
import type { ProdusLibra, ValoareLibra } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { EtichetaBanca, Pill } from '../../components/comune'
import { Tabel } from '../../components/Tabel'
import { etNume } from '../../components/valori'
import { useLang, type DictKey } from '../../i18n'
import { formatZi, num } from '../../util/format'
import { conditie, ePromo, SCURT, valoare, type Stare } from './logica'
import { clasament, config, optiuni, termenImplicit, type Filtre, type Rand } from './termene'

const OFERTE = ['toate', 'standard', 'promo'] as const
const CANALE = ['online', 'ghiseu']
const PLATI = ['la_scadenta', 'lunar', 'capitalizare']

/**
 * Clasamentul băncilor pentru un produs, la termenul ales: o privire de tipul
 * „cine dă cea mai bună dobândă la 12 luni, în lei”. Datele sunt aceleași ca în
 * tabelul pe câmpuri; aici se aleg pe termen, monedă și tip de ofertă.
 *
 * Sus, răspunsul (locul Libra, oferta ei, cea mai bună ofertă, mediana); dedesubt,
 * clasamentul, cu condițiile și sursa strânse în câte o coloană.
 */
export default function PeTermene({ ales, valori, banci, stare, mergi, m, deschide }: {
  ales: ProdusLibra
  valori: ValoareLibra[]
  banci: string[]
  stare: Stare
  mergi: (k: Record<string, string>) => void
  m: Meta
  deschide: (v: ValoareLibra) => void
}) {
  const { t, tn, locale } = useLang()
  const cfg = config(ales)!
  const indicator = cfg.indicatori.find((i) => i.id === stare.ind) ?? cfg.indicatori[0]!
  const opt = optiuni(cfg, valori, indicator)
  const ind = opt.indicatori.find((i) => i.id === indicator.id) ?? opt.indicatori[0]!
  const optToate = ind === indicator ? opt : optiuni(cfg, valori, ind)
  // RON întâi, dacă există: comparația implicită e în lei, ca scenariul de referință
  const monedaImplicita = optToate.monede.some((x) => x.cod === 'RON') ? 'RON' : 'toate'
  const monedaAleasa = stare.moneda && (stare.moneda === 'toate' || optToate.monede.some((x) => x.cod === stare.moneda))
    ? stare.moneda : monedaImplicita
  // termenele și băncile din listă, în moneda aleasă
  const optInd = optiuni(cfg, valori, ind, monedaAleasa)
  const cerut = Number(stare.termen)
  const termen = optInd.termene.some((x) => x.luni === cerut) ? cerut : termenImplicit(valori, optInd)
  const oferta = (OFERTE as readonly string[]).includes(stare.oferta ?? '') ? (stare.oferta as Filtre['oferta']) : 'toate'
  const toateVariantele = stare.variante === '1'
  // filtrele grilei apar doar dacă datele au ce despărți (la credite, de regulă nu)
  const canale = CANALE.filter((c) => optInd.canale.includes(c))
  const plati = PLATI.filter((p) => optInd.plati.includes(p))
  const canal = canale.includes(stare.canal ?? '') ? stare.canal! : 'toate'
  const plata = plati.includes(stare.plata ?? '') ? stare.plata! : 'toate'

  if (termen === null) return <p className="note">{t('pt.nicio_valoare')}</p>
  const f: Filtre = { indicator: ind, termen, moneda: monedaAleasa, oferta, canal, plata }
  const randuri = clasament(cfg, valori, f, toateVariantele)
  const cuValoare = new Set(randuri.map((r) => r.banca))
  const lipsa = banci.filter((b) => !cuValoare.has(b)).map((b) => m.nume[b] ?? b)
  const libra = randuri.find((r) => r.banca === 'libra')
  const lider = randuri[0]
  const nrBanci = cuValoare.size
  // mediana pe cea mai bună valoare a fiecărei bănci (cu „toate variantele”, o bancă ar trage de ea)
  const peBanca = randuri.filter((r, i) => randuri.findIndex((x) => x.banca === r.banca) === i).map((r) => r.v.valoare!)
    .sort((a, b) => a - b)
  const mediana = peBanca.length
    ? (peBanca.length % 2 ? peBanca[(peBanca.length - 1) / 2]! : (peBanca[peBanca.length / 2 - 1]! + peBanca[peBanca.length / 2]!) / 2)
    : null
  const procent = (n: number) => `${num(Math.round(n * 100) / 100, locale)}%`
  const bani = (n: number, mon?: string) => `${num(n, locale, 0)} ${mon === 'EUR' ? 'EUR' : mon === 'USD' ? 'USD' : 'lei'}`
  const numeScurt = (b: string) => SCURT[b] ?? m.nume[b] ?? b
  const lunile = (l: number) => tn('pl.et.luni', l)

  return (
    <div className="pt">
      <div className="pt-filtre">
        {opt.indicatori.length > 1 && (
          <label className="pt-f">{t('pt.f_indicator')}
            <Segmented value={ind.id} onChange={(v) => mergi({ ind: v, termen: '' })}
              options={opt.indicatori.map((i) => ({ value: i.id, label: t(i.eticheta) }))} />
          </label>
        )}
        <label className="pt-f">{t(cfg.axa)}
          {/* lângă fiecare termen, câte bănci au valoare la el: un clasament cu un rând nu compară nimic */}
          <Select value={termen} onChange={(v) => mergi({ termen: String(v) })} style={{ width: 170 }} popupMatchSelectWidth={false}
            options={optInd.termene.map((x) => ({ value: x.luni, label: tn('pt.termen_opt', x.banci, { luni: lunile(x.luni) }) }))} />
        </label>
        {optInd.monede.length > 0 && (
          <label className="pt-f">{t('pt.f_moneda')}
            <Select value={monedaAleasa} onChange={(v) => mergi({ moneda: v })} style={{ width: 100 }}
              options={[...optInd.monede.map((x) => ({ value: x.cod, label: x.cod })), { value: 'toate', label: t('pt.moneda_toate') }]} />
          </label>
        )}
        {canale.length > 0 && (
          <label className="pt-f">{t('pt.f_canal')}
            <Segmented value={canal} onChange={(v) => mergi({ canal: v === 'toate' ? '' : v })}
              options={[{ value: 'toate', label: t('pt.canal.toate') }, ...canale.map((c) => ({ value: c, label: t(`pt.canal.${c}` as DictKey) }))]} />
          </label>
        )}
        {plati.length > 1 && (
          <label className="pt-f">{t('pt.f_plata')}
            <Select value={plata} onChange={(v) => mergi({ plata: v === 'toate' ? '' : v })} style={{ width: 140 }}
              options={[{ value: 'toate', label: t('pt.plata.toate') }, ...plati.map((p) => ({ value: p, label: t(`pt.plata.${p}` as DictKey) }))]} />
          </label>
        )}
        <label className="pt-f">{t('pt.f_oferta')}
          <Segmented value={oferta} onChange={(v) => mergi({ oferta: v === 'toate' ? '' : v })}
            options={OFERTE.map((o) => ({ value: o, label: t(`pt.oferta_${o}`) }))} />
        </label>
        <label className="pt-variante">
          <Switch size="small" checked={toateVariantele} onChange={() => mergi({ variante: toateVariantele ? '' : '1' })} />
          {t('pt.variante_toate')}
        </label>
      </div>

      <div className="pt-kpi">
        <div className={`pt-kpi-c ${libra ? 'libra' : 'lipsa'}`}>
          <span className="et">{t('pt.kpi_pozitie')}</span>
          {libra
            ? <><b>{libra.pozitie}<small> / {nrBanci}</small></b><span className="sub">{tn('pt.kpi_din', nrBanci)}</span></>
            : <><b>—</b><span className="sub">{t('pt.kpi_lipsa')}</span></>}
        </div>
        <div className="pt-kpi-c">
          <span className="et">{t('pt.kpi_libra')}</span>
          {libra ? (
            <>
              <b>{valoare(libra.v, t, locale)}</b>
              <span className={`sub ${libra.diferenta ? 'rau' : 'bun'}`}>
                {libra.diferenta
                  ? t('pt.kpi_dif', { dif: `${libra.diferenta > 0 ? '+' : '−'}${num(Math.abs(libra.diferenta), locale)}` })
                  : t('pt.kpi_prima')}
              </span>
            </>
          ) : <><b>—</b><span className="sub">{t('pt.kpi_lipsa')}</span></>}
        </div>
        <div className="pt-kpi-c">
          <span className="et">{t('pt.kpi_lider')}</span>
          {lider && (
            <>
              <b>{valoare(lider.v, t, locale)}</b>
              <span className="sub pt-kpi-banca">{m.logo[lider.banca] && <img src={m.logo[lider.banca]} alt="" />}{numeScurt(lider.banca)}</span>
            </>
          )}
        </div>
        <div className="pt-kpi-c">
          <span className="et">{t('pt.kpi_mediana')}</span>
          <b>{mediana === null ? '—' : procent(mediana)}</b>
          <span className="sub">{tn('pt.kpi_din', peBanca.length)}</span>
        </div>
      </div>
      {monedaAleasa !== 'toate' && optInd.faraMoneda > 0 && <p className="note pt-sumar">{tn('pt.fara_moneda', optInd.faraMoneda)}</p>}

      <Tabel<Rand>
        randuri={randuri}
        cheieRand={(r) => r.cheie}
        clasaRand={(r) => (r.banca === 'libra' ? 'libra' : '')}
        onRand={(r) => deschide(r.v)}
        implicit={['pozitie', 'ascend']}
        gol={t('pt.nicio_valoare')}
        coloane={[
          { cheie: 'pozitie', cap: '#', num: true, s: (r) => r.pozitie, val: (r) => <span className="pt-poz">{r.pozitie}</span> },
          {
            cheie: 'banca', cap: t('pt.col_banca'), s: (r) => m.nume[r.banca] ?? r.banca,
            val: (r) => (
              <>
                <EtichetaBanca slug={r.banca} m={m} tag doarLogo />
                {/* denumirea produsului la bancă e dată din document: nu se traduce */}
                {r.v.denumire_banca && <span className="sub">{r.v.denumire_banca}</span>}
              </>
            ),
          },
          {
            cheie: 'valoare', cap: t(ind.eticheta), num: true, s: (r) => r.v.valoare,
            val: (r) => (
              <span className="pt-val">
                <b>{valoare(r.v, t, locale)}</b>
                {r.diferenta !== 0 && (
                  <Tooltip title={t('pt.diferenta_tooltip')}>
                    <span className="pt-dif">{r.diferenta > 0 ? '+' : '−'}{num(Math.abs(r.diferenta), locale)}</span>
                  </Tooltip>
                )}
                {!toateVariantele && r.variante > 1 && (
                  <button type="button" className="pl-mai" onClick={(e) => { e.stopPropagation(); mergi({ variante: '1' }) }}>
                    {tn('pt.variante', r.variante - 1)}
                  </button>
                )}
              </span>
            ),
          },
          ...(new Set(randuri.map((r) => r.v.camp)).size > 1
            ? [{ cheie: 'tip', cap: t('pt.col_tip'), s: (r: Rand) => etNume(r.v.camp, t), val: (r: Rand) => etNume(r.v.camp, t) }]
            : []),
          {
            // canalul, plata, suma, oferta și condiția din document, într-o singură coloană
            cheie: 'conditii', cap: t('pt.col_conditii'),
            val: (r) => {
              const s = r.v.scenariu
              const c = conditie(r.v)
              return (
                <span className="pt-cond-l">
                  {ePromo(s, r.v) && <Pill tip="ok">{t('pt.promo')}</Pill>}
                  {s?.referinta?.potrivire === 'exact' && <Pill>{t('pl.et.referinta')}</Pill>}
                  {CANALE.includes(s?.canal ?? '') && <span className="pt-tag">{t(`pt.canal.${s!.canal}` as DictKey)}</span>}
                  {PLATI.includes(s?.plata_dobanzii ?? '') && <span className="pt-tag">{t(`pt.plata.${s!.plata_dobanzii}` as DictKey)}</span>}
                  {s?.suma != null && (
                    <span className="pt-tag">{s.suma_max != null ? `${bani(s.suma, s.moneda)} – ${bani(s.suma_max, s.moneda)}` : bani(s.suma, s.moneda)}</span>
                  )}
                  {c && <Tooltip title={c}><span className="pt-cond">{c}</span></Tooltip>}
                </span>
              )
            },
          },
          {
            // starea verificării și data, apoi documentul (clic pe rând face același lucru)
            cheie: 'sursa', cap: t('pt.col_sursa'), s: (r) => r.v.data_colectare,
            val: (r) => (
              <span className="pt-sursa">
                {r.v.stare === 'validat' ? <Pill tip="ok">{t('pt.validat')}</Pill> : <Pill>{t('pt.propunere')}</Pill>}
                {r.v.ambiguu && <Pill tip="amb">{t('pl.neclar')}</Pill>}
                <span className="sub">
                  {formatZi(r.v.data_colectare, locale)}
                  {r.v.incredere != null && ` · ${t('pl.incredere', { n: num(r.v.incredere, locale) })}`}
                </span>
                <button type="button" className="pl-mai" onClick={(e) => { e.stopPropagation(); deschide(r.v) }}>{t('pt.vezi')}</button>
              </span>
            ),
          },
        ]}
      />

      {lipsa.length > 0 && (
        <details className="pt-lipsa">
          <summary>{tn('pt.fara_valoare', lipsa.length)}</summary>
          <p>{lipsa.join(', ')}</p>
        </details>
      )}
    </div>
  )
}
