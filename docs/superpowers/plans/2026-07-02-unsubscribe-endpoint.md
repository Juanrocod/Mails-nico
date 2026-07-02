# Endpoint de Unsubscribe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Depende de:** `docs/superpowers/plans/2026-07-02-config-yahoo.md` debe estar commiteado antes de arrancar este plan (ambos tocan `backend/app/main.py` y `backend/.env.example`).

**Goal:** El link "darse de baja" que ya se genera en cada mail (`email_generator.py`) hoy no hace nada — este plan agrega la ruta pública que lo procesa y marca al consorcio como dado de baja.

**Architecture:** El link hoy expone `clave_union` en texto plano en la URL (`?clave=C001`), lo cual permite que cualquiera dé de baja a cualquier consorcio adivinando o enumerando claves. Lo reemplazamos por un token firmado con HMAC-SHA256 usando `SECRET_KEY` (sin agregar dependencias nuevas, `hmac`/`hashlib` son de la librería estándar). El endpoint `GET /unsubscribe/{token}` es el único de toda la API que **no** requiere `get_current_user` — lo abre un consorcio desde su cliente de mail, no el operario logueado.

**Tech Stack:** FastAPI, `hmac`/`hashlib`/`base64` (stdlib).

## Global Constraints

- El link de baja debe seguir funcionando para siempre (no expira) — un consorcio puede abrir un mail viejo meses después.
- La comparación de firma HMAC usa `hmac.compare_digest` (no `==`) para evitar timing attacks.
- "Notificación al operario" (pedida por el spec) se resuelve en este plan como un log estructurado del evento — no existe hoy ningún sistema de notificaciones push/email en la app, y construir uno está fuera de alcance de este plan. El efecto ya es visible para el operario en el próximo ciclo: el consorcio aparece en la solapa Filtrados con motivo "Dado de baja".
- Correr tests: `cd backend && venv\Scripts\python -m pytest -v`

---

## File Structure

- Modify: `backend/app/core/security.py` — `generate_unsubscribe_token()` / `verify_unsubscribe_token()`
- Modify: `backend/app/core/config.py` — agregar `BACKEND_PUBLIC_URL: str = ""`
- Modify: `backend/app/services/email_generator.py` — usar el token en vez de `clave_union` en texto plano
- Modify: `backend/app/services/smtp_sender.py` — pasar `unsubscribe_base_url=settings.BACKEND_PUBLIC_URL` al generar el mail
- Create: `backend/app/routers/unsubscribe.py`
- Modify: `backend/app/main.py` — registrar el router
- Modify: `backend/.env.example` — documentar `BACKEND_PUBLIC_URL`
- Create: `backend/tests/test_security_unsubscribe_token.py`
- Create: `backend/tests/test_unsubscribe_router.py`
- Modify: `backend/tests/test_email_generator.py` — verificar que el HTML generado usa el token, no la clave en texto plano

---

### Task 1: Generar y verificar el token firmado

**Files:**
- Modify: `backend/app/core/security.py`
- Create: `backend/tests/test_security_unsubscribe_token.py`

**Interfaces:**
- Produces: `generate_unsubscribe_token(clave_union: str) -> str`, `verify_unsubscribe_token(token: str) -> str | None`

- [ ] **Step 1: Escribir el test (falla primero)**

```python
# backend/tests/test_security_unsubscribe_token.py
from app.core.security import generate_unsubscribe_token, verify_unsubscribe_token


def test_generate_and_verify_roundtrip():
    token = generate_unsubscribe_token("C001")
    assert verify_unsubscribe_token(token) == "C001"


def test_verify_token_invalido_devuelve_none():
    assert verify_unsubscribe_token("no-es-un-token-valido") == None


def test_verify_token_manipulado_devuelve_none():
    token = generate_unsubscribe_token("C001")
    # cambiar un caracter del token para simular manipulación
    tampered = token[:-1] + ("a" if token[-1] != "a" else "b")
    assert verify_unsubscribe_token(tampered) == None


def test_tokens_de_distintas_claves_son_distintos():
    token_a = generate_unsubscribe_token("C001")
    token_b = generate_unsubscribe_token("C002")
    assert token_a != token_b
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_security_unsubscribe_token.py -v`
Expected: FAIL con `ImportError: cannot import name 'generate_unsubscribe_token'`

