# Mails-nico Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transformar la base del proyecto Mails-finanzas en un sistema de cobro automático por mail para una empresa de mantenimiento de ascensores.

**Architecture:** Backend FastAPI con modelos Ciclo/Envio, servicios de parseo Excel, envío SMTP con rate limiting y watcher IMAP en background. Frontend React con flujo preview→confirmar y dashboard de seguimiento con 4 solapas.

**Tech Stack:** Python 3.12 + FastAPI, React 18 + TypeScript, PostgreSQL (Neon), Yahoo SMTP/IMAP, Jinja2 + premailer, openpyxl, shadcn/ui, TanStack Query v5, SSE.

## Global Constraints

- Rate limiting SMTP: exactamente 5 mails cada 30 segundos, sin excepciones
- Preview nunca escribe en DB; solo la confirmación crea Ciclo + Envios
- `prefiere_no_recibir_email` nunca se sobreescribe con uploads posteriores
- Una única migración Alembic limpia (`0001_initial.py`); sin historial broker
- Sin 2FA; auth = usuario + contraseña + JWT (8h), bcrypt cost 12, rate limit login 5/min/IP
- Tests corren con SQLite en memoria; `pytest` desde `backend/`
- Commits frecuentes; cada task termina con commit

---

### Task 1: Limpieza de archivos broker

**Files:**
- Delete: `backend/app/models/config_dj.py`
- Delete: `backend/app/models/config_filtros.py`
- Delete: `backend/app/models/invite_token.py`
- Delete: `backend/app/services/dj_engine.py`
- Delete: `backend/app/services/filtros_engine.py`
- Delete: `backend/app/services/session_store.py`
- Delete: `backend/app/services/minuta_generator.py`
- Delete: `backend/app/routers/session.py`
- Delete: `backend/app/routers/uploads.py`
- Delete: `backend/app/schemas/session.py`
- Delete: `backend/alembic/versions/0002_add_plantilla_config_dj.py`
- Delete: `backend/alembic/versions/0003_add_invite_tokens.py`
- Delete: `backend/alembic/versions/0004_security_hardening.py`
- Delete: `backend/alembic/versions/0005_excel_real.py`
- Delete: `backend/alembic/versions/0006_multi_dj.py`
- Delete: `backend/alembic/versions/ed7df405935c_initial.py`
- Delete: `backend/tests/test_dj_engine.py`
- Delete: `backend/tests/test_filtros_engine.py`
- Delete: `backend/tests/test_minuta_generator.py`
- Delete: `backend/tests/test_session_router.py`
- Delete: `backend/tests/test_session_store.py`
- Delete: `backend/tests/test_uploads.py`
- Delete: `backend/tests/test_register.py`
- Delete: `backend/create_invite.py`
- Delete: `frontend/src/components/minutas/MinutaCard.tsx`
- Delete: `frontend/src/components/minutas/MinutaDrawer.tsx`
- Delete: `frontend/src/components/profile/RegenerateTOTPModal.tsx`
- Delete: `frontend/src/hooks/useMinutas.ts`
- Delete: `frontend/src/hooks/useSession.ts`
- Delete: `frontend/src/services/configDJ.ts`
- Delete: `frontend/src/services/configFiltros.ts`
- Delete: `frontend/src/services/minutas.ts`
- Delete: `frontend/src/services/upload.ts`
- Delete: `frontend/src/pages/ConfigDJPage.tsx`
- Delete: `frontend/src/pages/DashboardPage.tsx`
- Delete: `frontend/src/pages/FiltradaPage.tsx`
- Delete: `frontend/src/pages/FiltrosMinutasPage.tsx`
- Delete: `frontend/src/pages/RegisterPage.tsx`
- Delete: `frontend/src/pages/ResetPasswordPage.tsx`
- Delete: `frontend/src/pages/TwoFactorPage.tsx`
- Modify: `backend/requirements.txt`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: proyecto limpio, sin referencias broker, con main.py mínimo

- [ ] **Step 1: Borrar modelos broker**

```powershell
Remove-Item backend/app/models/config_dj.py, backend/app/models/config_filtros.py, backend/app/models/invite_token.py
```

- [ ] **Step 2: Borrar servicios broker**

```powershell
Remove-Item backend/app/services/dj_engine.py, backend/app/services/filtros_engine.py, backend/app/services/session_store.py, backend/app/services/minuta_generator.py
```

- [ ] **Step 3: Borrar routers y schemas broker**

```powershell
Remove-Item backend/app/routers/session.py, backend/app/routers/uploads.py, backend/app/schemas/session.py
```

- [ ] **Step 4: Borrar migraciones antiguas**

```powershell
Remove-Item backend/alembic/versions/0002_add_plantilla_config_dj.py, backend/alembic/versions/0003_add_invite_tokens.py, backend/alembic/versions/0004_security_hardening.py, backend/alembic/versions/0005_excel_real.py, backend/alembic/versions/0006_multi_dj.py, "backend/alembic/versions/ed7df405935c_initial.py"
```

- [ ] **Step 5: Borrar tests broker**

```powershell
Remove-Item backend/tests/test_dj_engine.py, backend/tests/test_filtros_engine.py, backend/tests/test_minuta_generator.py, backend/tests/test_session_router.py, backend/tests/test_session_store.py, backend/tests/test_uploads.py, backend/tests/test_register.py, backend/create_invite.py
```

- [ ] **Step 6: Borrar archivos frontend broker**

```powershell
Remove-Item frontend/src/components/minutas/MinutaCard.tsx, frontend/src/components/minutas/MinutaDrawer.tsx -Recurse
Remove-Item frontend/src/components/profile/RegenerateTOTPModal.tsx
Remove-Item frontend/src/hooks/useMinutas.ts, frontend/src/hooks/useSession.ts
Remove-Item frontend/src/services/configDJ.ts, frontend/src/services/configFiltros.ts, frontend/src/services/minutas.ts, frontend/src/services/upload.ts
Remove-Item frontend/src/pages/ConfigDJPage.tsx, frontend/src/pages/DashboardPage.tsx, frontend/src/pages/FiltradaPage.tsx, frontend/src/pages/FiltrosMinutasPage.tsx, frontend/src/pages/RegisterPage.tsx, frontend/src/pages/ResetPasswordPage.tsx, frontend/src/pages/TwoFactorPage.tsx
```

- [ ] **Step 7: Actualizar requirements.txt**

Reemplazar el contenido de `backend/requirements.txt`:

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
sqlalchemy==2.0.30
alembic==1.13.1
pydantic==2.7.1
pydantic-settings==2.2.1
psycopg2-binary==2.9.9
python-jose[cryptography]==3.5.0
bcrypt==4.3.0
openpyxl==3.1.2
jinja2==3.1.4
premailer==3.10.0
python-multipart==0.0.9
slowapi==0.1.9
httpx==0.27.0
pytest==8.2.1
pytest-asyncio==0.23.6
anyio[trio]==4.3.0
gunicorn==22.0.0
```

- [ ] **Step 8: Reemplazar main.py**

Reemplazar el contenido de `backend/app/main.py`:

```python
import asyncio
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.limiter import limiter
from app.core.logging_config import setup_logging, RequestLoggingMiddleware
from app.routers import auth

setup_logging()
_logger = logging.getLogger("mails_nico")


def _run_migrations():
    try:
        from alembic.config import Config
        from alembic import command
        import os
        alembic_ini = os.path.join(os.path.dirname(os.path.dirname(__file__)), "alembic.ini")
        if os.path.exists(alembic_ini):
            alembic_cfg = Config(alembic_ini)
            alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            command.upgrade(alembic_cfg, "head")
            _logger.info("Migraciones aplicadas correctamente")
    except Exception as e:
        _logger.error("Error al aplicar migraciones: %s", e)


_run_migrations()

app = FastAPI(title="Sistema de Cobro por Mail", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response: StarletteResponse = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)

app.include_router(auth.router)


@app.get("/health")
def health():
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "ok", "database": "ok"}
    except Exception:
        return {"status": "degraded", "database": "error"}
```

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "chore: eliminar archivos broker, limpiar requirements y main"
```

---

### Task 2: Modelos DB y migración inicial limpia

**Files:**
- Modify: `backend/app/models/user.py`
- Modify: `backend/app/models/plantilla.py`
- Create: `backend/app/models/cliente_maestro.py`
- Create: `backend/app/models/ciclo.py`
- Create: `backend/app/models/envio.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial.py`

**Interfaces:**
- Produces: `User`, `Plantilla`, `ClienteMaestro`, `Ciclo`, `Envio` importables desde `app.models`
- Produces: `EstadoEnvio`, `MotivoFiltrado` enums importables desde `app.models.envio`

- [ ] **Step 1: Escribir test que verifica la creación de tablas**

Crear `backend/tests/test_models.py`:

```python
def test_tables_exist(db):
    from sqlalchemy import inspect
    inspector = inspect(db.bind)
    tables = inspector.get_table_names()
    for t in ["users", "plantilla", "clientes_maestro", "ciclos", "envios"]:
        assert t in tables, f"Tabla faltante: {t}"
```

- [ ] **Step 2: Correr test — debe fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_models.py -v
```

Expected: FAIL — tablas no existen aún.

- [ ] **Step 3: Reemplazar user.py**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
```

- [ ] **Step 4: Reemplazar plantilla.py**

```python
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime
from app.core.database import Base


class Plantilla(Base):
    __tablename__ = "plantilla"
    id = Column(Integer, primary_key=True, default=1)
    asunto = Column(String(255), nullable=False, default="Recordatorio de deuda")
    cuerpo_html = Column(Text, nullable=False, default="")
    nombre_empresa = Column(String(255), nullable=False, default="")
    logo_url = Column(String(512), nullable=True)
    color_primario = Column(String(7), nullable=False, default="#1a56db")
    monto_minimo = Column(Numeric(12, 2), nullable=False, default=0)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

- [ ] **Step 5: Crear cliente_maestro.py**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ClienteMaestro(Base):
    __tablename__ = "clientes_maestro"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clave_union = Column(String(100), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    localidad = Column(String(255), nullable=True)
    prefiere_no_recibir_email = Column(Boolean, default=False, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

- [ ] **Step 6: Crear ciclo.py**

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Ciclo(Base):
    __tablename__ = "ciclos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero = Column(Integer, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    envios = relationship("Envio", back_populates="ciclo", lazy="dynamic")
```

- [ ] **Step 7: Crear envio.py**

```python
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Numeric, Integer, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class EstadoEnvio(str, PyEnum):
    NO_CONTESTADO = "NO_CONTESTADO"
    CONTESTADO = "CONTESTADO"
    PAGO = "PAGO"
    REBOTADO = "REBOTADO"
    SIN_EMAIL = "SIN_EMAIL"
    FILTRADO = "FILTRADO"


class MotivoFiltrado(str, PyEnum):
    MONTO_MINIMO = "MONTO_MINIMO"
    DADO_DE_BAJA = "DADO_DE_BAJA"


class Envio(Base):
    __tablename__ = "envios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ciclo_id = Column(UUID(as_uuid=True), ForeignKey("ciclos.id"), nullable=False, index=True)
    ciclo_numero = Column(Integer, nullable=False)
    clave_union = Column(String(100), nullable=False, index=True)
    nombre_consorcio = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    monto = Column(Numeric(12, 2), nullable=False)
    estado = Column(Enum(EstadoEnvio), nullable=False, default=EstadoEnvio.NO_CONTESTADO)
    motivo_filtrado = Column(Enum(MotivoFiltrado), nullable=True)
    message_id = Column(String(512), nullable=True, index=True)
    reply_snippet = Column(Text, nullable=True)
    enviado_en = Column(DateTime, nullable=True)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ciclo = relationship("Ciclo", back_populates="envios")
```

- [ ] **Step 8: Actualizar models/__init__.py**

```python
from app.models.user import User
from app.models.plantilla import Plantilla
from app.models.cliente_maestro import ClienteMaestro
from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio, MotivoFiltrado

__all__ = ["User", "Plantilla", "ClienteMaestro", "Ciclo", "Envio", "EstadoEnvio", "MotivoFiltrado"]
```

- [ ] **Step 9: Actualizar alembic/env.py**

