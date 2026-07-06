import { Routes, Route, Navigate } from 'react-router-dom'
import AppLayout from './components/layout/AppLayout'
import AuthGuard from './components/layout/AuthGuard'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import NuevoEnvioPage from './pages/NuevoEnvioPage'
import SeguimientoPage from './pages/SeguimientoPage'
import MaestroPage from './pages/MaestroPage'
import PlantillaPage from './pages/PlantillaPage'
import ConfiguracionPage from './pages/ConfiguracionPage'
import ClientePerfilPage from './pages/ClientePerfilPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AuthGuard />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/nuevo-envio/*" element={<NuevoEnvioPage />} />
          <Route path="/seguimiento/*" element={<SeguimientoPage />} />
          <Route path="/maestro" element={<MaestroPage />} />
          <Route path="/plantilla" element={<PlantillaPage />} />
          <Route path="/configuracion" element={<ConfiguracionPage />} />
          <Route path="/clientes/:clave" element={<ClientePerfilPage />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