- [ ] **Step 3: Implementar las funciones en `security.py`**

Al final de `backend/app/core/security.py`, agregar:

```python
import base64
import hashlib
import hmac


def generate_unsubscribe_token(clave_union: str) -> str:
    from app.core.config import settings
    sig = hmac.new(settings.SECRET_KEY.encode(), clave_union.encode(), hashlib.sha256).hexdigest()
    payload = f"{clave_union}:{sig}"
    return base64.urlsafe_b64encode(payload.encode()).decode()


def verify_unsubscribe_token(token: str) -> str | None:
    from app.core.config import settings
    try:
        payload = base64.urlsafe_b64decode(token.encode()).decode()
        clave_union, sig = payload.rsplit(":", 1)
    except Exception:
        return None
    expected = hmac.new(settings.SECRET_KEY.encode(), clave_union.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    return clave_union
```

Nota: el import de `settings` se hace adentro de la función (no al principio del archivo), siguiendo el mismo patrón que ya usan `create_access_token`/`decode_token` más arriba en este mismo archivo — evita un import circular entre `security.py` y `config.py`.

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_security_unsubscribe_token.py -v`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/security.py backend/tests/test_security_unsubscribe_token.py
git commit -m "feat: token firmado HMAC para links de unsubscribe"
```

---

### Task 2: `email_generator.py` usa el token en vez de la clave en texto plano

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/services/email_generator.py`
- Modify: `backend/app/services/smtp_sender.py`
- Modify: `backend/tests/test_email_generator.py`

**Interfaces:**
- Consumes: `generate_unsubscribe_token` (Task 1)

- [ ] **Step 1: Agregar `BACKEND_PUBLIC_URL` a `Settings`**

En `backend/app/core/config.py`, agregar (junto a `ALLOWED_ORIGINS`):

```python
    BACKEND_PUBLIC_URL: str = ""
```

- [ ] **Step 2: Leer el test actual de `email_generator` para saber qué no romper**

Run (PowerShell): `Select-String -Path backend\tests\test_email_generator.py -Pattern "unsubscribe"`

Si hay algún assert que compara contra `?clave=`, hay que actualizarlo en el Step 5 de esta tarea para que compare contra el nuevo formato de URL con token.

- [ ] **Step 3: Escribir el test de la nueva URL de unsubscribe (falla primero)**

Agregar a `backend/tests/test_email_generator.py`:

```python
def test_unsubscribe_url_usa_token_firmado():
    from decimal import Decimal
    from app.services.excel_joiner import EnvioParsed
    from app.models.plantilla import Plantilla
    from app.core.security import verify_unsubscribe_token

    envio = EnvioParsed(
        clave_union="C001", nombre="Consorcio Uno", email="uno@mail.com",
        localidad=None, monto=Decimal("5000"), ciclo_numero_anterior=0,
    )
    plantilla = Plantilla(
        asunto="Deuda", cuerpo_html="<p>Hola {{nombre}}</p>",
        nombre_empresa="SA", color_primario="#1a56db", monto_minimo=0,
    )
    msg = generate_email(envio, plantilla, unsubscribe_base_url="https://api.ejemplo.com")
    html = msg.get_body(preferencelist=("html",)).get_content()

    assert "clave=C001" not in html  # ya no expone la clave en texto plano
    assert "https://api.ejemplo.com/unsubscribe/" in html

    # el token embebido en el HTML debe verificar correctamente contra C001
    start = html.index("/unsubscribe/") + len("/unsubscribe/")
    end = html.index('"', start)
    token = html[start:end]
    assert verify_unsubscribe_token(token) == "C001"
```

(Ajustar el import de `generate_email` al que ya usa el resto del archivo si difiere.)

- [ ] **Step 4: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_email_generator.py -v -k unsubscribe_url`
Expected: FAIL — el HTML actual todavía tiene `?clave=C001`, no `/unsubscribe/<token>`