```python
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.config import settings
from app.core.database import Base
from app.models.user import User
from app.models.plantilla import Plantilla
from app.models.cliente_maestro import ClienteMaestro
from app.models.ciclo import Ciclo
from app.models.envio import Envio

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 10: Crear alembic/versions/0001_initial.py**

```python
"""initial

Revision ID: 0001
Revises:
Create Date: 2026-06-30
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "plantilla",
        sa.Column("id", sa.Integer(), primary_key=True, default=1),
        sa.Column("asunto", sa.String(255), nullable=False),
        sa.Column("cuerpo_html", sa.Text(), nullable=False),
        sa.Column("nombre_empresa", sa.String(255), nullable=False),
        sa.Column("logo_url", sa.String(512), nullable=True),
        sa.Column("color_primario", sa.String(7), nullable=False),
        sa.Column("monto_minimo", sa.Numeric(12, 2), nullable=False),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "clientes_maestro",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clave_union", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("localidad", sa.String(255), nullable=True),
        sa.Column("prefiere_no_recibir_email", sa.Boolean(), nullable=False, default=False),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "ciclos",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("creado_en", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "envios",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ciclo_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("ciclos.id"), nullable=False),
        sa.Column("ciclo_numero", sa.Integer(), nullable=False),
        sa.Column("clave_union", sa.String(100), nullable=False),
        sa.Column("nombre_consorcio", sa.String(255), nullable=False),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("monto", sa.Numeric(12, 2), nullable=False),
        sa.Column("estado", sa.Enum("NO_CONTESTADO", "CONTESTADO", "PAGO", "REBOTADO", "SIN_EMAIL", "FILTRADO", name="estadoenvio"), nullable=False),
        sa.Column("motivo_filtrado", sa.Enum("MONTO_MINIMO", "DADO_DE_BAJA", name="motivofiltrado"), nullable=True),
        sa.Column("message_id", sa.String(512), nullable=True),
        sa.Column("reply_snippet", sa.Text(), nullable=True),
        sa.Column("enviado_en", sa.DateTime(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_envios_ciclo_id", "envios", ["ciclo_id"])
    op.create_index("ix_envios_clave_union", "envios", ["clave_union"])
    op.create_index("ix_envios_message_id", "envios", ["message_id"])


def downgrade() -> None:
    op.drop_table("envios")
    op.drop_table("ciclos")
    op.drop_table("clientes_maestro")
    op.drop_table("plantilla")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS estadoenvio")
    op.execute("DROP TYPE IF EXISTS motivofiltrado")
```

- [ ] **Step 11: Actualizar conftest.py**

```python
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test_secret_key_minimum_32_characters_here_ok")
os.environ.setdefault("RATELIMIT_ENABLED", "false")
os.environ.setdefault("YAHOO_EMAIL", "test@yahoo.com")
os.environ.setdefault("YAHOO_APP_PASSWORD", "testapppassword")

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.models.user import User
from app.models.plantilla import Plantilla
from app.models.cliente_maestro import ClienteMaestro
from app.models.ciclo import Ciclo
from app.models.envio import Envio

_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_TestingSessionLocal = sessionmaker(_engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(_engine)
    yield
    Base.metadata.drop_all(_engine)


@pytest.fixture
def db(setup_test_database):
    session = _TestingSessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def client(db):
    from app.main import app
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        username=f"test_{os.urandom(4).hex()}",
        hashed_password=hash_password("SecurePass123!"),
        is_active=True,
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def auth_headers(client, test_user):
    r = client.post("/auth/login", json={"username": test_user.username, "password": "SecurePass123!"})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def plantilla_default(db):
    p = Plantilla(
        id=1,
        asunto="Recordatorio de deuda",
        cuerpo_html="<p>Estimado {{nombre}}, su deuda es ${{monto}}.</p>",
        nombre_empresa="Ascensores SA",
        color_primario="#1a56db",
        monto_minimo=0,
    )
    db.add(p)
    db.flush()
    return p
```

- [ ] **Step 12: Correr test — debe pasar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_models.py -v
```

Expected: PASS

- [ ] **Step 13: Commit**

```bash
git add -A
git commit -m "feat: modelos User/Plantilla/ClienteMaestro/Ciclo/Envio + migración 0001_initial"
```

---

### Task 3: Auth simplificado (sin 2FA)

**Files:**
- Modify: `backend/app/core/security.py`
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/schemas/auth.py`
- Modify: `backend/app/routers/auth.py`
- Modify: `backend/scripts/seed_user.py`
- Modify: `backend/tests/test_auth.py`
- Modify: `backend/tests/test_security.py`
- Modify: `backend/tests/test_change_credentials.py`

**Interfaces:**
- Produces: `POST /auth/login` → `TokenResponse(access_token, refresh_token)`
- Produces: `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/change-password`
- Consumes: `hash_password`, `verify_password`, `create_access_token`, `create_refresh_token`, `decode_token` de security.py

- [ ] **Step 1: Reemplazar security.py (sin TOTP ni Fernet)**

```python
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

UTC = timezone.utc
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(subject: str, expires_delta: timedelta) -> str:
    from app.core.config import settings
    expire = datetime.now(UTC) + expires_delta
    return jwt.encode({"sub": subject, "exp": expire, "type": "access"}, settings.SECRET_KEY, algorithm="HS256")


def create_refresh_token(subject: str) -> str:
    from app.core.config import settings
    expire = datetime.now(UTC) + timedelta(hours=settings.REFRESH_TOKEN_EXPIRE_HOURS)
    return jwt.encode({"sub": subject, "exp": expire, "type": "refresh"}, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    from app.core.config import settings
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
```

- [ ] **Step 2: Reemplazar config.py**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    YAHOO_EMAIL: str
    YAHOO_APP_PASSWORD: str
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    REFRESH_TOKEN_EXPIRE_HOURS: int = 8
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def get_allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
```

- [ ] **Step 3: Reemplazar schemas/auth.py**

```python
import re
from pydantic import BaseModel, field_validator


def _validate_password(v: str) -> str:
    if not (8 <= len(v) <= 72):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[A-Z]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[0-9]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[^a-zA-Z0-9]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)
```

- [ ] **Step 4: Reemplazar routers/auth.py**

```python
from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse
from app.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(body.username, body.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=204)
def logout(current_user: User = Depends(get_current_user)):
    pass


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Refresh token inválido")
    user = db.query(User).filter(User.id == UUID(payload["sub"]), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no autorizado")
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    db.commit()
```

- [ ] **Step 5: Actualizar seed_user.py**

```python
"""Crear usuario operario inicial. Correr una vez: python backend/scripts/seed_user.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

os.environ.setdefault("YAHOO_EMAIL", "placeholder@yahoo.com")
os.environ.setdefault("YAHOO_APP_PASSWORD", "placeholder")

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User

USERNAME = os.environ.get("SEED_USERNAME", "operario")
PASSWORD = os.environ.get("SEED_PASSWORD", "Cambiar123!")

db = SessionLocal()
existing = db.query(User).filter(User.username == USERNAME).first()
if existing:
    print(f"Usuario '{USERNAME}' ya existe.")
else:
    user = User(username=USERNAME, hashed_password=hash_password(PASSWORD), is_active=True)
    db.add(user)
    db.commit()
    print(f"Usuario '{USERNAME}' creado con contraseña '{PASSWORD}'. Cambiarla inmediatamente.")
db.close()
```

- [ ] **Step 6: Reemplazar tests/test_auth.py**

```python
def test_login_exitoso(client, test_user):
    r = client.post("/auth/login", json={"username": test_user.username, "password": "SecurePass123!"})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_credenciales_invalidas(client, test_user):
    r = client.post("/auth/login", json={"username": test_user.username, "password": "wrong"})
    assert r.status_code == 401


def test_refresh(client, auth_headers, test_user):
    r = client.post("/auth/login", json={"username": test_user.username, "password": "SecurePass123!"})
    refresh_token = r.json()["refresh_token"]
    r2 = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_logout(client, auth_headers):
    r = client.post("/auth/logout", headers=auth_headers)
    assert r.status_code == 204


def test_me_requiere_auth(client):
    r = client.get("/auth/me")
    assert r.status_code in (401, 404)
```

- [ ] **Step 7: Reemplazar tests/test_security.py**

```python
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from datetime import timedelta


def test_hash_verify_password():
    h = hash_password("MiClave123!")
    assert verify_password("MiClave123!", h)
    assert not verify_password("wrong", h)


def test_access_token_roundtrip():
    token = create_access_token("user-123", timedelta(hours=1))
    payload = decode_token(token)
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
```

- [ ] **Step 8: Reemplazar tests/test_change_credentials.py**

```python
def test_change_password(client, auth_headers, test_user, db):
    r = client.post(
        "/auth/change-password",
        json={"old_password": "SecurePass123!", "new_password": "NuevaClave456@"},
        headers=auth_headers,
    )
    assert r.status_code == 204
    db.refresh(test_user)
    from app.core.security import verify_password
    assert verify_password("NuevaClave456@", test_user.hashed_password)


def test_change_password_wrong_old(client, auth_headers):
    r = client.post(
        "/auth/change-password",
        json={"old_password": "wrong", "new_password": "NuevaClave456@"},
        headers=auth_headers,
    )
    assert r.status_code == 401
```

- [ ] **Step 9: Correr tests**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_auth.py tests/test_security.py tests/test_change_credentials.py -v
```

Expected: todos PASS

- [ ] **Step 10: Commit**

```bash
git add -A
git commit -m "feat: auth simplificado sin 2FA (login directo a JWT)"
```

---

### Task 4: Plantilla CRUD (servicio + router)

**Files:**
- Create: `backend/app/schemas/plantilla.py`
- Modify: `backend/app/services/db_config.py`
- Create: `backend/app/routers/plantilla.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_db_config.py`

**Interfaces:**
- Produces: `GET /plantilla` → `PlantillaSchema`
- Produces: `PUT /plantilla` → `PlantillaSchema`
- Consumes: `db_config.load_plantilla(db)`, `db_config.save_plantilla(db, data)`

- [ ] **Step 1: Escribir tests**

Crear `backend/tests/test_plantilla.py`:

```python
def test_get_plantilla_sin_datos_devuelve_defaults(client, auth_headers):
    r = client.get("/plantilla", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "asunto" in data
    assert "cuerpo_html" in data
    assert "monto_minimo" in data


def test_put_plantilla(client, auth_headers):
    payload = {
        "asunto": "Deuda pendiente",
        "cuerpo_html": "<p>Hola {{nombre}}</p>",
        "nombre_empresa": "Ascensores SA",
        "color_primario": "#ff0000",
        "monto_minimo": 1500.00,
    }
    r = client.put("/plantilla", json=payload, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["asunto"] == "Deuda pendiente"
    assert float(r.json()["monto_minimo"]) == 1500.00


def test_put_plantilla_persiste(client, auth_headers):
    client.put("/plantilla", json={
        "asunto": "Recordatorio",
        "cuerpo_html": "<p>texto</p>",
        "nombre_empresa": "SA",
        "color_primario": "#000000",
        "monto_minimo": 500,
    }, headers=auth_headers)
    r = client.get("/plantilla", headers=auth_headers)
    assert r.json()["asunto"] == "Recordatorio"
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_plantilla.py -v
```

Expected: FAIL

- [ ] **Step 3: Crear schemas/plantilla.py**

```python
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PlantillaSchema(BaseModel):
    asunto: str
    cuerpo_html: str
    nombre_empresa: str
    logo_url: Optional[str] = None
    color_primario: str = "#1a56db"
    monto_minimo: Decimal

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Reemplazar services/db_config.py**

```python
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.plantilla import Plantilla
from app.schemas.plantilla import PlantillaSchema


