import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import PlantillaPage from './pages/PlantillaPage'
import AuthGuard from './components/layout/AuthGuard'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<AuthGuard />}>
        <Route path="/seguimiento/no-contestados" element={<div>Seguimiento - No Contestados</div>} />
        <Route path="/seguimiento/contestados" element={<div>Seguimiento - Contestados</div>} />
        <Route path="/seguimiento/pagos" element={<div>Seguimiento - Pagos</div>} />
        <Route path="/seguimiento/rebotados" element={<div>Seguimiento - Rebotados</div>} />
        <Route path="/nuevo-envio/para-enviar" element={<div>Nuevo Envío - Para Enviar</div>} />
        <Route path="/nuevo-envio/sin-email" element={<div>Nuevo Envío - Sin Email</div>} />
        <Route path="/nuevo-envio/filtrados" element={<div>Nuevo Envío - Filtrados</div>} />
        <Route path="/maestro" element={<div>Maestro de Clientes</div>} />
        <Route path="/plantilla" element={<PlantillaPage />} />
        <Route path="/configuracion" element={<div>Configuración</div>} />
      </Route>
      <Route path="/" element={<Navigate to="/seguimiento/no-contestados" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
