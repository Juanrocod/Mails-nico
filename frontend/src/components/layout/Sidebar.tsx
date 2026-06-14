import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  FileText,
  CheckCircle2,
  Send,
  CheckCircle,
  AlertTriangle,
  ClipboardList,
  Upload,
  LogOut,
} from 'lucide-react'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Separator } from '../ui/separator'
import { cn } from '../../lib/utils'
import { fetchMinutas } from '../../services/minutas'
import { clearTokens } from '../../services/api'
import ExcelUploadModal from '../upload/ExcelUploadModal'
import type { EstadoMinuta } from '../../types/domain'

function useBadgeCount(estado: EstadoMinuta): number {
  const { data } = useQuery({
    queryKey: ['minutas', estado],
    queryFn: () => fetchMinutas(estado),
    staleTime: 30_000,
  })
  return data?.total ?? 0
}

const NAV_ITEMS = [
  { to: '/dashboard/borradores', label: 'Borradores', icon: FileText, badge: 'BORRADOR' as EstadoMinuta },
  { to: '/dashboard/aprobados', label: 'Aprobados', icon: CheckCircle2, badge: 'APROBADO' as EstadoMinuta },
  { to: '/dashboard/enviados', label: 'Enviados', icon: Send, badge: 'ENVIADO' as EstadoMinuta },
  { to: '/dashboard/confirmados', label: 'Confirmados', icon: CheckCircle, badge: null },
  { to: '/dashboard/alertas', label: 'Alertas', icon: AlertTriangle, badge: 'ALERTA' as EstadoMinuta },
]

function NavItem({
  to,
  label,
  icon: Icon,
  count,
  isAlert,
}: {
  to: string
  label: string
  icon: React.ElementType
  count: number
  isAlert?: boolean
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
        <Icon className={cn('h-4 w-4 shrink-0', isAlert && 'text-red-500')} />
        {label}
      </span>
      {count > 0 && (
        <Badge
          variant="secondary"
          className={cn('text-xs tabular-nums', isAlert && 'bg-red-100 text-red-700')}
        >
          {count}
        </Badge>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const navigate = useNavigate()
  const [uploadOpen, setUploadOpen] = useState(false)

  const counts: Record<string, number> = {
    BORRADOR: useBadgeCount('BORRADOR'),
    APROBADO: useBadgeCount('APROBADO'),
    ENVIADO: useBadgeCount('ENVIADO'),
    ALERTA: useBadgeCount('ALERTA'),
  }

  function handleLogout() {
    clearTokens()
    navigate('/login')
  }

  return (
    <>
      <aside className="w-60 h-screen flex flex-col bg-white border-r border-slate-200 shrink-0">
        <div className="px-4 py-5 border-b border-slate-100">
          <p className="text-sm font-semibold text-slate-900">Gestión de Minutas</p>
          <p className="text-xs text-slate-400 mt-0.5">Sistema bursátil CNV</p>
        </div>

        <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
          {NAV_ITEMS.map(({ to, label, icon, badge }) => (
            <NavItem
              key={to}
              to={to}
              label={label}
              icon={icon}
              count={badge ? counts[badge] : 0}
              isAlert={badge === 'ALERTA'}
            />
          ))}
          <Separator className="my-2" />
          <NavLink
            to="/dashboard/audit"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-slate-100 text-slate-900 font-medium'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
              )
            }
          >
            <ClipboardList className="h-4 w-4 shrink-0" />
            Audit Trail
          </NavLink>
        </nav>

        <div className="p-3 border-t border-slate-100 space-y-2">
          <Button
            variant="outline"
            size="sm"
            className="w-full gap-2"
            onClick={() => setUploadOpen(true)}
          >
            <Upload className="h-3.5 w-3.5" />
            Subir Excel
          </Button>
          <div className="flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <div className="h-7 w-7 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-semibold text-slate-600">
                MO
              </div>
              <span className="text-xs text-slate-600">Middle Office</span>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={handleLogout}
              title="Cerrar sesión"
            >
              <LogOut className="h-3.5 w-3.5 text-slate-400" />
            </Button>
          </div>
        </div>
      </aside>

      <ExcelUploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} />
    </>
  )
}