def load_plantilla(db: Session) -> Plantilla:
    p = db.get(Plantilla, 1)
    if p is None:
        p = Plantilla(
            id=1,
            asunto="Recordatorio de deuda",
            cuerpo_html="<p>Estimado {{nombre}},</p><p>Le informamos que registra una deuda de ${{monto}}.</p>",
            nombre_empresa="",
            color_primario="#1a56db",
            monto_minimo=0,
            actualizado_en=datetime.now(timezone.utc),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


def save_plantilla(db: Session, data: PlantillaSchema) -> Plantilla:
    p = db.get(Plantilla, 1)
    if p is None:
        p = Plantilla(id=1)
        db.add(p)
    p.asunto = data.asunto
    p.cuerpo_html = data.cuerpo_html
    p.nombre_empresa = data.nombre_empresa
    p.logo_url = data.logo_url
    p.color_primario = data.color_primario
    p.monto_minimo = data.monto_minimo
    p.actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(p)
    return p
```

- [ ] **Step 5: Crear routers/plantilla.py**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.plantilla import PlantillaSchema
from app.services import db_config

router = APIRouter(prefix="/plantilla", tags=["plantilla"])


@router.get("", response_model=PlantillaSchema)
def get_plantilla(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db_config.load_plantilla(db)


@router.put("", response_model=PlantillaSchema)
def update_plantilla(
    body: PlantillaSchema,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db_config.save_plantilla(db, body)
```

- [ ] **Step 6: Agregar router en main.py**

En `backend/app/main.py` agregar:
```python
from app.routers import auth, plantilla
# ...
app.include_router(auth.router)
app.include_router(plantilla.router)
```

- [ ] **Step 7: Correr tests**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_plantilla.py -v
```

Expected: todos PASS

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: Plantilla CRUD (GET/PUT /plantilla)"
```

---

### Task 5: excel_parser — parseo de Excel deudores y maestro

**Files:**
- Modify: `backend/app/services/excel_parser.py`
- Create: `backend/tests/test_excel_parser.py`

**Interfaces:**
- Produces: `parse_deudores(file_bytes) -> list[DeudorRow]`
- Produces: `parse_maestro(file_bytes) -> list[MaestroRow]`
- Produces: `DeudorRow(clave_union, nombre, localidad, monto)`
- Produces: `MaestroRow(clave_union, nombre, email, localidad)`

**Nota:** Las columnas exactas están pendientes de confirmar con el cliente. El parser usa detección flexible por aliases. Cuando el cliente comparta el Excel real, solo hay que agregar el alias correspondiente a `DEUDOR_ALIASES` o `MAESTRO_ALIASES`.

- [ ] **Step 1: Escribir tests**

```python
# backend/tests/test_excel_parser.py
import io
import openpyxl
import pytest
from app.services.excel_parser import parse_deudores, parse_maestro, ExcelParseError


def _make_excel(headers: list, rows: list[list]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h)
    for r_idx, row in enumerate(rows, 2):
        for c_idx, val in enumerate(row, 1):
            ws.cell(row=r_idx, column=c_idx, value=val)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_parse_deudores_basico():
    data = _make_excel(
        ["nro cliente", "nombre", "localidad", "monto"],
        [["C001", "Consorcio Test", "CABA", 5000.00]],
    )
    rows = parse_deudores(data)
    assert len(rows) == 1
    assert rows[0].clave_union == "C001"
    assert rows[0].nombre == "Consorcio Test"
    assert rows[0].localidad == "CABA"
    assert float(rows[0].monto) == 5000.00


def test_parse_deudores_alias_detalle():
    """Acepta 'detalle del nombre' como alias de nombre."""
    data = _make_excel(
        ["nro cliente", "detalle del nombre", "localidad", "monto"],
        [["C002", "Otro Consorcio", "GBA", 3000.50]],
    )
    rows = parse_deudores(data)
    assert rows[0].nombre == "Otro Consorcio"


def test_parse_deudores_omite_monto_cero():
    data = _make_excel(
        ["nro cliente", "nombre", "localidad", "monto"],
        [["C003", "Consorcio Cero", "CABA", 0]],
    )
    rows = parse_deudores(data)
    assert len(rows) == 0


def test_parse_deudores_columna_faltante_lanza_error():
    data = _make_excel(["nombre", "monto"], [["Consorcio", 100]])
    with pytest.raises(ExcelParseError, match="clave_union"):
        parse_deudores(data)


def test_parse_maestro_basico():
    data = _make_excel(
        ["nro cliente", "nombre", "email", "localidad"],
        [["C001", "Consorcio Test", "test@mail.com", "CABA"]],
    )
    rows = parse_maestro(data)
    assert len(rows) == 1
    assert rows[0].email == "test@mail.com"


def test_parse_maestro_email_vacio_es_none():
    data = _make_excel(
        ["nro cliente", "nombre", "email", "localidad"],
        [["C001", "Consorcio Test", "", "CABA"]],
    )
    rows = parse_maestro(data)
    assert rows[0].email is None
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_excel_parser.py -v
```

Expected: FAIL

- [ ] **Step 3: Reemplazar services/excel_parser.py**

```python
import io
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import openpyxl


class ExcelParseError(Exception):
    pass


@dataclass
class DeudorRow:
    clave_union: str
    nombre: str
    localidad: Optional[str]
    monto: Decimal


@dataclass
class MaestroRow:
    clave_union: str
    nombre: str
    email: Optional[str]
    localidad: Optional[str]


# Aliases aceptados por columna. Agregar alias cuando el cliente comparta el Excel real.
DEUDOR_ALIASES: dict[str, list[str]] = {
    "clave_union": ["nro cliente", "nro_cliente", "cliente", "id cliente", "codigo"],
    "nombre": ["nombre", "detalle del nombre", "detalle", "razon social", "consorcio"],
    "localidad": ["localidad", "provincia", "ciudad", "zona"],
    "monto": ["monto", "deuda", "importe", "saldo", "monto adeudado"],
}

MAESTRO_ALIASES: dict[str, list[str]] = {
    "clave_union": ["nro cliente", "nro_cliente", "cliente", "id cliente", "codigo"],
    "nombre": ["nombre", "detalle del nombre", "detalle", "razon social", "consorcio"],
    "email": ["email", "mail", "correo", "e-mail"],
    "localidad": ["localidad", "provincia", "ciudad", "zona"],
}


def _normalize(s: str) -> str:
    return s.strip().lower()


def _find_column(headers: list[str], field: str, aliases: dict[str, list[str]]) -> Optional[int]:
    normalized = [_normalize(h) for h in headers]
    for alias in aliases[field]:
        if alias in normalized:
            return normalized.index(alias)
    return None


def _load_workbook(file_bytes: bytes) -> list[list]:
    wb = openpyxl.load_workbook(io.BytesIO(file_bytes), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    return rows


def parse_deudores(file_bytes: bytes) -> list[DeudorRow]:
    rows = _load_workbook(file_bytes)
    if not rows:
        raise ExcelParseError("El archivo está vacío")
    headers = [str(h) if h is not None else "" for h in rows[0]]
    col = {}
    for field in DEUDOR_ALIASES:
        idx = _find_column(headers, field, DEUDOR_ALIASES)
        if idx is None and field != "localidad":
            raise ExcelParseError(f"Columna requerida no encontrada: {field}. Encabezados: {headers}")
        col[field] = idx

    result = []
    for row in rows[1:]:
        clave = str(row[col["clave_union"]] or "").strip()
        nombre = str(row[col["nombre"]] or "").strip()
        monto_raw = row[col["monto"]]
        if not clave or not nombre or monto_raw is None:
            continue
        try:
            monto = Decimal(str(monto_raw))
        except Exception:
            continue
        if monto <= 0:
            continue
        localidad = None
        if col["localidad"] is not None:
            localidad = str(row[col["localidad"]] or "").strip() or None
        result.append(DeudorRow(clave_union=clave, nombre=nombre, localidad=localidad, monto=monto))
    return result


def parse_maestro(file_bytes: bytes) -> list[MaestroRow]:
    rows = _load_workbook(file_bytes)
    if not rows:
        raise ExcelParseError("El archivo está vacío")
    headers = [str(h) if h is not None else "" for h in rows[0]]
    col = {}
    for field in MAESTRO_ALIASES:
        idx = _find_column(headers, field, MAESTRO_ALIASES)
        if idx is None and field not in ("localidad", "email"):
            raise ExcelParseError(f"Columna requerida no encontrada: {field}. Encabezados: {headers}")
        col[field] = idx

    result = []
    for row in rows[1:]:
        clave = str(row[col["clave_union"]] or "").strip()
        nombre = str(row[col["nombre"]] or "").strip()
        if not clave or not nombre:
            continue
        email = None
        if col.get("email") is not None:
            raw_email = str(row[col["email"]] or "").strip()
            email = raw_email if raw_email else None
        localidad = None
        if col.get("localidad") is not None:
            raw_loc = str(row[col["localidad"]] or "").strip()
            localidad = raw_loc if raw_loc else None
        result.append(MaestroRow(clave_union=clave, nombre=nombre, email=email, localidad=localidad))
    return result
```

- [ ] **Step 4: Correr tests**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_excel_parser.py -v
```

Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: excel_parser con detección flexible de columnas por aliases"
```

---

### Task 6: Maestro de Clientes — servicio + router

**Files:**
- Create: `backend/app/schemas/maestro.py`
- Create: `backend/app/services/maestro_service.py`
- Create: `backend/app/routers/maestro.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_maestro.py`

**Interfaces:**
- Produces: `POST /maestro/upload` → `{ "actualizados": int, "nuevos": int, "total": int }`
- Produces: `GET /maestro` → `list[ClienteMaestroSchema]`
- Consumes: `parse_maestro(bytes)` de excel_parser
- Produces: `merge_maestro(db, rows)` — actualiza o crea ClienteMaestro, nunca sobreescribe `prefiere_no_recibir_email=True`

- [ ] **Step 1: Escribir tests**

```python
# backend/tests/test_maestro.py
import io
import openpyxl


def _make_maestro_excel(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nro cliente", "nombre", "email", "localidad"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_upload_maestro_crea_clientes(client, auth_headers):
    excel = _make_maestro_excel([
        ["C001", "Consorcio Uno", "uno@mail.com", "CABA"],
        ["C002", "Consorcio Dos", "dos@mail.com", "GBA"],
    ])
    r = client.post(
        "/maestro/upload",
        files={"file": ("maestro.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nuevos"] == 2
    assert data["total"] == 2


def test_upload_maestro_actualiza_sin_sobreescribir_baja(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(
        clave_union="C003",
        nombre="Consorcio Baja",
        email="baja@mail.com",
        prefiere_no_recibir_email=True,
    )
    db.add(cliente)
    db.flush()

    excel = _make_maestro_excel([["C003", "Consorcio Baja Actualizado", "nuevo@mail.com", "CABA"]])
    client.post(
        "/maestro/upload",
        files={"file": ("maestro.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    db.refresh(cliente)
    assert cliente.prefiere_no_recibir_email is True
    assert cliente.nombre == "Consorcio Baja Actualizado"


def test_get_maestro(client, auth_headers):
    r = client.get("/maestro", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_maestro.py -v
```

- [ ] **Step 3: Crear schemas/maestro.py**

```python
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class ClienteMaestroSchema(BaseModel):
    id: UUID
    clave_union: str
    nombre: str
    email: Optional[str]
    localidad: Optional[str]
    prefiere_no_recibir_email: bool
    activo: bool

    model_config = {"from_attributes": True}


class MaestroUploadResponse(BaseModel):
    nuevos: int
    actualizados: int
    total: int
```

- [ ] **Step 4: Crear services/maestro_service.py**

```python
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.cliente_maestro import ClienteMaestro
from app.services.excel_parser import MaestroRow


def merge_maestro(db: Session, rows: list[MaestroRow]) -> dict:
    nuevos = 0
    actualizados = 0
    for row in rows:
        existing = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == row.clave_union).first()
        if existing:
            existing.nombre = row.nombre
            existing.localidad = row.localidad
            if not existing.prefiere_no_recibir_email:
                existing.email = row.email
            existing.actualizado_en = datetime.now(timezone.utc)
            actualizados += 1
        else:
            db.add(ClienteMaestro(
                clave_union=row.clave_union,
                nombre=row.nombre,
                email=row.email,
                localidad=row.localidad,
                actualizado_en=datetime.now(timezone.utc),
            ))
            nuevos += 1
    db.commit()
    total = db.query(ClienteMaestro).count()
    return {"nuevos": nuevos, "actualizados": actualizados, "total": total}
```

- [ ] **Step 5: Crear routers/maestro.py**

```python
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.cliente_maestro import ClienteMaestro
from app.schemas.maestro import ClienteMaestroSchema, MaestroUploadResponse
from app.services.excel_parser import parse_maestro, ExcelParseError
from app.services.maestro_service import merge_maestro

router = APIRouter(prefix="/maestro", tags=["maestro"])


@router.post("/upload", response_model=MaestroUploadResponse)
async def upload_maestro(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        rows = parse_maestro(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return merge_maestro(db, rows)


@router.get("", response_model=list[ClienteMaestroSchema])
def get_maestro(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ClienteMaestro).order_by(ClienteMaestro.nombre).all()
```

- [ ] **Step 6: Agregar router en main.py**

```python
from app.routers import auth, plantilla, maestro
# ...
app.include_router(maestro.router)
```

- [ ] **Step 7: Correr tests**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_maestro.py -v
```

Expected: todos PASS

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: maestro de clientes — upload Excel y merge con protección de baja"
```

---

### Task 7: excel_joiner — cruce deudores con maestro

**Files:**
- Create: `backend/app/services/excel_joiner.py`
- Create: `backend/tests/test_excel_joiner.py`

**Interfaces:**
- Produces: `join_deudores(db, deudores, monto_minimo) -> PreviewData`
- Produces: `PreviewData(para_enviar, sin_email, filtrados)`
- Produces: `EnvioParsed(clave_union, nombre, email, localidad, monto, ciclo_numero_anterior)`

- [ ] **Step 1: Escribir tests**

```python
# backend/tests/test_excel_joiner.py
from decimal import Decimal
from app.services.excel_parser import DeudorRow
from app.services.excel_joiner import join_deudores, PreviewData
from app.models.cliente_maestro import ClienteMaestro


def _add_cliente(db, clave, nombre, email=None, baja=False):
    c = ClienteMaestro(clave_union=clave, nombre=nombre, email=email, prefiere_no_recibir_email=baja)
    db.add(c)
    db.flush()
    return c


def test_join_deudor_con_email(db):
    _add_cliente(db, "C001", "Consorcio Uno", email="uno@mail.com")
    deudores = [DeudorRow("C001", "Consorcio Uno", "CABA", Decimal("5000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.para_enviar) == 1
    assert preview.para_enviar[0].email == "uno@mail.com"
    assert len(preview.sin_email) == 0
    assert len(preview.filtrados) == 0


def test_join_deudor_sin_match_en_maestro(db):
    deudores = [DeudorRow("C999", "Desconocido", "CABA", Decimal("1000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.sin_email) == 1
    assert preview.sin_email[0].clave_union == "C999"


def test_join_filtrado_por_monto_minimo(db):
    _add_cliente(db, "C002", "Consorcio Dos", email="dos@mail.com")
    deudores = [DeudorRow("C002", "Consorcio Dos", "CABA", Decimal("300"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("500"))
    assert len(preview.filtrados) == 1
    assert preview.filtrados[0][1] == "MONTO_MINIMO"


def test_join_filtrado_por_baja(db):
    _add_cliente(db, "C003", "Consorcio Baja", email="baja@mail.com", baja=True)
    deudores = [DeudorRow("C003", "Consorcio Baja", "CABA", Decimal("9000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.filtrados) == 1
    assert preview.filtrados[0][1] == "DADO_DE_BAJA"


def test_join_sin_email_en_maestro(db):
    _add_cliente(db, "C004", "Sin Email", email=None)
    deudores = [DeudorRow("C004", "Sin Email", "CABA", Decimal("2000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.sin_email) == 1
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_excel_joiner.py -v
```

- [ ] **Step 3: Crear services/excel_joiner.py**

```python
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.cliente_maestro import ClienteMaestro
from app.models.envio import Envio, EstadoEnvio
from app.services.excel_parser import DeudorRow


@dataclass
class EnvioParsed:
    clave_union: str
    nombre: str
    email: str
    localidad: Optional[str]
    monto: Decimal
    ciclo_numero_anterior: int


@dataclass
class PreviewData:
    para_enviar: list[EnvioParsed]
    sin_email: list[DeudorRow]
    filtrados: list[tuple[DeudorRow, str]]  # (row, motivo)


def _ciclos_consecutivos_deudor(db: Session, clave_union: str) -> int:
    last = (
        db.query(Envio)
        .filter(Envio.clave_union == clave_union)
        .order_by(Envio.ciclo_numero.desc())
        .first()
    )
    if last is None or last.estado == EstadoEnvio.PAGO:
        return 0
    return last.ciclo_numero


def join_deudores(db: Session, deudores: list[DeudorRow], monto_minimo: Decimal) -> PreviewData:
    para_enviar = []
    sin_email = []
    filtrados = []

    claves = [d.clave_union for d in deudores]
    clientes = {
        c.clave_union: c
        for c in db.query(ClienteMaestro).filter(ClienteMaestro.clave_union.in_(claves)).all()
    }

    for deudor in deudores:
        cliente = clientes.get(deudor.clave_union)
        if cliente is None:
            sin_email.append(deudor)
            continue
        if cliente.prefiere_no_recibir_email:
            filtrados.append((deudor, "DADO_DE_BAJA"))
            continue
        if deudor.monto < monto_minimo:
            filtrados.append((deudor, "MONTO_MINIMO"))
            continue
        if not cliente.email:
            sin_email.append(deudor)
            continue
        ciclo_ant = _ciclos_consecutivos_deudor(db, deudor.clave_union)
        para_enviar.append(EnvioParsed(
            clave_union=deudor.clave_union,
            nombre=cliente.nombre,
            email=cliente.email,
            localidad=deudor.localidad or cliente.localidad,
            monto=deudor.monto,
            ciclo_numero_anterior=ciclo_ant,
        ))

    return PreviewData(para_enviar=para_enviar, sin_email=sin_email, filtrados=filtrados)
```

- [ ] **Step 4: Correr tests**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_excel_joiner.py -v
```

Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: excel_joiner — cruce deudores/maestro con filtrado y ciclo_numero"
```

---

### Task 8: email_generator — HTML con Jinja2 + premailer

**Files:**
- Create: `backend/app/services/email_generator.py`
- Create: `backend/app/templates/mail_cobro.html`
- Create: `backend/tests/test_email_generator.py`

**Interfaces:**
- Produces: `generate_email(envio_parsed, plantilla) -> EmailMessage`  donde `EmailMessage` es `email.message.EmailMessage` de stdlib
- Consumes: `EnvioParsed` de excel_joiner, `Plantilla` de models

- [ ] **Step 1: Escribir tests**

```python
# backend/tests/test_email_generator.py
from decimal import Decimal
from app.services.excel_joiner import EnvioParsed
from app.services.email_generator import generate_email


def _make_envio():
    return EnvioParsed(
        clave_union="C001",
        nombre="Consorcio Test",
        email="test@mail.com",
        localidad="CABA",
        monto=Decimal("5000.50"),
        ciclo_numero_anterior=0,
    )


def test_generate_email_tiene_asunto(plantilla_default):
    msg = generate_email(_make_envio(), plantilla_default)
    assert msg["Subject"] == plantilla_default.asunto


def test_generate_email_tiene_destinatario(plantilla_default):
    msg = generate_email(_make_envio(), plantilla_default)
    assert msg["To"] == "test@mail.com"


def test_generate_email_html_contiene_nombre(plantilla_default):
    msg = generate_email(_make_envio(), plantilla_default)
    body = msg.get_payload(decode=True)
    if body is None:
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                body = part.get_payload(decode=True)
                break
    assert b"Consorcio Test" in body


def test_generate_email_html_contiene_monto(plantilla_default):
    msg = generate_email(_make_envio(), plantilla_default)
    payload = None
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            break
    if payload is None:
        payload = msg.get_payload(decode=True)
    assert b"5000" in payload
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_email_generator.py -v
```

- [ ] **Step 3: Crear template mail_cobro.html**

Crear el directorio `backend/app/templates/` y el archivo `backend/app/templates/mail_cobro.html`:

```html
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body { font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 0; }
    .container { max-width: 600px; margin: 30px auto; background: #ffffff; border-radius: 8px; overflow: hidden; }
    .header { background: {{ color_primario }}; padding: 24px; text-align: center; }
    .header h1 { color: #ffffff; margin: 0; font-size: 22px; }
    .body { padding: 32px; color: #333333; line-height: 1.6; }
    .monto-box { background: #f9f9f9; border-left: 4px solid {{ color_primario }}; padding: 16px; margin: 24px 0; }
    .monto-box .label { font-size: 13px; color: #666; }
    .monto-box .valor { font-size: 28px; font-weight: bold; color: {{ color_primario }}; }
    .footer { background: #f4f4f4; padding: 16px; text-align: center; font-size: 12px; color: #999; }
    .unsubscribe { font-size: 11px; color: #bbb; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      {% if logo_url %}
      <img src="{{ logo_url }}" alt="{{ nombre_empresa }}" style="max-height:60px; margin-bottom:8px;"><br>
      {% endif %}
      <h1>{{ nombre_empresa }}</h1>
    </div>
    <div class="body">
      {{ cuerpo_html | safe }}
      <div class="monto-box">
        <div class="label">Monto adeudado</div>
        <div class="valor">${{ monto }}</div>
      </div>
      <p style="font-size:13px; color:#555;">
        Fecha de envío: {{ fecha_envio }}<br>
        Referencia: {{ clave_union }}
      </p>
    </div>
    <div class="footer">
      <p>{{ nombre_empresa }}</p>
      <p class="unsubscribe">
        Si no desea recibir más comunicaciones, 
        <a href="{{ unsubscribe_url }}">haga clic aquí para darse de baja</a>.
      </p>
    </div>
  </div>
</body>
</html>
```

- [ ] **Step 4: Crear services/email_generator.py**

```python
import os
from datetime import datetime, timezone
from decimal import Decimal
from email.message import EmailMessage

from jinja2 import Environment, FileSystemLoader
from premailer import transform

from app.models.plantilla import Plantilla
from app.services.excel_joiner import EnvioParsed

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
_jinja_env = Environment(loader=FileSystemLoader(_TEMPLATES_DIR), autoescape=False)


def generate_email(envio: EnvioParsed, plantilla: Plantilla, unsubscribe_base_url: str = "") -> EmailMessage:
    cuerpo_renderizado = _render_cuerpo(envio, plantilla)
    unsubscribe_url = f"{unsubscribe_base_url}/unsubscribe?clave={envio.clave_union}" if unsubscribe_base_url else "#"
    template = _jinja_env.get_template("mail_cobro.html")
    html_raw = template.render(
        nombre=envio.nombre,
        monto=f"{envio.monto:,.2f}",
        localidad=envio.localidad or "",
        clave_union=envio.clave_union,
        fecha_envio=datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        cuerpo_html=cuerpo_renderizado,
        nombre_empresa=plantilla.nombre_empresa,
        logo_url=plantilla.logo_url or "",
        color_primario=plantilla.color_primario,
        unsubscribe_url=unsubscribe_url,
    )
    html_inline = transform(html_raw)

    msg = EmailMessage()
    msg["Subject"] = plantilla.asunto
    msg["To"] = envio.email
    msg.set_content("Este mensaje requiere un cliente de correo con soporte HTML.")
    msg.add_alternative(html_inline, subtype="html")
    return msg


def _render_cuerpo(envio: EnvioParsed, plantilla: Plantilla) -> str:
    variables = {
        "nombre": envio.nombre,
        "monto": f"{envio.monto:,.2f}",
        "localidad": envio.localidad or "",
        "clave_union": envio.clave_union,
        "fecha_envio": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
    }
    result = plantilla.cuerpo_html
    for key, val in variables.items():
        result = result.replace(f"{{{{{key}}}}}", val)
    return result
```

- [ ] **Step 5: Correr tests**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_email_generator.py -v
```

Expected: todos PASS

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: email_generator con Jinja2 + premailer y template HTML de cobro"
```

---

---

### Task 9: smtp_sender — cola asyncio + rate limiting

**Files:**
- Create: `backend/app/services/smtp_sender.py`
- Create: `backend/tests/test_smtp_sender.py`

**Interfaces:**
- Produces: `async enviar_ciclo(envios: list[Envio], db, on_progress: Callable[[Envio], Awaitable[None]]) -> None`
- Consumes: `Envio` (modelo SQLAlchemy), `Plantilla` singleton via db_config
- Emite: llama `on_progress(envio)` después de cada envío exitoso para SSE

- [ ] **Step 1: Escribir tests (con SMTP mockeado)**

```python
# backend/tests/test_smtp_sender.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal
from app.services.smtp_sender import enviar_ciclo
from app.models.envio import Envio, EstadoEnvio
from app.models.plantilla import Plantilla


def _make_envio_db(db, ciclo, clave, nombre, email, monto):
    from datetime import datetime, timezone
    e = Envio(
        ciclo_id=ciclo.id,
        ciclo_numero=1,
        clave_union=clave,
        nombre_consorcio=nombre,
        email=email,
        monto=Decimal(str(monto)),
        estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.flush()
    return e


def _make_ciclo(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    c = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    return c


def test_enviar_ciclo_actualiza_estado_a_no_contestado(db, plantilla_default):
    ciclo = _make_ciclo(db)
    envio = _make_envio_db(db, ciclo, "C001", "Consorcio", "test@mail.com", 5000)

    progreso = []

    async def on_progress(e):
        progreso.append(e.id)

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<msg-id-123@yahoo.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo([envio], db, on_progress, rate_limit_override=(2, 0.01))
        )

    db.refresh(envio)
    assert envio.message_id == "<msg-id-123@yahoo.com>"
    assert envio.estado == EstadoEnvio.NO_CONTESTADO
    assert envio.enviado_en is not None
    assert envio.id in progreso


def test_enviar_ciclo_respeta_rate_limit(db, plantilla_default):
    ciclo = _make_ciclo(db)
    envios = [_make_envio_db(db, ciclo, f"C{i:03d}", f"Cons {i}", f"c{i}@mail.com", 1000) for i in range(4)]

    calls = []

    async def on_progress(e):
        calls.append(e.id)

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<mid@yahoo.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo(envios, db, on_progress, rate_limit_override=(2, 0.05))
        )

    assert len(calls) == 4
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_smtp_sender.py -v
```

- [ ] **Step 3: Crear services/smtp_sender.py**

```python
import asyncio
import logging
import smtplib
import ssl
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.envio import Envio, EstadoEnvio
from app.services import db_config
from app.services.email_generator import generate_email
from app.services.excel_joiner import EnvioParsed
from app.models.plantilla import Plantilla

_logger = logging.getLogger("mails_nico.smtp")

_DEFAULT_RATE_LIMIT = (5, 30.0)  # 5 mails, luego esperar 30 segundos


def _send_single_email(msg, from_email: str, app_password: str) -> str:
    context = ssl.create_default_context()
    with smtplib.SMTP("smtp.mail.yahoo.com", 587) as server:
        server.starttls(context=context)
        server.login(from_email, app_password)
        server.send_message(msg)
        return msg.get("Message-ID", "")


async def enviar_ciclo(
    envios: list[Envio],
    db: Session,
    on_progress: Callable[[Envio], Awaitable[None]],
    rate_limit_override: Optional[Tuple[int, float]] = None,
) -> None:
    plantilla = db_config.load_plantilla(db)
    batch_size, batch_wait = rate_limit_override or _DEFAULT_RATE_LIMIT
    from_email = settings.YAHOO_EMAIL
    app_password = settings.YAHOO_APP_PASSWORD

    sent_in_batch = 0
    for envio in envios:
        if sent_in_batch >= batch_size:
            _logger.info("Rate limit: esperando %.1f segundos", batch_wait)
            await asyncio.sleep(batch_wait)
            sent_in_batch = 0

        parsed = EnvioParsed(
            clave_union=envio.clave_union,
            nombre=envio.nombre_consorcio,
            email=envio.email,
            localidad=None,
            monto=envio.monto,
            ciclo_numero_anterior=envio.ciclo_numero - 1,
        )
        msg = generate_email(parsed, plantilla)
        msg["From"] = from_email
        import uuid
        msg_id = f"<{uuid.uuid4().hex}@yahoo.com>"
        msg["Message-ID"] = msg_id

        loop = asyncio.get_event_loop()
        try:
            returned_id = await loop.run_in_executor(
                None, _send_single_email, msg, from_email, app_password
            )
            envio.message_id = returned_id or msg_id
            envio.enviado_en = datetime.now(timezone.utc)
            db.add(envio)
            db.commit()
            sent_in_batch += 1
            await on_progress(envio)
            _logger.info("Enviado a %s (message_id=%s)", envio.email, envio.message_id)
        except Exception as exc:
            _logger.error("Error enviando a %s: %s", envio.email, exc)
```

- [ ] **Step 4: Correr tests**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_smtp_sender.py -v
```

Expected: todos PASS

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: smtp_sender con cola asyncio y rate limiting (5 mails / 30s)"
```

---

### Task 10: reply_classifier + imap_watcher

**Files:**
- Create: `backend/app/services/reply_classifier.py`
- Create: `backend/app/services/imap_watcher.py`
- Create: `backend/tests/test_reply_classifier.py`

**Interfaces:**
- Produces: `classify(msg: email.message.Message) -> EstadoEnvio`
- Produces: `async run_forever() -> None` — loop infinito, llamar con `asyncio.create_task()`

- [ ] **Step 1: Escribir tests del classifier**

```python
# backend/tests/test_reply_classifier.py
import email
from email.message import EmailMessage
from app.services.reply_classifier import classify
from app.models.envio import EstadoEnvio


def _make_msg(from_addr: str, has_attachment: bool = False, body: str = "Texto") -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["Subject"] = "Re: Recordatorio"
    msg.set_content(body)
    if has_attachment:
        msg.add_attachment(b"%PDF-1.4 fake", maintype="application", subtype="pdf", filename="comprobante.pdf")
    return msg


def test_mailer_daemon_es_rebotado():
    msg = _make_msg("mailer-daemon@yahoo.com")
    assert classify(msg) == EstadoEnvio.REBOTADO


def test_postmaster_es_rebotado():
    msg = _make_msg("postmaster@dominio.com")
    assert classify(msg) == EstadoEnvio.REBOTADO


def test_adjunto_pdf_es_pago():
    msg = _make_msg("consorcio@mail.com", has_attachment=True)
    assert classify(msg) == EstadoEnvio.PAGO


def test_adjunto_imagen_es_pago():
    msg = EmailMessage()
    msg["From"] = "consorcio@mail.com"
    msg.set_content("Adjunto comprobante")
    msg.add_attachment(b"fake-png", maintype="image", subtype="png", filename="pago.png")
    assert classify(msg) == EstadoEnvio.PAGO


def test_solo_texto_es_contestado():
    msg = _make_msg("consorcio@mail.com")
    assert classify(msg) == EstadoEnvio.CONTESTADO
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_reply_classifier.py -v
```

- [ ] **Step 3: Crear services/reply_classifier.py**

```python
import email.message
from app.models.envio import EstadoEnvio


def classify(msg: email.message.Message) -> EstadoEnvio:
    from_addr = str(msg.get("From", "")).lower()
    if "mailer-daemon" in from_addr or "postmaster" in from_addr:
        return EstadoEnvio.REBOTADO

    for part in msg.walk():
        ct = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in disposition or ct.startswith("image/") or ct == "application/pdf":
            return EstadoEnvio.PAGO

    return EstadoEnvio.CONTESTADO
```

- [ ] **Step 4: Correr tests del classifier**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_reply_classifier.py -v
```

Expected: todos PASS

- [ ] **Step 5: Crear services/imap_watcher.py**

```python
import asyncio
import email
import imaplib
import logging
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.envio import Envio, EstadoEnvio
from app.services.reply_classifier import classify

_logger = logging.getLogger("mails_nico.imap")
_POLL_INTERVAL = 600  # 10 minutos
_SEARCH_WINDOW_DAYS = 30


async def run_forever():
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(None, _poll_inbox)
        except Exception as exc:
            _logger.error("IMAP poll error: %s", exc)
        await asyncio.sleep(_POLL_INTERVAL)


def _poll_inbox():
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=_SEARCH_WINDOW_DAYS)
        active_envios = (
            db.query(Envio)
            .filter(
                Envio.message_id.isnot(None),
                Envio.estado == EstadoEnvio.NO_CONTESTADO,
                Envio.enviado_en >= cutoff,
            )
            .all()
        )
        if not active_envios:
            return

        message_id_map = {e.message_id: e for e in active_envios}

        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com", 993)
        mail.login(settings.YAHOO_EMAIL, settings.YAHOO_APP_PASSWORD)
        mail.select("INBOX")

        since_date = cutoff.strftime("%d-%b-%Y")
        _, data = mail.search(None, f'(SINCE "{since_date}")')
        msg_nums = data[0].split()

        for num in msg_nums:
            _, msg_data = mail.fetch(num, "(RFC822)")
            raw = msg_data[0][1]
            msg = email.message_from_bytes(raw)

            in_reply_to = msg.get("In-Reply-To", "").strip()
            references = msg.get("References", "").strip().split()

            matched_envio = message_id_map.get(in_reply_to)
            if matched_envio is None:
                for ref in references:
                    matched_envio = message_id_map.get(ref.strip())
                    if matched_envio:
                        break

            if matched_envio is None:
                continue

            new_estado = classify(msg)
            snippet = _extract_snippet(msg)
            matched_envio.estado = new_estado
            matched_envio.reply_snippet = snippet
            matched_envio.actualizado_en = datetime.now(timezone.utc)
            db.add(matched_envio)
            _logger.info("Envio %s → %s", matched_envio.id, new_estado)

        mail.logout()
        db.commit()
    finally:
        db.close()


