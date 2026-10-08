import { useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { App, AutoComplete, Button, Checkbox, Form, Input, Modal, Popconfirm, Radio, Segmented, Select, Tag, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { COD_PRODUS, SEGMENTE_LIBRA, type InventarProduse as Inventar, type ProdusDeSalvat, type ProdusInventar, type StareInBaza } from '@mcc/shared'
import { salveazaProdus, useInventarProduse, useTokenInventar, type ActiuneInventar } from '../api/inventar_produse'
import { Despre, Eroare, SeIncarca } from '../components/comune'
import { Tabel, type Coloana } from '../components/Tabel'
import { T, useLang, type DictKey } from '../i18n'
import { deLaServer } from '../i18n/server'
import { faraDiacritice, formatZi } from '../util/format'
import '../styles/inventar_produse.css'

/** Starea în bază nu e doar o culoare: simbolul o spune și la daltonism. */
const STARI: Record<StareInBaza, { simbol: string; culoare?: string }> = {
  identic: { simbol: '✓', culoare: 'success' },
  diferit: { simbol: '!', culoare: 'warning' },
  lipsa: { simbol: '+', culoare: 'processing' },
  inactiv: { simbol: '■', culoare: 'error' },
}

function StareBaza({ p }: { p: ProdusInventar }) {
  const { t } = useLang()
  if (!p.baza) return <span className="gri">—</span>
  const tag = (
    <Tag className="pill" color={STARI[p.baza].culoare} bordered>
      <span aria-hidden="true">{STARI[p.baza].simbol}</span> {t(`ip.baza.${p.baza}` as DictKey)}
    </Tag>
  )
  const titlu = p.baza === 'diferit'
    ? t('ip.baza.diferit_tooltip', { campuri: p.diferente.map((c) => t(`ip.camp.${c}` as DictKey)).join(', ') })
    : t(`ip.baza.${p.baza}_tooltip` as DictKey)
  return <Tooltip title={titlu}>{tag}</Tooltip>
}

/**
 * Inventar produse (Date & guvernanță): lista produselor Libra din
 * extragere_produse_bancare/produse_libra.json, axa comparației cu concurența.
 * Adăugarea, modificarea și ștergerea scriu în fișier, nu în bază; coloana
 * „În bază” arată ce n-a ajuns încă în tabela `produse_libra`. Filtrele stau în
 * adresă: `q` (cod sau denumire), `segment`.
 */
export default function InventarProduse() {
  const { t, tn, lang, locale } = useLang()
  const { message } = App.useApp()
  const qc = useQueryClient()
  const q = useInventarProduse()
  const tok = useTokenInventar()
  const [sp, setSp] = useSearchParams()
  const cauta = sp.get('q') ?? ''
  const segment = SEGMENTE_LIBRA.find((s) => s === sp.get('segment')) ?? ''
  // null = închis; { produs: null } = adăugare
  const [formular, setFormular] = useState<{ produs: ProdusInventar | null } | null>(null)
  const [sterge, setSterge] = useState<string | null>(null)

  const mergi = (k: Record<string, string>) => setSp((p) => {
    const n = new URLSearchParams(p)
    for (const [c, v] of Object.entries(k)) {
      if (v) n.set(c, v)
      else n.delete(c)
    }
    return n
  }, { replace: true })

  const d = q.data
  const lista = useMemo(() => {
    const ac = faraDiacritice(cauta.trim().toLowerCase())
    return (d?.produse ?? []).filter((p) => (!segment || p.segment === segment)
      && (!ac || faraDiacritice(`${p.cod} ${p.denumire} ${p.descriere ?? ''} ${p.categorie_cod ?? ''} ${p.tip_v2 ?? ''}`.toLowerCase()).includes(ac)))
  }, [d, cauta, segment])

  if (q.error) return <Eroare e={q.error} />
  if (!d) return <SeIncarca />

  const token = tok.data?.token
  const motivBlocat = token ? null : tok.isLoading ? t('comun.se_incarca') : t('ip.doar_citire')
  const nesincronizate = d.produse.filter((p) => p.baza && p.baza !== 'identic').length
  const faraTip = d.produse.filter((p) => !p.tip_v2).map((p) => p.cod)
  const numeTip = new Map(d.tipuri_v2.map((x) => [x.id, x.nume]))

  const salveaza = async (actiune: ActiuneInventar, produs: ProdusDeSalvat | { cod: string }) => {
    const r = await salveazaProdus(actiune, produs, d.versiune, token ?? '')
    if (r.eroare) return deLaServer(r.eroare, lang)
    message.success(t(`ip.ok.${actiune}` as DictKey, { cod: produs.cod }))
    await qc.invalidateQueries({ queryKey: ['inventar_produse'] })
    return null
  }

  const stergeProdus = async (cod: string) => {
    setSterge(cod)
    const eroare = await salveaza('sterge', { cod })
    setSterge(null)
    if (eroare) message.error(t('ip.nu_s_a_salvat', { eroare }), 8)
  }

  const coloane: Coloana<ProdusInventar>[] = [
    { cheie: 'cod', cap: t('ip.camp.cod'), s: (p) => p.cod, val: (p) => <span className="mono">{p.cod}</span> },
    // denumirile vin din catalogul Libra: nu se traduc
    {
      cheie: 'denumire', cap: t('ip.camp.denumire'), s: (p) => p.denumire,
      val: (p) => (
        <>
          {p.prioritar && <Tooltip title={t('ip.prioritar')}><span className="ip-stea" aria-label={t('ip.prioritar')}>★</span></Tooltip>}{p.denumire}
          {p.descriere
            ? <Tooltip title={p.descriere} placement="bottomLeft"><span className="sub ip-descriere">{p.descriere}</span></Tooltip>
            : <span className="sub ip-descriere">{t('ip.fara_descriere')}</span>}
        </>
      ),
    },
    { cheie: 'segment', cap: t('ip.camp.segment'), s: (p) => p.segment, val: (p) => p.segment ?? <span className="gri">—</span> },
    {
      cheie: 'categorie', cap: t('ip.camp.categorie_cod'), s: (p) => p.categorie_cod,
      val: (p) => p.categorie_cod ? <span className="mono">{p.categorie_cod}</span> : <span className="gri">—</span>,
    },
    {
      cheie: 'tip_v2', cap: t('ip.camp.tip_v2'), titlu: t('ip.col.tip_v2_titlu'), s: (p) => p.tip_v2,
      val: (p) => p.tip_v2
        ? <Tooltip title={numeTip.get(p.tip_v2)}><span className="mono ip-nowrap">{p.tip_v2}</span></Tooltip>
        : <Tooltip title={t('ip.fara_tip_tooltip')}><span className="ip-lipsa">{t('ip.fara_tip')}</span></Tooltip>,
    },
    {
      cheie: 'baza', cap: t('ip.col.baza'), titlu: t('ip.col.baza_titlu'),
      s: (p) => (p.baza ? ['identic', 'inactiv', 'lipsa', 'diferit'].indexOf(p.baza) : null), val: (p) => <StareBaza p={p} />,
    },
    {
      cheie: 'actiuni', cap: '',
      val: (p) => (
        <Tooltip title={motivBlocat}>
          <span className="ip-actiuni">
            <Button size="small" type="link" disabled={!token} onClick={() => setFormular({ produs: p })}>{t('ip.editeaza')}</Button>
            <Popconfirm title={t('ip.sterge_titlu', { cod: p.cod })} description={<p className="ip-confirma">{t('ip.sterge_text')}</p>}
              okText={t('ip.sterge')} okButtonProps={{ danger: true }} cancelText={t('ip.anuleaza')} onConfirm={() => stergeProdus(p.cod)}>
              <Button size="small" type="link" danger disabled={!token} loading={sterge === p.cod}>{t('ip.sterge')}</Button>
            </Popconfirm>
          </span>
        </Tooltip>
      ),
    },
  ]

  return (
    <>
      <section>
        <div className="ip-bara">
          <div className="filtre">
            <label className="f">{t('ip.cauta')}
              <Input className="cauta" allowClear placeholder={t('ip.cauta_placeholder')} value={cauta}
                onChange={(e) => mergi({ q: e.target.value })} />
            </label>
            <label className="f">{t('ip.camp.segment')}
              <Segmented value={segment || 'toate'} onChange={(v) => mergi({ segment: v === 'toate' ? '' : String(v) })}
                options={[{ value: 'toate', label: t('ip.toate') }, ...SEGMENTE_LIBRA.map((s) => ({ value: s, label: s }))]} />
            </label>
          </div>
          <div className="ip-dreapta">
            <span className="gri">{tn('ip.numar', d.produse.length, { afisate: lista.length })}</span>
            <Tooltip title={motivBlocat}>
              <Button type="primary" disabled={!token} onClick={() => setFormular({ produs: null })}>{t('ip.adauga')}</Button>
            </Tooltip>
          </div>
        </div>

        {!token && !tok.isLoading && <div className="callout warn ip-callout">{t('ip.doar_citire')}</div>}
        {faraTip.length > 0 && <div className="callout warn ip-callout">{tn('ip.fara_tip_avertisment', faraTip.length, { coduri: faraTip.join(', ') })}</div>}
        {!d.baza_disponibila && <div className="callout warn ip-callout">{t('ip.baza_indisponibila')}</div>}
        {(nesincronizate > 0 || d.doar_in_baza.length > 0) && (
          <div className="callout warn ip-callout">
            {nesincronizate > 0 && <>{tn('ip.nesincronizate', nesincronizate)} </>}
            {d.doar_in_baza.length > 0 && <>{tn('ip.doar_in_baza', d.doar_in_baza.length, { coduri: d.doar_in_baza.join(', ') })} </>}
            <T k="ip.cum_ajung" />
          </div>
        )}

        <Tabel randuri={lista} coloane={coloane} cheieRand={(p) => p.cod} implicit={['cod', 'ascend']}
          gol={d.produse.length ? t('ip.niciun_rezultat') : t('ip.gol')} />

        <p className="note ip-fisier">
          <T k="ip.fisier" params={{ fisier: <code>{d.fisier}</code>, data: formatZi(d.modificat, locale) }} />
        </p>
      </section>

      <Despre titlu="ip.despre_titlu">
        <p><T k="ip.despre_fisier" /></p>
        <p><T k="ip.despre_cod" /></p>
        <p><T k="ip.despre_tip_v2" /></p>
        <p><T k="ip.despre_sterge" /></p>
        <p><T k="ip.despre_descriere" /></p>
      </Despre>

      {formular && (
        <FormularProdus produs={formular.produs} inventar={d} onClose={() => setFormular(null)}
          onSalveaza={(p) => salveaza(formular.produs ? 'modifica' : 'adauga', p)} />
      )}
    </>
  )
}

interface Valori {
  cod: string
  denumire: string
  descriere?: string | null
  segment: ProdusDeSalvat['segment']
  categorie_cod?: string | null
  prioritar: boolean
  tip_v2: string
}

function FormularProdus({ produs, inventar, onClose, onSalveaza }: {
  produs: ProdusInventar | null
  inventar: Inventar
  onClose: () => void
  onSalveaza: (p: ProdusDeSalvat) => Promise<string | null>
}) {
  const { t } = useLang()
  const [form] = Form.useForm<Valori>()
  const [salvare, setSalvare] = useState(false)
  const [eroare, setEroare] = useState<string | null>(null)
  const nou = !produs
  const coduri = useMemo(() => new Set(inventar.produse.map((p) => p.cod)), [inventar])
  const categorii = useMemo(
    () => [...new Set(inventar.produse.map((p) => p.categorie_cod).filter((c): c is string => !!c))].sort(),
    [inventar],
  )

  const trimite = async (v: Valori) => {
    setSalvare(true)
    setEroare(null)
    const e = await onSalveaza({
      cod: v.cod.trim().toUpperCase(),
      denumire: v.denumire.trim(),
      descriere: v.descriere?.trim() || null,
      segment: v.segment,
      categorie_cod: v.categorie_cod?.trim().toUpperCase() || null,
      prioritar: v.prioritar,
      tip_v2: v.tip_v2,
    })
    setSalvare(false)
    if (e) setEroare(t('ip.nu_s_a_salvat', { eroare: e }))
    else onClose()
  }

  // codurile se scriu cu majuscule: ce se tastează se ridică pe loc, ca să nu existe două forme ale aceluiași cod
  const majuscule = (v: string | undefined) => v?.toUpperCase()

  return (
    <Modal open onCancel={onClose} destroyOnHidden width={560}
      title={nou ? t('ip.titlu_adauga') : t('ip.titlu_modifica', { cod: produs.cod })}
      okText={nou ? t('ip.adauga') : t('ip.salveaza')} cancelText={t('ip.anuleaza')}
      confirmLoading={salvare} onOk={() => form.submit()}>
      <Form<Valori> form={form} layout="vertical" requiredMark onFinish={trimite} className="ip-form"
        initialValues={produs
          ? {
            cod: produs.cod, denumire: produs.denumire, descriere: produs.descriere, segment: produs.segment ?? undefined,
            categorie_cod: produs.categorie_cod, prioritar: produs.prioritar, tip_v2: produs.tip_v2 ?? undefined,
          }
          : { prioritar: false }}>
        <Form.Item name="cod" label={t('ip.camp.cod')} normalize={majuscule}
          extra={nou ? t('ip.cod_ajutor') : t('ip.cod_blocat')}
          rules={nou ? [
            { required: true, message: t('ip.cod_obligatoriu') },
            { pattern: COD_PRODUS, message: t('ip.cod_format') },
            { validator: (_, v: string) => (v && coduri.has(v.trim()) ? Promise.reject(new Error(t('ip.cod_exista'))) : Promise.resolve()) },
          ] : []}>
          <Input className="mono" disabled={!nou} placeholder="CREDIT_SIMPLU_IMM" autoFocus={nou} />
        </Form.Item>
        <Form.Item name="denumire" label={t('ip.camp.denumire')}
          rules={[{ required: true, whitespace: true, message: t('ip.denumire_obligatorie') }, { max: 200, message: t('ip.denumire_lunga') }]}>
          <Input autoFocus={!nou} />
        </Form.Item>
        <Form.Item name="descriere" label={t('ip.camp.descriere')} extra={t('ip.descriere_ajutor')}
          rules={[{ max: 1000, message: t('ip.descriere_lunga') }]}>
          <Input.TextArea autoSize={{ minRows: 2, maxRows: 6 }} maxLength={1000} />
        </Form.Item>
        <Form.Item name="segment" label={t('ip.camp.segment')} rules={[{ required: true, message: t('ip.segment_obligatoriu') }]}>
          {/* Radio, nu Segmented: Segmented arată prima opțiune ca aleasă și când valoarea lipsește */}
          <Radio.Group optionType="button" buttonStyle="solid" options={[...SEGMENTE_LIBRA]} />
        </Form.Item>
        <Form.Item name="tip_v2" label={t('ip.camp.tip_v2')} extra={t('ip.tip_v2_ajutor')}
          rules={[{ required: true, message: t('ip.tip_v2_obligatoriu') }]}>
          <Select showSearch placeholder={t('ip.tip_v2_placeholder')} optionFilterProp="cauta"
            options={inventar.tipuri_v2.map((x) => ({
              value: x.id,
              cauta: `${x.nume} ${x.id}`,
              // numele tipurilor vin din produse_bancare_v2.json: nu se traduc
              label: <span className="ip-tip"><span>{x.nume}</span><span className="mono gri">{x.id}</span></span>,
            }))} />
        </Form.Item>
        <Form.Item name="categorie_cod" label={t('ip.camp.categorie_cod')} extra={t('ip.categorie_ajutor')} normalize={majuscule}
          rules={[{ pattern: COD_PRODUS, message: t('ip.cod_format') }]}>
          {/* o categorie nouă se tastează; cele existente se propun, ca să nu apară două forme ale aceleiași categorii */}
          <AutoComplete allowClear className="mono" placeholder={t('ip.categorie_placeholder')}
            options={categorii.map((c) => ({ value: c }))}
            filterOption={(input, o) => String(o?.value ?? '').includes(input.toUpperCase())} />
        </Form.Item>
        <Form.Item name="prioritar" valuePropName="checked">
          <Checkbox>{t('ip.camp.prioritar_lung')}</Checkbox>
        </Form.Item>
      </Form>
      {eroare && <div className="callout warn">{eroare}</div>}
    </Modal>
  )
}
