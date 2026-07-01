import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import PlantillaPage from './pages/PlantillaPage'
import NuevoEnvioPage from './pages/NuevoEnvioPage'
import SeguimientoPage from './pages/SeguimientoPage'
import AuthGuard from './components/layout/AuthGuard'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AuthGuard />}>
        <Route path="/seguimiento/no-contestados" element={<SeguimientoPage />} />
        <Route path="/seguimiento/contestados" element={<SeguimientoPage />} />
        <Route path="/seguimiento/pagos" element={<SeguimientoPage />} />
        <Route path="/seguimiento/rebotados" element={<SeguimientoPage />} />
        <Route path="/nuevo-envio/para-enviar" element={<NuevoEnvioPage />} />
        <Route path="/nuevo-envio/sin-email" element={<NuevoEnvioPage />} />
        <Route path="/nuevo-envio/filtrados" element={<NuevoEnvioPage />} />
        <Route path="/maestro" element={<div>Maestro de Clientes</div>} />
        <Route path="/plantilla" element={<PlantillaPage />} />
        <Route path="/configuracion" element={<div>Configuración</div>} />
      </Route>
      <Route path="/" element={<Navigate to="/seguimiento/no-contestados" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
