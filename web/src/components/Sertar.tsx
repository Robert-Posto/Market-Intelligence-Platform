import { useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Button, Checkbox, Collapse, Drawer, Input, Select, Tooltip } from 'antd'
import { Celula, type ValoareDovada } from '@mcc/shared'
import { api } from '../api/client'
import { useMeta } from '../api/meta'
import { T, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { compara, num } from '../util/format'
import { Pill } from './comune'
import { CitatEvidentiat, citatUtil, LinkSursa, MOTIV_CHEIE } from './Dovezi'
import { etDesc, etNume, unitTxt } from './valori'

/**
 * Sertarul cu dovezile din spatele unei celule (refăcut pe 25.09 în aplicația
 * veche): BCR · Administrare cont avea 316 valori în 38 de grupe, ~31.000 px de
 * derulat când fiecare valoare era un card deschis. De aceea:
 *   - rezumat sus (interval, câte variante, câte gratuite);
 *   - căutare și ascunderea variantelor „retrase din ofertă”;
 *   - grupele pliate, ordonate de la cea mai ieftină;
 *   - o valoare = un rând; citatul și detaliile la clic pe rând.
 * Grupat pe `serviciu` — numele dat de bancă — fiindcă aceeași etichetă acoperă
 * mai multe prețuri (pachete, praguri, monede).
 */
export interface CerereSertar {
  banca: string
  camp: string
  unitate: string
  /** categoria (depozite / credite / conturi_carduri): `nominala` e și dobândă de depozit, și de credit */
  scenariu: string
  termen?: string
  produs?: string
}

/** Textul românesc al datelor: „retrasă din ofertă” e scris de bancă, nu de noi. */
const RE_RETRAS = /retras[ăae]? din ofert|nu mai (sunt|este) disponibil/i

export default function Sertar({ cerere, onClose }: { cerere: CerereSertar | null; onClose: () => void }) {
  const { t } = useLang()
  const meta = useMeta()
  const date = useQuery({
    queryKey: ['celula', cerere],
    enabled: !!cerere,
    queryFn: () =>
      api('/api/celula', Celula, { banca: cerere!.banca, camp: cerere!.camp, unitate: cerere!.unitate, scenariu: cerere!.scenariu, termen: cerere!.termen ?? '', produs: cerere!.produs ?? '' }),
  })
  const titlu = cerere ? `${meta.data?.nume[cerere.banca] ?? cerere.banca} · ${etNume(cerere.camp, t)}` : ''
  return (
    <Drawer open={!!cerere} onClose={onClose} width="min(880px, 94vw)" title={<span className="sertar-titlu">{titlu}</span>} closeIcon={null}
      extra={<Button onClick={onClose}>{t('sertar.inchide')}</Button>} destroyOnClose>
      {date.isLoading && <p className="note">{t('comun.se_incarca')}</p>}
      {date.error && <p className="note" style={{ color: 'var(--warn)' }}><T k="comun.eroare" params={{ mesaj: (date.error as Error).message }} /></p>}
      {date.data && cerere && <Corp date={date.data} camp={cerere.camp} unitate={cerere.unitate} />}
    </Drawer>
  )
}

function Corp({ date, camp, unitate }: { date: ValoareDovada[]; camp: string; unitate: string }) {
  const { t, tn, locale } = useLang()
  const [cauta, setCauta] = useState('')
  const [ascundeRetrase, setAscundeRetrase] = useState(true)
  const [ordine, setOrdine] = useState<'pret' | 'nume' | 'multe'>('pret')
  const [deschise, setDeschise] = useState<string[] | null>(null)

  const retrase = useMemo(
    () => date.filter((r) => RE_RETRAS.test([r.serviciu, r.conditie, r.detaliu, r.sectiune].join(' '))),
    [date],
  )
  const q = cauta.trim().toLowerCase()
  const vizibile = date
    .filter((r) => !(ascundeRetrase && retrase.includes(r)))
    .filter((r) => !q || [r.serviciu, r.conditie, r.frecventa, r.detaliu, r.citat, r.sectiune, r.valoare === null ? r.valoare_text : num(r.valoare, locale)]
      .join(' ').toLowerCase().includes(q))
  const u = (r?: ValoareDovada) => unitTxt(r?.unitate || unitate, t)

  const vals = date.filter((r) => !r.ambiguu && r.valoare !== null).map((r) => r.valoare!)
  const nServ = new Set(date.map((r) => r.serviciu || '')).size
  const gratuite = date.filter((r) => !r.ambiguu && r.valoare === 0).length
  const amb = date.filter((r) => r.ambiguu).length
  const cuLink = date.filter((r) => r.link).length

  const grupuri = new Map<string, ValoareDovada[]>()
  for (const r of vizibile) {
    const k = r.serviciu || t('sertar.grup.fara_nume_serviciu')
    if (!grupuri.has(k)) grupuri.set(k, [])
    grupuri.get(k)!.push(r)
  }
  const minG = (rs: ValoareDovada[]) => {
    const v = rs.filter((r) => r.valoare !== null && !r.ambiguu).map((r) => r.valoare!)
    return v.length ? Math.min(...v) : Infinity
  }
  const lista = [...grupuri].sort((a, b) =>
    ordine === 'nume' ? a[0].localeCompare(b[0], locale)
      : ordine === 'multe' ? b[1].length - a[1].length
        : minG(a[1]) - minG(b[1]) || a[0].localeCompare(b[0], locale))
  // puține grupe, sau o căutare activă: deschise; altfel pliate, cu intervalul la vedere
  const implicitDeschise = lista.length <= 3 || !!q ? lista.map(([k]) => k) : []
  const active = deschise ?? implicitDeschise

  return (
    <>
      {etDesc(camp, t) && <div className="note" style={{ margin: '0 0 0' }}>{etDesc(camp, t)}</div>}
      <div className="s-rez">
        {vals.length > 0 && (
          <div><b>{num(Math.min(...vals), locale)} – {num(Math.max(...vals), locale)}{u(date[0])}</b> <span>{t('sertar.rezumat.interval')}</span></div>
        )}
        <div><b>{nServ}</b> <span>{t((nServ === 1 ? 'sertar.rezumat.variante_serviciu_1' : 'sertar.rezumat.variante_serviciu_n'))}</span></div>
        <div><b>{date.length}</b> <span>{t(date.length === 1 ? 'sertar.rezumat.valori_1' : 'sertar.rezumat.valori_n')}</span></div>
        {gratuite > 0 && <div><b style={{ color: 'var(--ok)' }}>{gratuite}</b> <span>{t(gratuite === 1 ? 'sertar.rezumat.gratuite_1' : 'sertar.rezumat.gratuite_n')}</span></div>}
        {amb > 0 && <div><b style={{ color: 'var(--warn)' }}>{amb}</b> <span>{t('sertar.rezumat.de_verificat')}</span></div>}
        <div><b>{cuLink}</b> <span>{t('sertar.rezumat.cu_link')}</span></div>
      </div>
      <div className="s-bara">
        <Input className="cauta" allowClear placeholder={t('sertar.cauta_placeholder')} value={cauta} onChange={(e) => setCauta(e.target.value)} style={{ width: 260 }} />
        {retrase.length > 0 && (
          <Checkbox checked={ascundeRetrase} onChange={(e) => setAscundeRetrase(e.target.checked)}>
            {t('sertar.ascunde_retrase', { n: retrase.length })}
          </Checkbox>
        )}
        <Tooltip title={t('sertar.ordine_tooltip')}>
          <Select value={ordine} onChange={setOrdine} style={{ minWidth: 190 }}
            options={[
              { value: 'pret', label: t('sertar.ordine.pret') },
              { value: 'nume', label: t('sertar.ordine.nume') },
              { value: 'multe', label: t('sertar.ordine.multe') },
            ]} />
        </Tooltip>
        <Button onClick={() => setDeschise(active.length === lista.length ? [] : lista.map(([k]) => k))}>{t('sertar.deschide_inchide_tot')}</Button>
      </div>
      {lista.length === 0 ? (
        <p className="note">{t('sertar.nicio_valoare_cautare')}</p>
      ) : (
        <Collapse
          className="grupe"
          activeKey={active}
          onChange={(k) => setDeschise(Array.isArray(k) ? k : [k])}
          items={lista.map(([serv, rs]) => {
            rs.sort((a, b) => Number(a.ambiguu) - Number(b.ambiguu) || compara(a.valoare, b.valoare, locale))
            const v = rs.filter((r) => r.valoare !== null && !r.ambiguu).map((r) => r.valoare!)
            const interval = !v.length ? '—' : Math.min(...v) === Math.max(...v)
              ? `${num(v[0], locale)}${u(rs[0])}` : `${num(Math.min(...v), locale)} – ${num(Math.max(...v), locale)}${u(rs[0])}`
            const sec = rs.find((r) => r.sectiune)
            return {
              key: serv,
              label: (
                <div className="g-cap">
                  <span className="gn">{serv}{sec && <span className="sub">{sec.sectiune}</span>}</span>
                  <span className="gi">{interval}</span>
                  <span className="gc">{tn('sertar.grup.n_valori', rs.length)}</span>
                </div>
              ),
              children: rs.map((r, i) => <Rand key={i} r={r} />),
            }
          })}
        />
      )}
    </>
  )
}

function Rand({ r }: { r: ValoareDovada }) {
  const { t, lang, locale } = useLang()
  const [des, setDes] = useState(false)
  const val = r.valoare !== null && r.valoare !== undefined ? `${num(r.valoare, locale)}${unitTxt(r.unitate, t)}` : r.valoare_text || '—'
  const ctx: ReactNode[] = [r.frecventa && <b key="f">{r.frecventa}</b>, r.conditie, r.detaliu].filter(Boolean)
  const scen = (r.cod_scenariu || '').split('|').filter(Boolean)
  const cit = citatUtil(r)
  const motiv = r.motiv_ambiguu && MOTIV_CHEIE[r.motiv_ambiguu]
  return (
    <div className={`r${des ? ' des' : ''}`} onClick={(e) => { if (!(e.target as HTMLElement).closest('a')) setDes(!des) }}>
      <div className="rv" style={r.ambiguu ? { color: 'var(--warn)' } : undefined}>
        {val}
        {(r.nr_aparitii ?? 0) > 1 && (
          <Tooltip title={t('sertar.rand.nr_aparitii_tooltip', { n: r.nr_aparitii! })}>
            <span className="mono gri" style={{ fontSize: 10 }}> ×{r.nr_aparitii}</span>
          </Tooltip>
        )}
      </div>
      <div className="rc">
        {ctx.length ? ctx.flatMap((x, i) => (i ? [' · ', x] : [x])) : <span className="gri">{t('sertar.rand.fara_conditii')}</span>}
        {r.ambiguu && <> <Pill tip="amb" title={motiv ? t(`coada.motiv_explicatie.${motiv}` as DictKey) : undefined}>{t('sertar.rand.de_verificat')}</Pill></>}
        <span className="ind">{cit ? t('sertar.rand.citat') : t('sertar.rand.detalii')} ▾</span>
      </div>
      <div className="rs"><LinkSursa r={r} /></div>
      <div className="rx">
        {cit ? (
          <div className="cit"><CitatEvidentiat r={r} /></div>
        ) : (
          <div className="cit fara">
            {r.sectiune ? <T k="sertar.rand.in_document_sectiune" params={{ sectiune: r.sectiune }} /> : t('sertar.rand.fara_text')}
          </div>
        )}
        <div className="meta">
          <Pill title={t('sertar.rand.metoda_tooltip')}>{r.metoda_extractie || '?'}</Pill>
          {scen.map((x) => <Pill key={x}>{x}</Pill>)}
          {/* motivul vine din bază în română; în engleză se arată tradus, cheia rămâne aceeași */}
          {r.ambiguu && <Pill tip="amb">{r.motiv_ambiguu ? deLaServer(r.motiv_ambiguu, lang) : t('sertar.rand.ambiguu')}</Pill>}
          {(r.confidence ?? 1) < 0.7 && <Pill tip="amb">{t('sertar.rand.incredere', { valoare: num(r.confidence, locale) })}</Pill>}
        </div>
      </div>
    </div>
  )
}
