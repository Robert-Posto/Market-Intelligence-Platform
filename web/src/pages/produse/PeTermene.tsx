import { Checkbox, Segmented, Tooltip } from 'antd'
import type { ProdusLibra, ValoareLibra } from '@mcc/shared'
import type { Meta } from '../../api/meta'
import { EtichetaBanca, Pill } from '../../components/comune'
import { Tabel } from '../../components/Tabel'
import { etNume } from '../../components/valori'
import { T, useLang, type DictKey } from '../../i18n'
import { formatZi, num } from '../../util/format'
import { conditie, ePromo, valoare, type Stare } from './logica'
import { clasament, config, optiuni, termenImplicit, type Filtre, type Rand } from './termene'

const OFERTE = ['toate', 'standard', 'promo'] as const
const CANALE = ['online', 'ghiseu']
const PLATI = ['la_scadenta', 'lunar', 'capitalizare']

/**
 * Clasamentul băncilor pentru un produs, la termenul ales: o privire de tipul
 * „cine dă cea mai bună dobândă la 12 luni, în lei”. Datele sunt aceleași ca în
 * tabelul pe câmpuri; aici se aleg pe termen, monedă și tip de ofertă.
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
  // termenele și băncile de pe butoane, în moneda aleasă
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
  const nrBanci = cuValoare.size
  const bani = (n: number, mon?: string) => `${num(n, locale, 0)} ${mon === 'EUR' ? 'EUR' : mon === 'USD' ? 'USD' : 'lei'}`

  return (
    <div className="pt">
      <div className="pt-filtre">
        {opt.indicatori.length > 1 && (
          <label className="pt-f">{t('pt.f_indicator')}
            <Segmented value={ind.id} onChange={(v) => mergi({ ind: v, termen: '' })}
              options={opt.indicatori.map((i) => ({ value: i.id, label: t(i.eticheta) }))} />
          </label>
        )}
        {optInd.monede.length > 0 && (
          <label className="pt-f">{t('pt.f_moneda')}
            <Segmented value={monedaAleasa} onChange={(v) => mergi({ moneda: v })}
              options={[...optInd.monede.map((x) => ({ value: x.cod, label: x.cod })), { value: 'toate', label: t('pt.moneda_toate') }]} />
          </label>
        )}
        <label className="pt-f">{t(cfg.axa)}
          <Segmented value={termen} onChange={(v) => mergi({ termen: String(v) })}
            options={optInd.termene.map((x) => ({ value: x.luni, label: String(x.luni) }))} />
        </label>
        {canale.length > 0 && (
          <label className="pt-f">{t('pt.f_canal')}
            <Segmented value={canal} onChange={(v) => mergi({ canal: v === 'toate' ? '' : v })}
              options={[{ value: 'toate', label: t('pt.canal.toate') }, ...canale.map((c) => ({ value: c, label: t(`pt.canal.${c}` as DictKey) }))]} />
          </label>
        )}
        {plati.length > 1 && (
          <label className="pt-f">{t('pt.f_plata')}
            <Segmented value={plata} onChange={(v) => mergi({ plata: v === 'toate' ? '' : v })}
              options={[{ value: 'toate', label: t('pt.plata.toate') }, ...plati.map((p) => ({ value: p, label: t(`pt.plata.${p}` as DictKey) }))]} />
          </label>
        )}
        <label className="pt-f">{t('pt.f_oferta')}
          <Segmented value={oferta} onChange={(v) => mergi({ oferta: v === 'toate' ? '' : v })}
            options={OFERTE.map((o) => ({ value: o, label: t(`pt.oferta_${o}`) }))} />
        </label>
        <Checkbox className="pt-variante" checked={toateVariantele} onChange={() => mergi({ variante: toateVariantele ? '' : '1' })}>
          {t('pt.variante_toate')}
        </Checkbox>
      </div>

      <p className="note pt-sumar">
        {libra
          ? <T k="pt.loc_libra" params={{ poz: libra.pozitie, n: nrBanci }} />
          : t('pt.libra_lipsa', { termen })}
        {monedaAleasa !== 'toate' && optInd.faraMoneda > 0 && <> {tn('pt.fara_moneda', optInd.faraMoneda)}</>}
      </p>

      <Tabel<Rand>
        randuri={randuri}
        cheieRand={(r) => r.cheie}
        clasaRand={(r) => (r.banca === 'libra' ? 'libra' : '')}
        onRand={(r) => deschide(r.v)}
        implicit={['pozitie', 'ascend']}
        gol={t('pt.nicio_valoare')}
        coloane={[
          { cheie: 'pozitie', cap: t('pt.col_pozitie'), num: true, s: (r) => r.pozitie, val: (r) => r.pozitie },
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
                {r.diferenta !== 0 && (
                  <Tooltip title={t('pt.diferenta_tooltip')}>
                    <span className="pt-dif">{r.diferenta > 0 ? '+' : '−'}{num(Math.abs(r.diferenta), locale)}</span>
                  </Tooltip>
                )}
                <b>{valoare(r.v, t, locale)}</b>
                {!toateVariantele && r.variante > 1 && (
                  <button type="button" className="pl-mai" onClick={() => mergi({ variante: '1' })}>{tn('pt.variante', r.variante - 1)}</button>
                )}
              </span>
            ),
          },
          ...(new Set(randuri.map((r) => r.v.camp)).size > 1
            ? [{ cheie: 'tip', cap: t('pt.col_tip'), s: (r: Rand) => etNume(r.v.camp, t), val: (r: Rand) => etNume(r.v.camp, t) }]
            : []),
          {
            cheie: 'canal', cap: t('pt.col_canal'), s: (r) => r.v.scenariu?.canal ?? '',
            val: (r) => t(`pt.canal.${CANALE.includes(r.v.scenariu?.canal ?? '') ? r.v.scenariu!.canal : 'toate'}` as DictKey),
          },
          {
            cheie: 'plata', cap: t('pt.col_plata'), s: (r) => r.v.scenariu?.plata_dobanzii ?? '',
            val: (r) => (PLATI.includes(r.v.scenariu?.plata_dobanzii ?? '') ? t(`pt.plata.${r.v.scenariu!.plata_dobanzii}` as DictKey) : '—'),
          },
          {
            cheie: 'suma', cap: t('pt.col_suma'), num: true, s: (r) => r.v.scenariu?.suma,
            val: (r) => {
              const s = r.v.scenariu
              if (s?.suma == null) return '—'
              return s.suma_max != null ? `${bani(s.suma, s.moneda)} – ${bani(s.suma_max, s.moneda)}` : bani(s.suma, s.moneda)
            },
          },
          {
            cheie: 'conditie', cap: t('pt.col_conditie'),
            val: (r) => {
              const c = conditie(r.v)
              return c ? <Tooltip title={c}><span className="pt-cond">{c}</span></Tooltip> : '—'
            },
          },
          {
            cheie: 'oferta', cap: t('pt.col_oferta'),
            val: (r) => (
              <>
                {ePromo(r.v.scenariu, r.v) ? <Pill tip="ok">{t('pt.promo')}</Pill> : <span className="gri">{t('pt.standard')}</span>}
                {r.v.scenariu?.referinta?.potrivire === 'exact' && <Pill>{t('pl.et.referinta')}</Pill>}
              </>
            ),
          },
          { cheie: 'colectat', cap: t('pt.col_colectat'), s: (r) => r.v.data_colectare, val: (r) => formatZi(r.v.data_colectare, locale) },
          {
            cheie: 'verificare', cap: t('pt.col_verificare'),
            val: (r) => (
              <>
                {r.v.stare === 'validat' ? <Pill tip="ok">{t('pt.validat')}</Pill> : <Pill>{t('pt.propunere')}</Pill>}
                {r.v.ambiguu && <Pill tip="amb">{t('pl.neclar')}</Pill>}
                {r.v.incredere != null && <span className="sub">{t('pl.incredere', { n: num(r.v.incredere, locale) })}</span>}
              </>
            ),
          },
          {
            cheie: 'document', cap: t('pt.col_document'),
            val: (r) => <button type="button" className="pl-mai" onClick={() => deschide(r.v)}>{t('pt.vezi')}</button>,
          },
        ]}
      />

      {lipsa.length > 0 && <p className="note">{t('pt.fara_valoare', { termen, banci: lipsa.join(', ') })}</p>}
    </div>
  )
}
