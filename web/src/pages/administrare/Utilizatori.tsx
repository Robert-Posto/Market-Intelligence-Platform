import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { App, Select, Switch, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import type { ContAplicatie, RolCont } from '@mcc/shared'
import { ApiError } from '../../api/client'
import { modificaCont, useConturi } from '../../api/utilizatori'
import { useSesiune } from '../../auth'
import { Comutator } from '../../components/Comutator'
import { Eroare, Pill, SeIncarca } from '../../components/comune'
import { Tabel, type Coloana } from '../../components/Tabel'
import { T, useLang, type DictKey } from '../../i18n'
import { moment } from '../logging/format'
import '../../styles/utilizatori.css'

/** Codurile de eroare ale lui POST /api/utilizatori/modifica care au text propriu; restul, generic. */
const ERORI_CU_TEXT = new Set(['propriul_cont', 'ultimul_admin', 'inexistent', 'interzis'])

/**
 * Tab-ul „Utilizatori” din Administrare: rolul fiecărui cont (admin, analist sau fără rol) și starea lui.
 * AD-ul verifică doar parola; contul apare aici la prima logare, fără rol (ca în SCC). Fiecare
 * schimbare se salvează pe loc, iar serverul o aplică imediat sesiunilor deschise. Filtrul
 * („așteaptă un rol”) stă în adresă.
 */
export default function Utilizatori() {
  const { t, locale } = useLang()
  const { message } = App.useApp()
  const qc = useQueryClient()
  const eu = useSesiune().utilizator?.utilizator
  const [sp, setSp] = useSearchParams()
  const filtru = sp.get('stare') === 'asteapta' ? 'asteapta' : 'toti'
  const [inLucru, setInLucru] = useState<string | null>(null)
  const q = useConturi()

  if (q.error) return <Eroare e={q.error} />
  if (!q.data) return <SeIncarca />
  if (!q.data.disponibil) return <section><p className="note"><T k="ut.nedisponibil" /></p></section>

  const toti = q.data.utilizatori
  const asteapta = toti.filter((u) => u.activ && u.rol === null)
  const randuri = filtru === 'asteapta' ? asteapta : toti

  const salveaza = async (u: ContAplicatie, schimbari: { rol?: RolCont | null; activ?: boolean }) => {
    setInLucru(u.utilizator)
    try {
      await modificaCont(u.utilizator, schimbari)
      message.success(t('ut.salvat', { u: u.utilizator }))
    } catch (e) {
      const cod = e instanceof ApiError ? e.message : String(e)
      message.error(ERORI_CU_TEXT.has(cod) ? t(`ut.eroare.${cod}` as DictKey) : t('ut.eroare.generic', { cod }), 6)
    } finally {
      setInLucru(null)
      await qc.invalidateQueries({ queryKey: ['utilizatori'] })
    }
  }

  const cand = (iso: string | null) => (iso ? moment(iso, locale) : '—')

  const coloane: Coloana<ContAplicatie>[] = [
    {
      cheie: 'utilizator',
      cap: t('ut.col.utilizator'),
      s: (u) => u.utilizator,
      val: (u) => (
        <span className="ut-cont">
          <code>{u.utilizator}</code>
          {u.utilizator === eu && <span className="ut-tu">{t('ut.tu')}</span>}
          {u.activ && u.rol === null && <Pill tip="amb">{t('ut.stare.asteapta')}</Pill>}
          {!u.activ && <Pill>{t('ut.stare.dezactivat')}</Pill>}
        </span>
      ),
    },
    { cheie: 'nume', cap: t('ut.col.nume'), s: (u) => u.nume, val: (u) => u.nume },
    {
      cheie: 'rol',
      cap: t('ut.col.rol'),
      s: (u) => u.rol ?? '',
      val: (u) => (
        <Tooltip title={u.utilizator === eu ? t('ut.propriul_cont_t') : null}>
          <Select<RolCont | undefined>
            className="ut-rol"
            size="small"
            aria-label={`${t('ut.col.rol')}: ${u.utilizator}`}
            value={u.rol ?? undefined}
            placeholder={t('ut.fara_rol')}
            allowClear
            disabled={u.utilizator === eu || inLucru === u.utilizator}
            onChange={(v) => void salveaza(u, { rol: v ?? null })}
            options={[
              { value: 'analist', label: t('auth.rol.analist') },
              { value: 'admin', label: t('auth.rol.admin') },
            ]}
          />
        </Tooltip>
      ),
    },
    {
      cheie: 'activ',
      cap: t('ut.col.activ'),
      s: (u) => (u.activ ? 1 : 0),
      val: (u) => (
        <Tooltip title={u.utilizator === eu ? t('ut.propriul_cont_t') : null}>
          <Switch
            size="small"
            aria-label={`${t('ut.col.activ')}: ${u.utilizator}`}
            checked={u.activ}
            disabled={u.utilizator === eu || inLucru === u.utilizator}
            onChange={(v) => void salveaza(u, { activ: v })}
          />
        </Tooltip>
      ),
    },
    {
      cheie: 'ultima_logare',
      cap: t('ut.col.ultima_logare'),
      titlu: t('ut.col.ultima_logare_t'),
      s: (u) => u.ultima_logare,
      val: (u) => cand(u.ultima_logare),
    },
    {
      cheie: 'modificat',
      cap: t('ut.col.modificat'),
      s: (u) => u.modificat,
      val: (u) => (u.modificat ? <>{cand(u.modificat)} <span className="note">{t('ut.de', { cine: u.modificat_de ?? '?' })}</span></> : '—'),
    },
    { cheie: 'creat', cap: t('ut.col.creat'), s: (u) => u.creat, val: (u) => cand(u.creat) },
  ]

  return (
    <>
      <p className="note ut-intro"><T k="ut.intro" /></p>
      <div className="ut-filtre">
        <Comutator<string>
          value={filtru}
          onChange={(v) => setSp((p) => {
            const n = new URLSearchParams(p)     // păstrează `tab` (Administrare)
            if (v === 'asteapta') n.set('stare', v)
            else n.delete('stare')
            return n
          }, { replace: true })}
          options={[
            { value: 'toti', label: t('ut.filtru.toti', { n: toti.length }) },
            { value: 'asteapta', label: t('ut.filtru.asteapta', { n: asteapta.length }) },
          ]}
        />
      </div>
      <section>
        <Tabel
          randuri={randuri}
          coloane={coloane}
          cheieRand={(u) => u.utilizator}
          gol={filtru === 'asteapta' ? t('ut.gol_asteapta') : undefined}
        />
      </section>
    </>
  )
}
