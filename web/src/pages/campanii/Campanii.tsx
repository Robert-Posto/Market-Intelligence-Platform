import type { ComponentType } from 'react'
import { Segmented, Tooltip } from 'antd'
import { useSearchParams } from 'react-router-dom'
import { useCampanii, useComunicate } from '../../api/campanii'
import { useMeta } from '../../api/meta'
import { useBing, useGoogle } from '../../api/reclame'
import { useRetele, useYoutube } from '../../api/youtube_retele'
import { Eroare, SeIncarca } from '../../components/comune'
import { useLang, type DictKey } from '../../i18n'
import { num } from '../../util/format'
import Bing from './Bing'
import Comunicate from './Comunicate'
import Google from './Google'
import Retele from './Retele'
import Site from './Site'
import Surse from './Surse'
import type { PropsSectiune } from './tipuri'
import YouTube from './YouTube'
import '../../styles/campanii_site.css'

type Cheie = 'site' | 'comunicate' | 'google' | 'bing' | 'youtube' | 'retele'

/**
 * 2.4, revamp 30.09: în loc de un teanc de secțiuni una sub alta (~7.000 px), un
 * comutator de secțiuni, ca iOS / Android la 2.3: o singură secțiune pe ecran,
 * aleasă în adresă (`?s=google`). Numele „YouTube” e propriu: nu are cheie.
 */
const SECTIUNI: { k: Cheie; nume: DictKey | null; titlu: DictKey; C: ComponentType<PropsSectiune> }[] = [
  { k: 'site', nume: 'campanii.sectiune.site', titlu: 'campanii.sectiune.site_titlu', C: Site },
  { k: 'comunicate', nume: 'campanii.sectiune.comunicate', titlu: 'campanii.sectiune.comunicate_titlu', C: Comunicate },
  { k: 'google', nume: 'campanii.sectiune.google', titlu: 'campanii.sectiune.google_titlu', C: Google },
  { k: 'bing', nume: 'campanii.sectiune.bing', titlu: 'campanii.sectiune.bing_titlu', C: Bing },
  { k: 'youtube', nume: null, titlu: 'campanii.sectiune.youtube_titlu', C: YouTube },
  { k: 'retele', nume: 'campanii.sectiune.retele', titlu: 'campanii.sectiune.retele_titlu', C: Retele },
]

export default function Campanii() {
  const { t, locale } = useLang()
  const [sp, setSp] = useSearchParams()
  const meta = useMeta()
  const camp = useCampanii()
  const com = useComunicate()
  const google = useGoogle()
  const bing = useBing()
  const yt = useYoutube()
  const rs = useRetele()

  if (meta.error) return <Eroare e={meta.error} />
  if (!meta.data) return <SeIncarca />
  const sec = SECTIUNI.find((x) => x.k === sp.get('s')) ?? SECTIUNI[0]!

  // câte are fiecare secțiune, pe comutator; până vine răspunsul, tabul rămâne fără cifră
  const n: Record<Cheie, number | undefined> = {
    site: camp.data?.randuri.filter((r) => r.in_comparatie && r.stare === 'activa').length,
    comunicate: com.data?.length,
    google: google.data ? google.data.total || 0 : undefined,
    bing: bing.data?.reclame.filter((r) => r.pondere_ro !== null && r.pondere_ro >= 50).length,
    // canale, nu suma videoclipurilor (fără agregare); un server fără ruta /api/youtube = 0, restul paginii merge
    youtube: yt.data ? Object.keys(yt.data.banci).length : yt.error ? 0 : undefined,
    retele: rs.data?.filter((r) => r.url !== 'NEGASIT').length,
  }

  const taburi = (
    <Segmented<Cheie>
      className="cm-taburi"
      value={sec.k}
      // ca mergi() din aplicația veche: adresa nouă are doar secțiunea, filtrele celei vechi se pierd
      onChange={(k) => setSp({ s: k })}
      options={SECTIUNI.map(({ k, nume, titlu }) => {
        const x = n[k]
        return {
          value: k,
          label: (
            <Tooltip title={x === undefined ? t(titlu) : `${num(x, locale, 0)} ${t(titlu)}`}>
              <span>
                {nume ? t(nume) : 'YouTube'}
                {x !== undefined && <span className="n">{num(x, locale, 0)}</span>}
              </span>
            </Tooltip>
          ),
        }
      })}
    />
  )

  return <sec.C key={sec.k} m={meta.data} taburi={taburi} subsol={<Surse />} />
}
