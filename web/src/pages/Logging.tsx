import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Button, Segmented, Select, Tag, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { CostZi, EroareJob, Job, JobsDisponibile, StareJob, TipJob } from '@mcc/shared'
import { useEroriJob, useJobs } from '../api/jobs'
import { useMeta } from '../api/meta'
import { Despre, Eroare, EtichetaBanca, SeIncarca } from '../components/comune'
import { Paginare } from '../components/Paginare'
import { Tabel, type Coloana } from '../components/Tabel'
import { T, useLang, type DictKey } from '../i18n'
import { num } from '../util/format'
import { GraficCost, culoareTip } from './logging/GraficCost'
import { intrare, moment, numeTip, partiDurata, tokeni, usd, ziLunga } from './logging/format'
import '../styles/logging.css'

const PERIOADE = [1, 7, 30, 90] as const
const PAS_ERORI = 20

/**
 * Starea nu e niciodată doar o culoare: simbolul și eticheta o spun și la
 * daltonism, și în print.
 */
const STARI: Record<StareJob, { simbol: string; culoare?: string }> = {
  reusit: { simbol: '✓', culoare: 'success' },
  cu_erori: { simbol: '!', culoare: 'warning' },
  esuat: { simbol: '✕', culoare: 'error' },
  in_curs: { simbol: '●', culoare: 'processing' },
  intrerupt: { simbol: '■' },
  abandonat: { simbol: '?', culoare: 'error' },
}

function Stare({ s }: { s: StareJob }) {
  const { t } = useLang()
  const tag = (
    <Tag className="pill" color={STARI[s].culoare} bordered>
      <span aria-hidden="true">{STARI[s].simbol}</span> {t(`lg.stare.${s}` as DictKey)}
    </Tag>
  )
  return s === 'abandonat' ? <Tooltip title={t('lg.stare.abandonat_tooltip')}>{tag}</Tooltip> : tag
}

function useDurata() {
  const { t } = useLang()
  return (s: number | null | undefined) => {
    const d = partiDurata(s)
    return d ? t(`lg.durata.${d.cheie}` as DictKey, d.p) : '—'
  }
}

/**
 * Logging: joburile fluxului extragere_produse_bancare (discovery, extragere,
 * produse noi), din tabelele `jobs` / `jobs_error` (migrarea 036). Filtrele stau
 * în adresă: `zile`, `tip`, iar `job` deschide erorile unui singur job.
 */