- [ ] **Step 5: Actualizar `email_generator.py`**

En `backend/app/services/email_generator.py`, agregar el import:

```python
from app.core.security import generate_unsubscribe_token
```

Y reemplazar las líneas 21-25:
```python
    unsubscribe_url = (
        f"{unsubscribe_base_url}/unsubscribe?clave={envio.clave_union}"
        if unsubscribe_base_url
        else "#"
    )
```
por:
```python
    if unsubscribe_base_url:
        token = generate_unsubscribe_token(envio.clave_union)
        unsubscribe_url = f"{unsubscribe_base_url}/unsubscribe/{token}"
    else:
        unsubscribe_url = "#"
```

- [ ] **Step 6: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_email_generator.py -v`
Expected: todos los tests de ese archivo pasan

- [ ] **Step 7: Pasar la URL pública real al generar el mail en `smtp_sender.py`**

En `backend/app/services/smtp_sender.py`, la línea 59 hoy es:
```python
        msg = generate_email(parsed, plantilla)
```
Reemplazar por:
```python
        msg = generate_email(parsed, plantilla, unsubscribe_base_url=settings.BACKEND_PUBLIC_URL)
```
(El import de `settings` en este archivo ya existe si no se borró en el plan de config-yahoo — si se borró porque quedó sin uso, volver a agregar `from app.core.config import settings`.)

- [ ] **Step 8: Correr toda la suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos pasan

- [ ] **Step 9: Commit**

```bash
git add backend/app/core/config.py backend/app/services/email_generator.py backend/app/services/smtp_sender.py backend/tests/test_email_generator.py
git commit -m "feat: link de unsubscribe usa token firmado en vez de clave en texto plano"
```

---

### Task 3: Endpoint público `GET /unsubscribe/{token}`

**Files:**
- Create: `backend/app/routers/unsubscribe.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_unsubscribe_router.py`

**Interfaces:**
- Consumes: `verify_unsubscribe_token` (Task 1)

- [ ] **Step 1: Escribir el test (falla primero)**

```python
# backend/tests/test_unsubscribe_router.py
from datetime import datetime, timezone
from app.models.cliente_maestro import ClienteMaestro
from app.core.security import generate_unsubscribe_token


def _seed_cliente(db, clave, baja=False):
    c = ClienteMaestro(
        clave_union=clave, nombre="Consorcio Test", email="test@mail.com",
        prefiere_no_recibir_email=baja, actualizado_en=datetime.now(timezone.utc),
    )
    db.add(c)
    db.flush()
    return c


def test_unsubscribe_marca_prefiere_no_recibir_email(client, db):
    _seed_cliente(db, "C500")
    token = generate_unsubscribe_token("C500")

    r = client.get(f"/unsubscribe/{token}")

    assert r.status_code == 200
    db.expire_all()
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C500").first()
    assert cliente.prefiere_no_recibir_email is True


def test_unsubscribe_no_requiere_autenticacion(client, db):
    _seed_cliente(db, "C501")
    token = generate_unsubscribe_token("C501")
    r = client.get(f"/unsubscribe/{token}")
    assert r.status_code == 200  # sin header Authorization y funciona igual


def test_unsubscribe_token_invalido_devuelve_400(client):
    r = client.get("/unsubscribe/token-truchisimo")
    assert r.status_code == 400


def test_unsubscribe_cliente_inexistente_devuelve_404(client):
    token = generate_unsubscribe_token("NO-EXISTE")
    r = client.get(f"/unsubscribe/{token}")
    assert r.status_code == 404


def test_unsubscribe_es_idempotente(client, db):
    _seed_cliente(db, "C502", baja=True)
    token = generate_unsubscribe_token("C502")
    r = client.get(f"/unsubscribe/{token}")
    assert r.status_code == 200
    db.expire_all()
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C502").first()
    assert cliente.prefiere_no_recibir_email is True
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_unsubscribe_router.py -v`
Expected: FAIL con 404 (ruta no existe)

- [ ] **Step 3: Implementar el router**

```python
# backend/app/routers/unsubscribe.py
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_unsubscribe_token
from app.models.cliente_maestro import ClienteMaestro

