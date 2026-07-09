# CLAUDE.md — Sistema de Cobro Automático por Mail

@CONTEXT.md

Guía de contexto para Claude Code. Leer antes de tocar cualquier archivo del proyecto.

---

## Qué es este proyecto

Sistema web para automatizar el envío de recordatorios de deuda a consorcios clientes de una empresa de mantenimiento de ascensores. El operario sube un Excel de deudores, el sistema lo cruza con un maestro de clientes, genera mails HTML personalizados y los envía automáticamente desde Yahoo o Gmail (proveedor configurable). Un watcher IMAP monitorea respuestas y un dashboard de cobranza muestra deuda, antigüedad y evolución por ciclo.

**Lee `CONTEXT.md` para el glosario del dominio antes de escribir cualquier código.**  
**Lee `docs/adr/` antes de tomar decisiones arquitectónicas.**  
**Lee `docs/PENDIENTES.md` para ver los gaps de implementación conocidos.**  
**Specs y planes ya ejecutados quedan como histórico en `docs/archive/`.**

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + FastAPI + SQLAlchemy 2.0 + Pydantic v2 |
| Frontend | React 18 + TypeScript + Vite + shadcn/ui + TanStack Query |
| Base de datos | SQLite en dev · PostgreSQL (Neon) en producción |
| Auth | JWT + bcrypt (sin 2FA) |
| Credenciales de email | Cifradas en DB con Fernet (`ENCRYPTION_KEY`) |
| Email envío | Yahoo/Gmail SMTP (`:587`, STARTTLS) — proveedor configurable |
| Email lectura | Yahoo/Gmail IMAP (`:993`, SSL) |
| Excel | openpyxl / pandas |
| Real-time | Server-Sent Events (SSE) |
| Deploy | Backend en Render (Docker, gunicorn+uvicorn) · Frontend en Vercel |

---

## Estructura del proyecto

```
Mails-nico/
├── CLAUDE.md · CONTEXT.md
├── docs/
│   ├── adr/                       ← decisiones arquitectónicas 0001–0007
│   ├── PENDIENTES.md              ← gaps conocidos vs. lo esperado
│   └── archive/{plans,specs}/     ← planes y specs ya ejecutados (histórico)
├── backend/
│   ├── app/
│   │   ├── core/                  ← config, database, security, dependencies, logging, limiter, validators, email_providers
│   │   ├── models/                ← User, ClienteMaestro, Plantilla, Ciclo, Envio, ConfiguracionSistema
│   │   ├── schemas/               ← auth, ciclo, maestro, envio, configuracion, dashboard, seguimiento (Pydantic)
│   │   ├── routers/               ← auth, ciclos, maestro, plantilla, configuracion, dashboard, seguimiento, unsubscribe
│   │   └── services/              ← auth, ciclo_service, config_service, dashboard_service, maestro_service,
│   │                                 excel_parser, excel_joiner, email_generator, smtp_sender,
│   │                                 imap_watcher, reply_classifier, db_config
│   ├── scripts/                   ← seed_user, limpiar_db_produccion, dev_setup
│   ├── tests/                     ← pytest (≈190 tests)
│   ├── alembic/versions/          ← 0001_initial … 0006_envio_saldado_en
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/                 ← Login, Dashboard, NuevoEnvio, Seguimiento, Maestro, Plantilla, Configuracion, ClientePerfil
        ├── components/            ← layout/, envios/, upload/, profile/, dashboard/, maestro/, ui/ (shadcn, no editar a mano)
        ├── services/              ← api, auth, ciclos, maestro, envios, plantilla, configuracion, dashboard, seguimiento
        ├── hooks/                 ← useAuth, useCiclo, useEnvios
        └── types/                 ← domain.ts (única fuente de verdad de tipos)
```

---

## Módulos del backend

