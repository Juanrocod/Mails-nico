# Frontend Scaffold — Gestión de Minutas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete React frontend for the Gestión de Minutas system — login with 2FA, dashboard with tabs by estado, minuta detail drawer with inline editing and approval actions, Excel upload modal, and audit trail page.

**Architecture:** SPA with React Router v6 protected routes, TanStack Query v5 for all server state (no useState for data), Axios with in-memory JWT (never localStorage), and shadcn/ui + Tailwind CSS v3 for components. The frontend communicates with a FastAPI backend on `http://localhost:8000`.

**Tech Stack:** React 18, TypeScript, Vite, React Router v6, TanStack Query v5, Axios v1, React Hook Form v7, shadcn/ui (Radix primitives + Tailwind v3), date-fns v3 (locale `es`), lucide-react.

**Key backend contract (do not invent endpoints):**
- `POST /auth/login` → `{ pending_token, message }`
- `POST /auth/verify-totp` → `{ access_token, refresh_token, token_type }`
- `POST /auth/refresh` → `{ access_token, refresh_token, token_type }`
- `GET /dashboard/{borradores|aprobados|enviados|confirmados|alertas}?page=1&size=50` → `{ items: Orden[], total, page, size }`
- `PATCH /orders/{id}/text` body `{ texto_minuta }` → `Orden`
- `POST /orders/{id}/approve` → `Orden`
- `POST /orders/{id}/send` → `Orden`
- `POST /orders/{id}/confirm` → `Orden`
- `POST /uploads/excel` (multipart) → `UploadResponse`
- `GET /audit/{orden_id}` → `AuditEvent[]`
- `GET /audit/{orden_id}/export/excel` → xlsx download

---

## File Map

| File | Responsibility |
|------|---------------|
| `frontend/` | Vite project root |
| `src/types/domain.ts` | All TypeScript domain types |
| `src/services/api.ts` | Axios instance + JWT interceptors (tokens in module vars) |
| `src/services/auth.ts` | login, verifyTotp, pending token module var |
| `src/services/minutas.ts` | fetchMinutas, editarTexto, aprobarMinuta, marcarEnviada, registrarConfirmacion |
| `src/services/upload.ts` | uploadExcel |
| `src/services/audit.ts` | fetchAuditTrail, getAuditExcelUrl |
| `src/hooks/useMinutas.ts` | TanStack Query hooks for all minuta operations |
| `src/hooks/useAuth.ts` | Login/logout/2FA navigation wrapper |
| `src/main.tsx` | Entry: QueryClientProvider + BrowserRouter + App |
| `src/App.tsx` | Route tree: login routes + guarded dashboard routes |
| `src/components/layout/AuthGuard.tsx` | Checks access token, redirects to /login if missing |
| `src/components/layout/AppLayout.tsx` | Sidebar + `<Outlet />` |
| `src/components/layout/Sidebar.tsx` | Nav links with badge counts + Upload button + logout |
| `src/pages/LoginPage.tsx` | Usuario + contraseña form |
| `src/pages/TwoFactorPage.tsx` | 6-digit TOTP form |
| `src/pages/DashboardPage.tsx` | Card list + MinutaDrawer state |
| `src/pages/AuditPage.tsx` | Per-order audit lookup + export |
| `src/components/minutas/MinutaCard.tsx` | Card UI (ALERTA gets red border) |
| `src/components/minutas/MinutaDrawer.tsx` | Lateral sheet: text edit, actions, DJ section, audit trail |
| `src/components/minutas/AuditTrailSection.tsx` | Collapsible audit events list |
| `src/components/upload/ExcelUploadModal.tsx` | 4-step upload modal |

---

## Task 1: Scaffold Vite + React + TypeScript project

**Files:**
- Create: `frontend/` (entire Vite project)

- [ ] **Step 1: Run Vite scaffold from the repo root**

```bash
npm create vite@latest frontend -- --template react-ts
```

Expected: creates `frontend/` with `src/main.tsx`, `src/App.tsx`, `vite.config.ts`, `tsconfig.json`, `package.json`.

- [ ] **Step 2: Install base Vite deps**

```bash
cd frontend && npm install
```

Expected: completes without errors, `node_modules/` created.

- [ ] **Step 3: Install application dependencies**

```bash
npm install react-router-dom@6 "@tanstack/react-query@5" axios react-hook-form "date-fns@3" lucide-react clsx tailwind-merge class-variance-authority
```

Expected: all packages resolve without peer dependency errors.

- [ ] **Step 4: Install Tailwind CSS v3 + PostCSS**

```bash
npm install -D "tailwindcss@3" postcss autoprefixer
npx tailwindcss init -p
```

Expected: creates `tailwind.config.js` and `postcss.config.js`.

- [ ] **Step 5: Commit**

```bash
cd ..
git add frontend/
git commit -m "chore: scaffold Vite + React + TypeScript frontend"
```

---

## Task 2: Initialize shadcn/ui + add required components

**Files:**
- Modify: `frontend/tailwind.config.js` (shadcn rewrites it)
- Modify: `frontend/src/index.css` (shadcn adds CSS variables)
- Create: `frontend/src/lib/utils.ts` (shadcn creates this)
- Create: `frontend/src/components/ui/` (shadcn copies components here)

- [ ] **Step 1: Run shadcn init**

```bash
cd frontend
npx shadcn@latest init
```

When prompted, answer:
- Which style? → **Default**
- Which color for base? → **Slate**
- Use CSS variables for theming? → **Yes**

Expected: modifies `tailwind.config.js`, overwrites `src/index.css` with CSS variables, creates `src/lib/utils.ts` with the `cn()` function, creates `components.json`.

- [ ] **Step 2: Install all shadcn components needed by this project**

```bash
npx shadcn@latest add button card badge sheet dialog textarea input collapsible skeleton separator scroll-area
```

Answer `y` to any "overwrite" prompts. Expected: all components appear in `src/components/ui/`.

- [ ] **Step 3: Verify tailwind.config.js has the right content paths**

