# Proveedor de Email Configurable (Yahoo/Gmail) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que el Operario elija desde la página de Configuración qué proveedor de mail (Yahoo o Gmail) usa el sistema para enviar y trackear respuestas, guardando ambas credenciales en DB, sin cambiar el comportamiento actual de Yahoo cuando nadie toca nada.

**Architecture:** Un registro estático de dos proveedores (`app/core/email_providers.py`) provee host/puerto SMTP e IMAP. `ConfiguracionSistema` gana un campo `proveedor_activo` + credenciales de Gmail. `config_service.py` expone un dispatcher (`get_active_provider`, `get_active_credentials`) que `smtp_sender.py` e `imap_watcher.py` consultan en cada envío/poll en vez de tener Yahoo hardcodeado. Se agregan 3 endpoints REST (`/configuracion/proveedor`, `/configuracion/gmail`) y un selector en `ConfiguracionPage.tsx`.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic, pytest, React 18 + TypeScript, Vite.

## Global Constraints

- Yahoo debe seguir funcionando exactamente igual si nadie configura nada (`proveedor_activo` default `"yahoo"`).
- Ninguna función existente de `config_service.py` relacionada a Yahoo se modifica (`get_yahoo_credentials`, `save_yahoo_credentials`, `load_config`).
- El endpoint `/configuracion/yahoo` no cambia su contrato.
- Migraciones Alembic usan `batch_alter_table` (compatibilidad SQLite/Postgres), según convención del proyecto.
- Credenciales de Gmail se cifran con el mismo Fernet (`ENCRYPTION_KEY`) que ya usa Yahoo.
- Tests backend: `cd backend && venv\Scripts\python -m pytest -v`.
- Tests frontend: no existe infraestructura de tests automatizados (no hay Vitest/RTL configurado); la verificación de los cambios de frontend es `cd frontend && npm run build` (typecheck + build) más verificación manual en el navegador.

---

### Task 1: Registro estático de proveedores

**Files:**
- Create: `backend/app/core/email_providers.py`
- Test: `backend/tests/test_email_providers.py`

**Interfaces:**
- Produces: `ProviderConfig` (dataclass: `smtp_host: str, smtp_port: int, imap_host: str, imap_port: int, message_id_domain: str`), `PROVIDERS: dict[str, ProviderConfig]` con claves `"yahoo"` y `"gmail"`, `DEFAULT_PROVIDER: str = "yahoo"`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_email_providers.py`:

```python
import pytest
from app.core.email_providers import PROVIDERS, DEFAULT_PROVIDER, ProviderConfig


def test_default_provider_is_yahoo():
    assert DEFAULT_PROVIDER == "yahoo"


def test_providers_has_yahoo_and_gmail():
    assert set(PROVIDERS.keys()) == {"yahoo", "gmail"}


def test_yahoo_provider_config_matches_current_hardcoded_values():
    yahoo = PROVIDERS["yahoo"]
    assert yahoo.smtp_host == "smtp.mail.yahoo.com"
    assert yahoo.smtp_port == 587
    assert yahoo.imap_host == "imap.mail.yahoo.com"
    assert yahoo.imap_port == 993
    assert yahoo.message_id_domain == "yahoo.com"


def test_gmail_provider_config():
    gmail = PROVIDERS["gmail"]
    assert gmail.smtp_host == "smtp.gmail.com"
    assert gmail.smtp_port == 587
    assert gmail.imap_host == "imap.gmail.com"
    assert gmail.imap_port == 993
    assert gmail.message_id_domain == "gmail.com"


def test_provider_config_is_frozen():
    yahoo = PROVIDERS["yahoo"]
    with pytest.raises(Exception):
        yahoo.smtp_host = "changed"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_email_providers.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.core.email_providers'`

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/core/email_providers.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderConfig:
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    message_id_domain: str


PROVIDERS: dict[str, ProviderConfig] = {
    "yahoo": ProviderConfig(
        smtp_host="smtp.mail.yahoo.com",
        smtp_port=587,
        imap_host="imap.mail.yahoo.com",
        imap_port=993,
        message_id_domain="yahoo.com",
    ),
    "gmail": ProviderConfig(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        imap_host="imap.gmail.com",
        imap_port=993,
        message_id_domain="gmail.com",
    ),
}

DEFAULT_PROVIDER = "yahoo"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_email_providers.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/email_providers.py backend/tests/test_email_providers.py
git commit -m "feat: agregar registro estatico de proveedores de email (yahoo/gmail)"
```

---

### Task 2: Modelo, migración y funciones de `config_service.py`

**Files:**
- Modify: `backend/app/models/configuracion_sistema.py`
- Modify: `backend/app/core/config.py`
- Create: `backend/alembic/versions/0004_proveedor_email.py`
- Modify: `backend/app/services/config_service.py`
- Modify: `backend/tests/test_config_service.py`

**Interfaces:**
- Consumes: `PROVIDERS`, `DEFAULT_PROVIDER` de `app.core.email_providers` (Task 1).
- Produces: `config_service.get_active_provider(db: Session) -> str`, `config_service.save_active_provider(db: Session, proveedor: str) -> ConfiguracionSistema`, `config_service.get_gmail_credentials(db: Session) -> tuple[str, str]`, `config_service.save_gmail_credentials(db: Session, gmail_email: str, gmail_app_password: str) -> ConfiguracionSistema`, `config_service.get_active_credentials(db: Session) -> tuple[str, str]`.

- [ ] **Step 1: Modify the model**

En `backend/app/models/configuracion_sistema.py`, reemplazar el contenido completo por:

```python
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base


