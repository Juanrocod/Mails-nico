# CLAUDE.md — Sistema de Gestión de Órdenes Bursátiles

Guía de contexto para Claude Code. Leer antes de tocar cualquier archivo del proyecto.

---

## Qué es este proyecto

Sistema web para automatizar la generación y gestión de Minutas bursátiles para un broker regulado por la CNV (Argentina). Middle Office sube un Excel exportado de la plataforma bursátil, el sistema genera los borradores de mail (Minutas) por cliente, Middle Office los revisa/edita/aprueba en un Dashboard y los envía manualmente. Toda acción queda registrada en un Audit Trail exportable.

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
├── CONTEXT.md                         ← glosario del dominio
├── docs/
│   ├── PRD.md                         ← spec completa del MVP
│   ├── pasos-automatizacion-posterior.md  ← roadmap Fase 2
│   └── adr/                           ← decisiones arquitectónicas
│       ├── 0001-entrada-via-excel.md
│       ├── 0002-envio-manual-fase1.md
│       ├── 0003-stack-fastapi-react.md
│       └── 0004-autenticacion-2fa.md
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                      ← config, seguridad, DB session
│   │   ├── models/                    ← modelos SQLAlchemy
│   │   ├── schemas/                   ← schemas Pydantic (request/response)
│   │   ├── routers/                   ← endpoints FastAPI por módulo
│   │   └── services/                  ← lógica de negocio
│   │       ├── excel_parser.py
│   │       ├── minuta_generator.py
│   │       ├── dj_engine.py
│   │       └── audit.py
│   ├── tests/
│   ├── requirements.txt
│   └── alembic/                       ← migraciones de DB
└── frontend/
    ├── src/
    │   ├── pages/                     ← Login, Dashboard
    │   ├── components/                ← MinutaCard, TabPanel, AuditLog, etc.
    │   ├── services/                  ← llamadas a la API
    │   └── types/                     ← tipos TypeScript del dominio
    ├── package.json
    └── vite.config.ts
```

---

## Módulos del backend

| Módulo | Archivo | Responsabilidad |
|--------|---------|----------------|
| auth | `routers/auth.py` + `services/auth.py` | Login, 2FA, JWT, sesiones, log de accesos |
| excel_parser | `services/excel_parser.py` | Leer y validar Excel, mapear columnas a Orden |
| minuta_generator | `services/minuta_generator.py` | Generar texto plano estructurado de la Minuta |
| dj_engine | `services/dj_engine.py` | Evaluar reglas de DJ y seleccionar template |
| orders | `routers/orders.py` + `services/orders.py` | CRUD de Órdenes, máquina de estados |
| audit | `services/audit.py` | Registro inmutable de AuditEvents |
| dashboard | `routers/dashboard.py` | Endpoints por solapa (Borradores, Aprobados, etc.) |

---

## Máquina de estados de la Minuta

```
BORRADOR → APROBADO → ENVIADO → CONFIRMADO
                                     ↑
                                  ALERTA
```

- Transiciones **solo hacia adelante**. Una vez aprobada, no vuelve a BORRADOR.
- Middle Office puede editar el texto en estado BORRADOR antes de aprobar.
- CONFIRMADO y ALERTA son estados terminales en Fase 1.

---

## Reglas de negocio críticas

1. **Cifrado obligatorio** — `cliente_email`, `cuenta_comitente`, `cuenta_cotapartista` siempre cifrados en DB.
2. **Audit Trail inmutable** — los AuditEvents nunca se modifican ni eliminan. Solo INSERT.
3. **2FA obligatorio** — no hay camino de login sin segundo factor.
4. **Texto editado registrado** — si Middle Office modifica el texto de la Minuta, `texto_editado = true` se persiste antes de aprobar.
5. **Parser tolerante a errores por fila** — si una fila del Excel falla, se reporta el error de esa fila sin bloquear las demás.
6. **DJ por configuración** — los templates de DJ están en DB, no hardcodeados. El `dj_engine` los evalúa en runtime.

---

## Convenciones de código

- Usar los términos exactos del glosario en `CONTEXT.md` para nombres de clases, variables y endpoints. No inventar sinónimos.
- Los endpoints del Dashboard siguen el patrón `/dashboard/{estado}` donde estado es uno de: `borradores`, `aprobados`, `enviados`, `confirmados`, `alertas`.
- Los eventos de Audit Trail se generan desde los servicios, nunca desde los routers.
- No hay soft-delete. Las Órdenes no se eliminan — solo cambian de estado.

---

## Pendientes bloqueantes

Estos ítems están pendientes de información del broker y **no deben implementarse** hasta tenerla:

- [ ] Estructura exacta de columnas del Excel — el `excel_parser` debe esperar el archivo modelo
- [ ] Templates y reglas de Declaración Jurada — el `dj_engine` puede buildarse pero sin reglas cargadas
- [ ] Infraestructura Azure — desarrollo local usa PostgreSQL local, no Azure

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
