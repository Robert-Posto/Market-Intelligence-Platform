import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './layout/AppShell'
import Overview from './pages/Overview'
import Produse from './pages/Produse'
import Rate from './pages/Rate'
import Mobil from './pages/Mobil'
import Campanii from './pages/campanii/Campanii'
import Retea from './pages/Retea'
import Context from './pages/Context'
import Istoric from './pages/Istoric'
import Versus from './pages/Versus'
import Banca from './pages/Banca'
import Concurenta from './pages/Concurenta'
import SursePagina from './pages/SursePagina'
import Coada from './pages/Coada'
import Logging from './pages/Logging'
import RulareManuala from './pages/RulareManuala'

/* maplibre-gl și pdfjs-dist sunt aproape jumătate din pachet (2,6 MB într-un singur fișier la 05.10.2026):
   se încarcă doar când se deschide harta sau un document, nu pe fiecare pagină */
const Harta = lazy(() => import('./pages/Harta'))
const Document = lazy(() => import('./pages/Document'))

export default function App() {
  return (
    <Routes>
      {/* harta și vizualizatorul PDF ocupă tot ecranul, ca în aplicația veche (harta.html, pdf.html) */}
      <Route path="/harta" element={<Suspense fallback={null}><Harta /></Suspense>} />
      <Route path="/document" element={<Suspense fallback={null}><Document /></Suspense>} />
      <Route element={<AppShell />}>
        <Route path="/overview" element={<Overview />} />
        <Route path="/produse" element={<Produse />} />
        <Route path="/rate" element={<Rate />} />
        <Route path="/mobil" element={<Mobil />} />
        <Route path="/campanii" element={<Campanii />} />
        <Route path="/retea" element={<Retea />} />
        <Route path="/context" element={<Context />} />
        <Route path="/istoric" element={<Istoric />} />
        <Route path="/versus" element={<Versus />} />
        <Route path="/banca" element={<Banca />} />
        <Route path="/concurenta" element={<Concurenta />} />
        <Route path="/surse" element={<SursePagina />} />
        <Route path="/coada" element={<Coada />} />
        <Route path="/logging" element={<Logging />} />
        <Route path="/rulare" element={<RulareManuala />} />
        {/* pagina 2.7 s-a mutat în 2.3 (ca în aplicația veche) */}
        <Route path="/sentiment" element={<Navigate to="/mobil?la=recenzii" replace />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  )
}