def _extract_snippet(msg) -> str:
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                return payload.decode(errors="replace")[:200]
    return ""
```

- [ ] **Step 6: Agregar IMAP watcher al startup en main.py**

En `backend/app/main.py` agregar:

```python
import asyncio
from app.services import imap_watcher

# ...después de crear el app FastAPI:

@app.on_event("startup")
async def startup():
    asyncio.create_task(imap_watcher.run_forever())
```

- [ ] **Step 7: Correr todos los tests hasta ahora**

```bash
cd backend && venv\Scripts\python -m pytest -v
```

Expected: todos PASS (smtp y imap tests no se corren end-to-end en CI, solo el classifier)

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: reply_classifier + imap_watcher polling cada 10min"
```

---

### Task 11: Ciclos API — preview + confirmar + SSE + stub Fase 3

**Files:**
- Create: `backend/app/schemas/ciclo.py`
- Create: `backend/app/schemas/envio.py`
- Create: `backend/app/routers/ciclos.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_ciclos.py`

**Interfaces:**
- Produces: `POST /ciclos/preview` (multipart Excel) → `PreviewResponse`
- Produces: `POST /ciclos/confirmar` (multipart Excel) → `StreamingResponse` (SSE)
- Produces: `POST /ciclos/desde-api` → HTTP 501
- Produces: `GET /ciclos/activo/envios` → `list[EnvioSchema]`
- Produces: `PATCH /envios/{id}/estado` → `EnvioSchema` (manual override CONTESTADO→PAGO)

