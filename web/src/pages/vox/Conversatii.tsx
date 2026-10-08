import { useState } from 'react'
import { App, Input, Popconfirm, Tooltip } from 'antd'
import { DeleteOutlined, EditOutlined, PlusOutlined, SearchOutlined } from '@ant-design/icons'
import type { ConversatieRezumat } from '@mcc/shared'
import { useLang, type DictKey } from '../../i18n'
import { deLaServer } from '../../i18n/server'
import { faraDiacritice } from '../../util/format'

/**
 * Coloana „Conversații” din pagina Vox (macheta aprobată pe 07.10.2026): conversațiile salvate pe
 * laptop (loguri/vox/conversatii/), pe zile, cu căutare, redenumire și ștergere. Stă în pagina Vox,
 * nu în bara vișinie: aceea depășește deja ecranul la 800px înălțime, iar lista crește.
 */

type Tr = (k: DictKey, p?: Record<string, string | number>) => string
export type Zi = 'azi' | 'ieri' | 'vechi'
const ZILE: Zi[] = ['azi', 'ieri', 'vechi']

/** Ziua unei ore față de azi, în ora laptopului. */
export function ziua(iso: string, acum = new Date()): Zi {
  const inceput = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime()
  const zile = Math.round((inceput(acum) - inceput(new Date(iso))) / 86400000)
  return zile <= 0 ? 'azi' : zile === 1 ? 'ieri' : 'vechi'
}

export const ora = (iso: string, locale: string) =>
  new Date(iso).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
const data = (iso: string, locale: string) =>
  new Date(iso).toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' })

/** „azi, 12:37” / „începută ieri la 18:20” …: cheile `<baza>_azi|_ieri|_vechi`. */
export function cand(iso: string, baza: 'vox.conv.ora' | 'vox.conv.inceputa', t: Tr, locale: string): string {
  return t(`${baza}_${ziua(iso)}` as DictKey, { ora: ora(iso, locale), zi: data(iso, locale) })
}

export interface RandConv extends ConversatieRezumat {
  /** prima întrebare care se potrivește, când potrivirea nu e în titlu */
  potrivire?: string
}

/**
 * Rădăcina unui cuvânt căutat, cu aceeași regulă ca `vox.cuvinte_cautare` din server (6+ litere pierd
 * ultimele 2, 5 litere ultima, cifrele rămân): „vamala” nu găsea „vamale”, iar căutarea merge pe
 * măsură ce scrii, deci rezultatele dispăreau la ultima literă.
 */
const radacina = (w: string) => (/^\d+$/.test(w) ? w : w.length >= 6 ? w.slice(0, -2) : w.length === 5 ? w.slice(0, -1) : w)

/** Fiecare cuvânt căutat trebuie să apară în titlu sau în întrebări, fără diacritice și majuscule. */
export function filtreaza(lista: ConversatieRezumat[], cauta: string): RandConv[] {
  const cuvinte = faraDiacritice(cauta).split(/[^\p{L}\p{N}]+/u).filter(Boolean).map(radacina)
  if (!cuvinte.length) return lista
  const are = (s: string, toate: boolean) => {
    const f = faraDiacritice(s)
    return toate ? cuvinte.every((w) => f.includes(w)) : cuvinte.some((w) => f.includes(w))
  }
  return lista.flatMap((c) => {
    if (!are([c.titlu, ...c.texte].join('\n'), true)) return []
    if (are(c.titlu, true)) return [c]
    return [{ ...c, potrivire: c.texte.find((x) => x !== c.titlu && are(x, false)) }]
  })
}

interface Props {
  lista: ConversatieRezumat[] | undefined
  eroare: boolean
  deschisa: string | null
  cauta: string
  /** cât o întrebare așteaptă răspunsul, conversația nu se schimbă */
  blocat: boolean
  /** fără tokenul lui Vox (Vox oprit) istoricul e doar de citit */
  poateModifica: boolean
  inSertar?: boolean
  onCauta: (q: string) => void
  onDeschide: (id: string) => void
  onNoua: () => void
  onRedenumeste: (id: string, titlu: string) => Promise<void>
  onSterge: (id: string) => Promise<void>
}

