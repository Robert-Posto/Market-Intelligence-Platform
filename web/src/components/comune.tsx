import type { ReactNode } from 'react'
import { Collapse, Tag, Tooltip } from 'antd'
import { Link } from 'react-router-dom'
import { SERVER_OPRIT } from '../api/client'
import type { Meta } from '../api/meta'
import { T, useLang, type DictKey } from '../i18n'
import { zileDeLa } from '../util/format'

/** Numele și sigla băncii; `fisa` duce la fișa băncii, `tag` marchează Libra cu „noi”. */
export function EtichetaBanca({ slug, m, fisa, tag }: { slug: string; m: Meta; fisa?: boolean; tag?: boolean }) {
  const { t } = useLang()
  const logo = m.logo[slug]
  const corp = (
    <span className="cl-banca">
      {logo && <img src={logo} alt="" />}
      <span className="nm">{m.nume[slug] ?? slug}</span>
      {tag && slug === 'libra' && <span className="tag-libra">{t('comun.tag_libra_noi')}</span>}
    </span>
  )
  if (!fisa) return corp
  return (
    <Tooltip title={t('comun.eticheta_banca.tooltip_fisa', { banca: m.nume[slug] ?? slug })}>
      {/* clicul pe nume nu ajunge la rândul de sub el */}
      <Link className="fisa" to={`/banca?b=${encodeURIComponent(slug)}`} onClick={(e) => e.stopPropagation()}>
        {corp}
      </Link>
    </Tooltip>
  )
}

/** Vârsta unei date: verde sub 7 zile, fără culoare până la 30, portocaliu peste. */
export function Varsta({ t: data }: { t: string | null | undefined }) {
  const { t, tn } = useLang()
  if (!data) return <Pill>{t('comun.varsta.fara_data')}</Pill>
  const z = zileDeLa(data)
  if (z <= 0) return <Pill tip="ok">{t('comun.varsta.azi')}</Pill>
  const txt = tn('comun.varsta.acum_zile', z, { z })
  return <Pill tip={z < 7 ? 'ok' : z > 30 ? 'amb' : undefined}>{txt}</Pill>
}

/** Pastila din aplicația veche, ca Tag AntD: neutră, verde (ok) sau portocalie (amb). */
export function Pill({ tip, title, children }: { tip?: 'ok' | 'amb'; title?: string; children: ReactNode }) {
  const tag = (
    <Tag className="pill" color={tip === 'ok' ? 'success' : tip === 'amb' ? 'warning' : undefined} bordered>
      {children}
    </Tag>
  )
  return title ? <Tooltip title={title}>{tag}</Tooltip> : tag
}

/** Explicațiile lungi, pliate: pagina începe cu datele, nu cu textul. */
export function Despre({ children, titlu }: { children: ReactNode; titlu?: DictKey }) {
  const { t } = useLang()
  return (
    <Collapse
      ghost
      className="despre"
      items={[{ key: 'd', label: <span className="despre-cap">ⓘ {t(titlu ?? 'comun.despre_date')}</span>, children: <div className="note">{children}</div> }]}
    />
  )
}

/** Secțiune pliabilă cu titlu h2 (Ce avem pe fiecare bancă, Detalii tehnice, Rulări). */
export function Pliat({ titlu, children, deschis }: { titlu: ReactNode; children: ReactNode; deschis?: boolean }) {
  return (
    <Collapse
      ghost
      className="pliat"
      defaultActiveKey={deschis ? ['p'] : []}
      items={[{ key: 'p', label: <h2>{titlu}</h2>, children }]}
    />
  )
}

export function Eroare({ e }: { e: unknown }) {
  const { t } = useLang()
  const mesaj = e instanceof Error ? e.message : String(e)
  if (mesaj === SERVER_OPRIT) {
    return (
      <section>
        <p className="note" style={{ color: 'var(--warn)', margin: 0 }}>
          {t('comun.server_oprit')}
          {import.meta.env.DEV && <> {t('comun.server_oprit_dev')}</>}
        </p>
      </section>
    )
  }
  return (
    <section>
      <p className="note" style={{ color: 'var(--warn)' }}>
        <T k="comun.eroare" params={{ mesaj }} />
      </p>
    </section>
  )
}

export function SeIncarca() {
  const { t } = useLang()
  return (
    <section>
      <p className="note">{t('comun.se_incarca')}</p>
    </section>
  )
}
