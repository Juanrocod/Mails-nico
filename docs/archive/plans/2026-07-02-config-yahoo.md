# Configuración Dinámica de Credenciales Yahoo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir que el operario cargue y actualice el email y app password de Yahoo desde la pantalla de Configuración, sin editar `.env` ni reiniciar el servidor.

**Architecture:** Nueva tabla singleton `configuracion_sistema` (mismo patrón que `Plantilla`, id=1) guarda `yahoo_email` en texto plano y `yahoo_app_password_encrypted` cifrado con Fernet (símétrico, clave en `ENCRYPTION_KEY`). `smtp_sender.py` e `imap_watcher.py` dejan de leer `settings.YAHOO_EMAIL`/`YAHOO_APP_PASSWORD` directo y pasan a pedirle las credenciales a un nuevo `config_service.py`, que devuelve lo guardado en DB o, si no hay nada cargado todavía, cae a `settings` (el `.env`) como fallback — así nada se rompe mientras el operario no cargó nada.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Alembic, `cryptography.fernet` (ya viene instalado como dependencia transitiva de `python-jose[cryptography]`, no hace falta agregar nada a `requirements.txt`), React + TypeScript.

## Global Constraints

- El app password de Yahoo NUNCA se devuelve en ninguna respuesta de API, ni siquiera cifrado. El GET solo informa si está configurado (`configurado: bool`) y el email (no es secreto).
- `ENCRYPTION_KEY` es una variable de entorno nueva y obligatoria (como `SECRET_KEY`) — sin ella el proceso no arranca.
- Migraciones con `batch_alter_table` no aplica acá porque es una tabla nueva (`create_table`), no una alteración.
- Todos los routers protegidos usan `Depends(get_current_user)` — este no es la excepción (a diferencia del endpoint de unsubscribe de otro plan, que sí es público).
- Correr tests: `cd backend && venv\Scripts\python -m pytest -v`

---

## File Structure

- Create: `backend/app/models/configuracion_sistema.py` — modelo `ConfiguracionSistema`
- Create: `backend/alembic/versions/0002_configuracion_sistema.py` — migración
- Create: `backend/app/services/config_service.py` — cifrado + load/save + `get_yahoo_credentials()`
- Create: `backend/app/schemas/configuracion.py` — request/response Pydantic
- Create: `backend/app/routers/configuracion.py` — endpoints GET/PUT `/configuracion/yahoo`
- Modify: `backend/app/core/config.py` — agregar `ENCRYPTION_KEY: str`
- Modify: `backend/app/services/smtp_sender.py` — leer credenciales desde `config_service` en vez de `settings`
- Modify: `backend/app/services/imap_watcher.py` — ídem
- Modify: `backend/app/main.py` — registrar `configuracion.router`
- Modify: `backend/tests/conftest.py` — env var `ENCRYPTION_KEY` de test + import del modelo nuevo
- Create: `backend/tests/test_config_service.py`
- Create: `backend/tests/test_configuracion_router.py`
- Modify: `backend/.env.example` — sacar basura de TOTP/2FA, agregar `ENCRYPTION_KEY`, documentar `YAHOO_EMAIL`/`YAHOO_APP_PASSWORD` como fallback opcional
- Modify: `frontend/src/types/domain.ts` — tipo `ConfiguracionYahoo`
- Create: `frontend/src/services/configuracion.ts`
- Modify: `frontend/src/pages/ConfiguracionPage.tsx` — nueva sección "Cuenta de Yahoo"

---

### Task 1: Modelo `ConfiguracionSistema` + migración

**Files:**
- Create: `backend/app/models/configuracion_sistema.py`
- Create: `backend/alembic/versions/0002_configuracion_sistema.py`
- Modify: `backend/tests/conftest.py`

**Interfaces:**
- Produces: `ConfiguracionSistema` (SQLAlchemy model) con columnas `id: int`, `yahoo_email: str | None`, `yahoo_app_password_encrypted: str | None`, `actualizado_en: datetime`. Tabla `configuracion_sistema`, singleton `id=1` (mismo patrón que `app/models/plantilla.py`).

- [ ] **Step 1: Crear el modelo**

