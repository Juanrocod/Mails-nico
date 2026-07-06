import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Inbox,
  Reply,
  CheckCircle2,
  Ban,
  Send,
  Users,
  FileText,
  Settings,
  Upload,
  LogOut,
  KeyRound,
} from 'lucide-react'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import { cn } from '../../lib/utils'
import { useAuth } from '../../hooks/useAuth'
import { useCicloContext } from '../../contexts/useCicloContext'
import ChangePasswordModal from '../profile/ChangePasswordModal'

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
            ? 'bg-secondary text-foreground font-medium'
            : 'text-muted-foreground hover:bg-secondary/60 hover:text-foreground'
        )
      }
    >
      <span className="flex items-center gap-2">
        <Icon className="h-4 w-4 shrink-0" />
        {label}
      </span>
      {count !== undefined && count > 0 && (
        <Badge variant="secondary" className="text-xs tabular-nums">
          {count}
        </Badge>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const { openUpload } = useCicloContext()
  const [changePassOpen, setChangePassOpen] = useState(false)

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
    <aside className="w-60 h-screen shrink-0 flex flex-col bg-background border-r border-border">
      <div className="px-4 py-5 border-b border-border">
        <p className="text-sm font-semibold text-foreground">Mails Nico</p>
        <p className="text-xs text-muted-foreground mt-0.5">Cobro automático</p>
      </div>

      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        <NavItem to="/dashboard" label="Dashboard" icon={LayoutDashboard} />

        <Separator className="my-2" />

        <NavItem to="/nuevo-envio/para-enviar" label="Nuevo Envío" icon={Send} />

        <Separator className="my-2" />

        <NavItem to="/seguimiento/no-contestados" label="No contestados" icon={Inbox} />
        <NavItem to="/seguimiento/contestados" label="Contestados" icon={Reply} />
        <NavItem to="/seguimiento/pagos" label="Pagos" icon={CheckCircle2} />
        <NavItem to="/seguimiento/rebotados" label="Rebotados" icon={Ban} />

        <Separator className="my-2" />

        <NavItem to="/maestro" label="Maestro de Clientes" icon={Users} />
        <NavItem to="/plantilla" label="Plantilla" icon={FileText} />
        <NavItem to="/configuracion" label="Configuración" icon={Settings} />
      </nav>

      <div className="p-3 border-t border-border space-y-2">
        <Button variant="outline" size="sm" className="w-full gap-2" onClick={openUpload}>
          <Upload className="h-3.5 w-3.5" />
          Subir Excel
        </Button>

        <div className="flex items-center justify-between px-1">
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-full bg-primary flex items-center justify-center text-[10px] font-semibold text-primary-foreground">
              OP
            </div>
            <span className="text-xs text-muted-foreground">Operario</span>
          </div>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={() => setChangePassOpen(true)}
              title="Cambiar contraseña"
            >
              <KeyRound className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={handleLogout}
              title="Cerrar sesión"
            >
              <LogOut className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
          </div>
        </div>
      </div>

      <ChangePasswordModal open={changePassOpen} onClose={() => setChangePassOpen(false)} />
    </aside>
  )
}
