import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import {
  LngLatBounds, Map as HartaGL, Marker, NavigationControl, Popup, ScaleControl,
  type ExpressionSpecification, type GeoJSONSource, type StyleSpecification,
} from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import type { ReteaBanca, ReteaPunct } from '@mcc/shared'
import { T, useLang, type DictKey } from '../../i18n'
import { num } from '../../util/format'
import { badgeChip, badgePunct, codBanca, type Sigle, type TipLocatie } from './desen'

const intunecat = typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches
const STIL_CARTO = intunecat
  ? 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json'
  : 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'
const STIL_REZERVA: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster', tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    },
  },
  layers: [
    { id: 'fundal', type: 'background', paint: { 'background-color': intunecat ? '#161113' : '#f3efea' } },
    { id: 'osm', type: 'raster', source: 'osm', paint: { 'raster-saturation': -0.6 } },
  ],
}

// sub zoom 13: puncte curate. peste: chip-uri cu logo.
const PRAG_CHIP = 13
const iconDupaZoom: ExpressionSpecification = ['step', ['zoom'], ['get', 'icon_punct'], PRAG_CHIP, ['get', 'icon_chip']]
// ATM-urile partenere estompate: rețea comună, nu a băncii
const opacitate: ExpressionSpecification = ['case', ['==', ['get', 'retea'], 'partener'], 0.45, 1]

function geojson(lista: ReteaPunct[]): GeoJSON.FeatureCollection<GeoJSON.Point> {
  return {
    type: 'FeatureCollection',
    features: lista.map((p) => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
      // doar ce citesc straturile; popup-ul ia punctul întreg după id
      properties: { id: p.id, tip: p.tip, retea: p.retea, icon_punct: `${p.banca}-${p.tip}-punct`, icon_chip: `${p.banca}-${p.tip}-chip` },
    })),
  }
}

/** Mesajul și adresa vin de la biblioteca hărții (în engleză, tehnice): rămân cum sunt, doar titlul se traduce. */
interface Diag { titlu: DictKey; mesaj: string; url: string }

/**
 * Harta MapLibre: fundal CARTO, cu trecere pe OpenStreetMap la eroare; punctele
 * ca texturi desenate o dată, grupuri la zoom mic, popup la clic.
 * `incadrare` = banca (băncile) din link: harta se centrează o dată pe punctele lor.
 */