- [ ] **Step 1: Escribir tests**

```python
# backend/tests/test_ciclos.py
import io
import openpyxl
from app.models.cliente_maestro import ClienteMaestro
from decimal import Decimal


def _make_deudores_excel(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nro cliente", "nombre", "localidad", "monto"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _seed_cliente(db, clave, nombre, email):
    from datetime import datetime, timezone
    c = ClienteMaestro(
        clave_union=clave,
        nombre=nombre,
        email=email,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(c)
    db.flush()


def test_preview_retorna_conteos(client, auth_headers, db, plantilla_default):
    _seed_cliente(db, "C001", "Consorcio Uno", "uno@mail.com")
    _seed_cliente(db, "C002", "Consorcio Dos", None)
    excel = _make_deudores_excel([
        ["C001", "Consorcio Uno", "CABA", 5000],
        ["C002", "Consorcio Dos", "GBA", 2000],
        ["C999", "Desconocido", "CABA", 1000],
    ])
    r = client.post(
        "/ciclos/preview",
        files={"file": ("deudores.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["para_enviar"] == 1
    assert data["sin_email"] == 2
    assert data["filtrados"] == 0
    assert data["total_deudores"] == 3


def test_preview_no_escribe_en_db(client, auth_headers, db, plantilla_default):
    from app.models.ciclo import Ciclo
    before = db.query(Ciclo).count()
    excel = _make_deudores_excel([["C001", "Test", "CABA", 5000]])
    client.post(
        "/ciclos/preview",
        files={"file": ("d.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert db.query(Ciclo).count() == before


def test_desde_api_retorna_501(client, auth_headers):
    r = client.post("/ciclos/desde-api", json={"deudores": []}, headers=auth_headers)
    assert r.status_code == 501


def test_get_envios_activo_vacio_antes_de_confirmar(client, auth_headers):
    r = client.get("/ciclos/activo/envios", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_patch_envio_estado_contestado_a_pago(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id,
        ciclo_numero=1,
        clave_union="C001",
        nombre_consorcio="Test",
        email="t@mail.com",
        monto=Decimal("1000"),
        estado=EstadoEnvio.CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()
    r = client.patch(f"/envios/{envio.id}/estado", json={"estado": "PAGO"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["estado"] == "PAGO"
```

- [ ] **Step 2: Correr tests — deben fallar**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_ciclos.py -v
```

- [ ] **Step 3: Crear schemas/ciclo.py**

```python
from decimal import Decimal
from pydantic import BaseModel


class PreviewResponse(BaseModel):
    para_enviar: int
    sin_email: int
    filtrados: int
    total_deudores: int
    monto_total_enviar: Decimal
```

- [ ] **Step 4: Crear schemas/envio.py**

```python
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel
from app.models.envio import EstadoEnvio, MotivoFiltrado


class EnvioSchema(BaseModel):
    id: UUID
    ciclo_id: UUID
    ciclo_numero: int
    clave_union: str
    nombre_consorcio: str
    email: Optional[str]
    monto: Decimal
    estado: EstadoEnvio
    motivo_filtrado: Optional[MotivoFiltrado]
    message_id: Optional[str]
    reply_snippet: Optional[str]
    enviado_en: Optional[datetime]
    actualizado_en: datetime

    model_config = {"from_attributes": True}


class EstadoUpdateRequest(BaseModel):
    estado: EstadoEnvio
```

- [ ] **Step 5: Crear routers/ciclos.py**

```python
import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio, MotivoFiltrado
from app.models.user import User
from app.schemas.ciclo import PreviewResponse
from app.schemas.envio import EnvioSchema, EstadoUpdateRequest
from app.services import db_config
from app.services.excel_joiner import join_deudores
from app.services.excel_parser import parse_deudores, ExcelParseError
from app.services.smtp_sender import enviar_ciclo

router = APIRouter(tags=["ciclos"])
_logger = logging.getLogger("mails_nico.ciclos")


