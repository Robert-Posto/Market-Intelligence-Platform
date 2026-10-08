import { useMemo, useState } from 'react'
import { Button, Modal, Segmented } from 'antd'
import { BarChartOutlined } from '@ant-design/icons'
import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { Meta } from '../../../api/meta'
import { Tabel, type Coloana } from '../../../components/Tabel'
import { useLang } from '../../../i18n'
import { num } from '../../../util/format'
import { googlePlay } from '../dateLocale'

interface Rand {
  banca: string
  nume: string
  descarcari: number
  prag: string | null
}

const RAND_PX = 26
// 1.990 (BRCI) … 94 de milioane (Revolut), 07.10.2026: pe scară liniară, Libra (187 de mii) ar avea
// 0,2% din bara Revolut, iar 9 bănci n-ar avea bară deloc. Implicit logaritmic, cu valoarea la capăt.
const TICKS_LOG = [1e3, 1e4, 1e5, 1e6, 1e7, 1e8]
const ANIMATIE_MS = 900

/** „Reduce motion” din sistem: fără animații, nici la modal, nici la bare. */
const faraMiscare = () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

function useDate(m: Meta): Rand[] {
  return useMemo(() => Object.entries(googlePlay?.aplicatii ?? {})
    .filter(([, x]) => (x.descarcari ?? 0) > 0)
    .map(([banca, x]) => ({ banca, nume: m.nume[banca] ?? banca, descarcari: x.descarcari!, prag: x.prag_descarcari }))
    .sort((a, b) => b.descarcari - a.descarcari), [m])
}

/**
 * Butonul „Arată grafic” din capul secțiunii Google Play și modalul cu descărcările pe bancă,
 * din `date/google_play.json` (colectorul Node). Doar Android: App Store nu publică descărcările.
 */
export default function GraficDescarcari({ m }: { m: Meta }) {
  const { t } = useLang()
  const [deschis, setDeschis] = useState(false)
  // barele se desenează abia după animația modalului: în timpul ei, ResponsiveContainer
  // măsoară o lățime încă neașezată, iar animația barelor ar rula nevăzută
  const [gata, setGata] = useState(false)
  const date = useDate(m)
  if (!date.length) return null
  const static_ = faraMiscare()

  return (
    <>
      <Button icon={<BarChartOutlined />} onClick={() => setDeschis(true)}>{t('mobil.desc_buton')}</Button>
      <Modal open={deschis} centered width={1000} footer={null} destroyOnHidden
        title={t('mobil.desc_titlu')}
        transitionName={static_ ? '' : undefined} maskTransitionName={static_ ? '' : undefined}
        onCancel={() => setDeschis(false)}
        afterOpenChange={(o) => setGata(o)}>
        <Continut date={date} m={m} gata={gata || static_} animat={!static_} />
      </Modal>
    </>
  )
}

/**
 * Forma „evidențiere”: Libra în accent, restul în gri de context, deci fără legendă; Libra se
 * recunoaște și după nume (îngroșat), nu doar după culoare. Valoarea stă la capătul fiecărei bare,
 * iar „Tabel” arată aceleași cifre ca text.
 */
