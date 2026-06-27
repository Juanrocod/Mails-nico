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
├── models/     ← User, Plantilla, ConfigDJ, ConfigFiltros, InviteToken
├── schemas/    ← auth.py, session.py  (tipos Pydantic request/response)
├── routers/    ← auth.py, uploads.py, session.py
└── services/   ← excel_parser, minuta_generator, dj_engine, filtros_engine, db_config, session_store, auth
```

## Patrón de routers

```python
router = APIRouter(prefix="/session", tags=["session"])

@router.get("/minutas", response_model=SessionMinutasResponse)
def get_minutas(
    estado: str = "BORRADOR",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ...
```

- Lógica de negocio va en `services/`, NO en routers
- Dependencias: `Depends(get_db)` y `Depends(get_current_user)` en endpoints protegidos
- Errores: `raise HTTPException(status_code=4xx, detail="mensaje")` en routers

## session_store — RAM, keyed por user_id

```python
from app.services import session_store

user_id = str(current_user.id)   # siempre str del UUID
minutas = session_store.get_minutas(user_id, "BORRADOR")
session_store.clear_borradores_y_filtradas(user_id)  # al subir nuevo Excel
```

- TTL: 12 horas
- Estados válidos de Minuta: `"BORRADOR"`, `"ENVIADO"`, `"FILTRADA"`
- Al subir Excel: limpiar BORRADOR + FILTRADA, conservar ENVIADO

## db_config — persistencia de configuración

- `Plantilla` y `ConfigFiltros`: singleton (id=1), usar `db.get(Model, 1)`
- `ConfigDJ`: multi-row con auto-increment, CRUD completo

```python
from app.services import db_config

plantilla = db_config.load_plantilla(db)           # str
config_djs = db_config.load_all_config_dj(db)      # list[ConfigDJData]
config_filtros = db_config.load_config_filtros(db)  # ConfigFiltrosData
```

## Schemas — naming

- `*Schema`: clases Pydantic para request/response de API
- `*Data`: dataclasses internas de servicios (`ConfigDJData`, `ConfigFiltrosData`, `OrdenParsed`)

## Migraciones Alembic

- Numeración secuencial: `0001_`, `0002_`, ..., `0006_` (current head)
- Usar `batch_alter_table` para todas las modificaciones (compatibilidad SQLite/PostgreSQL)

```python
def upgrade() -> None:
    with op.batch_alter_table("config_dj") as batch_op:
        batch_op.add_column(sa.Column("nombre", sa.String(200), nullable=False, server_default="DJ General"))
```

## Tests (pytest)

Fixtures en `conftest.py`: `client`, `auth_headers`, `db`.

```python
def test_get_config_dj_list_empty(client, auth_headers):
    r = client.get("/config/dj", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []
```

Correr tests: `cd backend && venv\Scripts\python -m pytest -v`