@router.post("/ciclos/preview", response_model=PreviewResponse)
async def preview_ciclo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        deudores = parse_deudores(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    plantilla = db_config.load_plantilla(db)
    preview = join_deudores(db, deudores, plantilla.monto_minimo)
    return PreviewResponse(
        para_enviar=len(preview.para_enviar),
        sin_email=len(preview.sin_email),
        filtrados=len(preview.filtrados),
        total_deudores=len(deudores),
        monto_total_enviar=sum(e.monto for e in preview.para_enviar),
    )


@router.post("/ciclos/confirmar")
async def confirmar_ciclo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = await file.read()
    try:
        deudores = parse_deudores(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    plantilla = db_config.load_plantilla(db)
    preview = join_deudores(db, deudores, plantilla.monto_minimo)

    ciclo_anterior = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if ciclo_anterior:
        ciclo_anterior.activo = False
        db.add(ciclo_anterior)

    ultimo_num = db.query(Ciclo).count()
    nuevo_ciclo = Ciclo(numero=ultimo_num + 1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(nuevo_ciclo)
    db.flush()

    envios_db = []
    for ep in preview.para_enviar:
        e = Envio(
            ciclo_id=nuevo_ciclo.id,
            ciclo_numero=nuevo_ciclo.numero,
            clave_union=ep.clave_union,
            nombre_consorcio=ep.nombre,
            email=ep.email,
            monto=ep.monto,
            estado=EstadoEnvio.NO_CONTESTADO,
            actualizado_en=datetime.now(timezone.utc),
        )
        db.add(e)
        envios_db.append(e)

    for deudor, motivo in preview.filtrados:
        e = Envio(
            ciclo_id=nuevo_ciclo.id,
            ciclo_numero=nuevo_ciclo.numero,
            clave_union=deudor.clave_union,
            nombre_consorcio=deudor.nombre,
            monto=deudor.monto,
            estado=EstadoEnvio.FILTRADO,
            motivo_filtrado=MotivoFiltrado[motivo],
            actualizado_en=datetime.now(timezone.utc),
        )
        db.add(e)

    for deudor in preview.sin_email:
        e = Envio(
            ciclo_id=nuevo_ciclo.id,
            ciclo_numero=nuevo_ciclo.numero,
            clave_union=deudor.clave_union,
            nombre_consorcio=deudor.nombre,
            monto=deudor.monto,
            estado=EstadoEnvio.SIN_EMAIL,
            actualizado_en=datetime.now(timezone.utc),
        )
        db.add(e)

    db.commit()
    for e in envios_db:
        db.refresh(e)

    async def event_generator():
        total = len(envios_db)
        sent = 0

        async def on_progress(envio: Envio):
            nonlocal sent
            sent += 1
            payload = json.dumps({"enviado": sent, "total": total, "id": str(envio.id)})
            yield f"data: {payload}\n\n"

        async for chunk in _stream_envios(envios_db, db, on_progress):
            yield chunk

        yield f"data: {json.dumps({'done': True, 'total': total})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _stream_envios(envios_db, db, on_progress):
    sent = 0
    total = len(envios_db)

    sse_queue: asyncio.Queue = asyncio.Queue()

    async def progress_callback(envio: Envio):
        nonlocal sent
        sent += 1
        payload = json.dumps({"enviado": sent, "total": total, "id": str(envio.id)})
        await sse_queue.put(f"data: {payload}\n\n")

    send_task = asyncio.create_task(enviar_ciclo(envios_db, db, progress_callback))

    while not send_task.done() or not sse_queue.empty():
        try:
            chunk = sse_queue.get_nowait()
            yield chunk
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.1)

    await send_task


@router.post("/ciclos/desde-api", status_code=501)
def desde_api(current_user: User = Depends(get_current_user)):
    raise HTTPException(status_code=501, detail="No implementado — Fase 3")


@router.get("/ciclos/activo/envios", response_model=list[EnvioSchema])
def get_envios_activo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ciclo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if not ciclo:
        return []
    return list(ciclo.envios)


@router.patch("/envios/{envio_id}/estado", response_model=EnvioSchema)
def update_envio_estado(
    envio_id: UUID,
    body: EstadoUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    envio = db.get(Envio, envio_id)
    if not envio:
        raise HTTPException(status_code=404, detail="Envio no encontrado")
    if envio.estado != EstadoEnvio.CONTESTADO or body.estado != EstadoEnvio.PAGO:
        raise HTTPException(status_code=400, detail="Solo se permite CONTESTADO → PAGO")
    envio.estado = EstadoEnvio.PAGO
    envio.actualizado_en = datetime.now(timezone.utc)
    db.add(envio)
    db.commit()
    db.refresh(envio)
    return envio
```

- [ ] **Step 6: Agregar router en main.py**

```python
from app.routers import auth, plantilla, maestro, ciclos
# ...
app.include_router(ciclos.router)
```

- [ ] **Step 7: Correr tests**

```bash
cd backend && venv\Scripts\python -m pytest tests/test_ciclos.py -v
```

Expected: todos PASS

- [ ] **Step 8: Correr suite completa**

```bash
cd backend && venv\Scripts\python -m pytest -v
```

Expected: todos PASS

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: ciclos API — preview/confirmar/SSE/desde-api stub + PATCH envio estado"
```

---

### Task 12: Frontend — limpieza y tipos de dominio

**Files:**
- Modify: `frontend/src/types/domain.ts`
- Modify: `frontend/src/services/api.ts`
- Modify: `frontend/src/services/auth.ts`
- Create: `frontend/src/services/ciclos.ts`
- Create: `frontend/src/services/maestro.ts`
- Create: `frontend/src/services/envios.ts`
- Create: `frontend/src/services/plantilla.ts` (ya existe, reemplazar)

**Interfaces:**
- Produces: tipos `Envio`, `Ciclo`, `PreviewCiclo`, `ClienteMaestro`, `Plantilla` en domain.ts
- Produces: servicios de API para cada entidad

- [ ] **Step 1: Reemplazar frontend/src/types/domain.ts**

```typescript
export type EstadoEnvio =
  | "NO_CONTESTADO"
  | "CONTESTADO"
  | "PAGO"
  | "REBOTADO"
  | "SIN_EMAIL"
  | "FILTRADO";

export type MotivoFiltrado = "MONTO_MINIMO" | "DADO_DE_BAJA";

export interface Envio {
  id: string;
  ciclo_id: string;
  ciclo_numero: number;
  clave_union: string;
  nombre_consorcio: string;
  email: string | null;
  monto: number;
  estado: EstadoEnvio;
  motivo_filtrado: MotivoFiltrado | null;
  message_id: string | null;
  reply_snippet: string | null;
  enviado_en: string | null;
  actualizado_en: string;
}

export interface PreviewCiclo {
  para_enviar: number;
  sin_email: number;
  filtrados: number;
  total_deudores: number;
  monto_total_enviar: number;
}

export interface ClienteMaestro {
  id: string;
  clave_union: string;
  nombre: string;
  email: string | null;
  localidad: string | null;
  prefiere_no_recibir_email: boolean;
  activo: boolean;
}

export interface Plantilla {
  asunto: string;
  cuerpo_html: string;
  nombre_empresa: string;
  logo_url: string | null;
  color_primario: string;
  monto_minimo: number;
}
```

- [ ] **Step 2: Verificar/actualizar frontend/src/services/api.ts**

El archivo debe exportar una función `apiFetch` que agrega el header Authorization. Si ya existe con esa forma, no modificar. Si no, reemplazar con:

```typescript
const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function apiFetch(path: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {
    ...(options.headers ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
  return fetch(`${BASE_URL}${path}`, { ...options, headers });
}
```

- [ ] **Step 3: Actualizar frontend/src/services/auth.ts**

```typescript
import { apiFetch } from "./api";

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const r = await apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw new Error("Credenciales inválidas");
  const data = await r.json();
  localStorage.setItem("access_token", data.access_token);
  localStorage.setItem("refresh_token", data.refresh_token);
  return data;
}

export async function logout(): Promise<void> {
  await apiFetch("/auth/logout", { method: "POST" });
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  const r = await apiFetch("/auth/change-password", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al cambiar contraseña");
  }
}
```

- [ ] **Step 4: Crear frontend/src/services/ciclos.ts**

```typescript
import { apiFetch } from "./api";
import type { Envio, PreviewCiclo } from "../types/domain";

export async function previewCiclo(file: File): Promise<PreviewCiclo> {
  const form = new FormData();
  form.append("file", file);
  const r = await apiFetch("/ciclos/preview", { method: "POST", body: form });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al procesar el Excel");
  }
  return r.json();
}

export function confirmarCiclo(
  file: File,
  onProgress: (data: { enviado: number; total: number; id?: string; done?: boolean }) => void,
): () => void {
  const form = new FormData();
  form.append("file", file);
  const token = localStorage.getItem("access_token");
  const controller = new AbortController();

  fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/ciclos/confirmar`, {
    method: "POST",
    body: form,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    signal: controller.signal,
  }).then(async (r) => {
    if (!r.ok || !r.body) return;
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          try {
            onProgress(JSON.parse(line.slice(6)));
          } catch {}
        }
      }
    }
  });

  return () => controller.abort();
}

export async function getEnviosActivo(): Promise<Envio[]> {
  const r = await apiFetch("/ciclos/activo/envios");
  if (!r.ok) throw new Error("Error cargando envíos");
  return r.json();
}
```

- [ ] **Step 5: Crear frontend/src/services/maestro.ts**

```typescript
import { apiFetch } from "./api";
import type { ClienteMaestro } from "../types/domain";

export async function uploadMaestro(file: File): Promise<{ nuevos: number; actualizados: number; total: number }> {
  const form = new FormData();
  form.append("file", file);
  const r = await apiFetch("/maestro/upload", { method: "POST", body: form });
  if (!r.ok) throw new Error("Error al subir maestro");
  return r.json();
}

export async function getMaestro(): Promise<ClienteMaestro[]> {
  const r = await apiFetch("/maestro");
  if (!r.ok) throw new Error("Error cargando maestro");
  return r.json();
}
```

- [ ] **Step 6: Crear frontend/src/services/envios.ts**

```typescript
import { apiFetch } from "./api";
import type { Envio } from "../types/domain";

export async function patchEnvioEstado(id: string, estado: "PAGO"): Promise<Envio> {
  const r = await apiFetch(`/envios/${id}/estado`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ estado }),
  });
  if (!r.ok) throw new Error("Error actualizando estado");
  return r.json();
}
```

- [ ] **Step 7: Reemplazar frontend/src/services/plantilla.ts**

```typescript
import { apiFetch } from "./api";
import type { Plantilla } from "../types/domain";

export async function getPlantilla(): Promise<Plantilla> {
  const r = await apiFetch("/plantilla");
  if (!r.ok) throw new Error("Error cargando plantilla");
  return r.json();
}

export async function updatePlantilla(data: Plantilla): Promise<Plantilla> {
  const r = await apiFetch("/plantilla", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) throw new Error("Error guardando plantilla");
  return r.json();
}
```

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "feat: domain types y servicios API (ciclos, maestro, envios, plantilla)"
```

---

### Task 13: Frontend — hooks + LoginPage simplificado

**Files:**
- Modify: `frontend/src/hooks/useAuth.ts`
- Create: `frontend/src/hooks/useCiclo.ts`
- Create: `frontend/src/hooks/useEnvios.ts`
- Modify: `frontend/src/pages/LoginPage.tsx`

**Interfaces:**
- Produces: `useAuth()` → `{ user, login, logout, isAuthenticated }`
- Produces: `useCiclo()` → `{ enviosActivo, previewData, preview, confirmar, isLoading }`
- Produces: `useEnvios()` → `{ envios, patchEstado }`

- [ ] **Step 1: Reemplazar hooks/useAuth.ts**

```typescript
import { useState, useCallback } from "react";
import { login as apiLogin, logout as apiLogout } from "../services/auth";

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!localStorage.getItem("access_token"));

  const login = useCallback(async (username: string, password: string) => {
    await apiLogin(username, password);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(async () => {
    await apiLogout();
    setIsAuthenticated(false);
  }, []);

  return { isAuthenticated, login, logout };
}
```

- [ ] **Step 2: Crear hooks/useCiclo.ts**

