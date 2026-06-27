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
├── pages/          ← LoginPage, TwoFactorPage, RegisterPage, ResetPasswordPage,
│                     DashboardPage, FiltradaPage, PlantillaPage, ConfigDJPage, FiltrosMinutasPage
├── components/
│   ├── layout/     ← AppLayout.tsx, Sidebar.tsx, AuthGuard.tsx, ErrorBoundary.tsx
│   ├── minutas/    ← MinutaCard.tsx, MinutaDrawer.tsx
│   ├── upload/     ← ExcelUploadModal.tsx
│   ├── profile/    ← ChangePasswordModal.tsx, RegenerateTOTPModal.tsx
│   └── ui/         ← shadcn/ui (auto-generados, no editar a mano)
├── services/       ← api.ts, auth.ts, minutas.ts, upload.ts, plantilla.ts, configDJ.ts, configFiltros.ts
├── hooks/          ← useAuth.ts, useSession.ts
└── types/          ← domain.ts (única fuente de verdad de tipos)
```

## Rutas (App.tsx)

```
/login                     → LoginPage
/login/2fa                 → TwoFactorPage
/register                  → RegisterPage
/reset-password            → ResetPasswordPage
/dashboard/borradores      → DashboardPage (estado="BORRADOR")
/dashboard/enviados        → DashboardPage (estado="ENVIADO")
/dashboard/filtradas       → FiltradaPage
/dashboard/plantilla       → PlantillaPage
/dashboard/config-dj       → ConfigDJPage        (multi-DJ CRUD)
/dashboard/filtros-minutas → FiltrosMinutasPage
/                          → redirect /dashboard/borradores
```

## Tipos de dominio (`src/types/domain.ts`)

```ts
type EstadoMinuta = "BORRADOR" | "ENVIADO" | "FILTRADA"

interface Minuta {
  id: string
  // Del Excel
  cliente_nombre: string
  cuenta_comitente: string
  cuenta_cotapartista: string
  id_orden: number
  fecha_operacion: string      // ISO datetime
  fecha_liquidacion: string
  operacion: string
  instrumento: string
  moneda: string
  cantidad: number             // -1 = N/A
  precio: number               // -1 = N/A
  monto: number
  estado_orden: string
  cantidad_operada: number     // -1 = N/A
  precio_operado: number       // -1 = N/A
  operador: string
  origen: string
  asesor: string
  requiere_conformidad: number // 0 | 1
  // De sesión
  dj_aplicada: boolean
  dj_texto: string | null
  estado: EstadoMinuta
  filtro_motivo: string | null
  texto_minuta: string
  texto_editado: boolean
  creado_en: string
}

type CampoRegla =
  | "operacion" | "operador" | "origen" | "estado" | "moneda" | "instrumento"
  | "cantidad" | "precio" | "monto" | "cantidad_operada" | "precio_operado" | "requiere_conformidad"

type OperadorRegla = "=" | "!=" | ">" | "<" | ">=" | "<="

interface ReglaConfig {
  campo: CampoRegla
  operador: OperadorRegla
  valor: string
}

interface ConfigDJ {
  id?: number
  nombre: string
  activa: boolean
  incluir_texto_en_minuta: boolean
  texto_alerta: string
  reglas: ReglaConfig[]
  logica: "AND" | "OR"
  activar_si_requiere_conformidad: boolean
}

interface ConfigFiltros {
  reglas: ReglaConfig[]
  logica: "AND" | "OR"
}
```

## Estado del servidor — TanStack Query

Query keys exactas:

| Key | Datos |
|-----|-------|
| `['minutas', 'BORRADOR']` | Minutas en borrador |
| `['minutas', 'ENVIADO']` | Minutas enviadas |
| `['minutas', 'FILTRADA']` | Minutas filtradas |
| `['plantilla']` | Plantilla de texto |
| `['config-dj']` | Array de ConfigDJ (multi-DJ) |
| `['config', 'filtros-minutas']` | ConfigFiltros singleton |

ConfigDJ es **multi-row** (array). Usar `useConfigDJList()` — no existe hook singular.
Invalidar minutas de todos los estados: `queryClient.invalidateQueries({ queryKey: ['minutas'] })`.

Hooks en `useSession.ts`:
- `usePlantilla()`, `useGuardarPlantilla()`
- `useConfigDJList()`, `useCrearConfigDJ()`, `useActualizarConfigDJ()`, `useEliminarConfigDJ()`
- `useConfigFiltros()`, `usePatchConfigFiltros()`
- `useAgregarFiltrada()`, `useAgregarTodasFiltradas()`

## Sidebar

Orden de ítems:
1. Borradores — badge con conteo
2. Enviados — badge con conteo
3. Filtradas — sin badge
4. `<Separator />`
5. Plantilla Estándar
6. Config DJ
7. Filtros de Minutas

Footer: botón "Subir Excel" + avatar MO + íconos (cambiar contraseña / regenerar TOTP / logout).

## Naming

- Componentes: PascalCase (`MinutaCard`, `ExcelUploadModal`)
- Hooks: `use` + camelCase (`useConfigDJList`, `useAgregarFiltrada`)
- Servicios: camelCase (`fetchAllConfigDJ`, `eliminarConfigDJ`)
- Archivos: nombre igual al export default

## Autenticación

- Tokens en variable de módulo en `api.ts` — NO localStorage ni sessionStorage
- Flujo: POST `/auth/login` → pending_2fa → POST `/auth/verify-2fa` → guardar token
- 401 → intenta refresh → si falla → clear token + redirect `/login`

## Formateo de fechas

```ts
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
format(new Date(fecha_operacion), 'dd/MM/yyyy HH:mm', { locale: es })
```

## Variable de entorno

`VITE_API_URL` en `frontend/.env` (no commitear). Dev: `http://localhost:8000`.
