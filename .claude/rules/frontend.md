---
paths:
  - "frontend/**/*.tsx"
  - "frontend/**/*.ts"
---

## Stack

- React 18 + TypeScript + Vite
- shadcn/ui + Tailwind CSS v3
- TanStack Query v5
- React Router v6
- React Hook Form v7
- Axios v1 — instancia única en `src/services/api.ts`
- date-fns v3 (locale `es`)
- lucide-react

## Estructura de carpetas

```
src/
├── pages/          ← LoginPage, DashboardPage, NuevoEnvioPage, SeguimientoPage,
│                     MaestroPage, PlantillaPage, ConfiguracionPage, ClientePerfilPage
├── components/
│   ├── layout/     ← AppLayout, Sidebar, AuthGuard, ErrorBoundary
│   ├── envios/     ← EnvioCard, EnvioDrawer
│   ├── upload/     ← ExcelUploadModal, ProgresoEnvio, FileDropzone, MaestroUploadModal
│   ├── profile/    ← ChangePasswordModal
│   ├── dashboard/  ← EvolucionChart
│   ├── maestro/    ← AgregarClienteModal
│   └── ui/         ← shadcn/ui (auto-generados, no editar a mano)
├── services/       ← api, auth, ciclos, maestro, envios, plantilla, configuracion, dashboard, seguimiento
├── hooks/          ← useAuth, useCiclo, useEnvios
└── types/          ← domain.ts (única fuente de verdad de tipos)
```

## Rutas (App.tsx)

```
/login                        → LoginPage
/dashboard                    → DashboardPage
/nuevo-envio/para-enviar      → NuevoEnvioPage (tab="PARA_ENVIAR")
/nuevo-envio/sin-email        → NuevoEnvioPage (tab="SIN_EMAIL")
/nuevo-envio/filtrados        → NuevoEnvioPage (tab="FILTRADO")
/seguimiento/no-contestados   → SeguimientoPage (tab="NO_CONTESTADO")
/seguimiento/contestados      → SeguimientoPage (tab="CONTESTADO")
/seguimiento/pagos            → SeguimientoPage (tab="PAGO")
/seguimiento/rebotados        → SeguimientoPage (tab="REBOTADO")
/maestro                      → MaestroPage
/clientes/:clave              → ClientePerfilPage
/plantilla                    → PlantillaPage
/configuracion                → ConfiguracionPage
/                             → redirect /dashboard
```

## Tipos de dominio (`src/types/domain.ts`)

```ts
type EstadoEnvio = "NO_CONTESTADO" | "CONTESTADO" | "PAGO" | "REBOTADO" | "SIN_EMAIL" | "FILTRADO"
type MotivoFiltrado = "MONTO_MINIMO" | "DADO_DE_BAJA"

interface Envio {
  id: string
  ciclo_id: string
  clave_union: string
  nombre_consorcio: string
  localidad: string
  monto: number
  email: string | null
  estado: EstadoEnvio
  motivo_filtrado: MotivoFiltrado | null
  message_id: string | null
  enviado_en: string | null
  reply_en: string | null
  reply_snippet: string | null
  tiene_adjunto: boolean
  ciclo_numero: number
}

interface Ciclo {
  id: string
  nombre_archivo: string
  total_deudores: number
  para_enviar: number
  sin_email: number
  filtrados: number
  activo: boolean
  creado_en: string
}

interface ClienteMaestro {
  id: string
  clave_union: string
  nombre: string
  email: string
  activo: boolean
  prefiere_no_recibir_email: boolean
  actualizado_en: string
}

interface Plantilla {
  asunto: string
  cuerpo: string
  monto_minimo: number
  logo_url: string | null
  color_primario: string
  nombre_empresa: string
  pie_email: string
}

interface PreviewCiclo {
  para_enviar: number
  sin_email: number
  filtrados: number
  items_para_enviar: Envio[]
  items_sin_email: Envio[]
  items_filtrados: Envio[]
}
```

## Estado del servidor — TanStack Query

Query keys exactas:

| Key | Datos |
|-----|-------|
| `['ciclo', 'activo']` | Ciclo activo actual |
| `['envios', estado]` | Envios por estado del ciclo activo |
| `['maestro']` | Lista de ClienteMaestro |
| `['plantilla']` | Plantilla singleton |

Hooks en `useCiclo.ts`:
- `useCicloActivo()`, `usePreviewCiclo()`, `useConfirmarEnvio()`

Hooks en `useEnvios.ts`:
- `useEnviosPorEstado(estado)`, `useMoverAPago(id)`, `useConteoEnvios()`

Invalidar todos los envios: `queryClient.invalidateQueries({ queryKey: ['envios'] })`.

## Sidebar

```
[ Seguimiento ]         ← header de sección
  No contestados  (N)   ← badge con conteo
  Contestados     (N)
  Pagos           (N)
  Rebotados       (N)
────────────────────
[ Gestión ]
  Nuevo Envío
  Maestro de Clientes
  Plantilla
  Configuración
```

Footer: avatar del operario + íconos (cambiar contraseña / logout).

## SSE — Progreso de envío

```ts
// En ProgresoEnvio.tsx
const eventSource = new EventSource('/ciclos/enviar-stream', { withCredentials: true })
eventSource.onmessage = (e) => {
  const envio: Envio = JSON.parse(e.data)
  setEnviados(prev => [...prev, envio])
}
eventSource.onerror = () => eventSource.close()
```

## Naming

- Componentes: PascalCase (`EnvioCard`, `ProgresoEnvio`)
- Hooks: `use` + camelCase (`useCicloActivo`, `useEnviosPorEstado`)
- Servicios: camelCase (`fetchEnviosPorEstado`, `confirmarEnvio`)
- Archivos: nombre igual al export default

## Autenticación

- Tokens (`access_token` + `refresh_token`) en **`localStorage`**, leídos/escritos en `api.ts`
- Flujo: POST `/auth/login` → guardar tokens (sin 2FA, respuesta directa)
- `apiFetch` agrega `Authorization: Bearer`; en 401 (salvo endpoints de auth) intenta
  `refreshAccessToken`; si falla → limpia tokens + redirect `/login`
- ⚠️ localStorage es accesible a JS (riesgo XSS). Aceptado para el MVP; ver `rules/seguridad.md`

## Formateo de fechas

```ts
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
format(new Date(enviado_en), 'dd/MM/yyyy HH:mm', { locale: es })
```

## Variable de entorno

`VITE_API_URL` en `frontend/.env` (no commitear). Dev: `http://localhost:8000`.