function Continut({ date, m, gata, animat }: { date: Rand[]; m: Meta; gata: boolean; animat: boolean }) {
  const { t, locale } = useLang()
  const [scara, setScara] = useState<'log' | 'liniar'>('log')
  const [vedere, setVedere] = useState<'grafic' | 'tabel'>('grafic')
  const compact = useMemo(() => new Intl.NumberFormat(locale, { notation: 'compact', maximumFractionDigits: 1 }), [locale])
  const fmt = (v: number) => compact.format(v)
  const inaltime = date.length * RAND_PX + 36

  const coloane: Coloana<Rand>[] = [
    { cheie: 'banca', cap: t('mobil.desc_col_banca'), s: (r) => r.nume, val: (r) => (r.banca === 'libra' ? <b>{r.nume}</b> : r.nume) },
    { cheie: 'descarcari', cap: t('mobil.desc_col_estimare'), num: true, s: (r) => r.descarcari, val: (r) => num(r.descarcari, locale, 0) },
    { cheie: 'prag', cap: t('mobil.desc_col_prag'), num: true, s: (r) => r.descarcari, val: (r) => r.prag ?? '—' },
  ]

  return (
    <div className="dl-sec">
      <div className="dl-cap">
        <p className="note" style={{ margin: 0 }}>{t('mobil.desc_sub', { n: date.length })}</p>
        <div className="dl-comenzi">
          {vedere === 'grafic' && (
            <Segmented size="small" value={scara} onChange={(v) => setScara(v as 'log' | 'liniar')}
              options={[{ value: 'log', label: t('mobil.desc_log') }, { value: 'liniar', label: t('mobil.desc_liniar') }]} />
          )}
          <Segmented size="small" value={vedere} onChange={(v) => setVedere(v as 'grafic' | 'tabel')}
            options={[{ value: 'grafic', label: t('mobil.desc_grafic') }, { value: 'tabel', label: t('mobil.desc_tabel') }]} />
        </div>
      </div>

      {vedere === 'tabel' ? (
        <div className="dl-tabel">
          <Tabel randuri={date} coloane={coloane} cheieRand={(r) => r.banca} libra={(r) => r.banca} implicit={['descarcari', 'descend']} />
        </div>
      ) : (
        <>
          <div className="dl-grafic" role="img" style={{ height: inaltime }}
            aria-label={t('mobil.desc_aria', { n: date.length, prima: date[0]!.nume, libra: fmt(date.find((r) => r.banca === 'libra')?.descarcari ?? 0) })}>
            {gata && (
              <ResponsiveContainer width="100%" height={inaltime}>
                <BarChart data={date} layout="vertical" margin={{ top: 4, right: 64, bottom: 4, left: 4 }} barCategoryGap={RAND_PX - 16}>
                  <CartesianGrid horizontal={false} stroke="var(--line)" />
                  <XAxis type="number" dataKey="descarcari" orientation="top"
                    scale={scara === 'log' ? 'log' : 'linear'}
                    domain={scara === 'log' ? [1e3, 2e8] : [0, 'auto']}
                    ticks={scara === 'log' ? TICKS_LOG : undefined}
                    allowDataOverflow tickFormatter={fmt} axisLine={false} tickLine={false}
                    tick={{ fill: 'var(--muted)', fontSize: 11 }} />
                  <YAxis type="category" dataKey="banca" width={190} interval={0} axisLine={false} tickLine={false}
                    tick={(p) => <EtichetaBanca x={Number(p.x)} y={Number(p.y)} slug={String(p.payload.value)} m={m} />} />
                  <Tooltip cursor={{ fill: 'var(--accent-tint)' }} isAnimationActive={false}
                    content={({ active, payload }) => {
                      const r = active && payload?.[0] ? (payload[0].payload as Rand) : null
                      return r ? (
                        <div className="dl-tip">
                          <b>{r.nume}</b>
                          <div>{t('mobil.desc_tip_estimare', { n: num(r.descarcari, locale, 0) })}</div>
                          <div className="gri">{t('mobil.desc_tip_prag', { prag: r.prag ?? '—' })}</div>
                        </div>
                      ) : null
                    }} />
                  {/* appear: barele cresc din axă; la schimbarea scării, Recharts animează trecerea */}
                  <Bar dataKey="descarcari" barSize={16} radius={[0, 4, 4, 0]}
                    isAnimationActive={animat} animationBegin={0} animationDuration={ANIMATIE_MS} animationEasing="ease-out">
                    {date.map((r) => <Cell key={r.banca} fill={r.banca === 'libra' ? 'var(--dl-libra)' : 'var(--dl-rest)'} />)}
                    <LabelList dataKey="descarcari" position="right" formatter={(v: unknown) => fmt(Number(v))}
                      style={{ fill: 'var(--ink)', fontSize: 11, fontFamily: 'var(--mono)' }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
          <p className="note dl-nota">{scara === 'log' ? t('mobil.desc_nota_log') : t('mobil.desc_nota_liniar')} {t('mobil.desc_nota_sursa')}</p>
        </>
      )}
    </div>
  )
}

/** Numele băncii pe axă, tăiat la 26 de caractere („ING Bank (Sucursala București)”); Libra îngroșată. */
function EtichetaBanca({ x, y, slug, m }: { x: number; y: number; slug: string; m: Meta }) {
  const nume = m.nume[slug] ?? slug
  const scurt = nume.length > 26 ? `${nume.slice(0, 25)}…` : nume
  return (
    <text x={x - 6} y={y} dy={4} textAnchor="end" fontSize={12} fill="var(--ink)"
      fontWeight={slug === 'libra' ? 700 : 400}>
      <title>{nume}</title>
      {scurt}
    </text>
  )
}
