# CLAUDE.md — Sistema de Gestión de Órdenes Bursátiles

@CONTEXT.md

Guía de contexto para Claude Code. Leer antes de tocar cualquier archivo del proyecto.

---

## Qué es este proyecto

Sistema web para automatizar la generación y gestión de Minutas bursátiles para un broker regulado por la CNV (Argentina). Middle Office sube un Excel exportado de la plataforma bursátil, el sistema genera los borradores de mail (Minutas) por cliente, Middle Office los revisa/edita en un Dashboard y los envía manualmente.

**Rama `master` = MVP sin persistencia de órdenes** (ver ADR-0006). La DB solo guarda usuarios/auth.  
**Rama `con-db(f2)` = Fase 2** con persistencia completa, audit trail y estados extendidos. No tocar hasta que el MVP esté validado.

**Lee `CONTEXT.md` para el glosario canónico del dominio antes de escribir cualquier código.**  
**Lee `docs/PRD.md` para el alcance completo, decisiones de implementación y user stories.**  
**Lee `docs/adr/` antes de tomar decisiones arquitectónicas — puede que ya estén resueltas.**

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | React 18 + TypeScript |
| Base de datos | PostgreSQL |
| Auth | JWT + TOTP (2FA) + bcrypt |
| Excel | openpyxl / pandas |
| PDF export | WeasyPrint o ReportLab |
| Hosting (futuro) | Azure App Service + Azure Static Web Apps + Azure DB for PostgreSQL |

---

## Estructura del proyecto

```
Gestion-Mails/
├── CLAUDE.md                          ← este archivo
├── CONTEXT.md                         ← glosario del dominio (importado con @)
├── CLAUDE.local.md                    ← preferencias locales (en .gitignore)
├── docs/
│   ├── PRD.md
│   ├── pasos-automatizacion-posterior.md  ← roadmap Fase 2
│   └── adr/                           ← 0001–0009 decisiones arquitectónicas
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                      ← config, seguridad, DB session, logging
│   │   ├── models/                    ← User, Plantilla, ConfigDJ, ConfigFiltros, InviteToken
│   │   ├── schemas/                   ← schemas Pydantic (auth.py, session.py)
│   │   ├── routers/                   ← auth.py, uploads.py, session.py
│   │   └── services/
│   │       ├── excel_parser.py
│   │       ├── minuta_generator.py
│   │       ├── dj_engine.py
│   │       ├── filtros_engine.py
│   │       ├── db_config.py
│   │       ├── session_store.py
│   │       └── auth.py
│   ├── tests/
│   ├── requirements.txt
│   └── alembic/                       ← migraciones 0001–0006
└── frontend/
    ├── src/
    │   ├── pages/                     ← Login, TwoFactor, Register, ResetPassword,
    │   │                                Dashboard, Filtrada, Plantilla, ConfigDJ, FiltrosMinutas
    │   ├── components/layout/         ← AppLayout, Sidebar, AuthGuard, ErrorBoundary
    │   ├── components/minutas/        ← MinutaCard, MinutaDrawer
    │   ├── components/upload/         ← ExcelUploadModal
    │   ├── components/profile/        ← ChangePasswordModal, RegenerateTOTPModal
    │   ├── services/                  ← api, auth, minutas, upload, plantilla, configDJ, configFiltros
    │   ├── hooks/                     ← useAuth, useSession
    │   └── types/                     ← domain.ts
    ├── package.json
    └── vite.config.ts
```

---

## Módulos del backend (MVP)