```typescript
import { useState, useCallback } from "react";
import { previewCiclo, confirmarCiclo, getEnviosActivo } from "../services/ciclos";
import type { Envio, PreviewCiclo } from "../types/domain";

export function useCiclo() {
  const [enviosActivo, setEnviosActivo] = useState<Envio[]>([]);
  const [previewData, setPreviewData] = useState<PreviewCiclo | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [progreso, setProgreso] = useState<{ enviado: number; total: number } | null>(null);

  const loadEnviosActivo = useCallback(async () => {
    const data = await getEnviosActivo();
    setEnviosActivo(data);
  }, []);

  const preview = useCallback(async (file: File) => {
    setIsLoading(true);
    try {
      const data = await previewCiclo(file);
      setPreviewData(data);
      return data;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const confirmar = useCallback(
    async (file: File, onDone?: () => void) => {
      setIsLoading(true);
      setProgreso({ enviado: 0, total: 0 });
      const cancel = confirmarCiclo(file, (data) => {
        if (data.done) {
          setIsLoading(false);
          loadEnviosActivo();
          onDone?.();
        } else {
          setProgreso({ enviado: data.enviado, total: data.total });
        }
      });
      return cancel;
    },
    [loadEnviosActivo],
  );

  return { enviosActivo, previewData, preview, confirmar, isLoading, progreso, loadEnviosActivo };
}
```

- [ ] **Step 3: Crear hooks/useEnvios.ts**

```typescript
import { useState, useCallback } from "react";
import { patchEnvioEstado } from "../services/envios";
import type { Envio } from "../types/domain";

export function useEnvios(initialEnvios: Envio[]) {
  const [envios, setEnvios] = useState<Envio[]>(initialEnvios);

  const patchEstado = useCallback(async (id: string, estado: "PAGO") => {
    const updated = await patchEnvioEstado(id, estado);
    setEnvios((prev) => prev.map((e) => (e.id === id ? updated : e)));
    return updated;
  }, []);

  return { envios, setEnvios, patchEstado };
}
```

- [ ] **Step 4: Reemplazar pages/LoginPage.tsx**

```tsx
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(username, password);
      navigate("/nuevo-envio");
    } catch {
      setError("Usuario o contraseña incorrectos");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle className="text-center">Sistema de Cobro</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Input
              placeholder="Usuario"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
            />
            <Input
              type="password"
              placeholder="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            {error && <p className="text-sm text-red-600">{error}</p>}
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "Ingresando..." : "Ingresar"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: useAuth/useCiclo/useEnvios hooks + LoginPage sin 2FA"
```

---

### Task 14: Frontend — Nuevo Envío (upload preview + confirmar + progreso)

**Files:**
- Create: `frontend/src/pages/NuevoEnvioPage.tsx`
- Create: `frontend/src/components/upload/ExcelUploadModal.tsx` (reemplazar existente)
- Create: `frontend/src/components/upload/ProgresoEnvio.tsx`

**Interfaces:**
- Consumes: `useCiclo()` de hooks/useCiclo
- Produces: flujo completo: subir Excel → ver preview → confirmar → barra de progreso SSE

- [ ] **Step 1: Crear components/upload/ProgresoEnvio.tsx**

```tsx
interface ProgresoEnvioProps {
  enviado: number;
  total: number;
}

export function ProgresoEnvio({ enviado, total }: ProgresoEnvioProps) {
  const pct = total > 0 ? Math.round((enviado / total) * 100) : 0;
  return (
    <div className="w-full space-y-2">
      <div className="flex justify-between text-sm text-gray-600">
        <span>Enviando mails...</span>
        <span>{enviado} / {total}</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-3">
        <div
          className="bg-blue-600 h-3 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-gray-500 text-right">{pct}% completado</p>
    </div>
  );
}
```

- [ ] **Step 2: Reemplazar components/upload/ExcelUploadModal.tsx**

```tsx
import { useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import type { PreviewCiclo } from "../../types/domain";

interface Props {
  open: boolean;
  onClose: () => void;
  onPreview: (file: File) => Promise<PreviewCiclo>;
  onConfirmar: (file: File) => void;
  isLoading: boolean;
}

export function ExcelUploadModal({ open, onClose, onPreview, onConfirmar, isLoading }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewCiclo | null>(null);
  const [error, setError] = useState("");

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setPreview(null);
    setError("");
  }

  async function handlePreview() {
    if (!file) return;
    setError("");
    try {
      const data = await onPreview(file);
      setPreview(data);
    } catch (e: any) {
      setError(e.message ?? "Error al procesar");
    }
  }

  function handleConfirmar() {
    if (!file) return;
    onConfirmar(file);
    onClose();
  }

  function handleClose() {
    setFile(null);
    setPreview(null);
    setError("");
    onClose();
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Nuevo Ciclo de Envío</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <input
            ref={inputRef}
            type="file"
            accept=".xlsx,.xls"
            className="hidden"
            onChange={handleFileChange}
          />
          <Button variant="outline" className="w-full" onClick={() => inputRef.current?.click()}>
            {file ? file.name : "Seleccionar Excel de deudores"}
          </Button>

          {file && !preview && (
            <Button className="w-full" onClick={handlePreview} disabled={isLoading}>
              {isLoading ? "Procesando..." : "Ver preview"}
            </Button>
          )}

          {error && <p className="text-sm text-red-600">{error}</p>}

          {preview && (
            <div className="rounded border p-4 space-y-2 bg-gray-50">
              <h3 className="font-semibold text-sm">Resumen del ciclo</h3>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <span className="text-gray-600">Para enviar:</span>
                <span className="font-medium text-green-700">{preview.para_enviar}</span>
                <span className="text-gray-600">Sin email:</span>
                <span className="font-medium text-amber-600">{preview.sin_email}</span>
                <span className="text-gray-600">Filtrados:</span>
                <span className="font-medium text-gray-500">{preview.filtrados}</span>
                <span className="text-gray-600">Total deudores:</span>
                <span className="font-medium">{preview.total_deudores}</span>
              </div>
              <div className="flex gap-2 pt-2">
                <Button variant="outline" className="flex-1" onClick={() => setPreview(null)}>
                  Volver
                </Button>
                <Button className="flex-1" onClick={handleConfirmar}>
                  Confirmar envío
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 3: Crear pages/NuevoEnvioPage.tsx**

```tsx
import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Button } from "../components/ui/button";
import { ExcelUploadModal } from "../components/upload/ExcelUploadModal";
import { ProgresoEnvio } from "../components/upload/ProgresoEnvio";
import { useCiclo } from "../hooks/useCiclo";
import type { Envio } from "../types/domain";

