import { Navigate, Route, Routes } from 'react-router-dom'
import AppShell from './layout/AppShell'
import Overview from './pages/Overview'
import Produse from './pages/Produse'
import Rate from './pages/Rate'
import Mobil from './pages/Mobil'
import Campanii from './pages/campanii/Campanii'
import InLucru from './pages/InLucru'
import { TOATE } from './pagini'

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/overview" element={<Overview />} />
        <Route path="/produse" element={<Produse />} />
        <Route path="/rate" element={<Rate />} />
        <Route path="/mobil" element={<Mobil />} />
        <Route path="/campanii" element={<Campanii />} />
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