Open `frontend/tailwind.config.js`. It should include `./src/**/*.{ts,tsx}` in `content`. If shadcn didn't add it, add it manually:

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      // shadcn extends go here — leave whatever shadcn generated
    },
  },
  plugins: [require("tailwindcss-animate")],
}
```

If shadcn added `tailwindcss-animate`, install it:

```bash
npm install -D tailwindcss-animate
```

- [ ] **Step 4: Create directory structure**

```bash
mkdir -p src/pages src/components/layout src/components/minutas src/components/upload src/services src/hooks src/types
```

- [ ] **Step 5: Create frontend/.env**

Create `frontend/.env` with:
```
VITE_API_URL=http://localhost:8000
```

This file must NOT be committed (root `.gitignore` already excludes `.env`).

- [ ] **Step 6: Commit**

```bash
cd ..
git add frontend/src/components/ui/ frontend/src/lib/ frontend/components.json frontend/tailwind.config.js frontend/src/index.css frontend/postcss.config.js
git commit -m "chore: initialize shadcn/ui with Slate theme and add UI components"
```

---

## Task 3: Domain types (`src/types/domain.ts`)

**Files:**
- Create: `frontend/src/types/domain.ts`

- [ ] **Step 1: Write domain types matching the backend schemas exactly**

Create `frontend/src/types/domain.ts`:

```ts
export type EstadoMinuta = 'BORRADOR' | 'APROBADO' | 'ENVIADO' | 'CONFIRMADO' | 'ALERTA'
export type TipoOperacion = 'COMPRA' | 'VENTA'
export type Liquidacion = 'CI' | '24HS' | '48HS'
export type AccionAudit = 'CREADA' | 'EDITADA' | 'APROBADA' | 'ENVIADA' | 'CONFIRMADA' | 'ALERTA_GENERADA'

export interface Orden {
  id: string
  excel_upload_id: string
  cliente_nombre: string
  cliente_email: string
  cuenta_comitente: string
  cuenta_cotapartista: string
  instrumento: string
  tipo: TipoOperacion
  cantidad: number
  precio: number
  moneda: string
  liquidacion: Liquidacion
  fecha_operacion: string
  dj_aplicada: boolean
  dj_tipo: string | null
  estado: EstadoMinuta
  texto_minuta: string
  texto_editado: boolean
  created_at: string
  updated_at: string
}

export interface AuditEvent {
  id: string
  orden_id: string
  usuario_id: string | null
  accion: AccionAudit
  ip_origen: string | null
  timestamp: string
  detalle: Record<string, unknown> | null
}

export interface DashboardPage {
  items: Orden[]
  total: number
  page: number
  size: number
}

export interface UploadResponse {
  upload_id: string
  nombre_archivo: string
  total_ordenes: number
  ordenes_validas: number
  ordenes_con_error: number
  errors: { fila: number; mensaje: string }[]
}

export interface LoginResponse {
  pending_token: string
  message: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}
```

Note: `created_at` / `updated_at` match the backend `OrdenResponse` schema (not `creado_en` — that name appears in `CONTEXT.md` but the actual backend field is `created_at`).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/domain.ts
git commit -m "feat(frontend): add domain types matching backend schemas"
```

---

## Task 4: Axios instance with JWT interceptors (`src/services/api.ts`)

**Files:**
- Create: `frontend/src/services/api.ts`

- [ ] **Step 1: Write api.ts**

Create `frontend/src/services/api.ts`:

```ts
import axios from 'axios'

let accessToken: string | null = null
let refreshToken: string | null = null

export function setTokens(access: string, refresh: string): void {
  accessToken = access
  refreshToken = refresh
}

export function clearTokens(): void {
  accessToken = null
  refreshToken = null
}

export function getAccessToken(): string | null {
  return accessToken
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
})

api.interceptors.request.use((config) => {
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      refreshToken
    ) {
      originalRequest._retry = true
      try {
        const res = await axios.post(
          `${import.meta.env.VITE_API_URL}/auth/refresh`,
          { refresh_token: refreshToken }
        )
        setTokens(res.data.access_token, res.data.refresh_token)
        originalRequest.headers.Authorization = `Bearer ${res.data.access_token}`
        return api(originalRequest)
      } catch {
        clearTokens()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)
```

Tokens live in module-level variables — never in `localStorage` or `sessionStorage`. On 401, the interceptor tries one refresh. If refresh also fails, it clears tokens and hard-redirects to `/login`.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/api.ts
git commit -m "feat(frontend): add Axios instance with in-memory JWT interceptors"
```

---

## Task 5: Auth service (`src/services/auth.ts`)

**Files:**
- Create: `frontend/src/services/auth.ts`

- [ ] **Step 1: Write auth.ts**

Create `frontend/src/services/auth.ts`:

```ts
import { api } from './api'
import type { LoginResponse, TokenResponse } from '../types/domain'

let pendingToken: string | null = null

export function setPendingToken(token: string): void {
  pendingToken = token
}

export function getPendingToken(): string | null {
  return pendingToken
}

export function clearPendingToken(): void {
  pendingToken = null
}

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/login', { username, password })
  return res.data
}

export async function verifyTotp(
  pending_token: string,
  code: string
): Promise<TokenResponse> {
  const res = await api.post<TokenResponse>('/auth/verify-totp', {
    pending_token,
    code,
  })
  return res.data
}
```

The `pendingToken` module variable bridges the two login pages (LoginPage sets it, TwoFactorPage reads it). This is intentional — it matches the in-memory pattern used for the JWT tokens.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/services/auth.ts
git commit -m "feat(frontend): add auth service with pending token handling"
```

---

## Task 6: Data services (`src/services/minutas.ts`, `upload.ts`, `audit.ts`)

**Files:**
- Create: `frontend/src/services/minutas.ts`
- Create: `frontend/src/services/upload.ts`
- Create: `frontend/src/services/audit.ts`

- [ ] **Step 1: Write minutas.ts**

Create `frontend/src/services/minutas.ts`:

```ts
import { api } from './api'
import type { DashboardPage, Orden, EstadoMinuta } from '../types/domain'

const ESTADO_SLUG: Record<EstadoMinuta, string> = {
  BORRADOR: 'borradores',
  APROBADO: 'aprobados',
  ENVIADO: 'enviados',
  CONFIRMADO: 'confirmados',
  ALERTA: 'alertas',
}

export async function fetchMinutas(
  estado: EstadoMinuta,
  page = 1,
  size = 50
): Promise<DashboardPage> {
  const res = await api.get<DashboardPage>(`/dashboard/${ESTADO_SLUG[estado]}`, {
    params: { page, size },
  })
  return res.data
}

export async function editarTexto(
  ordenId: string,
  texto_minuta: string
): Promise<Orden> {
  const res = await api.patch<Orden>(`/orders/${ordenId}/text`, { texto_minuta })
  return res.data
}

export async function aprobarMinuta(ordenId: string): Promise<Orden> {
  const res = await api.post<Orden>(`/orders/${ordenId}/approve`)
  return res.data
}

export async function marcarEnviada(ordenId: string): Promise<Orden> {
  const res = await api.post<Orden>(`/orders/${ordenId}/send`)
  return res.data
}

export async function registrarConfirmacion(ordenId: string): Promise<Orden> {
  const res = await api.post<Orden>(`/orders/${ordenId}/confirm`)
  return res.data
}
```