class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"
    id = Column(Integer, primary_key=True, default=1)
    proveedor_activo = Column(String(20), nullable=False, default="yahoo")
    yahoo_email = Column(String(255), nullable=True)
    yahoo_app_password_encrypted = Column(String(512), nullable=True)
    gmail_email = Column(String(255), nullable=True)
    gmail_app_password_encrypted = Column(String(512), nullable=True)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

- [ ] **Step 2: Add Gmail settings to config.py**

En `backend/app/core/config.py`, insertar después de la línea `YAHOO_APP_PASSWORD: str`:

```python
    GMAIL_EMAIL: str = ""
    GMAIL_APP_PASSWORD: str = ""
```

El archivo completo queda:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ENCRYPTION_KEY: str
    YAHOO_EMAIL: str
    YAHOO_APP_PASSWORD: str
    GMAIL_EMAIL: str = ""
    GMAIL_APP_PASSWORD: str = ""
    ACCESS_TOKEN_EXPIRE_HOURS: int = 8
    REFRESH_TOKEN_EXPIRE_HOURS: int = 8
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000"
    BACKEND_PUBLIC_URL: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    def get_allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()
```

- [ ] **Step 3: Write the Alembic migration**

Create `backend/alembic/versions/0004_proveedor_email.py`:

```python
"""proveedor_email_configurable

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("configuracion_sistema") as batch_op:
        batch_op.add_column(
            sa.Column("proveedor_activo", sa.String(20), nullable=False, server_default="yahoo")
        )
        batch_op.add_column(sa.Column("gmail_email", sa.String(255), nullable=True))
        batch_op.add_column(sa.Column("gmail_app_password_encrypted", sa.String(512), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("configuracion_sistema") as batch_op:
        batch_op.drop_column("gmail_app_password_encrypted")
        batch_op.drop_column("gmail_email")
        batch_op.drop_column("proveedor_activo")
```

- [ ] **Step 4: Write the failing tests for provider selection**

Append to `backend/tests/test_config_service.py`:

```python
def test_get_active_provider_default_yahoo(db):
    assert config_service.get_active_provider(db) == "yahoo"


def test_get_active_provider_invalido_cae_a_yahoo(db):
    config = config_service.load_config(db)
    config.proveedor_activo = "outlook"
    db.commit()
    assert config_service.get_active_provider(db) == "yahoo"


def test_save_active_provider_persiste(db):
    config_service.save_active_provider(db, "gmail")
    assert config_service.get_active_provider(db) == "gmail"
```

- [ ] **Step 5: Run tests to verify they fail**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_config_service.py -v`
Expected: FAIL — `AttributeError: module 'app.services.config_service' has no attribute 'get_active_provider'`

- [ ] **Step 6: Implement provider selection functions**

En `backend/app/services/config_service.py`, agregar el import y las funciones. El archivo completo queda:

```python
import logging
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email_providers import PROVIDERS, DEFAULT_PROVIDER
from app.models.configuracion_sistema import ConfiguracionSistema

_logger = logging.getLogger("mails_nico.config")


def _fernet() -> Fernet:
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet().decrypt(value.encode()).decode()


def load_config(db: Session) -> ConfiguracionSistema:
    config = db.get(ConfiguracionSistema, 1)
    if config is None:
        config = ConfiguracionSistema(id=1, actualizado_en=datetime.now(timezone.utc))
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def save_yahoo_credentials(db: Session, yahoo_email: str, yahoo_app_password: str) -> ConfiguracionSistema:
    config = load_config(db)
    config.yahoo_email = yahoo_email
    config.yahoo_app_password_encrypted = encrypt(yahoo_app_password)
    config.actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


def get_yahoo_credentials(db: Session) -> tuple[str, str]:
    """Credenciales de Yahoo desde la DB; si el operario todavía no cargó nada, cae al .env."""
    config = load_config(db)
    if config.yahoo_email and config.yahoo_app_password_encrypted:
        return config.yahoo_email, decrypt(config.yahoo_app_password_encrypted)
    return settings.YAHOO_EMAIL, settings.YAHOO_APP_PASSWORD


def get_active_provider(db: Session) -> str:
    """Proveedor activo configurado por el operario. Si el valor guardado no es uno
    conocido (ej. dato corrupto o editado a mano en DB), cae al default sin romper."""
    config = load_config(db)
    if config.proveedor_activo in PROVIDERS:
        return config.proveedor_activo
    _logger.warning(
        "proveedor_activo invalido en DB (%s), usando default %s", config.proveedor_activo, DEFAULT_PROVIDER
    )
    return DEFAULT_PROVIDER


def save_active_provider(db: Session, proveedor: str) -> ConfiguracionSistema:
    config = load_config(db)
    config.proveedor_activo = proveedor
    config.actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


def save_gmail_credentials(db: Session, gmail_email: str, gmail_app_password: str) -> ConfiguracionSistema:
    config = load_config(db)
    config.gmail_email = gmail_email
    config.gmail_app_password_encrypted = encrypt(gmail_app_password)
    config.actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


def get_gmail_credentials(db: Session) -> tuple[str, str]:
    """Credenciales de Gmail desde la DB; si el operario todavía no cargó nada, cae al .env."""
    config = load_config(db)
    if config.gmail_email and config.gmail_app_password_encrypted:
        return config.gmail_email, decrypt(config.gmail_app_password_encrypted)
    return settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD


def get_active_credentials(db: Session) -> tuple[str, str]:
    """Credenciales del proveedor activo (Yahoo o Gmail)."""
    if get_active_provider(db) == "gmail":
        return get_gmail_credentials(db)
    return get_yahoo_credentials(db)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_config_service.py -v`
Expected: PASS (todos los tests, incluidos los 5 pre-existentes de Yahoo)

- [ ] **Step 8: Write the failing tests for Gmail credentials and dispatcher**

Append to `backend/tests/test_config_service.py`:

```python
def test_save_gmail_credentials_persiste_cifrado(db):
    config_service.save_gmail_credentials(db, "cliente@gmail.com", "app-password-gmail")
    config = config_service.load_config(db)
    assert config.gmail_email == "cliente@gmail.com"
    assert config.gmail_app_password_encrypted != "app-password-gmail"
    assert config_service.decrypt(config.gmail_app_password_encrypted) == "app-password-gmail"


def test_get_gmail_credentials_usa_db_cuando_esta_configurado(db):
    config_service.save_gmail_credentials(db, "cliente@gmail.com", "app-password-gmail")
    email, password = config_service.get_gmail_credentials(db)
    assert email == "cliente@gmail.com"
    assert password == "app-password-gmail"


def test_get_gmail_credentials_cae_a_settings_si_no_esta_configurado(db):
    email, password = config_service.get_gmail_credentials(db)
    assert email == ""
    assert password == ""


def test_get_active_credentials_usa_yahoo_por_default(db):
    config_service.save_yahoo_credentials(db, "cliente@yahoo.com", "app-password-yahoo")
    email, password = config_service.get_active_credentials(db)
    assert email == "cliente@yahoo.com"
    assert password == "app-password-yahoo"


def test_get_active_credentials_usa_gmail_cuando_esta_activo(db):
    config_service.save_active_provider(db, "gmail")
    config_service.save_gmail_credentials(db, "cliente@gmail.com", "app-password-gmail")
    email, password = config_service.get_active_credentials(db)
    assert email == "cliente@gmail.com"
    assert password == "app-password-gmail"
```

- [ ] **Step 9: Run tests to verify they pass**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_config_service.py -v`
Expected: PASS (14 tests en total en el archivo)

- [ ] **Step 10: Commit**

```bash
git add backend/app/models/configuracion_sistema.py backend/app/core/config.py \
  backend/alembic/versions/0004_proveedor_email.py backend/app/services/config_service.py \
  backend/tests/test_config_service.py
git commit -m "feat: agregar proveedor_activo y credenciales de gmail a ConfiguracionSistema"
```

---

### Task 3: Schemas y endpoints de configuración

**Files:**
- Modify: `backend/app/schemas/configuracion.py`
- Modify: `backend/app/routers/configuracion.py`
- Modify: `backend/tests/test_configuracion_router.py`

**Interfaces:**
- Consumes: `config_service.get_active_provider`, `save_active_provider`, `load_config`, `save_gmail_credentials` (Task 2).
- Produces: `GET/PUT /configuracion/proveedor`, `GET/PUT /configuracion/gmail`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_configuracion_router.py`:

```python
def test_get_proveedor_default_yahoo(client, auth_headers):
    r = client.get("/configuracion/proveedor", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["proveedor"] == "yahoo"


def test_put_proveedor_gmail(client, auth_headers):
    r = client.put("/configuracion/proveedor", json={"proveedor": "gmail"}, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["proveedor"] == "gmail"

    r2 = client.get("/configuracion/proveedor", headers=auth_headers)
    assert r2.json()["proveedor"] == "gmail"


def test_put_proveedor_invalido_rechaza(client, auth_headers):
    r = client.put("/configuracion/proveedor", json={"proveedor": "outlook"}, headers=auth_headers)
    assert r.status_code == 422


def test_get_proveedor_requiere_auth(client):
    r = client.get("/configuracion/proveedor")
    assert r.status_code in (401, 403)


def test_get_configuracion_gmail_sin_configurar(client, auth_headers):
    r = client.get("/configuracion/gmail", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is False
    assert data["gmail_email"] is None


def test_put_configuracion_gmail(client, auth_headers):
    r = client.put(
        "/configuracion/gmail",
        json={"gmail_email": "cliente@gmail.com", "gmail_app_password": "abcd efgh ijkl mnop"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is True
    assert data["gmail_email"] == "cliente@gmail.com"
    assert "gmail_app_password" not in data


def test_put_configuracion_gmail_rechaza_password_vacia(client, auth_headers):
    r = client.put(
        "/configuracion/gmail",
        json={"gmail_email": "cliente@gmail.com", "gmail_app_password": ""},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_get_configuracion_gmail_requiere_auth(client):
    r = client.get("/configuracion/gmail")
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_configuracion_router.py -v`
Expected: FAIL con `404 Not Found` en los asserts de status 200 (las rutas no existen todavía)

- [ ] **Step 3: Add the new schemas**

En `backend/app/schemas/configuracion.py`, agregar `Literal` al import y las clases nuevas. El archivo completo queda:

```python
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


class ConfiguracionYahooRequest(BaseModel):
    yahoo_email: EmailStr
    yahoo_app_password: str = Field(min_length=1)


class ConfiguracionYahooResponse(BaseModel):
    yahoo_email: Optional[str] = None
    configurado: bool

    model_config = {"from_attributes": True}


class ConfiguracionGmailRequest(BaseModel):
    gmail_email: EmailStr
    gmail_app_password: str = Field(min_length=1)


class ConfiguracionGmailResponse(BaseModel):
    gmail_email: Optional[str] = None
    configurado: bool

    model_config = {"from_attributes": True}


class ConfiguracionProveedorRequest(BaseModel):
    proveedor: Literal["yahoo", "gmail"]


class ConfiguracionProveedorResponse(BaseModel):
    proveedor: Literal["yahoo", "gmail"]
```

- [ ] **Step 4: Add the new endpoints**

En `backend/app/routers/configuracion.py`, reemplazar el contenido completo por:

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.configuracion import (
    ConfiguracionYahooRequest,
    ConfiguracionYahooResponse,
    ConfiguracionGmailRequest,
    ConfiguracionGmailResponse,
    ConfiguracionProveedorRequest,
    ConfiguracionProveedorResponse,
)
from app.services import config_service

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


@router.get("/yahoo", response_model=ConfiguracionYahooResponse)
def get_yahoo_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = config_service.load_config(db)
    return ConfiguracionYahooResponse(
        yahoo_email=config.yahoo_email,
        configurado=bool(config.yahoo_email and config.yahoo_app_password_encrypted),
    )


@router.put("/yahoo", response_model=ConfiguracionYahooResponse)
def put_yahoo_config(
    body: ConfiguracionYahooRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = config_service.save_yahoo_credentials(db, body.yahoo_email, body.yahoo_app_password)
    return ConfiguracionYahooResponse(yahoo_email=config.yahoo_email, configurado=True)


@router.get("/gmail", response_model=ConfiguracionGmailResponse)
def get_gmail_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = config_service.load_config(db)
    return ConfiguracionGmailResponse(
        gmail_email=config.gmail_email,
        configurado=bool(config.gmail_email and config.gmail_app_password_encrypted),
    )


@router.put("/gmail", response_model=ConfiguracionGmailResponse)
def put_gmail_config(
    body: ConfiguracionGmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = config_service.save_gmail_credentials(db, body.gmail_email, body.gmail_app_password)
    return ConfiguracionGmailResponse(gmail_email=config.gmail_email, configurado=True)


@router.get("/proveedor", response_model=ConfiguracionProveedorResponse)
def get_proveedor(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ConfiguracionProveedorResponse(proveedor=config_service.get_active_provider(db))


@router.put("/proveedor", response_model=ConfiguracionProveedorResponse)
def put_proveedor(
    body: ConfiguracionProveedorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config_service.save_active_provider(db, body.proveedor)
    return ConfiguracionProveedorResponse(proveedor=body.proveedor)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_configuracion_router.py -v`
Expected: PASS (todos los tests, incluidos los 5 pre-existentes de Yahoo)

- [ ] **Step 6: Run the full backend test suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: PASS (ningún test pre-existente roto)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/configuracion.py backend/app/routers/configuracion.py \
  backend/tests/test_configuracion_router.py
git commit -m "feat: agregar endpoints de configuracion para proveedor y credenciales de gmail"
```

---

### Task 4: Integrar el proveedor activo en `smtp_sender.py`

**Files:**
- Modify: `backend/app/services/smtp_sender.py`
- Modify: `backend/tests/test_smtp_sender.py`

**Interfaces:**
- Consumes: `PROVIDERS` (Task 1), `config_service.get_active_provider`, `config_service.get_active_credentials` (Task 2).
- Produces: `_send_single_email(msg, from_email: str, app_password: str, smtp_host: str, smtp_port: int) -> str` (firma cambiada — agrega `smtp_host`, `smtp_port`).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_smtp_sender.py`:

```python
def test_enviar_ciclo_usa_host_yahoo_por_default(db, plantilla_default):
    ciclo = _make_ciclo(db)
    envio = _make_envio_db(db, ciclo, "C010", "Consorcio", "test@mail.com", 5000)

    async def on_progress(e):
        pass

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<msg-id@yahoo.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo([envio], db, on_progress, rate_limit_override=(2, 0.01))
        )

    args = mock_send.call_args.args
    assert args[3] == "smtp.mail.yahoo.com"
    assert args[4] == 587


def test_enviar_ciclo_usa_host_gmail_cuando_esta_activo(db, plantilla_default):
    from app.services import config_service
    config_service.save_active_provider(db, "gmail")

    ciclo = _make_ciclo(db)
    envio = _make_envio_db(db, ciclo, "C011", "Consorcio2", "test2@mail.com", 3000)

    async def on_progress(e):
        pass

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<msg-id@gmail.com>"
        asyncio.get_event_loop().run_until_complete(
            enviar_ciclo([envio], db, on_progress, rate_limit_override=(2, 0.01))
        )

    args = mock_send.call_args.args
    assert args[3] == "smtp.gmail.com"
    assert args[4] == 587
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_smtp_sender.py -v`
Expected: FAIL con `IndexError: tuple index out of range` (hoy `_send_single_email` se llama con solo 3 args posicionales)

- [ ] **Step 3: Implement the provider-aware sender**

Reemplazar el contenido completo de `backend/app/services/smtp_sender.py`:

```python
import asyncio
import logging
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from typing import Awaitable, Callable, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email_providers import PROVIDERS
from app.services import config_service
from app.models.envio import Envio
from app.services import db_config
from app.services.email_generator import generate_email
from app.services.excel_joiner import EnvioParsed

_logger = logging.getLogger("mails_nico.smtp")

_DEFAULT_RATE_LIMIT: Tuple[int, float] = (5, 30.0)  # 5 mails, luego esperar 30 segundos


def _send_single_email(msg, from_email: str, app_password: str, smtp_host: str, smtp_port: int) -> str:
    context = ssl.create_default_context()
    with smtplib.SMTP(smtp_host, smtp_port) as server:
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
    provider = PROVIDERS[config_service.get_active_provider(db)]
    from_email, app_password = config_service.get_active_credentials(db)

    sent_in_batch = 0
    loop = asyncio.get_running_loop()

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
        msg = generate_email(parsed, plantilla, unsubscribe_base_url=settings.BACKEND_PUBLIC_URL)
        msg["From"] = from_email
        msg_id = f"<{uuid.uuid4().hex}@{provider.message_id_domain}>"
        msg["Message-ID"] = msg_id

        try:
            returned_id = await loop.run_in_executor(
                None,
                _send_single_email,
                msg,
                from_email,
                app_password,
                provider.smtp_host,
                provider.smtp_port,
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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_smtp_sender.py -v`
Expected: PASS (incluye los 2 tests pre-existentes, que siguen funcionando porque mockean `_send_single_email` completo)

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/smtp_sender.py backend/tests/test_smtp_sender.py
git commit -m "feat: smtp_sender resuelve host/puerto segun el proveedor activo"
```

---

### Task 5: Integrar el proveedor activo en `imap_watcher.py`

**Files:**
- Modify: `backend/app/services/imap_watcher.py`
- Create: `backend/tests/test_imap_watcher.py`

**Interfaces:**
- Consumes: `PROVIDERS` (Task 1), `config_service.get_active_provider`, `config_service.get_active_credentials` (Task 2).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_imap_watcher.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

from app.services import imap_watcher, config_service
from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio


def _make_ciclo(db):
    c = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    return c


def _make_envio_no_contestado(db, ciclo, clave, message_id):
    e = Envio(
        ciclo_id=ciclo.id,
        ciclo_numero=1,
        clave_union=clave,
        nombre_consorcio="Consorcio",
        email="test@mail.com",
        monto=Decimal("1000"),
        estado=EstadoEnvio.NO_CONTESTADO,
        message_id=message_id,
        enviado_en=datetime.now(timezone.utc),
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.commit()
    return e


def _usar_sesion_de_test(db, monkeypatch):
    # _poll_inbox abre su propia sesion via SessionLocal(); la reemplazamos por la
    # sesion de test para que vea los datos sembrados por los fixtures, y anulamos
    # close() para no cortar la sesion que el fixture `db` todavia necesita.
    monkeypatch.setattr(imap_watcher, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)


def test_poll_inbox_sin_envios_activos_no_conecta(db, monkeypatch):
    _usar_sesion_de_test(db, monkeypatch)
    with patch("app.services.imap_watcher.imaplib.IMAP4_SSL") as mock_imap:
        imap_watcher._poll_inbox()
    mock_imap.assert_not_called()


def test_poll_inbox_usa_host_yahoo_por_default(db, monkeypatch):
    _usar_sesion_de_test(db, monkeypatch)
    ciclo = _make_ciclo(db)
    _make_envio_no_contestado(db, ciclo, "C001", "<abc@yahoo.com>")

    with patch("app.services.imap_watcher.imaplib.IMAP4_SSL") as mock_imap:
        mock_conn = MagicMock()
        mock_conn.search.return_value = ("OK", [b""])
        mock_imap.return_value = mock_conn
        imap_watcher._poll_inbox()

    mock_imap.assert_called_once_with("imap.mail.yahoo.com", 993)


def test_poll_inbox_usa_host_gmail_cuando_esta_activo(db, monkeypatch):
    _usar_sesion_de_test(db, monkeypatch)
    config_service.save_active_provider(db, "gmail")
    ciclo = _make_ciclo(db)
    _make_envio_no_contestado(db, ciclo, "C002", "<def@gmail.com>")

    with patch("app.services.imap_watcher.imaplib.IMAP4_SSL") as mock_imap:
        mock_conn = MagicMock()
        mock_conn.search.return_value = ("OK", [b""])
        mock_imap.return_value = mock_conn
        imap_watcher._poll_inbox()

    mock_imap.assert_called_once_with("imap.gmail.com", 993)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_imap_watcher.py -v`
Expected: FAIL — `mock_imap.assert_called_once_with("imap.mail.yahoo.com", 993)` falla porque hoy se llama con `("imap.mail.yahoo.com", 993)` posicional pero via credenciales de `get_yahoo_credentials` sin pasar por `get_active_provider`; en el caso de gmail falla porque el host resuelto sigue siendo el de yahoo (hardcodeado)

- [ ] **Step 3: Implement the provider-aware watcher**

Reemplazar el contenido completo de `backend/app/services/imap_watcher.py`:

```python
import asyncio
import email
import imaplib
import logging
from datetime import datetime, timedelta, timezone

from app.core.database import SessionLocal
from app.core.email_providers import PROVIDERS
from app.models.envio import Envio, EstadoEnvio
from app.services import config_service
from app.services.reply_classifier import classify

_logger = logging.getLogger("mails_nico.imap")
_POLL_INTERVAL = 600  # 10 minutos
_SEARCH_WINDOW_DAYS = 30


async def run_forever():
    """
    Loop infinito que realiza polling IMAP cada 10 minutos.
    Se ejecuta como background task al iniciar la aplicación.
    """
    while True:
        try:
            await asyncio.get_event_loop().run_in_executor(None, _poll_inbox)
        except Exception as exc:
            _logger.error("IMAP poll error: %s", exc)
        await asyncio.sleep(_POLL_INTERVAL)


def _poll_inbox():
    """
    Conexión sincrónica a IMAP para buscar respuestas a Envios activos.
    Se ejecuta en executor para no bloquear el event loop.
    """
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

        provider = PROVIDERS[config_service.get_active_provider(db)]
        email_addr, app_password = config_service.get_active_credentials(db)
        mail = imaplib.IMAP4_SSL(provider.imap_host, provider.imap_port)
        try:
            mail.login(email_addr, app_password)
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

                new_estado, tiene_adjunto = classify(msg)
                snippet = _extract_snippet(msg)
                matched_envio.estado = new_estado
                matched_envio.reply_snippet = snippet
                matched_envio.reply_en = datetime.now(timezone.utc)
                matched_envio.tiene_adjunto = tiene_adjunto
                matched_envio.actualizado_en = datetime.now(timezone.utc)
                db.add(matched_envio)
                _logger.info("Envio %s → %s", matched_envio.id, new_estado)

            db.commit()
        finally:
            try:
                mail.logout()
            except Exception:
                pass
    finally:
        db.close()


def _extract_snippet(msg) -> str:
    """Extrae los primeros 200 caracteres del cuerpo de texto del email."""
    for part in msg.walk():
        if part.get_content_type() == "text/plain":
            payload = part.get_payload(decode=True)
            if payload:
                return payload.decode(errors="replace")[:200]
    return ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_imap_watcher.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Run the full backend test suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: PASS (todo el backend, incluidos todos los tests de tasks anteriores)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/imap_watcher.py backend/tests/test_imap_watcher.py
git commit -m "feat: imap_watcher resuelve host/puerto segun el proveedor activo"
```

---

### Task 6: Tipos y servicio de frontend

**Files:**
- Modify: `frontend/src/types/domain.ts`
- Modify: `frontend/src/services/configuracion.ts`

**Interfaces:**
- Consumes: `GET/PUT /configuracion/proveedor`, `GET/PUT /configuracion/gmail` (Task 3).
- Produces: tipos `ProveedorEmail`, `ConfiguracionProveedor`, `ConfiguracionGmail`; funciones `getProveedorActivo()`, `updateProveedorActivo(proveedor)`, `getConfiguracionGmail()`, `updateConfiguracionGmail(email, password)`.

- [ ] **Step 1: Add the new types**

En `frontend/src/types/domain.ts`, agregar al final del archivo (después de `ConfiguracionYahoo`):

```ts
export type ProveedorEmail = "yahoo" | "gmail";

export interface ConfiguracionProveedor {
  proveedor: ProveedorEmail;
}

export interface ConfiguracionGmail {
  gmail_email: string | null;
  configurado: boolean;
}
```

- [ ] **Step 2: Add the new service functions**

Reemplazar el contenido completo de `frontend/src/services/configuracion.ts`:

```ts
import { apiFetch } from "./api";
import type { ConfiguracionYahoo, ConfiguracionGmail, ConfiguracionProveedor, ProveedorEmail } from "../types/domain";

export async function getConfiguracionYahoo(): Promise<ConfiguracionYahoo> {
  const r = await apiFetch("/configuracion/yahoo");
  if (!r.ok) throw new Error("Error cargando configuración de Yahoo");
  return r.json();
}

export async function updateConfiguracionYahoo(
  yahoo_email: string,
  yahoo_app_password: string,
): Promise<ConfiguracionYahoo> {
  const r = await apiFetch("/configuracion/yahoo", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ yahoo_email, yahoo_app_password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error guardando la configuración de Yahoo");
  }
  return r.json();
}

export async function getConfiguracionGmail(): Promise<ConfiguracionGmail> {
  const r = await apiFetch("/configuracion/gmail");
  if (!r.ok) throw new Error("Error cargando configuración de Gmail");
  return r.json();
}

export async function updateConfiguracionGmail(
  gmail_email: string,
  gmail_app_password: string,
): Promise<ConfiguracionGmail> {
  const r = await apiFetch("/configuracion/gmail", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ gmail_email, gmail_app_password }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error guardando la configuración de Gmail");
  }
  return r.json();
}

export async function getProveedorActivo(): Promise<ConfiguracionProveedor> {
  const r = await apiFetch("/configuracion/proveedor");
  if (!r.ok) throw new Error("Error cargando el proveedor activo");
  return r.json();
}

export async function updateProveedorActivo(proveedor: ProveedorEmail): Promise<ConfiguracionProveedor> {
  const r = await apiFetch("/configuracion/proveedor", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proveedor }),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error guardando el proveedor activo");
  }
  return r.json();
}
```

- [ ] **Step 3: Verify the frontend typechecks**

Run: `cd frontend && npm run build`
Expected: Compila sin errores de TypeScript (nada todavía consume las funciones nuevas, pero deben tipar correctamente)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/domain.ts frontend/src/services/configuracion.ts
git commit -m "feat: tipos y servicio de frontend para proveedor de email configurable"
```

---

### Task 7: Selector de proveedor en `ConfiguracionPage.tsx`

**Files:**
- Modify: `frontend/src/pages/ConfiguracionPage.tsx`

**Interfaces:**
- Consumes: `getProveedorActivo`, `updateProveedorActivo`, `getConfiguracionGmail`, `updateConfiguracionGmail` (Task 6), `ProveedorEmail` type (Task 6).

- [ ] **Step 1: Implement the provider selector and conditional forms**

Reemplazar el contenido completo de `frontend/src/pages/ConfiguracionPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  getConfiguracionYahoo,
  updateConfiguracionYahoo,
  getConfiguracionGmail,
  updateConfiguracionGmail,
  getProveedorActivo,
  updateProveedorActivo,
} from "../services/configuracion";
import type { ProveedorEmail } from "../types/domain";

export default function ConfiguracionPage() {
  const [proveedor, setProveedor] = useState<ProveedorEmail>("yahoo");
  const [proveedorStatus, setProveedorStatus] = useState("");

  const [yahooEmail, setYahooEmail] = useState("");
  const [yahooPassword, setYahooPassword] = useState("");
  const [yahooConfigurado, setYahooConfigurado] = useState(false);
  const [yahooStatus, setYahooStatus] = useState("");

  const [gmailEmail, setGmailEmail] = useState("");
  const [gmailPassword, setGmailPassword] = useState("");
  const [gmailConfigurado, setGmailConfigurado] = useState(false);
  const [gmailStatus, setGmailStatus] = useState("");

  useEffect(() => {
    getProveedorActivo()
      .then((data) => setProveedor(data.proveedor))
      .catch(() => {});
    getConfiguracionYahoo()
      .then((data) => {
        setYahooConfigurado(data.configurado);
        if (data.yahoo_email) setYahooEmail(data.yahoo_email);
      })
      .catch(() => {});
    getConfiguracionGmail()
      .then((data) => {
        setGmailConfigurado(data.configurado);
        if (data.gmail_email) setGmailEmail(data.gmail_email);
      })
      .catch(() => {});
  }, []);

  async function handleCambiarProveedor(nuevo: ProveedorEmail) {
    setProveedor(nuevo);
    setProveedorStatus("Guardando...");
    try {
      await updateProveedorActivo(nuevo);
      setProveedorStatus("Guardado correctamente");
    } catch (e: unknown) {
      setProveedorStatus(e instanceof Error ? e.message : "Error");
    }
  }

  async function handleGuardarYahoo() {
    setYahooStatus("Guardando...");
    try {
      const data = await updateConfiguracionYahoo(yahooEmail, yahooPassword);
      setYahooConfigurado(data.configurado);
      setYahooPassword("");
      setYahooStatus("Guardado correctamente");
    } catch (e: unknown) {
      setYahooStatus(e instanceof Error ? e.message : "Error");
    }
  }

  async function handleGuardarGmail() {
    setGmailStatus("Guardando...");
    try {
      const data = await updateConfiguracionGmail(gmailEmail, gmailPassword);
      setGmailConfigurado(data.configurado);
      setGmailPassword("");
      setGmailStatus("Guardado correctamente");
    } catch (e: unknown) {
      setGmailStatus(e instanceof Error ? e.message : "Error");
    }
  }

  return (
    <div className="max-w-3xl mx-auto space-y-4">
      <div>
        <h1 className="text-xl font-semibold text-foreground">Configuración</h1>
        <p className="text-sm text-muted-foreground mt-1">Proveedor y credenciales de la cuenta de email.</p>
      </div>

      <div className="max-w-sm space-y-4">
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Proveedor de email</label>
          <select
            className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            value={proveedor}
            onChange={(e) => handleCambiarProveedor(e.target.value as ProveedorEmail)}
          >
            <option value="yahoo">Yahoo</option>
            <option value="gmail">Gmail</option>
          </select>
          {proveedorStatus && <p className="text-sm text-muted-foreground">{proveedorStatus}</p>}
        </div>

        {proveedor === "yahoo" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Cuenta de Yahoo</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {yahooConfigurado
                  ? "Configurada — cargá una nueva clave para reemplazarla."
                  : "Sin configurar. El sistema no puede enviar ni leer mails hasta que cargues esto."}
              </p>
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">Email de Yahoo</label>
              <Input
                type="email"
                value={yahooEmail}
                onChange={(e) => setYahooEmail(e.target.value)}
                placeholder="empresa@yahoo.com"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">App password</label>
              <Input
                type="password"
                value={yahooPassword}
                onChange={(e) => setYahooPassword(e.target.value)}
                placeholder="Generada desde la cuenta de Yahoo (no la contraseña normal)"
              />
            </div>
            {yahooStatus && <p className="text-sm text-muted-foreground">{yahooStatus}</p>}
            <Button onClick={handleGuardarYahoo} disabled={!yahooEmail || !yahooPassword}>
              Guardar credenciales de Yahoo
            </Button>
          </div>
        )}

        {proveedor === "gmail" && (
          <div className="space-y-4">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Cuenta de Gmail</h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                {gmailConfigurado
                  ? "Configurada — cargá una nueva clave para reemplazarla."
                  : "Sin configurar. El sistema no puede enviar ni leer mails hasta que cargues esto."}
              </p>
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">Email de Gmail</label>
              <Input
                type="email"
                value={gmailEmail}
                onChange={(e) => setGmailEmail(e.target.value)}
                placeholder="empresa@gmail.com"
              />
            </div>
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-foreground">App password</label>
              <Input
                type="password"
                value={gmailPassword}
                onChange={(e) => setGmailPassword(e.target.value)}
                placeholder="Requiere verificación en 2 pasos activada en la cuenta de Google"
              />
            </div>
            {gmailStatus && <p className="text-sm text-muted-foreground">{gmailStatus}</p>}
            <Button onClick={handleGuardarGmail} disabled={!gmailEmail || !gmailPassword}>
              Guardar credenciales de Gmail
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify the frontend builds**

Run: `cd frontend && npm run build`
Expected: Compila sin errores de TypeScript

- [ ] **Step 3: Manual verification**

Run: `cd frontend && npm run dev` (con el backend corriendo en paralelo)
1. Navegar a `/configuracion`, loguearse si hace falta.
2. Confirmar que el selector muestra "Yahoo" por default y el formulario de Yahoo debajo.
3. Cambiar el selector a "Gmail" — confirmar que aparece "Guardado correctamente" y el formulario cambia a los campos de Gmail.
4. Cargar un email + password de Gmail y guardar — confirmar el mensaje "Guardado correctamente" y que "configurado" pasa a mostrarse como configurada al recargar la página.
5. Volver el selector a "Yahoo" — confirmar que las credenciales de Yahoo cargadas previamente (si las había) siguen apareciendo.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/ConfiguracionPage.tsx
git commit -m "feat: selector de proveedor de email en la pagina de Configuracion"
```

---

## Nota operativa post-implementación

Para testear localmente con Gmail una vez implementado este plan:
1. Activar verificación en 2 pasos en la cuenta de Google que se vaya a usar.
2. Generar un app password desde la configuración de seguridad de Google.
3. Levantar el backend y el frontend en local, ir a `/configuracion`, seleccionar "Gmail" y cargar el email + app password ahí.
4. El sistema queda usando Gmail para SMTP e IMAP hasta que se vuelva a cambiar el selector a "Yahoo".