```python
# backend/app/models/configuracion_sistema.py
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base


class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"
    id = Column(Integer, primary_key=True, default=1)
    yahoo_email = Column(String(255), nullable=True)
    yahoo_app_password_encrypted = Column(String(512), nullable=True)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

- [ ] **Step 2: Crear la migración Alembic**

```python
# backend/alembic/versions/0002_configuracion_sistema.py
"""configuracion_sistema

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuracion_sistema",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("yahoo_email", sa.String(255), nullable=True),
        sa.Column("yahoo_app_password_encrypted", sa.String(512), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("configuracion_sistema")
```

- [ ] **Step 3: Correr la migración en la DB de desarrollo**

Run: `cd backend && venv\Scripts\python -m alembic upgrade head`
Expected: termina sin error, `alembic upgrade  -> 0002, configuracion_sistema` en la salida.

- [ ] **Step 4: Registrar el modelo en `conftest.py` para que los tests lo vean**

En `backend/tests/conftest.py`, junto a los demás imports de modelos (línea ~21, después de `from app.models.envio import Envio`), agregar:

```python
from app.models.configuracion_sistema import ConfiguracionSistema
```

Esto es necesario porque `Base.metadata.create_all(_engine)` (línea 42) solo crea tablas de modelos que ya fueron importados por Python — si no se importa acá, la tabla `configuracion_sistema` no existe en la DB de tests aunque el modelo esté bien escrito.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/configuracion_sistema.py backend/alembic/versions/0002_configuracion_sistema.py backend/tests/conftest.py
git commit -m "feat: modelo y migración de configuracion_sistema"
```

---

### Task 2: Cifrado + `config_service.py`

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/tests/conftest.py`
- Create: `backend/app/services/config_service.py`
- Create: `backend/tests/test_config_service.py`

**Interfaces:**
- Consumes: `ConfiguracionSistema` (Task 1), `settings.ENCRYPTION_KEY`, `settings.YAHOO_EMAIL`, `settings.YAHOO_APP_PASSWORD`
- Produces:
  - `config_service.load_config(db: Session) -> ConfiguracionSistema`
  - `config_service.save_yahoo_credentials(db: Session, yahoo_email: str, yahoo_app_password: str) -> ConfiguracionSistema`
  - `config_service.get_yahoo_credentials(db: Session) -> tuple[str, str]` — `(email, app_password_plano)`, usado por Task 3

- [ ] **Step 1: Agregar `ENCRYPTION_KEY` a `Settings`**

En `backend/app/core/config.py`, agregar el campo (después de `SECRET_KEY: str`, línea 6):

```python
    ENCRYPTION_KEY: str
```

- [ ] **Step 2: Agregar `ENCRYPTION_KEY` de test a `conftest.py`**

En `backend/tests/conftest.py`, junto a los demás `os.environ.setdefault` (después de la línea 7 `YAHOO_APP_PASSWORD`), agregar:

```python
os.environ.setdefault("ENCRYPTION_KEY", "d7YW8J0w_22uQFcAoYlsBiERC-gzOFsBMyhs-Qs2xfU=")
```

Esta es una clave Fernet válida fija, generada una sola vez para que los tests sean determinísticos (no hace falta que sea secreta, es solo de test).

- [ ] **Step 3: Escribir el test de cifrado (falla primero)**

```python
# backend/tests/test_config_service.py
from app.services import config_service


def test_encrypt_decrypt_roundtrip():
    original = "mi-app-password-super-secreto"
    encrypted = config_service.encrypt(original)
    assert encrypted != original
    assert config_service.decrypt(encrypted) == original


def test_encrypt_valor_vacio_devuelve_vacio():
    assert config_service.encrypt("") == ""
    assert config_service.decrypt("") == ""


def test_load_config_crea_fila_default_si_no_existe(db):
    config = config_service.load_config(db)
    assert config.id == 1
    assert config.yahoo_email is None
    assert config.yahoo_app_password_encrypted is None


def test_save_yahoo_credentials_persiste_cifrado(db):
    config_service.save_yahoo_credentials(db, "cliente@yahoo.com", "app-password-123")
    config = config_service.load_config(db)
    assert config.yahoo_email == "cliente@yahoo.com"
    assert config.yahoo_app_password_encrypted != "app-password-123"
    assert config_service.decrypt(config.yahoo_app_password_encrypted) == "app-password-123"


def test_get_yahoo_credentials_usa_db_cuando_esta_configurado(db):
    config_service.save_yahoo_credentials(db, "cliente@yahoo.com", "app-password-123")
    email, password = config_service.get_yahoo_credentials(db)
    assert email == "cliente@yahoo.com"
    assert password == "app-password-123"


def test_get_yahoo_credentials_cae_a_settings_si_no_esta_configurado(db):
    email, password = config_service.get_yahoo_credentials(db)
    # conftest.py setea estas vars de entorno como fallback de test
    assert email == "test@yahoo.com"
    assert password == "testapppassword"
```

- [ ] **Step 4: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_config_service.py -v`
Expected: FAIL con `ModuleNotFoundError: No module named 'app.services.config_service'`

- [ ] **Step 5: Implementar `config_service.py`**

```python
# backend/app/services/config_service.py
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.configuracion_sistema import ConfiguracionSistema


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
```

- [ ] **Step 6: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_config_service.py -v`
Expected: `6 passed`

- [ ] **Step 7: Commit**

```bash
git add backend/app/core/config.py backend/tests/conftest.py backend/app/services/config_service.py backend/tests/test_config_service.py
git commit -m "feat: cifrado y persistencia de credenciales Yahoo en DB"
```

---

### Task 3: `smtp_sender.py` e `imap_watcher.py` leen desde `config_service`

**Files:**
- Modify: `backend/app/services/smtp_sender.py`
- Modify: `backend/app/services/imap_watcher.py`

**Interfaces:**
- Consumes: `config_service.get_yahoo_credentials(db)` (Task 2)

- [ ] **Step 1: Cambiar `smtp_sender.enviar_ciclo` para usar `config_service`**

En `backend/app/services/smtp_sender.py`, reemplazar el import de `settings` (línea 11) y las líneas 39-40:

```python
from app.core.config import settings
```
por
```python
from app.services import config_service
```

Y reemplazar:
```python
    from_email = settings.YAHOO_EMAIL
    app_password = settings.YAHOO_APP_PASSWORD
```
por
```python
    from_email, app_password = config_service.get_yahoo_credentials(db)
```

- [ ] **Step 2: Correr los tests de smtp_sender para verificar que siguen pasando**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_smtp_sender.py -v`
Expected: `2 passed` (estos tests mockean `_send_single_email`, no dependen de credenciales reales, así que no deberían romperse)

- [ ] **Step 3: Cambiar `imap_watcher._poll_inbox` para usar `config_service`**

En `backend/app/services/imap_watcher.py`, agregar el import (junto a los demás, línea 10):

```python
from app.services import config_service
```

Y reemplazar las líneas 52-54:
```python
        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com", 993)
        try:
            mail.login(settings.YAHOO_EMAIL, settings.YAHOO_APP_PASSWORD)
```
por
```python
        yahoo_email, yahoo_app_password = config_service.get_yahoo_credentials(db)
        mail = imaplib.IMAP4_SSL("imap.mail.yahoo.com", 993)
        try:
            mail.login(yahoo_email, yahoo_app_password)
```

- [ ] **Step 4: Verificar que `settings` ya no se usa en `imap_watcher.py` salvo si hace falta en otro lado**

Run (PowerShell): `Select-String -Path backend\app\services\imap_watcher.py -Pattern "settings\."`
Expected: sin resultados (ya no queda ninguna referencia a `settings.YAHOO_*`). Si el import de `settings` (línea 7) quedó sin uso, borrarlo.

- [ ] **Step 5: Correr toda la suite de tests para confirmar que nada se rompió**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos los tests pasan (44 + los 6 nuevos de Task 2 = 50)

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/smtp_sender.py backend/app/services/imap_watcher.py
git commit -m "feat: smtp_sender e imap_watcher usan credenciales Yahoo desde config_service"
```

---

### Task 4: Schema + router `/configuracion/yahoo`

**Files:**
- Create: `backend/app/schemas/configuracion.py`
- Create: `backend/app/routers/configuracion.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_configuracion_router.py`

**Interfaces:**
- Consumes: `config_service.load_config`, `config_service.save_yahoo_credentials` (Task 2)
- Produces: `GET /configuracion/yahoo`, `PUT /configuracion/yahoo` — ambos requieren `get_current_user`

- [ ] **Step 1: Escribir el test del router (falla primero)**

```python
# backend/tests/test_configuracion_router.py
def test_get_configuracion_yahoo_sin_configurar(client, auth_headers):
    r = client.get("/configuracion/yahoo", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is False
    assert data["yahoo_email"] is None


def test_put_configuracion_yahoo(client, auth_headers):
    r = client.put(
        "/configuracion/yahoo",
        json={"yahoo_email": "cliente@yahoo.com", "yahoo_app_password": "abcd efgh ijkl mnop"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["configurado"] is True
    assert data["yahoo_email"] == "cliente@yahoo.com"
    assert "yahoo_app_password" not in data


def test_put_configuracion_yahoo_persiste(client, auth_headers):
    client.put(
        "/configuracion/yahoo",
        json={"yahoo_email": "otro@yahoo.com", "yahoo_app_password": "clave-app"},
        headers=auth_headers,
    )
    r = client.get("/configuracion/yahoo", headers=auth_headers)
    assert r.json()["yahoo_email"] == "otro@yahoo.com"
    assert r.json()["configurado"] is True


def test_get_configuracion_yahoo_requiere_auth(client):
    r = client.get("/configuracion/yahoo")
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_configuracion_router.py -v`
Expected: FAIL con 404 (la ruta no existe todavía)

- [ ] **Step 3: Crear el schema**

```python
# backend/app/schemas/configuracion.py
from typing import Optional
from pydantic import BaseModel, EmailStr


class ConfiguracionYahooRequest(BaseModel):
    yahoo_email: EmailStr
    yahoo_app_password: str


class ConfiguracionYahooResponse(BaseModel):
    yahoo_email: Optional[str] = None
    configurado: bool

    model_config = {"from_attributes": True}
```

- [ ] **Step 4: Crear el router**

```python
# backend/app/routers/configuracion.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.configuracion import ConfiguracionYahooRequest, ConfiguracionYahooResponse
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
```

- [ ] **Step 5: Registrar el router en `main.py`**

En `backend/app/main.py`, cambiar la línea 17:
```python
from app.routers import auth, plantilla, maestro, ciclos
```
por
```python
from app.routers import auth, plantilla, maestro, ciclos, configuracion
```

Y agregar después de la línea 52 (`app.include_router(ciclos.router)`):
```python
app.include_router(configuracion.router)
```

- [ ] **Step 6: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_configuracion_router.py -v`
Expected: `4 passed`

- [ ] **Step 7: Correr toda la suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos pasan (54 tests)

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/configuracion.py backend/app/routers/configuracion.py backend/app/main.py backend/tests/test_configuracion_router.py
git commit -m "feat: endpoints GET/PUT /configuracion/yahoo"
```

---

### Task 5: Frontend — servicio + tipos

**Files:**
- Modify: `frontend/src/types/domain.ts`
- Create: `frontend/src/services/configuracion.ts`

**Interfaces:**
- Produces: `ConfiguracionYahoo` type, `getConfiguracionYahoo()`, `updateConfiguracionYahoo(yahoo_email, yahoo_app_password)`

- [ ] **Step 1: Agregar el tipo a `domain.ts`**

Al final de `frontend/src/types/domain.ts`, agregar:

```ts
export interface ConfiguracionYahoo {
  yahoo_email: string | null;
  configurado: boolean;
}
```

- [ ] **Step 2: Crear el servicio**

```ts
// frontend/src/services/configuracion.ts
import { apiFetch } from "./api";
import type { ConfiguracionYahoo } from "../types/domain";

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
```

- [ ] **Step 3: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit -p .`
Expected: sin errores

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/domain.ts frontend/src/services/configuracion.ts
git commit -m "feat: tipos y servicio de configuración de Yahoo"
```

---

### Task 6: Frontend — formulario en `ConfiguracionPage.tsx`

**Files:**
- Modify: `frontend/src/pages/ConfiguracionPage.tsx`

**Interfaces:**
- Consumes: `getConfiguracionYahoo`, `updateConfiguracionYahoo` (Task 5)

- [ ] **Step 1: Leer el archivo actual**

`frontend/src/pages/ConfiguracionPage.tsx` hoy solo tiene el formulario de cambio de contraseña dentro de `<div className="max-w-sm space-y-4">`. Vamos a agregar una segunda sección debajo, con su propio `<div className="max-w-sm space-y-4">`, separada por un `<div className="pt-2 border-t border-border" />` o simplemente más espacio — seguir el mismo patrón visual que ya usa la página (label `text-sm font-medium text-foreground`, `space-y-1.5` por campo).

- [ ] **Step 2: Agregar el estado y la carga inicial**

Agregar los imports al principio del archivo:

```tsx
import { useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { changePassword } from "../services/auth";
import { getConfiguracionYahoo, updateConfiguracionYahoo } from "../services/configuracion";
```

Dentro del componente, junto a los estados existentes, agregar:

```tsx
  const [yahooEmail, setYahooEmail] = useState("");
  const [yahooPassword, setYahooPassword] = useState("");
  const [yahooConfigurado, setYahooConfigurado] = useState(false);
  const [yahooStatus, setYahooStatus] = useState("");

  useEffect(() => {
    getConfiguracionYahoo()
      .then((data) => {
        setYahooConfigurado(data.configurado);
        if (data.yahoo_email) setYahooEmail(data.yahoo_email);
      })
      .catch(() => {});
  }, []);

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
```

- [ ] **Step 3: Agregar la sección al JSX**

Después del bloque `<div className="max-w-sm space-y-4">...</div>` del cambio de contraseña, y antes del cierre del `<div className="max-w-3xl mx-auto space-y-4">` exterior, agregar:

```tsx
      <div className="max-w-sm space-y-4 pt-4 border-t border-border">
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
```

- [ ] **Step 4: Verificar tipos y build**

Run: `cd frontend && npx tsc --noEmit -p . && npm run build`
Expected: sin errores, build exitoso

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ConfiguracionPage.tsx
git commit -m "feat: formulario de credenciales Yahoo en Configuración"
```

---

### Task 7: Arreglar `.env.example`

**Files:**
- Modify: `backend/.env.example`

**Interfaces:**
- (ninguna — solo documentación)

- [ ] **Step 1: Reescribir el archivo completo**

El `.env.example` actual referencia `ENCRYPTION_KEY`/`TOTP_ISSUER` para 2FA (funcionalidad que este proyecto no tiene, sacada del broker original — ver ADR de auth simple sin 2FA) y no lista `YAHOO_EMAIL`/`YAHOO_APP_PASSWORD`, que sí son obligatorios en `config.py`. Reemplazar `backend/.env.example` completo por:

```bash
# Base de datos — PostgreSQL en producción, SQLite para dev local
DATABASE_URL=postgresql://user:password@localhost:5432/mails_nico
# DATABASE_URL=sqlite:///./dev.db

# Clave JWT — mínimo 32 caracteres, generar con: python -c "import secrets; print(secrets.token_urlsafe(48))"
SECRET_KEY=CAMBIAR_EN_PRODUCCION_min_32_chars

# Clave de cifrado simétrico (Fernet) para las credenciales de Yahoo guardadas en DB.
# Generar con: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
ENCRYPTION_KEY=CAMBIAR_EN_PRODUCCION_generar_fernet_key

# Credenciales de Yahoo — sirven de valor inicial/fallback. Una vez que el operario
# las carga desde Configuración > Cuenta de Yahoo, esas prevalecen sobre esto.
YAHOO_EMAIL=placeholder@yahoo.com
YAHOO_APP_PASSWORD=placeholder

# Expiración de tokens (horas)
ACCESS_TOKEN_EXPIRE_HOURS=8
REFRESH_TOKEN_EXPIRE_HOURS=24

# Orígenes permitidos para CORS (separados por coma)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
```

- [ ] **Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "fix: .env.example sin referencias a 2FA, con ENCRYPTION_KEY y credenciales Yahoo"
```

---

## Self-Review

**Spec coverage:** cubre el punto 2 de `docs/PENDIENTES.md` (Configuración incompleta) en la parte de credenciales Yahoo. Los "datos de empresa" que menciona ese punto (nombre, logo, color) ya se gestionan desde `PlantillaPage.tsx` — no se duplican acá a propósito.

**Placeholder scan:** sin TBD/TODO. Todo el código de cada step es completo y ejecutable.

**Type consistency:** `config_service.get_yahoo_credentials` devuelve `tuple[str, str]` consistente entre Task 2 (definición) y Task 3 (dos consumidores). `ConfiguracionYahooResponse` en Task 4 coincide con lo que el frontend espera en Task 5.

**Dependencia con otros planes:** el plan de "Endpoint de unsubscribe" y el de "Logo del mail" tocan `backend/app/main.py` y `backend/.env.example` — deben ejecutarse **después** de que este plan esté commiteado, no en paralelo con él.