export default function Conversatii(p: Props) {
  const { t, tn, lang, locale } = useLang()
  const { message } = App.useApp()
  const [editez, setEditez] = useState<string | null>(null)
  const randuri = filtreaza(p.lista ?? [], p.cauta)
  const greseala = (e: unknown) => void message.error(deLaServer((e as Error).message, lang))
  const salveaza = async (id: string, titlu: string) => {
    setEditez(null)
    try {
      await p.onRedenumeste(id, titlu)
    } catch (e) {
      greseala(e)
    }
  }
  return (
    <aside className={p.inSertar ? 'vox-conv in-sertar' : 'vox-conv'} aria-label={t('vox.conv.titlu_coloana')}>
      <button type="button" className="vox-conv-noua" onClick={p.onNoua} disabled={p.blocat}>
        <PlusOutlined /> {t('vox.conv.noua')}
      </button>
      <Input
        allowClear
        prefix={<SearchOutlined />}
        value={p.cauta}
        onChange={(e) => p.onCauta(e.target.value)}
        placeholder={t('vox.conv.cauta')}
        aria-label={t('vox.conv.cauta')}
      />
      {p.eroare && <p className="vox-conv-nota">{t('vox.conv.eroare_lista')}</p>}
      {p.lista?.length === 0 && <p className="vox-conv-nota">{t('vox.conv.goala')}</p>}
      {!!p.lista?.length && randuri.length === 0 && <p className="vox-conv-nota">{t('vox.conv.nimic', { q: p.cauta })}</p>}
      {ZILE.map((zi) => {
        const grupa = randuri.filter((c) => ziua(c.ultima) === zi)
        if (!grupa.length) return null
        return (
          <div key={zi} className="vox-conv-grupa">
            <h3>{t(`vox.conv.${zi}` as DictKey)}</h3>
            <ul>
              {grupa.map((c) => {
                const activ = c.id === p.deschisa
                return (
                  <li key={c.id} className={activ ? 'activ' : undefined}>
                    {editez === c.id ? (
                      <Input
                        size="small"
                        autoFocus
                        maxLength={120}
                        defaultValue={c.redenumita ? c.titlu : ''}
                        placeholder={c.texte[0]}
                        aria-label={t('vox.conv.titlu_nou')}
                        onPressEnter={(e) => void salveaza(c.id, e.currentTarget.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Escape') setEditez(null)
                        }}
                        onBlur={() => setEditez(null)}
                      />
                    ) : (
                      <button
                        type="button"
                        className="vox-conv-deschide"
                        onClick={() => p.onDeschide(c.id)}
                        disabled={p.blocat}
                        aria-current={activ ? 'true' : undefined}
                      >
                        <span className="t">{c.titlu}</span>
                        {c.potrivire && <span className="potrivire">↳ {c.potrivire}</span>}
                        <span className="m">
                          {tn('vox.conv.n_intrebari', c.intrebari)} · {zi === 'vechi' ? data(c.ultima, locale) : ora(c.ultima, locale)}
                        </span>
                      </button>
                    )}
                    {p.poateModifica && editez !== c.id && (
                      <span className="vox-conv-actiuni">
                        <Tooltip title={t('vox.conv.redenumeste')}>
                          <button type="button" aria-label={t('vox.conv.redenumeste')} disabled={p.blocat} onClick={() => setEditez(c.id)}>
                            <EditOutlined />
                          </button>
                        </Tooltip>
                        <Popconfirm
                          title={t('vox.conv.sterge_confirm')}
                          okText={t('vox.conv.sterge')}
                          cancelText={t('vox.conv.renunta')}
                          okButtonProps={{ danger: true }}
                          onConfirm={async () => {
                            try {
                              await p.onSterge(c.id)
                            } catch (e) {
                              greseala(e)
                            }
                          }}
                        >
                          <button type="button" aria-label={t('vox.conv.sterge')} disabled={p.blocat}>
                            <DeleteOutlined />
                          </button>
                        </Popconfirm>
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>
          </div>
        )
      })}
      <p className="vox-conv-unde">{t('vox.conv.unde')}</p>
    </aside>
  )
}