export default function NuevoEnvioPage() {
  const { enviosActivo, preview, confirmar, isLoading, progreso, loadEnviosActivo } = useCiclo();
  const [modalOpen, setModalOpen] = useState(false);

  useEffect(() => {
    loadEnviosActivo();
  }, [loadEnviosActivo]);

  const paraEnviar = enviosActivo.filter((e) => e.estado === "NO_CONTESTADO" && e.email);
  const sinEmail = enviosActivo.filter((e) => e.estado === "SIN_EMAIL");
  const filtrados = enviosActivo.filter((e) => e.estado === "FILTRADO");

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Nuevo Envío</h1>
        <Button onClick={() => setModalOpen(true)}>Subir Excel de deudores</Button>
      </div>

      {progreso && isLoading && (
        <div className="rounded border p-4 bg-blue-50">
          <ProgresoEnvio enviado={progreso.enviado} total={progreso.total} />
        </div>
      )}

      <Tabs defaultValue="para_enviar">
        <TabsList>
          <TabsTrigger value="para_enviar">Para enviar ({paraEnviar.length})</TabsTrigger>
          <TabsTrigger value="sin_email">Sin Email ({sinEmail.length})</TabsTrigger>
          <TabsTrigger value="filtrados">Filtrados ({filtrados.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="para_enviar">
          <EnvioTable envios={paraEnviar} />
        </TabsContent>
        <TabsContent value="sin_email">
          <EnvioTable envios={sinEmail} />
        </TabsContent>
        <TabsContent value="filtrados">
          <EnvioTable envios={filtrados} showMotivo />
        </TabsContent>
      </Tabs>

      <ExcelUploadModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onPreview={preview}
        onConfirmar={(file) => confirmar(file)}
        isLoading={isLoading}
      />
    </div>
  );
}

function EnvioTable({ envios, showMotivo }: { envios: Envio[]; showMotivo?: boolean }) {
  if (envios.length === 0) {
    return <p className="text-sm text-gray-500 py-4">Sin registros en esta categoría.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-left text-gray-600">
            <th className="py-2 pr-4">Consorcio</th>
            <th className="py-2 pr-4">Email</th>
            <th className="py-2 pr-4">Monto</th>
            {showMotivo && <th className="py-2">Motivo</th>}
          </tr>
        </thead>
        <tbody>
          {envios.map((e) => (
            <tr key={e.id} className="border-b hover:bg-gray-50">
              <td className="py-2 pr-4">{e.nombre_consorcio}</td>
              <td className="py-2 pr-4 text-gray-600">{e.email ?? "—"}</td>
              <td className="py-2 pr-4">${Number(e.monto).toLocaleString("es-AR")}</td>
              {showMotivo && <td className="py-2 text-xs text-gray-500">{e.motivo_filtrado ?? "—"}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: NuevoEnvioPage con flujo preview→confirmar y barra de progreso SSE"
```

---

### Task 15: Frontend — Seguimiento (4 solapas)

**Files:**
- Create: `frontend/src/pages/SeguimientoPage.tsx`
- Create: `frontend/src/components/envios/EnvioCard.tsx`
- Create: `frontend/src/components/envios/EnvioDrawer.tsx`

**Interfaces:**
- Consumes: `getEnviosActivo()`, `patchEnvioEstado()`
- Produces: 4 solapas: No contestados / Contestados / Pagos / Rebotados; drawer con detalle y botón override CONTESTADO→PAGO

- [ ] **Step 1: Crear components/envios/EnvioCard.tsx**

```tsx
import type { Envio } from "../../types/domain";

const ESTADO_BADGE: Record<string, string> = {
  NO_CONTESTADO: "bg-yellow-100 text-yellow-800",
  CONTESTADO: "bg-blue-100 text-blue-800",
  PAGO: "bg-green-100 text-green-800",
  REBOTADO: "bg-red-100 text-red-800",
};

interface Props {
  envio: Envio;
  onClick: () => void;
}

export function EnvioCard({ envio, onClick }: Props) {
  return (
    <div
      className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-medium">{envio.nombre_consorcio}</p>
          <p className="text-sm text-gray-500">{envio.email ?? "Sin email"}</p>
        </div>
        <div className="text-right">
          <p className="font-semibold">${Number(envio.monto).toLocaleString("es-AR")}</p>
          <span className={`text-xs px-2 py-0.5 rounded-full ${ESTADO_BADGE[envio.estado] ?? ""}`}>
            {envio.estado.replace("_", " ")}
          </span>
        </div>
      </div>
      {envio.reply_snippet && (
        <p className="text-xs text-gray-400 mt-2 line-clamp-1">{envio.reply_snippet}</p>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Crear components/envios/EnvioDrawer.tsx**

```tsx
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "../ui/sheet";
import { Button } from "../ui/button";
import type { Envio } from "../../types/domain";

interface Props {
  envio: Envio | null;
  onClose: () => void;
  onMarcarPago: (id: string) => void;
}

export function EnvioDrawer({ envio, onClose, onMarcarPago }: Props) {
  if (!envio) return null;

  return (
    <Sheet open={!!envio} onOpenChange={onClose}>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>{envio.nombre_consorcio}</SheetTitle>
        </SheetHeader>
        <div className="mt-4 space-y-3 text-sm">
          <Row label="Email" value={envio.email ?? "—"} />
          <Row label="Monto" value={`$${Number(envio.monto).toLocaleString("es-AR")}`} />
          <Row label="Estado" value={envio.estado.replace("_", " ")} />
          <Row label="Ciclo #" value={String(envio.ciclo_numero)} />
          {envio.enviado_en && (
            <Row label="Enviado" value={new Date(envio.enviado_en).toLocaleString("es-AR")} />
          )}
          {envio.reply_snippet && (
            <div>
              <p className="text-gray-500 mb-1">Respuesta:</p>
              <p className="bg-gray-50 rounded p-2 text-xs whitespace-pre-wrap">{envio.reply_snippet}</p>
            </div>
          )}
          {envio.estado === "CONTESTADO" && (
            <Button className="w-full mt-4" onClick={() => { onMarcarPago(envio.id); onClose(); }}>
              Marcar como PAGO
            </Button>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  );
}
```

- [ ] **Step 3: Crear pages/SeguimientoPage.tsx**

```tsx
import { useEffect, useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { EnvioCard } from "../components/envios/EnvioCard";
import { EnvioDrawer } from "../components/envios/EnvioDrawer";
import { getEnviosActivo } from "../services/ciclos";
import { patchEnvioEstado } from "../services/envios";
import type { Envio } from "../types/domain";

export default function SeguimientoPage() {
  const [envios, setEnvios] = useState<Envio[]>([]);
  const [selected, setSelected] = useState<Envio | null>(null);

  useEffect(() => {
    getEnviosActivo().then(setEnvios).catch(console.error);
  }, []);

  async function marcarPago(id: string) {
    const updated = await patchEnvioEstado(id, "PAGO");
    setEnvios((prev) => prev.map((e) => (e.id === id ? updated : e)));
  }

  const noContestados = envios.filter((e) => e.estado === "NO_CONTESTADO");
  const contestados = envios.filter((e) => e.estado === "CONTESTADO");
  const pagos = envios.filter((e) => e.estado === "PAGO");
  const rebotados = envios.filter((e) => e.estado === "REBOTADO");

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-2xl font-bold">Seguimiento</h1>

      <Tabs defaultValue="no_contestados">
        <TabsList>
          <TabsTrigger value="no_contestados">No contestados ({noContestados.length})</TabsTrigger>
          <TabsTrigger value="contestados">Contestados ({contestados.length})</TabsTrigger>
          <TabsTrigger value="pagos">Pagos ({pagos.length})</TabsTrigger>
          <TabsTrigger value="rebotados">Rebotados ({rebotados.length})</TabsTrigger>
        </TabsList>

        {(["no_contestados", "contestados", "pagos", "rebotados"] as const).map((tab) => {
          const list =
            tab === "no_contestados" ? noContestados
            : tab === "contestados" ? contestados
            : tab === "pagos" ? pagos
            : rebotados;
          return (
            <TabsContent key={tab} value={tab}>
              <div className="space-y-2 mt-2">
                {list.length === 0 ? (
                  <p className="text-sm text-gray-500 py-4">Sin registros.</p>
                ) : (
                  list.map((e) => (
                    <EnvioCard key={e.id} envio={e} onClick={() => setSelected(e)} />
                  ))
                )}
              </div>
            </TabsContent>
          );
        })}
      </Tabs>

      <EnvioDrawer
        envio={selected}
        onClose={() => setSelected(null)}
        onMarcarPago={marcarPago}
      />
    </div>
  );
}
```

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: SeguimientoPage con 4 solapas y drawer para override CONTESTADO→PAGO"
```

---

### Task 16: Frontend — Sidebar, App routing, páginas de soporte

**Files:**
- Modify: `frontend/src/components/layout/Sidebar.tsx`
- Modify: `frontend/src/components/layout/AppLayout.tsx`
- Modify: `frontend/src/components/layout/AuthGuard.tsx`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/MaestroPage.tsx`
- Create: `frontend/src/pages/PlantillaPage.tsx`
- Create: `frontend/src/pages/ConfiguracionPage.tsx`

**Interfaces:**
- Produces: rutas `/login`, `/nuevo-envio`, `/seguimiento`, `/maestro`, `/plantilla`, `/configuracion`
- Produces: sidebar con secciones "Seguimiento" y "Gestión"

- [ ] **Step 1: Reemplazar components/layout/Sidebar.tsx**

```tsx
import { Link, useLocation } from "react-router-dom";
import { cn } from "../../lib/utils";

const NAV = [
  { section: "Principal", items: [
    { to: "/nuevo-envio", label: "Nuevo Envío" },
    { to: "/seguimiento", label: "Seguimiento" },
  ]},
  { section: "Gestión", items: [
    { to: "/maestro", label: "Maestro de Clientes" },
    { to: "/plantilla", label: "Plantilla de Mail" },
    { to: "/configuracion", label: "Configuración" },
  ]},
];

export function Sidebar() {
  const { pathname } = useLocation();
  return (
    <aside className="w-56 border-r bg-white h-screen flex flex-col">
      <div className="p-4 border-b">
        <p className="font-semibold text-sm">Sistema de Cobro</p>
      </div>
      <nav className="flex-1 overflow-y-auto p-2 space-y-4">
        {NAV.map(({ section, items }) => (
          <div key={section}>
            <p className="text-xs font-semibold text-gray-400 uppercase px-2 mb-1">{section}</p>
            {items.map(({ to, label }) => (
              <Link
                key={to}
                to={to}
                className={cn(
                  "block px-3 py-2 rounded text-sm transition-colors",
                  pathname === to
                    ? "bg-blue-50 text-blue-700 font-medium"
                    : "text-gray-700 hover:bg-gray-100",
                )}
              >
                {label}
              </Link>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 2: Reemplazar components/layout/AuthGuard.tsx**

```tsx
import { Navigate } from "react-router-dom";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem("access_token");
  if (!token) return <Navigate to="/login" replace />;
  return <>{children}</>;
}
```

- [ ] **Step 3: Reemplazar components/layout/AppLayout.tsx**

```tsx
import { Outlet } from "react-router-dom";
import { Sidebar } from "./Sidebar";
import { ErrorBoundary } from "./ErrorBoundary";

export function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <main className="flex-1 overflow-y-auto bg-gray-50">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
    </div>
  );
}
```

- [ ] **Step 4: Crear pages/MaestroPage.tsx**

```tsx
import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { getMaestro, uploadMaestro } from "../services/maestro";
import type { ClienteMaestro } from "../types/domain";

export default function MaestroPage() {
  const [clientes, setClientes] = useState<ClienteMaestro[]>([]);
  const [status, setStatus] = useState("");

  useEffect(() => {
    getMaestro().then(setClientes).catch(console.error);
  }, []);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus("Subiendo...");
    try {
      const r = await uploadMaestro(file);
      setStatus(`Listo: ${r.nuevos} nuevos, ${r.actualizados} actualizados`);
      getMaestro().then(setClientes);
    } catch {
      setStatus("Error al subir el archivo");
    }
  }

  return (
    <div className="p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Maestro de Clientes</h1>
        <label>
          <input type="file" accept=".xlsx,.xls" className="hidden" onChange={handleUpload} />
          <Button asChild><span>Actualizar Maestro</span></Button>
        </label>
      </div>
      {status && <p className="text-sm text-gray-600">{status}</p>}
      <p className="text-sm text-gray-500">{clientes.length} clientes registrados</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b text-left text-gray-600">
              <th className="py-2 pr-4">Clave</th>
              <th className="py-2 pr-4">Nombre</th>
              <th className="py-2 pr-4">Email</th>
              <th className="py-2">Baja</th>
            </tr>
          </thead>
          <tbody>
            {clientes.map((c) => (
              <tr key={c.id} className="border-b hover:bg-gray-50">
                <td className="py-2 pr-4 font-mono text-xs">{c.clave_union}</td>
                <td className="py-2 pr-4">{c.nombre}</td>
                <td className="py-2 pr-4 text-gray-600">{c.email ?? "—"}</td>
                <td className="py-2">{c.prefiere_no_recibir_email ? "Sí" : "No"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Crear pages/PlantillaPage.tsx**

```tsx
import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { getPlantilla, updatePlantilla } from "../services/plantilla";
import type { Plantilla } from "../types/domain";

const DEFAULTS: Plantilla = {
  asunto: "Recordatorio de deuda",
  cuerpo_html: "<p>Estimado <strong>{{nombre}}</strong>,</p><p>Le informamos que registra una deuda con nuestra empresa. Quedo a disposición ante cualquier consulta.</p>",
  nombre_empresa: "",
  logo_url: null,
  color_primario: "#1a56db",
  monto_minimo: 0,
};

export default function PlantillaPage() {
  const [form, setForm] = useState<Plantilla>(DEFAULTS);
  const [status, setStatus] = useState("");

  useEffect(() => {
    getPlantilla().then(setForm).catch(console.error);
  }, []);

  function set(field: keyof Plantilla, value: string | number) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSave() {
    setStatus("Guardando...");
    try {
      await updatePlantilla(form);
      setStatus("Guardado correctamente");
    } catch {
      setStatus("Error al guardar");
    }
  }

  return (
    <div className="p-6 max-w-2xl space-y-4">
      <h1 className="text-2xl font-bold">Plantilla de Mail</h1>
      <div className="space-y-3">
        <label className="block text-sm font-medium">Asunto</label>
        <Input value={form.asunto} onChange={(e) => set("asunto", e.target.value)} />

        <label className="block text-sm font-medium">Cuerpo HTML</label>
        <p className="text-xs text-gray-500">
          Variables: {"{{nombre}}"}, {"{{monto}}"}, {"{{localidad}}"}, {"{{clave_union}}"}, {"{{fecha_envio}}"}
        </p>
        <Textarea
          rows={8}
          value={form.cuerpo_html}
          onChange={(e) => set("cuerpo_html", e.target.value)}
          className="font-mono text-sm"
        />

        <label className="block text-sm font-medium">Nombre empresa</label>
        <Input value={form.nombre_empresa} onChange={(e) => set("nombre_empresa", e.target.value)} />

        <label className="block text-sm font-medium">Color primario (hex)</label>
        <div className="flex gap-2 items-center">
          <input type="color" value={form.color_primario} onChange={(e) => set("color_primario", e.target.value)} />
          <Input value={form.color_primario} onChange={(e) => set("color_primario", e.target.value)} className="w-32" />
        </div>

        <label className="block text-sm font-medium">Monto mínimo de envío ($)</label>
        <Input
          type="number"
          value={form.monto_minimo}
          onChange={(e) => set("monto_minimo", Number(e.target.value))}
        />
      </div>
      {status && <p className="text-sm text-gray-600">{status}</p>}
      <Button onClick={handleSave}>Guardar plantilla</Button>
    </div>
  );
}
```

- [ ] **Step 6: Crear pages/ConfiguracionPage.tsx**

```tsx
import { useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { changePassword } from "../services/auth";

export default function ConfiguracionPage() {
  const [oldPass, setOldPass] = useState("");
  const [newPass, setNewPass] = useState("");
  const [status, setStatus] = useState("");

  async function handleChange() {
    setStatus("Cambiando...");
    try {
      await changePassword(oldPass, newPass);
      setStatus("Contraseña cambiada correctamente");
      setOldPass("");
      setNewPass("");
    } catch (e: any) {
      setStatus(e.message ?? "Error");
    }
  }

  return (
    <div className="p-6 max-w-sm space-y-4">
      <h1 className="text-2xl font-bold">Configuración</h1>
      <div className="space-y-3">
        <label className="block text-sm font-medium">Contraseña actual</label>
        <Input type="password" value={oldPass} onChange={(e) => setOldPass(e.target.value)} />
        <label className="block text-sm font-medium">Nueva contraseña</label>
        <Input type="password" value={newPass} onChange={(e) => setNewPass(e.target.value)} />
      </div>
      {status && <p className="text-sm text-gray-600">{status}</p>}
      <Button onClick={handleChange}>Cambiar contraseña</Button>
    </div>
  );
}
```

- [ ] **Step 7: Reemplazar App.tsx**

```tsx
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout/AppLayout";
import { AuthGuard } from "./components/layout/AuthGuard";
import LoginPage from "./pages/LoginPage";
import NuevoEnvioPage from "./pages/NuevoEnvioPage";
import SeguimientoPage from "./pages/SeguimientoPage";
import MaestroPage from "./pages/MaestroPage";
import PlantillaPage from "./pages/PlantillaPage";
import ConfiguracionPage from "./pages/ConfiguracionPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          element={
            <AuthGuard>
              <AppLayout />
            </AuthGuard>
          }
        >
          <Route path="/nuevo-envio" element={<NuevoEnvioPage />} />
          <Route path="/seguimiento" element={<SeguimientoPage />} />
          <Route path="/maestro" element={<MaestroPage />} />
          <Route path="/plantilla" element={<PlantillaPage />} />
          <Route path="/configuracion" element={<ConfiguracionPage />} />
          <Route path="/" element={<Navigate to="/nuevo-envio" replace />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
```

- [ ] **Step 8: Verificar que el frontend compila**

```bash
cd frontend && npm run build
```

Expected: sin errores de TypeScript ni de bundling.

- [ ] **Step 9: Commit final**

```bash
git add -A
git commit -m "feat: frontend completo — sidebar, routing, Maestro/Plantilla/Configuracion pages"
```

---

## Notas de despliegue

1. Configurar `backend/.env` con `DATABASE_URL`, `SECRET_KEY`, `YAHOO_EMAIL`, `YAHOO_APP_PASSWORD`
2. Correr `alembic upgrade head` para crear las tablas
3. Correr `python backend/scripts/seed_user.py` para crear el usuario operario
4. Cambiar la contraseña inicial desde `/configuracion`
5. Subir el Excel maestro desde `/maestro` antes del primer ciclo
6. Configurar la plantilla desde `/plantilla`

## Pendientes bloqueantes (antes del primer ciclo real)

- [ ] Columnas exactas del Excel de deudores del cliente → agregar aliases en `excel_parser.py:DEUDOR_ALIASES`
- [ ] Columnas exactas del Excel maestro → agregar aliases en `excel_parser.py:MAESTRO_ALIASES`
- [ ] App password de Yahoo del cliente → configurar en `.env`