| Módulo | Archivo | Responsabilidad |
|--------|---------|----------------|
| auth | `routers/auth.py` + `services/auth.py` | Login, 2FA, JWT, sesiones, log de accesos |
| excel_parser | `services/excel_parser.py` | Leer y validar Excel, mapear columnas a OrdenParsed |
| minuta_generator | `services/minuta_generator.py` | Generar texto plano de la Minuta con plantilla configurable |
| dj_engine | `services/dj_engine.py` | Evaluar config DJ y aplicar texto de alerta (multi-DJ) |
| filtros_engine | `services/filtros_engine.py` | Evaluar si una Orden debe marcarse FILTRADA según ConfigFiltros |
| db_config | `services/db_config.py` | CRUD para Plantilla, ConfigDJ (multi-row) y ConfigFiltros en DB |
| session_store | `services/session_store.py` | Store en RAM: minutas por user_id, TTL 12h |
| uploads | `routers/uploads.py` | POST /uploads/excel — parsea, filtra, evalúa DJs, retorna minutas |
| session | `routers/session.py` | GET/PATCH minutas, plantilla, config-dj (CRUD), filtros-minutas |

> Los módulos `orders`, `audit` y `dashboard` (con persistencia en DB) viven en `con-db(f2)`, no en master.

---

## Máquina de estados de la Minuta (MVP)

```
BORRADOR → ENVIADO
BORRADOR → FILTRADA  (automático al hacer upload, si la Orden matchea ConfigFiltros)
FILTRADA → BORRADOR  (manual — Middle Office hace clic "Agregar" en la solapa Filtradas)
```

- Middle Office edita el texto en BORRADOR, copia con el botón "Copiar contenido" y luego presiona "Enviado".
- BORRADOR → ENVIADO es irreversible.
- FILTRADA → BORRADOR mueve la Minuta a la solapa de Borradores para su revisión.
- No hay APROBADO, CONFIRMADO ni ALERTA en el MVP.

> La máquina de estados completa está documentada en `con-db(f2)`.

---

## Reglas de negocio críticas (MVP)

1. **2FA obligatorio** — no hay camino de login sin segundo factor.
2. **Parser tolerante a errores por fila** — si una fila del Excel falla, se reporta el error de esa fila sin bloquear las demás.
3. **DJ por configuración en RAM** — la config de DJ (activo + texto de alerta) se guarda en el session store, no en DB.
4. **Sin cifrado de órdenes en MVP** — los datos de órdenes nunca llegan a la DB, por lo que el cifrado de `cliente_email` / `cuenta_comitente` / `cuenta_cotapartista` aplica solo en Fase 2.
5. **Sin audit trail en MVP** — no hay qué auditar si nada persiste.
6. **Texto editado en RAM** — `texto_editado = true` se mantiene en el objeto Minuta en memoria.

---

## Convenciones de código

- Usar los términos exactos del glosario en `CONTEXT.md` para nombres de clases, variables y endpoints. No inventar sinónimos.
- Los endpoints de sesión siguen el patrón `/session/minutas` y `/session/minutas/{id}/enviado`.
- Las tabs del Dashboard MVP son: `borradores`, `enviados`, `filtradas`, `plantilla`, `config-dj`, `filtros-minutas`.
- No hay soft-delete. Las Minutas solo cambian de estado en RAM (BORRADOR → ENVIADO).

---

## Pendientes bloqueantes

Estos ítems están pendientes de información del broker y **no deben implementarse** hasta tenerla:

- [ ] Templates de texto legal para las Declaraciones Juradas — el motor DJ (`dj_engine`) y la UI de configuración están implementados; falta que el broker provea el texto legal real
- [ ] Infraestructura Azure — desarrollo local usa PostgreSQL / SQLite, no Azure

---

## Fase 2 — No implementar aún

Todo lo listado en `docs/pasos-automatizacion-posterior.md` está **fuera del alcance del MVP**. No agregar integración con Microsoft Graph API, monitoreo de mails, ni automatización de Confirmaciones hasta que Fase 1 esté validada en producción.

---

## Cómo correr el proyecto en desarrollo

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

Variables de entorno requeridas (crear `backend/.env`):
```
DATABASE_URL=postgresql://user:pass@localhost:5432/gestion_mails
SECRET_KEY=<clave JWT — mínimo 32 chars>
TOTP_ISSUER=GestionMails
```
