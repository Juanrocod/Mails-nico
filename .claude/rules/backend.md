---
paths:
  - "backend/**/*.py"
  - "backend/alembic/**"
---

## Stack

- Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, pytest
- SQLite en dev (`dev.db`), PostgreSQL en producción
- Gunicorn + UvicornWorker en producción

## Estructura de módulos

```
app/
├── core/       ← config.py, database.py, security.py, dependencies.py, logging_config.py, limiter.py
├── models/     ← User, ClienteMaestro, Plantilla, Ciclo, Envio
├── schemas/    ← auth.py, ciclo.py, maestro.py, envio.py  (Pydantic request/response)
├── routers/    ← auth.py, ciclos.py, maestro.py, plantilla.py
└── services/
    ├── auth.py
    ├── excel_parser.py       ← parsea Excel deudores y maestro; retorna dataclasses
    ├── excel_joiner.py       ← cruza deudores con ClienteMaestro; retorna PreviewData
    ├── email_generator.py    ← genera HTML del mail con Jinja2 + premailer (CSS inline)
    ├── smtp_sender.py        ← envío con cola asyncio y rate limiting (5 mails / 30s)
    ├── imap_watcher.py       ← polling IMAP cada 10 min; background task asyncio
    ├── reply_classifier.py   ← clasifica respuestas detectadas por imap_watcher
    └── db_config.py          ← CRUD de Plantilla singleton
```

## Patrón de routers

```python
router = APIRouter(prefix="/ciclos", tags=["ciclos"])

@router.post("/preview", response_model=PreviewResponse)
def preview_ciclo(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ...
```

- Lógica de negocio va en `services/`, NO en routers
- Dependencias: `Depends(get_db)` y `Depends(get_current_user)` en endpoints protegidos
- Errores: `raise HTTPException(status_code=4xx, detail="mensaje")` en routers

## Enums de dominio

```python
class EstadoEnvio(str, Enum):
    NO_CONTESTADO = "NO_CONTESTADO"
    CONTESTADO    = "CONTESTADO"
    PAGO          = "PAGO"
    REBOTADO      = "REBOTADO"
    SIN_EMAIL     = "SIN_EMAIL"
    FILTRADO      = "FILTRADO"

class MotivoFiltrado(str, Enum):
    MONTO_MINIMO = "MONTO_MINIMO"
    DADO_DE_BAJA = "DADO_DE_BAJA"
```

## smtp_sender — rate limiting

```python
from app.services import smtp_sender

# Encola y envía con delay (5 mails cada 30s); callback SSE por cada envío exitoso
await smtp_sender.enviar_ciclo(envios, on_progress=sse_callback)
```

- Rate limiting es **innegociable** — nunca saltear
- `on_progress` recibe el Envio ya enviado para que el router emita el evento SSE

## imap_watcher — background task

```python
# En app/main.py
@app.on_event("startup")
async def startup():
    asyncio.create_task(imap_watcher.run_forever())
```

- Usa `message_id` de Envios activos (últimos 30 días) para matching con `In-Reply-To`
- Llama a `reply_classifier.classify(msg)` → actualiza `Envio.estado` en DB

## reply_classifier — lógica de clasificación

| Condición | Estado resultante |
|-----------|-----------------|
| `From` contiene `mailer-daemon` o `postmaster` | `REBOTADO` |
| Tiene adjunto (image/* o application/pdf) | `PAGO` |
| Solo texto | `CONTESTADO` |

## db_config — Plantilla singleton

```python
from app.services import db_config

plantilla = db_config.load_plantilla(db)  # PlantillaData
db_config.save_plantilla(db, data)
```

`Plantilla` singleton: `id=1`, usar `db.get(Plantilla, 1)`.

## Schemas — naming

- `*Schema`: Pydantic para request/response de API
- `*Data`: dataclasses internas de servicios (`EnvioParsed`, `PreviewData`, `PlantillaData`)

## Migraciones Alembic

- Una única migración inicial limpia: `0001_initial.py`
- Usar `batch_alter_table` para todas las modificaciones (compatibilidad SQLite/PostgreSQL)

```python
def upgrade() -> None:
    with op.batch_alter_table("envio") as batch_op:
        batch_op.add_column(sa.Column("reply_snippet", sa.Text(), nullable=True))
```

## Tests (pytest)

Fixtures en `conftest.py`: `client`, `auth_headers`, `db`.

```python
def test_preview_ciclo(client, auth_headers, excel_deudores_fixture):
    r = client.post("/ciclos/preview", files={"file": excel_deudores_fixture}, headers=auth_headers)
    assert r.status_code == 200
    assert "para_enviar" in r.json()
    assert "sin_email" in r.json()
```

Correr tests: `cd backend && venv\Scripts\python -m pytest -v`