export default function Mapa({ banci, vizibile, toate, sigle, logo, culoareGrup, incadrare, onZona }: {
  banci: ReteaBanca[]
  vizibile: ReteaPunct[]
  toate: ReteaPunct[]
  sigle: Sigle | null
  logo: Record<string, string>
  culoareGrup: string | null
  incadrare: string | null
  onZona: (n: number) => void
}) {
  const { t, locale } = useLang()
  const container = useRef<HTMLDivElement>(null)
  const harta = useRef<HartaGL | null>(null)
  const [diag, setDiag] = useState<Diag | null>(null)
  /* de câte ori s-a încărcat un stil: la trecerea pe rezervă, sursa și straturile se pun din nou.
     `stilIncarcat` spune dacă stilul curent e gata: între setStyle și „style.load”, addSource aruncă eroare. */
  const [stil, setStil] = useState(0)
  const stilIncarcat = useRef(false)
  const [gata, setGata] = useState(false)
  const [ales, setAles] = useState<ReteaPunct | null>(null)
  const [popup] = useState(() => new Popup({ closeButton: true, offset: 16, maxWidth: '310px' }))
  const [corpPopup] = useState(() => document.createElement('div'))

  // ce citesc handler-ele hărții, mereu la zi, fără să le înregistrăm din nou la fiecare randare
  const actual = useRef({ vizibile, culoareGrup, t, locale, onZona, dupaId: new Map<number, ReteaPunct>() })
  actual.current.vizibile = vizibile
  actual.current.culoareGrup = culoareGrup
  actual.current.t = t
  actual.current.locale = locale
  actual.current.onZona = onZona
  useEffect(() => { actual.current.dupaId = new Map(toate.map((p) => [p.id, p])) }, [toate])

  const grupe = useRef<Record<number, Marker>>({})
  const curataGrupe = () => {
    for (const id in grupe.current) { grupe.current[id]!.remove(); delete grupe.current[id] }
  }

  /* Grupele (bule cu număr) sunt elemente DOM peste hartă: textul lor nu depinde
     de fonturile stilului de fond, deci merg și pe fondul de rezervă. Filtrarea
     se face în datele sursei, fiindcă gruparea se calculează din ele. */
  const actualizeazaGrupe = () => {
    const map = harta.current
    const sursa = map?.getSource<GeoJSONSource>('locatii')
    if (!map || !sursa) return
    const { t: tr, locale: loc, culoareGrup: cul } = actual.current
    const vazute: Record<number, boolean> = {}
    for (const x of map.querySourceFeatures('locatii')) {
      if (!x.properties.cluster) continue
      const id = Number(x.properties.cluster_id)
      if (vazute[id]) continue
      vazute[id] = true
      if (grupe.current[id]) continue
      const n = Number(x.properties.point_count)
      const coord = (x.geometry as GeoJSON.Point).coordinates as [number, number]
      const el = document.createElement('div')
      const d = n < 10 ? 28 : n < 50 ? 34 : n < 200 ? 42 : 50
      el.className = 'ht-grup'
      el.style.width = el.style.height = `${d}px`
      // o singură bancă aleasă: grupul are culoarea ei
      if (cul) el.style.background = cul
      el.textContent = String(x.properties.point_count_abbreviated)
      el.title = tr('harta.grup.title', { n: num(n, loc, 0) })
      // sursa se ia la clic, nu de acum: după trecerea pe fondul de rezervă e alt obiect, cu același id
      el.onclick = () => {
        void map.getSource<GeoJSONSource>('locatii')?.getClusterExpansionZoom(id)
          .then((z) => map.easeTo({ center: coord, zoom: z + 0.3 }))
      }
      grupe.current[id] = new Marker({ element: el }).setLngLat(coord).addTo(map)
    }
    for (const id in grupe.current) if (!vazute[id]) { grupe.current[id]!.remove(); delete grupe.current[id] }
  }

  const inZona = () => {
    const map = harta.current
    if (!map) return
    const z = map.getBounds()
    const { vizibile: v, onZona: f } = actual.current
    f(v.filter((p) => z.contains([p.lon, p.lat])).length)
  }

  // harta se creează o singură dată; fundalul se alege după tema sistemului, ca în pagina veche
  useEffect(() => {
    const map = new HartaGL({
      container: container.current!, style: STIL_CARTO,
      center: [25.0, 45.9], zoom: 6.4, attributionControl: { compact: true },
    })
    harta.current = map
    map.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ maxWidth: 110, unit: 'metric' }))

    let cazutPeRezerva = false
    map.on('error', (e) => {
      const err = e?.error as (Error & { status?: number; url?: string }) | undefined
      const m = err?.message || (err?.status ? String(err.status) : '')
      const url = err?.url ? ` · ${err.url}` : ''
      if (/style|403|401|key|forbidden|Failed to fetch|NetworkError/i.test(m) && !cazutPeRezerva) {
        cazutPeRezerva = true
        stilIncarcat.current = false
        setDiag({ titlu: 'harta.diag.carto_inaccesibil', mesaj: m, url })
        /* `diff: false`: stilul se reconstruiește și vine „style.load”, deci punctele se pun din nou.
           Cu diff (implicit), o dală CARTO căzută DUPĂ încărcare scotea sursa și straturile punctelor,
           iar pagina veche dădea apoi „Cannot read properties of undefined (reading 'setData')”. */
        map.setStyle(STIL_REZERVA, { diff: false })
      } else {
        setDiag({ titlu: 'harta.diag.eroare_harta', mesaj: m, url })
      }
    })
    map.on('style.load', () => {
      stilIncarcat.current = true
      setStil((n) => n + 1)
    })

    for (const strat of ['atm', 'sucursala']) {
      map.on('click', strat, (e) => {
        const p = actual.current.dupaId.get(Number(e.features?.[0]?.properties.id))
        if (!p) return
        popup.setLngLat(e.lngLat).setDOMContent(corpPopup).addTo(map)
        setAles(p)
      })
      map.on('mouseenter', strat, () => { map.getCanvas().style.cursor = 'pointer' })
      map.on('mouseleave', strat, () => { map.getCanvas().style.cursor = '' })
    }
    map.on('moveend', () => { actualizeazaGrupe(); inZona() })
    map.on('sourcedata', (e) => { if (e.sourceId === 'locatii' && e.isSourceLoaded) actualizeazaGrupe() })
    const inchis = () => setAles(null)
    popup.on('close', inchis)

    return () => {
      popup.off('close', inchis)
      curataGrupe()
      popup.remove()
      map.remove()
      harta.current = null
      stilIncarcat.current = false
      setGata(false)
    }
  }, [])

  // texturile, sursa și straturile: după stil și după sigle (culoarea vine din logo)
  useEffect(() => {
    const map = harta.current
    if (!map || !stilIncarcat.current || !sigle) return
    // 11 bănci × 2 tipuri × 2 variante (punct / chip) = 44 texturi, desenate o dată
    const ratie = Math.min(window.devicePixelRatio || 1, 2)
    for (const b of banci) {
      for (const tip of ['sucursala', 'atm'] as TipLocatie[]) {
        const p = `${b.slug}-${tip}-punct`
        const ch = `${b.slug}-${tip}-chip`
        const cul = sigle.culori[b.slug] ?? '#5b6b7a'
        if (!map.hasImage(p)) map.addImage(p, badgePunct(codBanca(b.slug), cul, tip, ratie), { pixelRatio: ratie })
        if (!map.hasImage(ch)) map.addImage(ch, badgeChip(sigle.imagini[b.slug], cul, tip, ratie, t('harta.chip.atm')), { pixelRatio: ratie })
      }
    }
    if (!map.getSource('locatii')) {
      map.addSource('locatii', { type: 'geojson', data: geojson(actual.current.vizibile), cluster: true, clusterMaxZoom: 9, clusterRadius: 44 })
    }
    // ATM-urile dedesubt, sucursalele deasupra — când se suprapun, contează sucursala
    if (!map.getLayer('atm')) {
      map.addLayer({
        id: 'atm', type: 'symbol', source: 'locatii',
        filter: ['all', ['!', ['has', 'point_count']], ['==', ['get', 'tip'], 'atm']],
        paint: { 'icon-opacity': opacitate },
        layout: {
          'icon-image': iconDupaZoom, 'icon-allow-overlap': true, 'icon-ignore-placement': true,
          'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.72, 12.9, 1.0, PRAG_CHIP, 0.50, 16, 0.72],
        },
      })
    }
    if (!map.getLayer('sucursala')) {
      map.addLayer({
        id: 'sucursala', type: 'symbol', source: 'locatii',
        filter: ['all', ['!', ['has', 'point_count']], ['==', ['get', 'tip'], 'sucursala']],
        layout: {
          'icon-image': iconDupaZoom, 'icon-allow-overlap': true, 'icon-ignore-placement': true,
          'icon-size': ['interpolate', ['linear'], ['zoom'], 10, 0.78, 12.9, 1.0, PRAG_CHIP, 0.55, 16, 0.80],
        },
      })
    }
    setGata(true)
    // `t` lipsește intenționat: eticheta „ATM” e aceeași în ambele limbi, iar texturile nu se redesenează
  }, [stil, sigle, banci])

  // filtrele schimbă datele sursei, nu straturile: gruparea se calculează din ele
  useEffect(() => {
    const map = harta.current
    if (!gata || !map) return
    curataGrupe()
    map.getSource<GeoJSONSource>('locatii')?.setData(geojson(vizibile))
    inZona()
  }, [gata, vizibile])

  // titlul grupelor e în limba paginii: la schimbarea limbii se desenează din nou
  useEffect(() => {
    if (!gata) return
    curataGrupe()
    actualizeazaGrupe()
  }, [locale])

  // bancă aleasă din link: harta se centrează pe punctele ei
  useEffect(() => {
    const map = harta.current
    const v = actual.current.vizibile
    if (!gata || !map || !incadrare || !v.length) return
    const b = new LngLatBounds()
    v.forEach((p) => b.extend([p.lon, p.lat]))
    map.fitBounds(b, { padding: 60, maxZoom: 13, duration: 0 })
  }, [gata, incadrare])

  return (
    <div className="ht-zona">
      <div className="ht-map" ref={container} />
      {diag && (
        <div className="ht-diag">
          <b>{t(diag.titlu)}</b>
          <code>{diag.mesaj || t('harta.diag.eroare_necunoscuta')}{diag.url}</code>
        </div>
      )}
      {ales && createPortal(<ContinutPopup p={ales} culoare={sigle?.culori[ales.banca]} logo={logo[ales.banca]} />, corpPopup)}
    </div>
  )
}