| Módulo | Responsabilidad |
|--------|----------------|
| `auth` | Login, JWT, bcrypt, log de accesos, rate limiting |
| `config_service` | Credenciales de email (Fernet), proveedor activo, `probar_conexion` (login SMTP+IMAP real) |
| `excel_parser` | Parsea Excel de deudores y Excel maestro |
| `excel_joiner` | Cruza deudores con ClienteMaestro; detecta sin mail y filtrados |
| `email_generator` | Genera HTML del mail con Jinja2 + premailer (estilos inline) |
| `smtp_sender` | Envío con cola y rate limiting: 5 mails cada 30 s |
| `imap_watcher` | Polling IMAP cada 10 min (background); advisory lock para que 1 solo worker pollee |
| `reply_classifier` | Adjunto → PAGO, texto → CONTESTADO, mailer-daemon → REBOTADO |
| `dashboard_service` | KPIs (deuda, deudores, +90d), morosos por antigüedad, evolución por ciclo |
| `db_config` | CRUD de Plantilla singleton |
| `ciclos` router | Preview (en memoria), confirmar-envío (SSE), reenvío |
| `maestro` router | Upload Excel maestro (merge), CRUD clientes |
| `seguimiento` router | Estados por ciclo, refresco IMAP manual, respuestas tardías |
| `unsubscribe` router | `GET /unsubscribe/{token}` → setea `prefiere_no_recibir_email` |

---

## Flujo principal

1. Operario sube Excel deudores → **preview en memoria** (nada en DB)
2. Confirma → Ciclo + Envios creados en DB → `smtp_sender` envía con rate limiting
3. SSE actualiza barra de progreso en tiempo real
4. `imap_watcher` (background, cada 10 min) detecta respuestas → `reply_classifier` actualiza estado

## Estados de un Envio

```
NO_CONTESTADO → CONTESTADO  (reply sin adjunto)
NO_CONTESTADO → PAGO        (reply con adjunto)
NO_CONTESTADO → REBOTADO    (mailer-daemon)
CONTESTADO    → PAGO        (override manual del operario)
```

`FILTRADO` y `SIN_EMAIL`: se crean en DB al confirmar pero nunca se envía mail.  
`motivo_filtrado`: `MONTO_MINIMO` | `DADO_DE_BAJA`

---

## Reglas de negocio críticas

1. **Preview no escribe en DB** — el Excel puede re-subirse N veces sin efectos secundarios
2. **Rate limiting SMTP es innegociable** — 5 mails cada 30 segundos, sin excepciones
3. **Merge del maestro preserva `prefiere_no_recibir_email`** — nunca se sobreescribe
4. **`DADO_DE_BAJA` filtra en todos los ciclos futuros** — automáticamente al cruzar con maestro
5. **Envios históricos no se borran** — base para `ciclo_numero`, antigüedad de deuda y evolución
6. **PAGO es inferido, no confirmado** — se deriva de un adjunto en la respuesta; la UI lo aclara

---

## Estado del proyecto

En producción, validado con volumen real. El Excel usa `nro cliente` (8 dígitos con ceros a la izquierda), `nombre`, `localidad`, `monto`. No hay pendientes bloqueantes de datos; ver `docs/PENDIENTES.md` para mejoras conocidas.

**Entornos:** `master` → prod (Vercel + Render Starter + Neon). `desarrollo` → preview (Vercel + Render free + branch Neon dev). Render free bloquea SMTP, así que dev no envía/lee mail real.

---

## Cómo correr en desarrollo

```bash
# Backend
cd backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python scripts/seed_user.py         # crea usuario operario inicial
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install && npm run dev
```

Variables de entorno (`backend/.env`, ver `.env.example`):
```
DATABASE_URL=sqlite:///./dev.db        # o postgresql://... en prod
SECRET_KEY=<mínimo 32 chars>
ENCRYPTION_KEY=<Fernet key>            # cifra credenciales de email en DB
YAHOO_EMAIL / YAHOO_APP_PASSWORD       # fallback; el operario las carga desde Configuración
GMAIL_EMAIL / GMAIL_APP_PASSWORD       # opcional
ALLOWED_ORIGINS=<origins CORS, coma-separados>
BACKEND_PUBLIC_URL=<URL pública, para el link de unsubscribe>
```