router = APIRouter(tags=["unsubscribe"])
_logger = logging.getLogger("mails_nico.unsubscribe")

_PAGINA_CONFIRMACION = """<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><title>Baja confirmada</title></head>
<body style="font-family: Arial, sans-serif; max-width: 480px; margin: 60px auto; text-align: center; color: #333;">
  <h1 style="font-size: 20px;">Listo, diste de baja tu suscripción</h1>
  <p>No vas a recibir más recordatorios de cobro por mail de este remitente.</p>
</body>
</html>"""


@router.get("/unsubscribe/{token}", response_class=HTMLResponse)
def unsubscribe(token: str, db: Session = Depends(get_db)):
    clave_union = verify_unsubscribe_token(token)
    if clave_union is None:
        raise HTTPException(status_code=400, detail="Link inválido")

    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == clave_union).first()
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if not cliente.prefiere_no_recibir_email:
        cliente.prefiere_no_recibir_email = True
        db.add(cliente)
        db.commit()
        _logger.info(
            "Baja voluntaria vía unsubscribe: clave_union=%s nombre=%s",
            cliente.clave_union, cliente.nombre,
        )

    return HTMLResponse(content=_PAGINA_CONFIRMACION)
```

Nota: este router **no** usa `Depends(get_current_user)` en ningún endpoint — es el único caso en toda la API. Lo abre el consorcio desde su cliente de mail, no el operario logueado.

- [ ] **Step 4: Registrar el router en `main.py`**

En `backend/app/main.py`, cambiar el import (línea agregada por el plan de config-yahoo, ahora con un router más):
```python
from app.routers import auth, plantilla, maestro, ciclos, configuracion
```
por
```python
from app.routers import auth, plantilla, maestro, ciclos, configuracion, unsubscribe
```

Y agregar después de `app.include_router(configuracion.router)`:
```python
app.include_router(unsubscribe.router)
```

- [ ] **Step 5: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_unsubscribe_router.py -v`
Expected: `5 passed`

- [ ] **Step 6: Correr toda la suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos pasan

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/unsubscribe.py backend/app/main.py backend/tests/test_unsubscribe_router.py
git commit -m "feat: endpoint público GET /unsubscribe/{token}"
```

---

### Task 4: Documentar `BACKEND_PUBLIC_URL` en `.env.example`

**Files:**
- Modify: `backend/.env.example`

- [ ] **Step 1: Agregar la variable**

Al final de `backend/.env.example` (el plan de config-yahoo ya reescribió este archivo antes; acá solo se agrega, no se pisa lo demás), agregar:

```bash
# URL pública del backend (para armar el link de unsubscribe en los mails).
# En dev puede quedar vacío — el link queda deshabilitado ("#") hasta configurar esto.
BACKEND_PUBLIC_URL=https://api.tudominio.com
```

- [ ] **Step 2: Commit**

```bash
git add backend/.env.example
git commit -m "docs: agregar BACKEND_PUBLIC_URL a .env.example"
```

---

## Self-Review

**Spec coverage:** cubre el punto crítico #1 de `docs/PENDIENTES.md` (endpoint de unsubscribe) completo, incluyendo el requisito legal de que el link funcione. La "notificación al operario" se resuelve con logging estructurado — documentado explícitamente como decisión de alcance en Global Constraints, no es un placeholder olvidado.

**Placeholder scan:** sin TBD. Todo el código está completo.

**Type consistency:** `generate_unsubscribe_token`/`verify_unsubscribe_token` (Task 1) se consumen igual en Task 2 (`email_generator.py`) y Task 3 (`unsubscribe.py`) — mismas firmas.

**Seguridad:** se corrige explícitamente la vulnerabilidad de enumeración de `clave_union` que tenía el link original (era texto plano en la URL) — el token firmado impide forjar o adivinar links de baja de otros consorcios.
