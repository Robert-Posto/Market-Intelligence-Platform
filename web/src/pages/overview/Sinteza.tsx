import { useEffect, useRef, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Select, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { Rulari as RulariSchema, type ContinutNews } from '@mcc/shared'
import { api, apiPost } from '../../api/client'
import { useMeta, type Meta } from '../../api/meta'
import { useNews } from '../../api/news'
import { useRol } from '../../auth'
import { Eroare, SeIncarca } from '../../components/comune'
import { useLang, type DictKey } from '../../i18n'
import '../../styles/sinteza.css'

/** id-ul din app/rulari.py (COMENZI) al scriptului ingest/brief_stiri.py */
const COMANDA = 'brief_stiri'

/** „09.10.2026, 16:20”, în fusul browserului (created_at vine în UTC). */
function momentul(iso: string, locale: string) {
  return new Date(iso).toLocaleString(locale, { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

/**
 * Containerul „Sinteză” din Overview (09.10.2026: o vreme pagină separată, „Sinteza zilei”): brief-ul
 * de știri din piața bancară (tabela `news`), cu butonul
 * care pornește unul nou prin rulările manuale (`brief_stiri`: colectare, curățare, model). Fiecare
 * câmp din `continut` e un card: titlul e câmpul (Sinteză, Alerte, ...), dedesubt textul lui. Butonul
 * e doar al adminului, ca restul rulărilor; un brief mai vechi se alege din listă (`?sinteza=<id>`).
 */
export default function Sinteza() {
  const { t, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const ales = Number(sp.get('sinteza')) || undefined
  const q = useNews(ales)
  const meta = useMeta()

  if (q.error) return <Eroare e={q.error} />
  if (!q.data || !meta.data) return <div className="sz"><SeIncarca /></div>
  const d = q.data
  if (!d.disponibil) {
    return (
      <div className="sz">
        <header className="sz-cap"><h2>{t('sz.titlu_gol')}</h2></header>
        <p className="note">{t('sz.nedisponibil', { motiv: d.motiv })}</p>
      </div>
    )
  }
  const b = d.brief
  const alege = (id: number) => setSp((p) => {
    const n = new URLSearchParams(p)
    if (id === d.istoric[0]?.id) n.delete('sinteza')
    else n.set('sinteza', String(id))
    return n
  }, { replace: true })

  return (
    <div className="sz">
      <header className="sz-cap">
        <div>
          <h2>{b ? t('sz.titlu', { data: momentul(b.created_at, locale) }) : t('sz.titlu_gol')}</h2>
          {b && (
            <div className="note">
              {t('sz.subtitlu', {
                stiri: b.continut.generare.nr_stiri, subiecte: b.continut.generare.nr_subiecte,
                de_la: momentul(b.continut.perioada.de_la, locale), pana_la: momentul(b.continut.perioada.pana_la, locale),
              })}
            </div>
          )}
        </div>
        <div className="sz-actiuni">
          {d.istoric.length > 1 && (
            <Select
              size="small"
              className="sz-istoric"
              aria-label={t('sz.mai_veche')}
              title={t('sz.mai_veche')}
              value={b?.id}
              onChange={alege}
              options={d.istoric.map((x) => ({ value: x.id, label: momentul(x.created_at, locale) }))}
            />
          )}
          <Refresh ultimul={d.istoric[0]?.id ?? null} />
        </div>
      </header>
      {b ? <Carduri c={b.continut} m={meta.data} /> : <p className="note">{t('sz.gol')}</p>}
    </div>
  )
}

/** Butonul de refresh: pornește `brief_stiri`, arată cât a trecut și reîncarcă sinteza la final. */
function Refresh({ ultimul }: { ultimul: number | null }) {
  const { t } = useLang()
  const { message } = App.useApp()
  const admin = useRol() === 'admin'
  const qc = useQueryClient()
  const rq = useQuery({
    queryKey: ['rulari'],
    queryFn: () => api('/api/rulari', RulariSchema),
    enabled: admin,
    retry: false,
    refetchInterval: (x) => (x.state.data?.curenta ? 2000 : false),
  })
  const r = rq.data
  const curenta = r?.curenta ?? null
  const ruleaza = curenta?.id === COMANDA
  // la final (rula → nu mai rulează): sinteza nouă sau motivul pentru care nu e
  const inainte = useRef<{ ruleaza: boolean; ultimul: number | null }>({ ruleaza: false, ultimul })
  useEffect(() => {
    const p = inainte.current
    if (p.ruleaza && !ruleaza && r) {
      const cod = r.comenzi.find((c) => c.id === COMANDA)?.ultima?.cod
      void qc.invalidateQueries({ queryKey: ['news'] }).then(() => {
        const nou = qc.getQueryData<{ disponibil: boolean; istoric?: { id: number }[] }>(['news', 'ultimul'])?.istoric?.[0]?.id
        if (cod !== 0) message.error(t('sz.esuat'))
        else if (nou === p.ultimul) message.info(t('sz.fara_nou'))
      })
    }
    inainte.current = { ruleaza, ultimul: ruleaza ? p.ultimul : ultimul }
  }, [ruleaza, r, ultimul, qc, message, t])

  if (!admin) return null
  const motiv = rq.error ? t('sz.blocat_rulari')
    : !r ? null
      : !r.activ ? t('sz.blocat_inactiv')
        : curenta && !ruleaza ? t('sz.blocat_ruleaza', { nume: curenta.nume })
          : null
  const scurs = curenta?.scurs_s ?? 0
  const porneste = async () => {
    const x = await apiPost('/api/rulari/porneste', { id: COMANDA }, r?.token ?? '')
    if (x.eroare) {
      message.error(x.eroare)
      return
    }
    inainte.current = { ruleaza: true, ultimul }
    message.info(t('sz.pornit'))
    await qc.invalidateQueries({ queryKey: ['rulari'] })
  }
  return (
    <Tooltip title={motiv ?? t('sz.refresh_titlu')}>
      <Button size="small" type="primary" loading={ruleaza} disabled={!r || !!motiv} onClick={porneste}>
        {ruleaza
          ? t('sz.se_genereaza', { scurs: `${Math.floor(scurs / 60)}:${String(scurs % 60).padStart(2, '0')}` })
          : t('sz.refresh')}
      </Button>
    </Tooltip>
  )
}

const GRAVITATE: Record<ContinutNews['alerte'][number]['gravitate'], DictKey> = {
  critica: 'sz.grav.critica', ridicata: 'sz.grav.ridicata', medie: 'sz.grav.medie', scazuta: 'sz.grav.scazuta',
}
const DIRECTIE: Record<ContinutNews['trenduri'][number]['directie'], [string, DictKey]> = {
  crestere: ['↑', 'sz.dir.crestere'], scadere: ['↓', 'sz.dir.scadere'], stabil: ['→', 'sz.dir.stabil'], nou: ['✦', 'sz.dir.nou'],
}

/** Un card: titlul e câmpul din `continut`, cu numărul de elemente; dedesubt, textul lui. */
function Card({ titlu, n, lat, clasa, children }: {
  titlu: string; n?: number; lat?: boolean; clasa?: string; children: ReactNode
}) {
  const { t } = useLang()
  return (
    <article className={`sz-card${lat ? ' sz-card-lat' : ''}${clasa ? ` ${clasa}` : ''}`}>
      <h3>{titlu}{n !== undefined && <span className="sz-n">{n}</span>}</h3>
      {n === 0 ? <p className="sz-gol">{t('sz.nimic')}</p> : children}
    </article>
  )
}

function Carduri({ c, m }: { c: ContinutNews; m: Meta }) {
  const { t, locale } = useLang()
  const surse = new Map(c.surse.map((s) => [s.id, s]))
  // trimiterile la știri: [3] cu linkul articolului; titlul și publicația în tooltip
  const Citate = ({ ids }: { ids: number[] }) => (
    <span className="sz-citate">
      {ids.map((i) => {
        const s = surse.get(i)
        return s
          ? <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" title={`${s.titlu} · ${s.publicatie}`}>{i}</a>
          : null
      })}
    </span>
  )
  const banca = (slug: string) => m.nume[slug] ?? slug

  return (
    <div className="sz-grila">
      <Card titlu={t('sz.sec.sinteza')} lat clasa="sz-card-sinteza">
        <p className="sz-text">{c.sinteza}</p>
      </Card>

      <Card titlu={t('sz.sec.alerte')} n={c.alerte.length}>
        {c.alerte.map((a, i) => (
          <div key={i} className="sz-el">
            <div className="sz-el-cap">
              <span className={`sz-eticheta sz-grav-${a.gravitate}`}>{t(GRAVITATE[a.gravitate])}</span>
              <b>{a.titlu}</b> <Citate ids={a.surse} />
            </div>
            <p>{a.descriere}</p>
            <p><b>{t('sz.impact_libra')}</b> {a.impact_libra}</p>
            {a.banci.length > 0 && <p className="sz-mic">{a.banci.map(banca).join(' · ')}</p>}
          </div>
        ))}
      </Card>

      <Card titlu={t('sz.sec.oportunitati')} n={c.oportunitati.length}>
        {c.oportunitati.map((x, i) => (
          <div key={i} className="sz-el">
            <div className="sz-el-cap">
              <span className="sz-eticheta">{t(`sz.tip.${x.tip}` as DictKey)}</span>
              <b>{x.titlu}</b> <Citate ids={x.surse} />
            </div>
            <p>{x.propunere}</p>
            <p className="gri"><b>{t('sz.argument')}</b> {x.argument}</p>
          </div>
        ))}
      </Card>

      <Card titlu={t('sz.sec.concurenta')} n={c.concurenta.length}>
        {c.concurenta.map((x, i) => (
          <div key={i} className="sz-el">
            <p><b>{banca(x.banca)}</b> — {x.descriere} <Citate ids={x.surse} /></p>
          </div>
        ))}
      </Card>

      <Card titlu={t('sz.sec.trenduri')} n={c.trenduri.length}>
        {c.trenduri.map((x, i) => (
          <div key={i} className="sz-el">
            <div className="sz-el-cap">
              <span className={`sz-eticheta sz-dir-${x.directie}`}>{DIRECTIE[x.directie][0]} {t(DIRECTIE[x.directie][1])}</span>
              <b>{x.tema}</b> <Citate ids={x.surse} />
            </div>
            <p>{x.descriere}</p>
          </div>
        ))}
      </Card>

      <Card titlu={t('sz.sec.predictii')} n={c.predictii.length}>
        {c.predictii.map((x, i) => (
          <div key={i} className="sz-el">
            <div className="sz-el-cap"><b>{x.enunt}</b> <Citate ids={x.surse} /></div>
            <p className="sz-mic">{t(`sz.incr.${x.incredere}` as DictKey)} · {t('sz.orizont', { o: x.orizont })}</p>
            <p className="gri">{x.argument}</p>
          </div>
        ))}
      </Card>

      <Card titlu={t('sz.sec.surse_titlu')} n={c.surse.length} clasa="sz-card-surse">
        <ol className="sz-surse">
          {c.surse.map((s) => (
            <li key={s.id} value={s.id}>
              <a className="sursa" href={s.url} target="_blank" rel="noopener noreferrer">{s.titlu}</a>
              <span className="gri"> · {s.publicatie} · {momentul(s.publicat_la, locale)}</span>
            </li>
          ))}
        </ol>
      </Card>

      <p className="note sz-nota">{t('sz.nota', { model: c.generare.model })}</p>
    </div>
  )
}