- [ ] **Step 2: Write upload.ts**

Create `frontend/src/services/upload.ts`:

```ts
import { api } from './api'
import type { UploadResponse } from '../types/domain'

export async function uploadExcel(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post<UploadResponse>('/uploads/excel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data
}
```

- [ ] **Step 3: Write audit.ts**

Create `frontend/src/services/audit.ts`:

```ts
import { api } from './api'
import type { AuditEvent } from '../types/domain'

export async function fetchAuditTrail(ordenId: string): Promise<AuditEvent[]> {
  const res = await api.get<AuditEvent[]>(`/audit/${ordenId}`)
  return res.data
}

export function getAuditExcelUrl(ordenId: string): string {
  return `${import.meta.env.VITE_API_URL}/audit/${ordenId}/export/excel`
}
```

Note: `getAuditExcelUrl` returns a URL string so the caller can set `window.location.href` for a direct browser download (the backend returns a file attachment, not JSON).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/minutas.ts frontend/src/services/upload.ts frontend/src/services/audit.ts
git commit -m "feat(frontend): add data services for minutas, upload, and audit"
```

---

## Task 7: TanStack Query hooks (`src/hooks/useMinutas.ts`, `useAuth.ts`)

**Files:**
- Create: `frontend/src/hooks/useMinutas.ts`
- Create: `frontend/src/hooks/useAuth.ts`

- [ ] **Step 1: Write useMinutas.ts**

Create `frontend/src/hooks/useMinutas.ts`:

```ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  fetchMinutas,
  aprobarMinuta,
  marcarEnviada,
  registrarConfirmacion,
  editarTexto,
} from '../services/minutas'
import type { EstadoMinuta } from '../types/domain'

export function useMinutas(estado: EstadoMinuta) {
  return useQuery({
    queryKey: ['minutas', estado],
    queryFn: () => fetchMinutas(estado),
  })
}

export function useAprobarMinuta() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: aprobarMinuta,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'APROBADO'] })
    },
  })
}

export function useMarcarEnviada() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: marcarEnviada,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'APROBADO'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'ENVIADO'] })
    },
  })
}

export function useRegistrarConfirmacion() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: registrarConfirmacion,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'ENVIADO'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'ALERTA'] })
      qc.invalidateQueries({ queryKey: ['minutas', 'CONFIRMADO'] })
    },
  })
}

export function useEditarTexto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ ordenId, texto }: { ordenId: string; texto: string }) =>
      editarTexto(ordenId, texto),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR'] })
    },
  })
}
```

- [ ] **Step 2: Write useAuth.ts**

Create `frontend/src/hooks/useAuth.ts`:

```ts
import { useNavigate } from 'react-router-dom'
import {
  login,
  verifyTotp,
  setPendingToken,
  getPendingToken,
  clearPendingToken,
} from '../services/auth'
import { setTokens, clearTokens, getAccessToken } from '../services/api'

