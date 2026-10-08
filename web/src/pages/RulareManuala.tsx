import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Modal, Radio, Select, Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import { Rulari as RulariSchema, type ComandaRulare, type RulareManualaCatalog } from '@mcc/shared'
import { api, apiPost } from '../api/client'
import { useMeta, type Meta } from '../api/meta'
import { useCatalogRulare, useEstimareRulare } from '../api/rulare_manuala'
import { EtichetaBanca, Eroare, SeIncarca } from '../components/comune'
import { useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { numeTip, usd } from './logging/format'
import Rulari, { useDurata } from './Rulari'
import '../styles/rulare_manuala.css'

/**
 * Rulare manuală (grupul Jobs): butonul „Începe job” deschide un modal în care se aleg
 * tipul jobului (discovery, extragere, produse noi), banca și, unde trebuie, produsul Libra;
 * cu toate alese apare estimarea de cost și durată din joburile încheiate. Pornirea trece
 * prin aceleași rute ca rulările din Overview (/api/rulari/porneste: listă fixă, token,
 * o rulare odată; pe mai multe bănci, câte `paralel_banci` simultan), iar sub buton stau
 * rularea curentă și scripturile de colectare.
 */
export default function RulareManuala() {
  const meta = useMeta()
  const rq = useQuery({
    queryKey: ['rulari'],
    queryFn: () => api('/api/rulari', RulariSchema),
    refetchInterval: (q) => (q.state.data?.curenta ? 2000 : false),
  })
  const cat = useCatalogRulare()
  const [deschis, setDeschis] = useState(false)
  const { t } = useLang()

  const err = meta.error ?? cat.error
  if (err) return <Eroare e={err} />
  if (!meta.data || !cat.data) return <SeIncarca />
  const d = rq.data
  const motiv = !d ? null : !d.activ ? t('rm.blocat_inactiv') : d.curenta ? t('rm.blocat_ruleaza') : null

  return (
    <>
      <section className="rm-start">
        <p className="note" style={{ margin: 0, maxWidth: '90ch' }}>{t('rm.intro')}</p>
        <div className="rm-start-butoane">
          <Tooltip title={motiv}>
            <Button type="primary" size="large" disabled={!d || !!motiv} onClick={() => setDeschis(true)}>{t('rm.incepe')}</Button>
          </Tooltip>
          <Link to="/logging">{t('rm.vezi_joburi')}</Link>
        </div>
      </section>
      <Rulari m={meta.data} />
      {deschis && d && (
        <ModalJob cat={cat.data} comenzi={d.comenzi} m={meta.data} token={d.token ?? ''} onClose={() => setDeschis(false)} />
      )}
    </>
  )
}

function ModalJob({ cat, comenzi, m, token, onClose }: {
  cat: RulareManualaCatalog; comenzi: ComandaRulare[]; m: Meta; token: string; onClose: () => void
}) {
  const { t, tn, lang, locale } = useLang()
  const { message } = App.useApp()
  const qc = useQueryClient()
  const durata = useDurata()
  const [tip, setTip] = useState('')
  // mai multe bănci odată: serverul le pune la coadă și rulează câte `paralel_banci` simultan (app/rulari.py)
  const [banci, setBanci] = useState<string[]>([])
  const [produs, setProdus] = useState('')
  const [pornire, setPornire] = useState(false)
  const [eroare, setEroare] = useState<string | null>(null)

  const ales = cat.tipuri.find((x) => x.id === tip)
  const lista = ales?.banci ?? cat.banci
  const cuProdus = ales?.produs === 'obligatoriu'
  const gata = !!ales && banci.length > 0 && (!cuProdus || !!produs)
  const est = useEstimareRulare(tip, banci, cuProdus ? produs : '', gata)
  const e = est.data
  const numeBanca = (b: string) => m.nume[b] ?? b
  const multi = banci.length > 1
  const paralel = comenzi.find((c) => c.id === tip)?.paralel_banci ?? 1
  const total = multi ? e?.total : null
  const fara_surse = tip === 'extragere' && !multi && e?.surse && e.surse.gasite === 0
  // la mai multe bănci, cele fără surse se pot scoate dintr-un clic; dacă nu rămâne niciuna, nu se pornește
  const toate_fara_surse = tip === 'extragere' && multi && !!total && total.fara_surse.length === banci.length

  const alegeTip = (x: string) => {
    setTip(x)
    setEroare(null)
    // aplicațiile mobile au altă listă de bănci decât extragerea: ce nu e în lista nouă cade
    const noua = cat.tipuri.find((y) => y.id === x)?.banci ?? cat.banci
    setBanci((v) => v.filter((b) => noua.includes(b)))
  }

  const porneste = async () => {
    setPornire(true)
    setEroare(null)
    const corp = multi ? { id: tip, banci, produs: cuProdus ? produs : null } : { id: tip, banca: banci[0], produs: cuProdus ? produs : null }
    const r = await apiPost('/api/rulari/porneste', corp, token)
    setPornire(false)
    if (r.eroare) {
      setEroare(t('rm.nu_a_pornit', { eroare: deLaServer(r.eroare, lang) }))
      return
    }
    const nume = numeTip(t, tip, ales?.denumire ?? tip)
    const prod = cuProdus ? ` · ${produs}` : ''
    message.success(multi ? t('rm.pornit_multi', { nume, n: banci.length, produs: prod })
      : t('rm.pornit', { nume, banca: numeBanca(banci[0]!), produs: prod }), 6)
    await qc.invalidateQueries({ queryKey: ['rulari'] })
    onClose()
  }

  return (
    <Modal open onCancel={onClose} title={t('rm.modal_titlu')} width={720} destroyOnHidden
      footer={[
        <Button key="a" onClick={onClose}>{t('rm.anuleaza')}</Button>,
        <Button key="p" type="primary" loading={pornire} disabled={!gata || !e || est.isFetching || !!fara_surse || toate_fara_surse} onClick={porneste}>
          {multi ? t('rm.porneste_multi', { n: banci.length }) : t('rm.porneste')}
        </Button>,
      ]}>
      <div className="rm-pas">
        <h4>1 · {t('rm.pas_tip')}</h4>
        <Radio.Group className="rm-tipuri" value={tip} onChange={(x) => alegeTip(x.target.value as string)}>
          {cat.tipuri.map((x) => (
            <Radio key={x.id} value={x.id} className="rm-tip">
              <b>{numeTip(t, x.id, x.denumire)}</b>
              <span className="sub">{t(`rm.tip.${x.id}.ce` as DictKey)}</span>
            </Radio>
          ))}
        </Radio.Group>
      </div>

      <div className="rm-pas">
        <div className="rm-pas-cap">
          <h4>2 · {t('rm.pas_banci')}</h4>
          <span className="rm-banci-butoane">
            <Button size="small" disabled={!ales || banci.length === lista.length} onClick={() => setBanci([...lista])}>
              {t('rm.toate_bancile', { n: lista.length })}
            </Button>
            <Button size="small" type="text" disabled={!banci.length} onClick={() => setBanci([])}>{t('rm.goleste')}</Button>
          </span>
        </div>
        <Select mode="multiple" allowClear showSearch value={banci} placeholder={t('rm.alege_banci')} style={{ width: '100%' }}
          maxTagCount="responsive" optionFilterProp="nume" onChange={(v: string[]) => setBanci(v)}
          options={lista
            .map((b) => ({ value: b, nume: numeBanca(b), label: <EtichetaBanca slug={b} m={m} /> }))
            .sort((a, b) => a.nume.localeCompare(b.nume, locale))} />
        {multi && <p className="note rm-nota-coada">{paralel > 1 && banci.length > 1 ? t('rm.in_paralel', { n: banci.length, p: paralel }) : t('rm.pe_rand', { n: banci.length })}</p>}
      </div>

      {cuProdus && (
        <div className="rm-pas">
          <h4>3 · {t('rm.pas_produs')}</h4>
          <Select showSearch value={produs || undefined} placeholder={t('rm.alege_produs')} style={{ width: '100%' }}
            optionFilterProp="cauta" onChange={(v: string) => setProdus(v)}
            options={cat.produse.map((p) => ({
              value: p.cod,
              cauta: `${p.denumire} ${p.cod}`,
              // denumirea produsului vine din catalogul Libra: nu se traduce
              label: (
                <span className="rm-produs">
                  <span>{p.denumire}</span>
                  <span className="mono gri">{p.cod}{p.segment ? ` · ${p.segment}` : ''}{p.prioritar ? ` · ${t('rm.prioritar')}` : ''}</span>
                </span>
              ),
            }))} />
        </div>
      )}

      <div className="rm-estimare">
        <h4>{multi ? t('rm.estimare_titlu_multi', { n: banci.length }) : t('rm.estimare_titlu')}</h4>
        {!gata ? <p className="note">{t('rm.completeaza')}</p>
          : est.isLoading ? <p className="note">{t('comun.se_incarca')}</p>
          : est.error ? <p className="note" style={{ color: 'var(--warn)' }}>{(est.error as Error).message}</p>
          : e && multi ? (
            total ? (
              <>
                <div className="rm-cifre">
                  <div>
                    <span className="gri">{t('rm.cost_total')}</span>
                    <b>~{usd(total.cost_med ?? 0, locale)}</b>
                    {(total.cost_max ?? 0) > (total.cost_min ?? 0) && (
                      <span className="sub">{t('rm.interval_cost', { min: usd(total.cost_min ?? 0, locale), max: usd(total.cost_max ?? 0, locale) })}</span>
                    )}
                  </div>
                  <div>
                    <span className="gri">{t('rm.durata_totala')}</span>
                    <b>~{durata(total.durata_med)}</b>
                    {total.durata_max != null && total.durata_max > (total.durata_med ?? 0) && (
                      <span className="sub">{t('rm.durata_max', { max: durata(total.durata_max) })}</span>
                    )}
                  </div>
                  <p className="sub rm-baza">{(total.paralel_banci ?? 1) > 1 ? t('rm.baza_multi_paralel', { n: total.n_banci, p: total.paralel_banci ?? 1 }) : t('rm.baza_multi', { n: total.n_banci })} {t('rm.nota_cost')}</p>
                </div>
                {total.fara_estimare.length > 0 && (
                  <p className="note">{tn('rm.fara_estimare_multi', total.fara_estimare.length, { banci: total.fara_estimare.map(numeBanca).join(', ') })}</p>
                )}
                {total.fara_surse.length > 0 && (
                  <div className="callout warn">
                    {tn('rm.fara_surse_multi', total.fara_surse.length, { banci: total.fara_surse.map(numeBanca).join(', ') })}{' '}
                    {!toate_fara_surse && (
                      <Button size="small" onClick={() => setBanci((v) => v.filter((b) => !total.fara_surse.includes(b)))}>
                        {t('rm.scoate_fara_surse')}
                      </Button>
                    )}
                  </div>
                )}
              </>
            ) : <p className="note">{t('rm.fara_istoric')}</p>
          ) : e && (
            <>
              {e.estimare ? (
                <div className="rm-cifre">
                  <div>
                    <span className="gri">{t('rm.cost')}</span>
                    <b>~{usd(e.estimare.cost_med, locale)}</b>
                    {e.estimare.cost_max > e.estimare.cost_min && (
                      <span className="sub">{t('rm.interval_cost', { min: usd(e.estimare.cost_min, locale), max: usd(e.estimare.cost_max, locale) })}</span>
                    )}
                  </div>
                  <div>
                    <span className="gri">{t('rm.durata')}</span>
                    <b>~{durata(e.estimare.durata_med)}</b>
                    {e.estimare.durata_max != null && e.estimare.durata_max > (e.estimare.durata_med ?? 0) && (
                      <span className="sub">{t('rm.durata_max', { max: durata(e.estimare.durata_max) })}</span>
                    )}
                  </div>
                  <p className="sub rm-baza">{tn(`rm.baza.${e.estimare.nivel}`, e.estimare.n)}. {t('rm.nota_cost')}</p>
                </div>
              ) : <p className="note">{t('rm.fara_istoric')}</p>}
              {e.surse && (
                fara_surse
                  ? <div className="callout warn">{e.surse.negasite > 0 ? t('rm.negasit_anterior') + ' ' : ''}{t('rm.fara_surse')}</div>
                  : tip === 'extragere'
                    ? <p className="note">{tn('rm.surse_extragere', e.surse.gasite)}</p>
                    : e.surse.gasite > 0
                      ? <p className="note">{tn('rm.surse_existente', e.surse.gasite, { data: e.surse.ultima ?? '—' })}</p>
                      : e.surse.negasite > 0 ? <p className="note">{t('rm.negasit_anterior')}</p> : null
              )}
            </>
          )}
        {eroare && <div className="callout warn" style={{ marginTop: 10 }}>{eroare}</div>}
      </div>
    </Modal>
  )
}
