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
import SursePagina from './pages/SursePagina'
import Coada from './pages/Coada'
import Harta from './pages/Harta'
import Document from './pages/Document'
import InLucru from './pages/InLucru'
import { TOATE } from './pagini'

export default function App() {
  return (
    <Routes>
      {/* harta și vizualizatorul PDF ocupă tot ecranul, ca în aplicația veche (harta.html, pdf.html) */}
      <Route path="/harta" element={<Harta />} />
      <Route path="/document" element={<Document />} />
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
        <Route path="/surse" element={<SursePagina />} />
        <Route path="/coada" element={<Coada />} />
        {TOATE.filter((p) => !p.mutata).map((p) => (
          <Route key={p.id} path={`/${p.id}`} element={<InLucru id={p.id} />} />
        ))}
        {/* pagina 2.7 s-a mutat în 2.3 (ca în aplicația veche) */}
        <Route path="/sentiment" element={<Navigate to="/mobil?la=recenzii" replace />} />
        <Route path="*" element={<Navigate to="/overview" replace />} />
      </Route>
    </Routes>
  )
}