/* Overture nu are note și recenzii de locație, deci popup-ul nu arată
   niciuna. Notele de dinainte erau mock și au fost șterse (migrarea 014). */
function ContinutPopup({ p, culoare, logo }: { p: ReteaPunct; culoare: string | undefined; logo: string | undefined }) {
  const { t } = useLang()
  const sursa = p.sursa === 'locator_banca' ? t('harta.popup.sursa_locator_banca')
    : p.sursa === 'mock' ? t('harta.popup.sursa_mock') : 'Overture Maps'
  return (
    <>
      <div className="ht-pop-cap" style={{ borderLeftColor: culoare ?? '#5b6b7a' }}>
        {logo && <img className="ht-pop-logo" src={logo} alt={p.banca_nume} />}
        <div className="ht-pop-t">{p.nume}</div>
        <div className="ht-pop-m">{[p.adresa, p.sector].filter(Boolean).join(' · ')}</div>
      </div>
      {p.program && <div className="ht-pop-m">{t('harta.popup.program', { program: p.program })}</div>}
      {p.retea === 'partener' && <div className="ht-pop-m"><T k="harta.popup.atm_partener" /></div>}
      <span className={`ht-pill${p.sursa === 'mock' ? ' mock' : ''}`}>
        {t(p.tip === 'sucursala' ? 'harta.popup.tip_sucursala' : 'harta.popup.tip_atm')} · {sursa}{p.furnizori ? ` (${p.furnizori})` : ''}
      </span>
    </>
  )
}
