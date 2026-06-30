# CLAUDE.md — Sistema de Cobro Automático por Mail

@CONTEXT.md

Guía de contexto para Claude Code. Leer antes de tocar cualquier archivo del proyecto.

---

## Qué es este proyecto

Sistema web para automatizar el envío de recordatorios de deuda a consorcios clientes de una empresa de mantenimiento de ascensores. El operario sube un Excel de deudores, el sistema lo cruza con un maestro de clientes, genera mails HTML personalizados y los envía automáticamente desde Yahoo Mail. Un watcher IMAP monitorea respuestas y actualiza el dashboard.

**Lee `CONTEXT.md` para el glosario del dominio antes de escribir cualquier código.**  
**Lee `docs/superpowers/specs/2026-06-30-mails-nico-design.md` para el spec completo.**  
**Lee `docs/adr/` antes de tomar decisiones arquitectónicas.**

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | React 18 + TypeScript |
| Base de datos | PostgreSQL (Neon en producción) |
| Auth | JWT + bcrypt (sin 2FA) |
| Email envío | Yahoo SMTP (`smtp.mail.yahoo.com:587`) |
| Email lectura | Yahoo IMAP (`imap.mail.yahoo.com:993`) |
| Excel | openpyxl / pandas |
| Real-time | Server-Sent Events (SSE) |

---

## Estructura del proyecto

```
Mails-nico/
├── CLAUDE.md
├── CONTEXT.md
├── docs/
│   ├── adr/                           ← decisiones arquitectónicas 0001–0007
│   └── superpowers/specs/             ← spec de diseño aprobado
├── backend/
│   ├── app/
│   │   ├── core/                      ← config, database, security, dependencies, logging, limiter
│   │   ├── models/                    ← User, ClienteMaestro, Plantilla, Ciclo, Envio
│   │   ├── schemas/                   ← auth, ciclo, maestro, envio (Pydantic)
│   │   ├── routers/                   ← auth, ciclos, maestro, plantilla
│   │   └── services/
│   │       ├── auth.py
│   │       ├── excel_parser.py
│   │       ├── excel_joiner.py
│   │       ├── email_generator.py
│   │       ├── smtp_sender.py
│   │       ├── imap_watcher.py
│   │       ├── reply_classifier.py
│   │       └── db_config.py
│   ├── tests/
│   ├── alembic/                       ← migración inicial única (0001_initial.py)
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/                     ← Login, NuevoEnvio, Seguimiento, Maestro, Plantilla, Configuracion
        ├── components/layout/         ← AppLayout, Sidebar, AuthGuard, ErrorBoundary
        ├── components/envios/         ← EnvioCard, EnvioDrawer
        ├── components/upload/         ← ExcelUploadModal, ProgresoEnvio
        ├── components/profile/        ← ChangePasswordModal
        ├── components/ui/             ← shadcn/ui (no editar a mano)
        ├── services/                  ← api, auth, ciclos, maestro, envios, plantilla
        ├── hooks/                     ← useAuth, useCiclo, useEnvios
        └── types/                     ← domain.ts
```

---

## Módulos del backend

| Módulo | Responsabilidad |
|--------|----------------|
| `auth` | Login, JWT, bcrypt, log de accesos, rate limiting |
| `excel_parser` | Parsea Excel de deudores y Excel maestro |
| `excel_joiner` | Cruza deudores con ClienteMaestro; detecta sin mail y filtrados |
| `email_generator` | Genera HTML del mail con Jinja2 + premailer (estilos inline) |
| `smtp_sender` | Envío con cola y rate limiting: 5 mails cada 30 segundos |
| `imap_watcher` | Polling IMAP cada 10 min; detecta respuestas y rebotes (background task) |
| `reply_classifier` | Adjunto → PAGO, texto → CONTESTADO, mailer-daemon → REBOTADO |
| `db_config` | CRUD de Plantilla singleton |
| `ciclos` router | Preview (en memoria), confirmar-envio (SSE), stub Fase 3 |
| `maestro` router | Upload Excel maestro (merge), GET clientes |

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
5. **Envios históricos no se borran** — base para `ciclo_numero` (Fase 2)

---

## Pendientes bloqueantes

- [ ] Columnas exactas y clave de unión del Excel de deudores
- [ ] Columnas exactas y clave de unión del Excel maestro
- [ ] App password de Yahoo del cliente

---

## Cómo correr en desarrollo

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Variables de entorno (`backend/.env`):
```
DATABASE_URL=postgresql://user:pass@localhost:5432/mails_nico
SECRET_KEY=<mínimo 32 chars>
YAHOO_EMAIL=<email del cliente>
YAHOO_APP_PASSWORD=<app password de Yahoo>
```
