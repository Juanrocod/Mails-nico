import { NavLink, useNavigate } from 'react-router-dom'
import { LogOut, KeyRound } from 'lucide-react'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import { cn } from '../../lib/utils'
import { useAuth } from '../../hooks/useAuth'

function NavItem({
  to,
  label,
  icon: Icon,
  count,
}: {
  to: string
  label: string
  icon: React.ElementType
  count?: number
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          'flex items-center justify-between px-3 py-2 rounded-md text-sm transition-colors',
          isActive
            ? 'bg-slate-100 text-slate-900 font-medium'
            : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
        )
      }
    >
      <span className="flex items-center gap-2">
        <Icon className="h-4 w-4 shrink-0" />
        {label}
      </span>
      {count !== undefined && count > 0 && (
        <span className="text-xs bg-slate-200 text-slate-700 px-2 py-0.5 rounded-full">
          {count}
        </span>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    try {
      await logout()
    } catch {
      // continuar aunque falle la red — siempre limpiar estado local
    } finally {
      navigate('/login')
    }
  }

  return (
    <aside className="w-64 border-r border-slate-200 bg-white flex flex-col">
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        <div className="space-y-2">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-3">
            Seguimiento
          </h2>
          <nav className="space-y-1">
            <NavItem to="/seguimiento/no-contestados" label="No contestados" icon={() => null} />
            <NavItem to="/seguimiento/contestados" label="Contestados" icon={() => null} />
            <NavItem to="/seguimiento/pagos" label="Pagos" icon={() => null} />
            <NavItem to="/seguimiento/rebotados" label="Rebotados" icon={() => null} />
          </nav>
        </div>

        <Separator />

        <div className="space-y-2">
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide px-3">
            Gestión
          </h2>
          <nav className="space-y-1">
            <NavItem to="/nuevo-envio/para-enviar" label="Nuevo Envío" icon={() => null} />
            <NavItem to="/maestro" label="Maestro de Clientes" icon={() => null} />
            <NavItem to="/plantilla" label="Plantilla" icon={() => null} />
            <NavItem to="/configuracion" label="Configuración" icon={() => null} />
          </nav>
        </div>
      </div>

      <Separator />

      <div className="p-4 space-y-2">
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start text-slate-600 hover:text-slate-900"
          onClick={() => {}}
        >
          <KeyRound className="h-4 w-4 mr-2" />
          Cambiar contraseña
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="w-full justify-start text-red-600 hover:text-red-900"
          onClick={handleLogout}
        >
          <LogOut className="h-4 w-4 mr-2" />
          Salir
        </Button>
      </div>
    </aside>
  )
}
