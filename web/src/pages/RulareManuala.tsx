import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Button, Modal, Radio, Select, Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import { Rulari as RulariSchema, type RulareManualaCatalog } from '@mcc/shared'
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
 * un proces odată), iar sub buton stau rularea curentă și scripturile de colectare.
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
        <ModalJob cat={cat.data} m={meta.data} token={d.token ?? ''} onClose={() => setDeschis(false)} />
      )}
    </>
  )
}

function ModalJob({ cat, m, token, onClose }: { cat: RulareManualaCatalog; m: Meta; token: string; onClose: () => void }) {
  const { t, tn, lang, locale } = useLang()
  const { message } = App.useApp()
  const qc = useQueryClient()
  const durata = useDurata()
  const [tip, setTip] = useState('')
  const [banca, setBanca] = useState('')
  const [produs, setProdus] = useState('')
  const [pornire, setPornire] = useState(false)
  const [eroare, setEroare] = useState<string | null>(null)

  const ales = cat.tipuri.find((x) => x.id === tip)
  const cuProdus = ales?.produs === 'obligatoriu'
  const gata = !!ales && !!banca && (!cuProdus || !!produs)
  const est = useEstimareRulare(tip, banca, cuProdus ? produs : '', gata)
  const e = est.data
  const numeBanca = (b: string) => m.nume[b] ?? b
  const fara_surse = tip === 'extragere' && e?.surse && e.surse.gasite === 0

  const porneste = async () => {
    setPornire(true)
    setEroare(null)
    const r = await apiPost('/api/rulari/porneste', { id: tip, banca, produs: cuProdus ? produs : null }, token)
    setPornire(false)
    if (r.eroare) {
      setEroare(t('rm.nu_a_pornit', { eroare: deLaServer(r.eroare, lang) }))
      return
    }
    message.success(t('rm.pornit', {
      nume: numeTip(t, tip, ales?.denumire ?? tip), banca: numeBanca(banca), produs: cuProdus ? ` · ${produs}` : '',
    }), 6)
    await qc.invalidateQueries({ queryKey: ['rulari'] })
    onClose()
  }

  return (
    <Modal open onCancel={onClose} title={t('rm.modal_titlu')} width={720} destroyOnHidden
      footer={[
        <Button key="a" onClick={onClose}>{t('rm.anuleaza')}</Button>,
        <Button key="p" type="primary" loading={pornire} disabled={!gata || !e || !!fara_surse} onClick={porneste}>{t('rm.porneste')}</Button>,
      ]}>
      <div className="rm-pas">
        <h4>1 · {t('rm.pas_tip')}</h4>
        <Radio.Group className="rm-tipuri" value={tip} onChange={(x) => { setTip(x.target.value as string); setEroare(null) }}>
          {cat.tipuri.map((x) => (
            <Radio key={x.id} value={x.id} className="rm-tip">
              <b>{numeTip(t, x.id, x.denumire)}</b>
              <span className="sub">{t(`rm.tip.${x.id}.ce` as DictKey)}</span>
            </Radio>
          ))}
        </Radio.Group>
      </div>

      <div className="rm-pas">
        <h4>2 · {t('rm.pas_banca')}</h4>
        <Select showSearch value={banca || undefined} placeholder={t('rm.alege_banca')} style={{ width: '100%' }}
          optionFilterProp="nume" onChange={(v: string) => setBanca(v)}
          options={cat.banci
            .map((b) => ({ value: b, nume: numeBanca(b), label: <EtichetaBanca slug={b} m={m} /> }))
            .sort((a, b) => a.nume.localeCompare(b.nume, locale))} />
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
        <h4>{t('rm.estimare_titlu')}</h4>
        {!gata ? <p className="note">{t('rm.completeaza')}</p>
          : est.isLoading ? <p className="note">{t('comun.se_incarca')}</p>
          : est.error ? <p className="note" style={{ color: 'var(--warn)' }}>{(est.error as Error).message}</p>
          : e && (
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