export function useAuth() {
  const navigate = useNavigate()

  async function handleLogin(username: string, password: string): Promise<void> {
    const res = await login(username, password)
    setPendingToken(res.pending_token)
    navigate('/login/2fa')
  }

  async function handleVerify2fa(code: string): Promise<void> {
    const token = getPendingToken()
    if (!token) {
      navigate('/login')
      return
    }
    const res = await verifyTotp(token, code)
    clearPendingToken()
    setTokens(res.access_token, res.refresh_token)
    navigate('/dashboard/borradores')
  }

  function handleLogout(): void {
    clearTokens()
    navigate('/login')
  }

  function isAuthenticated(): boolean {
    return getAccessToken() !== null
  }

  return { handleLogin, handleVerify2fa, handleLogout, isAuthenticated }
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/
git commit -m "feat(frontend): add useMinutas and useAuth hooks"
```

---

## Task 8: App entry + Router + AuthGuard

**Files:**
- Modify: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx` (replace default)
- Create: `frontend/src/components/layout/AuthGuard.tsx`

- [ ] **Step 1: Rewrite main.tsx**

Replace the entire contents of `frontend/src/main.tsx`:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>
)
```

- [ ] **Step 2: Write App.tsx**

Replace the entire contents of `frontend/src/App.tsx`:

```tsx
import { Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import TwoFactorPage from './pages/TwoFactorPage'
import DashboardPage from './pages/DashboardPage'
import AuditPage from './pages/AuditPage'
import AppLayout from './components/layout/AppLayout'
import AuthGuard from './components/layout/AuthGuard'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/login/2fa" element={<TwoFactorPage />} />
      <Route element={<AuthGuard />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard/borradores" element={<DashboardPage estado="BORRADOR" />} />
          <Route path="/dashboard/aprobados" element={<DashboardPage estado="APROBADO" />} />
          <Route path="/dashboard/enviados" element={<DashboardPage estado="ENVIADO" />} />
          <Route path="/dashboard/confirmados" element={<DashboardPage estado="CONFIRMADO" />} />
          <Route path="/dashboard/alertas" element={<DashboardPage estado="ALERTA" />} />
          <Route path="/dashboard/audit" element={<AuditPage />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/dashboard/borradores" replace />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
```

- [ ] **Step 3: Write AuthGuard.tsx**

Create `frontend/src/components/layout/AuthGuard.tsx`:

```tsx
import { Navigate, Outlet } from 'react-router-dom'
import { getAccessToken } from '../../services/api'

export default function AuthGuard() {
  if (!getAccessToken()) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}
```

Note: This check runs synchronously. On page refresh, `accessToken` will be `null` (module re-initializes), so the user will be redirected to `/login`. This is by design — tokens live in memory only.

- [ ] **Step 4: Create placeholder page files so App.tsx compiles**

These will be replaced in later tasks, but are needed now to avoid import errors.

Create `frontend/src/pages/LoginPage.tsx`:
```tsx
export default function LoginPage() {
  return <div>Login</div>
}
```

Create `frontend/src/pages/TwoFactorPage.tsx`:
```tsx
export default function TwoFactorPage() {
  return <div>2FA</div>
}
```

Create `frontend/src/pages/DashboardPage.tsx`:
```tsx
import type { EstadoMinuta } from '../types/domain'
export default function DashboardPage({ estado }: { estado: EstadoMinuta }) {
  return <div>Dashboard: {estado}</div>
}
```

Create `frontend/src/pages/AuditPage.tsx`:
```tsx
export default function AuditPage() {
  return <div>Audit</div>
}
```

Create `frontend/src/components/layout/AppLayout.tsx`:
```tsx
import { Outlet } from 'react-router-dom'
export default function AppLayout() {
  return <Outlet />
}
```

- [ ] **Step 5: Delete Vite boilerplate**

Delete `frontend/src/assets/react.svg` and `public/vite.svg` if they exist. Also delete any `App.css` if it was generated.

```bash
cd frontend
rm -f src/assets/react.svg public/vite.svg src/App.css
```

- [ ] **Step 6: Verify the project compiles**

```bash
npm run build
```

Expected: build succeeds (0 TypeScript errors). Ignore warnings about `__vite_ssr__` or similar Vite internals.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/src/
git commit -m "feat(frontend): add routing, AuthGuard, and placeholder pages"
```

---

## Task 9: AppLayout + Sidebar

**Files:**
- Modify: `frontend/src/components/layout/AppLayout.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Write AppLayout.tsx**

Replace `frontend/src/components/layout/AppLayout.tsx`:

```tsx
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'

export default function AppLayout() {
  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  )
}
```

- [ ] **Step 2: Write Sidebar.tsx**

Create `frontend/src/components/layout/Sidebar.tsx`:

```tsx
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
```

Note: `Sidebar` calls `useBadgeCount` for each estado that has a badge. TanStack Query will deduplicate these calls with the ones made by `DashboardPage` — the cache is shared by query key.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/layout/
git commit -m "feat(frontend): add AppLayout and Sidebar with badge counts"
```

---

## Task 10: LoginPage

**Files:**
- Modify: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Write LoginPage.tsx**

Replace `frontend/src/pages/LoginPage.tsx`:

```tsx
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { useAuth } from '../hooks/useAuth'

interface FormValues {
  username: string
  password: string
}

export default function LoginPage() {
  const { handleLogin } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<FormValues>()

  async function onSubmit(data: FormValues) {
    try {
      setError(null)
      await handleLogin(data.username, data.password)
    } catch {
      setError('Credenciales inválidas. Verificá tu usuario y contraseña.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-semibold text-slate-900">Gestión de Minutas</h1>
          <p className="text-sm text-slate-500">Ingresá con tus credenciales</p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 bg-white p-6 rounded-lg border border-slate-200 shadow-sm"
        >
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Usuario</label>
            <Input
              {...register('username', { required: true })}
              placeholder="usuario"
              autoComplete="username"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Contraseña</label>
            <Input
              {...register('password', { required: true })}
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{error}</p>
          )}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Ingresando...' : 'Ingresar'}
          </Button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat(frontend): implement LoginPage with react-hook-form"
```

---

## Task 11: TwoFactorPage

**Files:**
- Modify: `frontend/src/pages/TwoFactorPage.tsx`

- [ ] **Step 1: Write TwoFactorPage.tsx**

Replace `frontend/src/pages/TwoFactorPage.tsx`:

```tsx
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { useAuth } from '../hooks/useAuth'

interface FormValues {
  code: string
}

export default function TwoFactorPage() {
  const navigate = useNavigate()
  const { handleVerify2fa } = useAuth()
  const [error, setError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<FormValues>()

  async function onSubmit(data: FormValues) {
    try {
      setError(null)
      await handleVerify2fa(data.code)
    } catch {
      setError('Código inválido. Revisá tu aplicación de autenticación.')
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center space-y-1">
          <h1 className="text-2xl font-semibold text-slate-900">Verificación 2FA</h1>
          <p className="text-sm text-slate-500">
            Ingresá el código de tu aplicación de autenticación
          </p>
        </div>

        <form
          onSubmit={handleSubmit(onSubmit)}
          className="space-y-4 bg-white p-6 rounded-lg border border-slate-200 shadow-sm"
        >
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-700">Código de 6 dígitos</label>
            <Input
              {...register('code', {
                required: true,
                minLength: 6,
                maxLength: 6,
                pattern: /^\d{6}$/,
              })}
              placeholder="000000"
              inputMode="numeric"
              autoComplete="one-time-code"
              className="text-center text-xl tracking-[0.5em]"
              maxLength={6}
            />
          </div>

          {error && (
            <p className="text-sm text-red-600 bg-red-50 rounded px-3 py-2">{error}</p>
          )}

          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? 'Verificando...' : 'Verificar'}
          </Button>

          <Button
            type="button"
            variant="ghost"
            className="w-full text-sm text-slate-500"
            onClick={() => navigate('/login')}
          >
            Volver al login
          </Button>
        </form>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/TwoFactorPage.tsx
git commit -m "feat(frontend): implement TwoFactorPage with TOTP form"
```

---

## Task 12: MinutaCard

**Files:**
- Create: `frontend/src/components/minutas/MinutaCard.tsx`

- [ ] **Step 1: Write MinutaCard.tsx**

Create `frontend/src/components/minutas/MinutaCard.tsx`:

```tsx
import { format, formatDistanceToNow } from 'date-fns'
import { es } from 'date-fns/locale'
import { FileText, PenLine } from 'lucide-react'
import { Badge } from '../ui/badge'
import { Card } from '../ui/card'
import { cn } from '../../lib/utils'
import type { Orden } from '../../types/domain'

const ESTADO_BADGE: Record<string, string> = {
  BORRADOR: 'bg-slate-100 text-slate-700 hover:bg-slate-100',
  APROBADO: 'bg-blue-100 text-blue-700 hover:bg-blue-100',
  ENVIADO: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-100',
  CONFIRMADO: 'bg-green-100 text-green-700 hover:bg-green-100',
  ALERTA: 'bg-red-100 text-red-700 hover:bg-red-100',
}

function formatPrecio(precio: number, moneda: string): string {
  const currency = moneda === 'USD' ? 'USD' : 'ARS'
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(precio)
}

interface Props {
  orden: Orden
  onClick: () => void
}

export default function MinutaCard({ orden, onClick }: Props) {
  const isAlerta = orden.estado === 'ALERTA'

  return (
    <Card
      className={cn(
        'p-4 cursor-pointer hover:shadow-md transition-all select-none',
        isAlerta && 'border-red-400 hover:border-red-500'
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-slate-900 truncate max-w-[200px]">
              {orden.cliente_nombre}
            </span>
            <Badge
              variant="secondary"
              className={cn(
                'text-xs font-semibold shrink-0',
                orden.tipo === 'COMPRA'
                  ? 'bg-emerald-100 text-emerald-700 hover:bg-emerald-100'
                  : 'bg-red-100 text-red-700 hover:bg-red-100'
              )}
            >
              {orden.tipo}
            </Badge>
            {orden.dj_aplicada && (
              <FileText
                className="h-3.5 w-3.5 text-slate-400 shrink-0"
                aria-label="Con Declaración Jurada"
              />
            )}
            {orden.texto_editado && (
              <PenLine
                className="h-3.5 w-3.5 text-amber-500 shrink-0"
                aria-label="Texto editado manualmente"
              />
            )}
          </div>

          <p className="text-sm text-slate-700">
            {orden.instrumento} — {orden.cantidad.toLocaleString('es-AR')} ×{' '}
            {formatPrecio(orden.precio, orden.moneda)} {orden.moneda}
          </p>

          <div className="flex items-center gap-2 text-xs text-slate-500 flex-wrap">
            <span>Liq. {orden.liquidacion}</span>
            <span>·</span>
            <span>
              {format(new Date(orden.fecha_operacion), 'dd/MM/yyyy HH:mm', { locale: es })}
            </span>
            {isAlerta && (
              <>
                <span>·</span>
                <span className="text-red-600 font-medium">
                  {formatDistanceToNow(new Date(orden.updated_at), {
                    addSuffix: true,
                    locale: es,
                  })}
                </span>
              </>
            )}
          </div>
        </div>

        <Badge
          variant="secondary"
          className={cn('text-xs shrink-0 self-start mt-0.5', ESTADO_BADGE[orden.estado])}
        >
          {orden.estado}
        </Badge>
      </div>
    </Card>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/minutas/MinutaCard.tsx
git commit -m "feat(frontend): add MinutaCard component with ALERTA styling"
```

---

## Task 13: AuditTrailSection

**Files:**
- Create: `frontend/src/components/minutas/AuditTrailSection.tsx`

- [ ] **Step 1: Write AuditTrailSection.tsx**

Create `frontend/src/components/minutas/AuditTrailSection.tsx`:

```tsx
import { useQuery } from '@tanstack/react-query'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { ChevronDown } from 'lucide-react'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../ui/collapsible'
import { Skeleton } from '../ui/skeleton'
import { fetchAuditTrail } from '../../services/audit'
import type { AccionAudit } from '../../types/domain'

const ACCION_LABEL: Record<AccionAudit, string> = {
  CREADA: 'Minuta creada',
  EDITADA: 'Texto editado',
  APROBADA: 'Aprobada',
  ENVIADA: 'Marcada como enviada',
  CONFIRMADA: 'Confirmación registrada',
  ALERTA_GENERADA: 'Alerta generada',
}

interface Props {
  ordenId: string
}

export default function AuditTrailSection({ ordenId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ['audit', ordenId],
    queryFn: () => fetchAuditTrail(ordenId),
  })

  return (
    <Collapsible>
      <CollapsibleTrigger className="flex items-center justify-between w-full text-sm font-medium text-slate-700 hover:text-slate-900 py-1 group">
        <span>Audit Trail</span>
        <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-data-[state=open]:rotate-180" />
      </CollapsibleTrigger>
      <CollapsibleContent className="pt-3">
        {isLoading && <Skeleton className="h-24 w-full rounded-md" />}
        {data && data.length === 0 && (
          <p className="text-xs text-slate-400">Sin eventos registrados.</p>
        )}
        {data && data.length > 0 && (
          <div className="space-y-3">
            {data.map((event) => (
              <div
                key={event.id}
                className="border-l-2 border-slate-200 pl-3 space-y-0.5"
              >
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium text-slate-700">
                    {ACCION_LABEL[event.accion] ?? event.accion}
                  </span>
                  <span className="text-xs text-slate-400">
                    {format(new Date(event.timestamp), 'dd/MM/yyyy HH:mm:ss', {
                      locale: es,
                    })}
                  </span>
                </div>
                {event.ip_origen && (
                  <p className="text-[11px] text-slate-400">IP: {event.ip_origen}</p>
                )}
              </div>
            ))}
          </div>
        )}
      </CollapsibleContent>
    </Collapsible>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/minutas/AuditTrailSection.tsx
git commit -m "feat(frontend): add AuditTrailSection collapsible component"
```

---

## Task 14: MinutaDrawer

**Files:**
- Create: `frontend/src/components/minutas/MinutaDrawer.tsx`

- [ ] **Step 1: Write MinutaDrawer.tsx**

Create `frontend/src/components/minutas/MinutaDrawer.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { Copy, PenLine, ChevronDown } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '../ui/sheet'
import { Badge } from '../ui/badge'
import { Button } from '../ui/button'
import { Textarea } from '../ui/textarea'
import { Separator } from '../ui/separator'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '../ui/collapsible'
import { cn } from '../../lib/utils'
import AuditTrailSection from './AuditTrailSection'
import {
  useAprobarMinuta,
  useMarcarEnviada,
  useRegistrarConfirmacion,
  useEditarTexto,
} from '../../hooks/useMinutas'
import type { Orden } from '../../types/domain'

const ESTADO_BADGE: Record<string, string> = {
  BORRADOR: 'bg-slate-100 text-slate-700',
  APROBADO: 'bg-blue-100 text-blue-700',
  ENVIADO: 'bg-yellow-100 text-yellow-800',
  CONFIRMADO: 'bg-green-100 text-green-700',
  ALERTA: 'bg-red-100 text-red-700',
}

interface Props {
  orden: Orden | null
  onClose: () => void
}

export default function MinutaDrawer({ orden, onClose }: Props) {
  const [texto, setTexto] = useState('')
  const aprobar = useAprobarMinuta()
  const enviar = useMarcarEnviada()
  const confirmar = useRegistrarConfirmacion()
  const editarTexto = useEditarTexto()

  useEffect(() => {
    if (orden) setTexto(orden.texto_minuta)
  }, [orden?.id])

  const isLoading =
    aprobar.isPending ||
    enviar.isPending ||
    confirmar.isPending ||
    editarTexto.isPending

  async function handleGuardar() {
    if (!orden) return
    await editarTexto.mutateAsync({ ordenId: orden.id, texto })
  }

  async function handleAprobar() {
    if (!orden) return
    await aprobar.mutateAsync(orden.id)
    onClose()
  }

  async function handleEnviar() {
    if (!orden) return
    await enviar.mutateAsync(orden.id)
    onClose()
  }

  async function handleConfirmar() {
    if (!orden) return
    await confirmar.mutateAsync(orden.id)
    onClose()
  }

  function handleCopiar() {
    if (!orden) return
    navigator.clipboard.writeText(orden.texto_minuta)
  }

  const isBorrador = orden?.estado === 'BORRADOR'
  const textoModificado = texto !== orden?.texto_minuta

  return (
    <Sheet open={orden !== null} onOpenChange={(open) => { if (!open) onClose() }}>
      <SheetContent
        side="right"
        className="w-[600px] sm:max-w-[600px] p-0 flex flex-col overflow-hidden"
      >
        {orden && (
          <>
            <SheetHeader className="px-6 py-4 border-b border-slate-200 shrink-0">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <SheetTitle className="text-base font-semibold truncate">
                    {orden.cliente_nombre}
                  </SheetTitle>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Comitente: {orden.cuenta_comitente} · Cotapartista:{' '}
                    {orden.cuenta_cotapartista}
                  </p>
                </div>
                <Badge
                  variant="secondary"
                  className={cn('shrink-0 text-xs', ESTADO_BADGE[orden.estado])}
                >
                  {orden.estado}
                </Badge>
              </div>
            </SheetHeader>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {/* Texto de la Minuta */}
              <section className="space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-slate-700">Texto de la Minuta</h3>
                  <div className="flex items-center gap-2">
                    {orden.texto_editado && (
                      <span className="flex items-center gap-1 text-xs text-amber-600">
                        <PenLine className="h-3 w-3" />
                        Editado
                      </span>
                    )}
                    {!isBorrador && (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-7 gap-1.5 text-xs"
                        onClick={handleCopiar}
                      >
                        <Copy className="h-3.5 w-3.5" />
                        Copiar
                      </Button>
                    )}
                  </div>
                </div>
                {isBorrador ? (
                  <Textarea
                    value={texto}
                    onChange={(e) => setTexto(e.target.value)}
                    rows={14}
                    className="font-mono text-xs resize-none"
                  />
                ) : (
                  <pre className="text-xs font-mono bg-slate-50 border border-slate-200 rounded-md p-3 whitespace-pre-wrap break-words max-h-80 overflow-y-auto">
                    {orden.texto_minuta}
                  </pre>
                )}
              </section>

              {/* DJ section */}
              {orden.dj_aplicada && (
                <>
                  <Separator />
                  <Collapsible>
                    <CollapsibleTrigger className="flex items-center justify-between w-full text-sm font-medium text-slate-700 hover:text-slate-900 py-1 group">
                      <span>Declaración Jurada — {orden.dj_tipo ?? 'Incluida'}</span>
                      <ChevronDown className="h-4 w-4 text-slate-400 transition-transform group-data-[state=open]:rotate-180" />
                    </CollapsibleTrigger>
                    <CollapsibleContent className="pt-2">
                      <p className="text-xs text-slate-500">
                        La Declaración Jurada está incluida al final del texto de la Minuta.
                      </p>
                    </CollapsibleContent>
                  </Collapsible>
                </>
              )}

              {/* Acciones */}
              <Separator />
              <section className="space-y-3">
                <h3 className="text-sm font-medium text-slate-700">Acciones</h3>
                <div className="flex flex-wrap gap-2">
                  {orden.estado === 'BORRADOR' && (
                    <>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleGuardar}
                        disabled={isLoading || !textoModificado}
                      >
                        Guardar edición
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleAprobar}
                        disabled={isLoading}
                      >
                        Aprobar
                      </Button>
                    </>
                  )}
                  {orden.estado === 'APROBADO' && (
                    <Button size="sm" onClick={handleEnviar} disabled={isLoading}>
                      Marcar como Enviada
                    </Button>
                  )}
                  {(orden.estado === 'ENVIADO' || orden.estado === 'ALERTA') && (
                    <Button size="sm" onClick={handleConfirmar} disabled={isLoading}>
                      Registrar Confirmación
                    </Button>
                  )}
                  {orden.estado === 'CONFIRMADO' && (
                    <p className="text-xs text-slate-500 py-1">
                      Orden confirmada. Sin acciones disponibles.
                    </p>
                  )}
                </div>
              </section>

              {/* Audit Trail */}
              <Separator />
              <AuditTrailSection ordenId={orden.id} />
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/minutas/MinutaDrawer.tsx
git commit -m "feat(frontend): add MinutaDrawer with editing, actions, and audit trail"
```

---

## Task 15: ExcelUploadModal

**Files:**
- Create: `frontend/src/components/upload/ExcelUploadModal.tsx`

- [ ] **Step 1: Write ExcelUploadModal.tsx**

Create `frontend/src/components/upload/ExcelUploadModal.tsx`:

```tsx
import { useRef, useState } from 'react'
import { Upload } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog'
import { Button } from '../ui/button'
import { cn } from '../../lib/utils'
import { uploadExcel } from '../../services/upload'
import type { UploadResponse } from '../../types/domain'

type Step = 'select' | 'preview' | 'uploading' | 'done'

interface Props {
  open: boolean
  onClose: () => void
}

export default function ExcelUploadModal({ open, onClose }: Props) {
  const qc = useQueryClient()
  const inputRef = useRef<HTMLInputElement>(null)
  const [step, setStep] = useState<Step>('select')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<UploadResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  function reset() {
    setStep('select')
    setFile(null)
    setResult(null)
    setError(null)
  }

  function handleClose() {
    reset()
    onClose()
  }

  function selectFile(f: File) {
    if (!f.name.match(/\.(xlsx|xls)$/i)) {
      setError('Solo se aceptan archivos .xlsx o .xls')
      return
    }
    setFile(f)
    setError(null)
    setStep('preview')
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setIsDragOver(false)
    const dropped = e.dataTransfer.files[0]
    if (dropped) selectFile(dropped)
  }

  async function handleUpload() {
    if (!file) return
    setStep('uploading')
    try {
      const res = await uploadExcel(file)
      setResult(res)
      qc.invalidateQueries({ queryKey: ['minutas', 'BORRADOR'] })
      setStep('done')
    } catch {
      setError('Error al procesar el archivo. Verificá el formato e intentá de nuevo.')
      setStep('preview')
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) handleClose() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Subir Excel de Operaciones</DialogTitle>
        </DialogHeader>

        {step === 'select' && (
          <div className="space-y-4">
            <div
              className={cn(
                'border-2 border-dashed rounded-lg p-10 text-center cursor-pointer transition-colors',
                isDragOver
                  ? 'border-slate-400 bg-slate-50'
                  : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50/50'
              )}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true) }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleDrop}
              onClick={() => inputRef.current?.click()}
            >
              <Upload className="h-8 w-8 mx-auto text-slate-300 mb-3" />
              <p className="text-sm text-slate-600 font-medium">
                Arrastrá el archivo o hacé click para seleccionar
              </p>
              <p className="text-xs text-slate-400 mt-1">Solo .xlsx o .xls</p>
            </div>
            <input
              ref={inputRef}
              type="file"
              accept=".xlsx,.xls"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) selectFile(f)
                e.target.value = ''
              }}
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>
        )}

        {step === 'preview' && file && (
          <div className="space-y-4">
            <div className="bg-slate-50 rounded-md p-3 border border-slate-200">
              <p className="text-sm font-medium text-slate-800">{file.name}</p>
              <p className="text-xs text-slate-500 mt-0.5">
                {(file.size / 1024).toFixed(1)} KB
              </p>
            </div>
            <p className="text-sm text-slate-600">
              El archivo será procesado y se generarán las Minutas en estado Borrador.
            </p>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => { setFile(null); setStep('select') }}>
                Cambiar archivo
              </Button>
              <Button onClick={handleUpload}>Procesar</Button>
            </div>
          </div>
        )}

        {step === 'uploading' && (
          <div className="py-10 text-center space-y-3">
            <div className="h-8 w-8 mx-auto border-2 border-slate-200 border-t-slate-700 rounded-full animate-spin" />
            <p className="text-sm text-slate-600">Procesando archivo...</p>
          </div>
        )}

        {step === 'done' && result && (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-md p-4">
              <p className="text-sm font-semibold text-green-800">
                {result.ordenes_validas}{' '}
                {result.ordenes_validas === 1 ? 'Minuta generada' : 'Minutas generadas'} en
                Borradores
              </p>
              <p className="text-xs text-green-700 mt-0.5">
                Total procesadas: {result.total_ordenes} · Con errores:{' '}
                {result.ordenes_con_error}
              </p>
            </div>

            {result.errors.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-slate-700">Errores por fila:</p>
                <div className="max-h-36 overflow-y-auto space-y-1">
                  {result.errors.map((err) => (
                    <div
                      key={err.fila}
                      className="text-xs text-red-700 bg-red-50 rounded px-2 py-1 border border-red-100"
                    >
                      Fila {err.fila}: {err.mensaje}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button className="w-full" onClick={handleClose}>
              Cerrar
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/upload/ExcelUploadModal.tsx
git commit -m "feat(frontend): add ExcelUploadModal with 4-step flow"
```

---

## Task 16: DashboardPage

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: Write DashboardPage.tsx**

Replace `frontend/src/pages/DashboardPage.tsx`:

```tsx
import { useState } from 'react'
import { Skeleton } from '../components/ui/skeleton'
import MinutaCard from '../components/minutas/MinutaCard'
import MinutaDrawer from '../components/minutas/MinutaDrawer'
import { useMinutas } from '../hooks/useMinutas'
import type { EstadoMinuta, Orden } from '../types/domain'

const ESTADO_TITULO: Record<EstadoMinuta, string> = {
  BORRADOR: 'Borradores',
  APROBADO: 'Aprobados',
  ENVIADO: 'Enviados',
  CONFIRMADO: 'Confirmados',
  ALERTA: 'Alertas',
}

interface Props {
  estado: EstadoMinuta
}

export default function DashboardPage({ estado }: Props) {
  const { data, isLoading, isError } = useMinutas(estado)
  const [selectedOrden, setSelectedOrden] = useState<Orden | null>(null)

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div className="flex items-baseline gap-3">
        <h2 className="text-xl font-semibold text-slate-900">
          {ESTADO_TITULO[estado]}
        </h2>
        {data && (
          <span className="text-sm text-slate-400">
            {data.total} {data.total === 1 ? 'orden' : 'órdenes'}
          </span>
        )}
      </div>

      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      )}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">
            Error al cargar las órdenes. Verificá tu conexión e intentá de nuevo.
          </p>
        </div>
      )}

      {data && data.items.length === 0 && !isLoading && (
        <div className="text-center py-16">
          <p className="text-sm text-slate-400">No hay órdenes en estado {estado}.</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="space-y-3">
          {data.items.map((orden) => (
            <MinutaCard
              key={orden.id}
              orden={orden}
              onClick={() => setSelectedOrden(orden)}
            />
          ))}
        </div>
      )}

      <MinutaDrawer
        orden={selectedOrden}
        onClose={() => setSelectedOrden(null)}
      />
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(frontend): implement DashboardPage with MinutaCard list and drawer"
```

---

## Task 17: AuditPage

**Files:**
- Modify: `frontend/src/pages/AuditPage.tsx`

Note: The backend has per-order audit endpoints only (`GET /audit/{orden_id}` and `GET /audit/{orden_id}/export/excel`). There is no global audit trail API endpoint. This page implements the available per-order audit lookup. A global audit endpoint can be added to the backend later to expand this page.

- [ ] **Step 1: Write AuditPage.tsx**

Replace `frontend/src/pages/AuditPage.tsx`:

```tsx
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { Download, Search } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Skeleton } from '../components/ui/skeleton'
import { fetchAuditTrail, getAuditExcelUrl } from '../services/audit'
import type { AccionAudit } from '../types/domain'

const ACCION_LABEL: Record<AccionAudit, string> = {
  CREADA: 'Creada',
  EDITADA: 'Texto editado',
  APROBADA: 'Aprobada',
  ENVIADA: 'Marcada como enviada',
  CONFIRMADA: 'Confirmación registrada',
  ALERTA_GENERADA: 'Alerta generada',
}

interface FormValues {
  ordenId: string
}

export default function AuditPage() {
  const [activeOrdenId, setActiveOrdenId] = useState<string | null>(null)

  const { register, handleSubmit, formState: { isSubmitting } } = useForm<FormValues>()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['audit', activeOrdenId],
    queryFn: () => fetchAuditTrail(activeOrdenId!),
    enabled: activeOrdenId !== null,
  })

  function onSubmit({ ordenId }: FormValues) {
    setActiveOrdenId(ordenId.trim())
  }

  function handleExportExcel() {
    if (!activeOrdenId) return
    window.location.href = getAuditExcelUrl(activeOrdenId)
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Audit Trail</h2>
          <p className="text-sm text-slate-500 mt-0.5">
            Ingresá el ID de una orden para ver su historial de eventos.
          </p>
        </div>
        {activeOrdenId && data && data.length > 0 && (
          <Button variant="outline" size="sm" className="gap-2" onClick={handleExportExcel}>
            <Download className="h-3.5 w-3.5" />
            Exportar Excel
          </Button>
        )}
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="flex gap-2">
        <Input
          {...register('ordenId', { required: true })}
          placeholder="UUID de la orden"
          className="font-mono text-sm"
        />
        <Button type="submit" size="sm" className="gap-2 shrink-0" disabled={isSubmitting}>
          <Search className="h-3.5 w-3.5" />
          Buscar
        </Button>
      </form>

      {isLoading && <Skeleton className="h-48 w-full rounded-lg" />}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
          <p className="text-sm text-red-700">
            No se encontró la orden o no hay eventos registrados.
          </p>
        </div>
      )}

      {data && data.length === 0 && (
        <p className="text-sm text-slate-400 text-center py-8">
          Sin eventos para esta orden.
        </p>
      )}

      {data && data.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Acción
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  Fecha y hora
                </th>
                <th className="text-left px-4 py-3 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  IP
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((event) => (
                <tr key={event.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-medium text-slate-800">
                    {ACCION_LABEL[event.accion] ?? event.accion}
                  </td>
                  <td className="px-4 py-3 text-slate-600 tabular-nums">
                    {format(new Date(event.timestamp), 'dd/MM/yyyy HH:mm:ss', { locale: es })}
                  </td>
                  <td className="px-4 py-3 text-slate-400 font-mono text-xs">
                    {event.ip_origen ?? '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AuditPage.tsx
git commit -m "feat(frontend): add AuditPage with per-order audit lookup and Excel export"
```

---

## Task 18: Final build verification + dev server test

**Files:** None created — verification only.

- [ ] **Step 1: Full TypeScript build check**

```bash
cd frontend
npm run build
```

Expected: exits 0 with no TypeScript errors. Warnings about bundle size are OK.

- [ ] **Step 2: Start dev server**

```bash
npm run dev
```

Expected output (approx.):
```
  VITE v5.x.x  ready in Xms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
```

- [ ] **Step 3: Verify routes in browser**

Open `http://localhost:5173/` in a browser.

| Route | Expected result |
|-------|----------------|
| `/` | Redirects to `/login` (no token in memory) |
| `/login` | Shows login form with usuario + contraseña fields |
| `/login/2fa` | Shows TOTP form |
| `/dashboard/borradores` | Redirects to `/login` (auth guard blocks) |

These are smoke tests — you cannot fully test dashboard without a running backend and valid credentials.

- [ ] **Step 4: Check Sidebar badge queries don't fail noisily**

After login (if backend is running), navigate to `/dashboard/borradores`. Open browser DevTools → Network tab. Verify:
- `GET /dashboard/borradores` returns 200
- `GET /dashboard/aprobados`, `enviados`, `alertas` also called (Sidebar badge counts)
- No CORS errors (backend must have `http://localhost:5173` in its CORS origins)

- [ ] **Step 5: Final commit**

```bash
cd ..
git add frontend/
git commit -m "feat(frontend): complete frontend MVP scaffold — login, dashboard, drawer, upload, audit"
```

---

## Spec Coverage Checklist

| Spec requirement | Implemented in task |
|-----------------|---------------------|
| `/login` route | Task 10 |
| `/login/2fa` route | Task 11 |
| `/dashboard/{estado}` routes (5 tabs) | Task 8 + Task 16 |
| `/dashboard/audit` route | Task 8 + Task 17 |
| Auth guard for dashboard routes | Task 8 |
| Redirect `/` → `/dashboard/borradores` | Task 8 |
| Sidebar with badge counts | Task 9 |
| "Subir Excel" button in sidebar | Task 9 |
| Logout clears tokens + redirects | Task 9 |
| `MinutaCard` with all fields | Task 12 |
| ALERTA card with red border + elapsed time | Task 12 |
| DJ icon + edited icon on card | Task 12 |
| `MinutaDrawer` (600px, from right) | Task 14 |
| Editable textarea in BORRADOR only | Task 14 |
| Copy to clipboard in non-BORRADOR states | Task 14 |
| "Editado manualmente" badge | Task 14 |
| DJ collapsible section | Task 14 |
| Acciones por estado (all 5 states) | Task 14 |
| Audit trail collapsible in drawer | Task 13 + Task 14 |
| `ExcelUploadModal` — 4-step flow | Task 15 |
| Drag & drop + file selector | Task 15 |
| Preview with error list per row | Task 15 |
| Invalidate borradores query on upload | Task 15 |
| `AuditPage` with export | Task 17 |
| Access token in memory (never localStorage) | Task 4 + Task 5 |
| Refresh token flow on 401 | Task 4 |
| `date-fns` with `es` locale | Tasks 12, 13, 17 |
| TanStack Query cache invalidation on mutations | Task 7 |

## Notes for backend

- The `AuditPage` currently uses per-order audit lookup. To support a global audit trail with date filtering, add `GET /audit/` with optional `date_from`/`date_to` query params and `GET /audit/export/excel` (global) to the backend.
- The backend has no `POST /auth/logout` endpoint. The frontend clears tokens client-side only, which is sufficient for the MVP.
- Backend CORS must allow `http://localhost:5173` during development.