export default function Logging() {
  const { t, tn, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const zile = PERIOADE.find((p) => String(p) === sp.get('zile')) ?? 30
  const tip = sp.get('tip') || null
  const jobAles = sp.get('job') ? Number(sp.get('job')) : null
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  const panou = useRef<HTMLDivElement>(null)

  const q = useJobs(zile, tip)
  const meta = useMeta()
  const inCurs = !!q.data?.disponibil && q.data.totaluri.in_curs > 0
  const eroriJob = useEroriJob(jobAles, inCurs)

  const mergi = useCallback((k: Record<string, string>) => setSp((p) => {
    const n = new URLSearchParams(p)
    for (const [c, v] of Object.entries(k)) {
      if (v) n.set(c, v)
      else n.delete(c)
    }
    return n
  }, { replace: true }), [setSp])

  const alege = useCallback((id: number) => {
    mergi({ job: jobAles === id ? '' : String(id) })
    requestAnimationFrame(() => panou.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
  }, [jobAles, mergi])

  if (q.error) return <Eroare e={q.error} />
  if (meta.error) return <Eroare e={meta.error} />
  if (!q.data || !meta.data) return <SeIncarca />
  if (!q.data.disponibil) return <section><p className="note"><T k="lg.nedisponibil" /></p></section>

  const d = q.data
  const job = d.joburi.find((j) => j.id === jobAles) ?? null
  const erori = jobAles !== null ? (eroriJob.data?.disponibil ? eroriJob.data.erori : null) : d.erori

  return (
    <div className="lg" style={{ opacity: q.isPlaceholderData ? 0.6 : 1 }}>
      <div className="lg-filtre">
        <Segmented<number>
          value={zile}
          onChange={(v) => mergi({ zile: v === 30 ? '' : String(v) })}
          options={PERIOADE.map((p) => ({ value: p, label: t(`lg.perioada.${p}` as DictKey) }))}
        />
        <Select
          className="lg-select"
          value={tip ?? ''}
          aria-label={t('lg.tip')}
          onChange={(v: string) => mergi({ tip: v, job: '' })}
          options={[{ value: '', label: t('lg.tip_toate') }, ...d.tipuri.map((x) => ({ value: x.cod, label: numeTip(t, x.cod, x.denumire) }))]}
        />
        {inCurs && (
          <span className="lg-viu">
            <Stare s="in_curs" /> {tn('lg.in_curs', d.totaluri.in_curs)}
          </span>
        )}
      </div>

      <Indicatori d={d} />

      <section>
        <div className="lg-cap">
          <div>
            <h2>{t('lg.cost.titlu')}</h2>
            <p className="note">{t('lg.cost.sub')}</p>
          </div>
          <Segmented
            size="small"
            value={vedere}
            onChange={(v) => setVedere(v as 'grafic' | 'tabel')}
            options={[{ value: 'grafic', label: t('lg.vedere.grafic') }, { value: 'tabel', label: t('lg.vedere.tabel') }]}
          />
        </div>
        <Cost zile={d.cost_pe_zi} tipuri={d.tipuri} vedere={vedere} />
      </section>

      <section>
        <div className="lg-cap">
          <div>
            <h2>{t('lg.joburi.titlu')}</h2>
            <p className="note">
              {t(d.joburi.length >= d.limita ? 'lg.joburi.sub_limita' : 'lg.joburi.sub', { n: num(d.joburi.length, locale, 0) })}
            </p>
          </div>
        </div>
        {d.joburi.length ? (
          <TabelJoburi joburi={d.joburi} tipuri={d.tipuri} jobAles={jobAles} alege={alege} />
        ) : (
          <p className="note"><T k="lg.joburi.gol" /></p>
        )}
      </section>

      <section ref={panou}>
        <PanouErori d={d} job={job} jobAles={jobAles} erori={erori} renunta={() => mergi({ job: '' })} />
      </section>

      <section>
        <Despre>
          <T k="lg.despre_cost" />
          <br />
          <br />
          <T k="lg.despre_stari" />
          <br />
          <br />
          <T k="lg.despre_tipuri" />
        </Despre>
      </section>
    </div>
  )
}

function Indicatori({ d }: { d: JobsDisponibile }) {
  const { t, tn, locale } = useLang()
  const durata = useDurata()
  const k = d.totaluri
  return (
    <div className="kpi">
      <div>
        <div className="e">{t('lg.kpi.cost')}</div>
        <div className="n">{usd(k.cost_usd, locale)}{k.cost_complet ? '' : '+'}</div>
        <div className="l"><T k={k.cost_complet ? 'lg.kpi.cost_l' : 'lg.kpi.cost_partial'} /></div>
      </div>
      <div>
        <div className="e">{t('lg.kpi.joburi')}</div>
        <div className="n">{num(k.joburi, locale, 0)}</div>
        <div className="l">{k.cu_probleme ? tn('lg.kpi.probleme', k.cu_probleme) : t('lg.kpi.fara_probleme')}</div>
      </div>
      <div>
        <div className="e">{t('lg.kpi.erori')}</div>
        <div className={`n${k.errors ? ' lg-atentie' : ''}`}>{num(k.errors, locale, 0)}</div>
        <div className="l"><T k="lg.kpi.erori_l" /></div>
      </div>
      <div>
        <div className="e">{t('lg.kpi.tokeni')}</div>
        <div className="n">{tokeni(intrare(k) + k.tokeni_iesire, locale)}</div>
        <div className="l">{t('lg.kpi.tokeni_l', { intrare: tokeni(intrare(k), locale), iesire: tokeni(k.tokeni_iesire, locale) })}</div>
      </div>
      <div>
        <div className="e">{t('lg.kpi.durata')}</div>
        <div className="n">{durata(k.durata_s)}</div>
        <div className="l">{tn('lg.kpi.apeluri', k.apeluri, { n: num(k.apeluri, locale, 0) })}</div>
      </div>
    </div>
  )
}

/** Tipurile care au cost în perioadă, în ordinea din job_types. */
const cuCost = (zile: CostZi[], tipuri: TipJob[]) => tipuri.filter((x) => zile.some((z) => (z.costuri[x.cod] ?? 0) > 0))

function Cost({ zile, tipuri, vedere }: { zile: CostZi[]; tipuri: TipJob[]; vedere: 'grafic' | 'tabel' }) {
  const { t, locale } = useLang()
  const afisate = cuCost(zile, tipuri)
  if (!afisate.length) return <p className="note">{t('lg.cost.gol')}</p>

  const coloane: Coloana<CostZi>[] = [
    { cheie: 'zi', cap: t('lg.col.zi'), s: (z) => z.zi, val: (z) => ziLunga(z.zi, locale) },
    ...afisate.map((x): Coloana<CostZi> => ({
      cheie: x.cod,
      cap: <><span className="lg-cheie" style={{ background: culoareTip(tipuri, x.cod) }} />{numeTip(t, x.cod, x.denumire)}</>,
      num: true,
      s: (z) => z.costuri[x.cod] ?? 0,
      val: (z) => (z.costuri[x.cod] ? usd(z.costuri[x.cod]!, locale) : '—'),
    })),
    { cheie: 'total', cap: t('lg.col.total'), num: true, s: (z) => z.total, val: (z) => <b>{usd(z.total, locale)}</b> },
    { cheie: 'joburi', cap: t('lg.col.joburi'), num: true, s: (z) => z.joburi, val: (z) => num(z.joburi, locale, 0) },
  ]

  return (
    <>
      {vedere === 'grafic' ? (
        // un tip fără cost în perioadă nu primește loc în stivă, dar culoarea o dă lista întreagă
        <GraficCost zile={zile} tipuri={tipuri} afisate={afisate} />
      ) : (
        <Tabel randuri={zile.filter((z) => z.joburi > 0)} coloane={coloane} cheieRand={(z) => z.zi} implicit={['zi', 'descend']} />
      )}
      <div className="lg-legenda">
        {afisate.map((x) => (
          <span key={x.cod} title={x.descriere ?? undefined}>
            <span className="lg-cheie" style={{ background: culoareTip(tipuri, x.cod) }} />
            {numeTip(t, x.cod, x.denumire)} <b className="mono">{usd(zile.reduce((s, z) => s + (z.costuri[x.cod] ?? 0), 0), locale)}</b>
          </span>
        ))}
      </div>
    </>
  )
}

function TabelJoburi({ joburi, tipuri, jobAles, alege }: {
  joburi: Job[]; tipuri: TipJob[]; jobAles: number | null; alege: (id: number) => void
}) {
  const { t, locale } = useLang()
  const meta = useMeta()
  const durata = useDurata()
  const coloane = useMemo((): Coloana<Job>[] => [
    { cheie: 'inceput', cap: t('lg.col.inceput'), s: (j) => j.started_at, val: (j) => <span className="mono" title={`#${j.id}`}>{moment(j.started_at, locale)}</span> },
    {
      cheie: 'tip', cap: t('lg.col.tip'), s: (j) => numeTip(t, j.type, j.tip),
      val: (j) => <span className="lg-tip-job"><span className="lg-cheie" style={{ background: culoareTip(tipuri, j.type) }} />{numeTip(t, j.type, j.tip)}</span>,
    },
    {
      // doar sigla, mărită: numele rămâne la hover și la sortare
      cheie: 'banca', cap: t('lg.col.banca'), s: (j) => j.nume_banca ?? j.banca,
      val: (j) => (j.banca && meta.data ? <EtichetaBanca slug={j.banca} m={meta.data} doarLogo /> : (j.banca ?? '—')),
    },
    {
      cheie: 'pornire', cap: t('lg.col.pornire'), s: (j) => Number(j.runed_manually),
      val: (j) => (
        <Tooltip title={t(j.runed_manually ? 'lg.pornire.manual_tooltip' : 'lg.pornire.automat_tooltip')}>
          <Tag className="pill" color={j.runed_manually ? 'gold' : 'blue'} bordered>
            {t(j.runed_manually ? 'lg.pornire.manual' : 'lg.pornire.automat')}
          </Tag>
        </Tooltip>
      ),
    },
    { cheie: 'stare', cap: t('lg.col.stare'), s: (j) => j.stare, val: (j) => <Stare s={j.stare} /> },
    { cheie: 'durata', cap: t('lg.col.durata'), num: true, s: (j) => j.durata_s, val: (j) => durata(j.durata_s) },
    { cheie: 'apeluri', cap: t('lg.col.apeluri'), num: true, s: (j) => j.apeluri, val: (j) => num(j.apeluri, locale, 0) },
    {
      cheie: 'tokeni', cap: t('lg.col.tokeni'), num: true, s: (j) => intrare(j) + j.tokeni_iesire,
      val: (j) => (
        <Tooltip title={t('lg.tokeni_tooltip', {
          fara: num(j.tokeni_intrare, locale, 0), citire: num(j.tokeni_cache_citire, locale, 0),
          scriere: num(j.tokeni_cache_scriere, locale, 0), iesire: num(j.tokeni_iesire, locale, 0),
        })}>
          <span>{tokeni(intrare(j), locale)} / {tokeni(j.tokeni_iesire, locale)}</span>
        </Tooltip>
      ),
    },
    {
      cheie: 'cost', cap: t('lg.col.cost'), num: true, s: (j) => j.cost_usd,
      val: (j) => (j.cost_complet ? usd(j.cost_usd, locale) : <Tooltip title={t('lg.cost_partial_tooltip')}><span>{usd(j.cost_usd, locale)}+</span></Tooltip>),
    },
    {
      cheie: 'erori', cap: t('lg.col.erori'), num: true, s: (j) => j.errors,
      val: (j) => (
        <Button
          size="small"
          type={jobAles === j.id ? 'primary' : 'default'}
          danger={j.errors > 0 && jobAles !== j.id}
          aria-label={t('lg.erori_job_aria', { n: j.errors, id: j.id })}
          onClick={() => alege(j.id)}
        >
          {num(j.errors, locale, 0)}
        </Button>
      ),
    },
  ], [t, locale, tipuri, meta.data, durata, jobAles, alege])

  return (
    <div className="lg-joburi">
      <Tabel
        randuri={joburi}
        coloane={coloane}
        cheieRand={(j) => String(j.id)}
        implicit={['inceput', 'descend']}
        onRand={(j) => alege(j.id)}
        clasaRand={(j) => (j.id === jobAles ? 'lg-ales' : '')}
      />
    </div>
  )
}

/** Parametrii jobului ca linie de comandă, fără valorile goale sau false. */
function argumente(p: Record<string, unknown>): string {
  return Object.entries(p)
    .filter(([k, v]) => v !== null && v !== false && v !== undefined && !k.startsWith('_'))
    .map(([k, v]) => `--${k.replace(/_/g, '-')}${v === true ? '' : ` ${String(v)}`}`)
    .join(' ')
}

function PanouErori({ d, job, jobAles, erori, renunta }: {
  d: JobsDisponibile; job: Job | null; jobAles: number | null; erori: EroareJob[] | null; renunta: () => void
}) {
  const { t, locale } = useLang()
  const durata = useDurata()
  const [offset, setOffset] = useState(0)
  // altă listă (alt job, alt filtru): se pornește iar de la primele
  useEffect(() => setOffset(0), [jobAles, d.filtre.zile, d.filtre.tip])

  const sub = jobAles !== null && job
    ? `${numeTip(t, job.type, job.tip)} · ${job.nume_banca ?? job.banca ?? '—'} · ${moment(job.started_at, locale)} · ${durata(job.durata_s)}`
    : erori && erori.length >= d.limita
      ? t('lg.erori.sub_limita', { n: d.limita })
      : t('lg.erori.sub')

  return (
    <>
      <div className="lg-cap">
        <div>
          <h2>{jobAles !== null ? t('lg.erori.titlu_job', { id: jobAles }) : t('lg.erori.titlu')}</h2>
          <p className="note">{sub}</p>
        </div>
        {jobAles !== null && <Button size="small" onClick={renunta}>{t('lg.erori.toate')}</Button>}
      </div>

      {job && (job.rezumat || job.model || job.parametri) && (
        <dl className="lg-detalii">
          {job.rezumat && (<><dt>{t('lg.detalii.rezumat')}</dt><dd>{job.rezumat}</dd></>)}
          {job.model && (<><dt>{t('lg.detalii.model')}</dt><dd className="mono">{job.model}</dd></>)}
          {job.parametri && (<><dt>{t('lg.detalii.parametri')}</dt><dd className="mono">{argumente(job.parametri)}</dd></>)}
        </dl>
      )}

      {erori === null ? (
        <SeIncarca />
      ) : !erori.length ? (
        <p className="note">{t(jobAles !== null ? 'lg.erori.gol_job' : 'lg.erori.gol')}</p>
      ) : (
        <>
          <ul className="lg-erori">
            {erori.slice(offset, offset + PAS_ERORI).map((e) => (
              <ItemEroare key={e.id} e={e} cuJob={jobAles === null} />
            ))}
          </ul>
          <Paginare total={erori.length} offset={offset} limit={PAS_ERORI} onChange={setOffset} />
        </>
      )}
    </>
  )
}

function ItemEroare({ e, cuJob }: { e: EroareJob; cuJob: boolean }) {
  const { t, locale } = useLang()
  const linii = e.eroare.trim().split('\n')
  // la un traceback, rândul care spune ce s-a întâmplat e ultimul, nu primul
  const titlu = linii[0]!.startsWith('Traceback') ? linii[linii.length - 1]! : linii[0]!
  const lung = linii.length > 1 || titlu.length > 220
  return (
    <li>
      <div className="lg-eroare-meta">
        <span className="mono">{moment(e.created_at, locale)}</span>
        {cuJob && (
          <>
            <span>{numeTip(t, e.type, e.tip)}</span>
            <span>{e.nume_banca ?? e.banca ?? '—'}</span>
            <span className="mono">{t('lg.erori.job', { id: e.id_job })}</span>
          </>
        )}
        {e.context && <span className="mono lg-context" title={e.context}>{e.context}</span>}
      </div>
      {/* textul erorii vine din script: excepția Python, în engleză sau română, nu se traduce */}
      <div className="lg-eroare-titlu">{titlu.length > 220 ? `${titlu.slice(0, 220)}…` : titlu}</div>
      {lung && (
        <details className="lg-eroare-tot">
          <summary>{t('lg.erori.tot_textul')}</summary>
          <pre className="mono">{e.eroare}</pre>
        </details>
      )}
    </li>
  )
}
