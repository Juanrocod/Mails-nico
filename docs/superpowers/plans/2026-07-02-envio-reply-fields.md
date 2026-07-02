# Campos reply_en y tiene_adjunto en Envio — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Depende de:** `docs/superpowers/plans/2026-07-02-config-yahoo.md` debe estar commiteado antes de arrancar (ese plan crea la migración `0002`, esta la encadena como `0003`; y ambos tocan `backend/app/services/imap_watcher.py`, en secciones distintas del archivo pero conviene no editarlo en paralelo).
> Puede ejecutarse en paralelo con `unsubscribe-endpoint` y `logo-upload` (no comparten ningún archivo).

**Goal:** El spec (sección 5, modelo de datos) define `reply_en` (fecha exacta de la respuesta, separada del snippet) y `tiene_adjunto` (si la respuesta tenía adjunto) en `Envio`. Hoy no existen — sin ellos no se puede distinguir un `PAGO` detectado por adjunto real de uno marcado a mano por el operario, ni mostrar cuándo llegó la respuesta.

**Architecture:** Dos columnas nuevas en `envios` (migración `0003`). `reply_classifier.classify()` hoy solo devuelve el `EstadoEnvio` — se extiende para devolver también si el mensaje tenía adjunto, y `imap_watcher._poll_inbox()` setea ambos campos al procesar cada respuesta. El override manual del operario (`PATCH /envios/{id}/estado`, `CONTESTADO` → `PAGO`) **no** togglea `tiene_adjunto` — ese campo refleja únicamente lo que vino por IMAP, que es justamente el dato que permite distinguir ambos caminos.

**Tech Stack:** SQLAlchemy 2.0, Alembic.

## Global Constraints

- `reply_en` es nullable (`NO_CONTESTADO` no tiene respuesta todavía). `tiene_adjunto` no es nullable, default `False`.
- No tocar la lógica de clasificación existente (mailer-daemon → REBOTADO, adjunto → PAGO, texto → CONTESTADO) — solo se agrega el dato extra que ya se calculaba internamente pero se descartaba.
- Correr tests: `cd backend && venv\Scripts\python -m pytest -v`

---

## File Structure

- Create: `backend/alembic/versions/0003_envio_reply_fields.py`
- Modify: `backend/app/models/envio.py`
- Modify: `backend/app/services/reply_classifier.py` — devolver también `tiene_adjunto`
- Modify: `backend/app/services/imap_watcher.py` — setear `reply_en`/`tiene_adjunto`
- Modify: `backend/app/schemas/envio.py` — exponer los campos nuevos
- Modify: `backend/tests/test_reply_classifier.py`
- Modify: `backend/tests/test_models.py` (o crear si no existe test de este modelo)
- Modify: `frontend/src/types/domain.ts` — agregar los campos a `Envio`
- Modify: `frontend/src/components/envios/EnvioDrawer.tsx` — mostrar `reply_en` en vez de solo el snippet

---

### Task 1: Migración + modelo

**Files:**
- Create: `backend/alembic/versions/0003_envio_reply_fields.py`
- Modify: `backend/app/models/envio.py`

**Interfaces:**
- Produces: `Envio.reply_en: datetime | None`, `Envio.tiene_adjunto: bool`

- [ ] **Step 1: Agregar las columnas al modelo**

En `backend/app/models/envio.py`, agregar el import de `Boolean` a la línea 4:
```python
from sqlalchemy import Column, String, Text, Numeric, Integer, DateTime, ForeignKey, Enum, Boolean
```

Y agregar las dos columnas nuevas después de `reply_snippet` (línea 36):
```python
    reply_snippet = Column(Text, nullable=True)
    reply_en = Column(DateTime, nullable=True)
    tiene_adjunto = Column(Boolean, nullable=False, default=False)
```

- [ ] **Step 2: Crear la migración**

Usar `batch_alter_table`, como indica `.claude/rules/backend.md`, para compatibilidad SQLite/PostgreSQL:

```python
# backend/alembic/versions/0003_envio_reply_fields.py
"""envio reply_en y tiene_adjunto

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.add_column(sa.Column("reply_en", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("tiene_adjunto", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.drop_column("tiene_adjunto")
        batch_op.drop_column("reply_en")
```

- [ ] **Step 3: Correr la migración en la DB de desarrollo**

Run: `cd backend && venv\Scripts\python -m alembic upgrade head`
Expected: termina sin error, `-> 0003, envio reply_en y tiene_adjunto` en la salida.

- [ ] **Step 4: Correr toda la suite (los tests de conftest usan `Base.metadata.create_all`, no Alembic, así que ya ven las columnas nuevas sin pasos extra)**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos pasan (el modelo con columnas nuevas no rompe nada existente porque son nullable/con default)

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/envio.py backend/alembic/versions/0003_envio_reply_fields.py
git commit -m "feat: columnas reply_en y tiene_adjunto en Envio"
```

---

### Task 2: `reply_classifier` devuelve también si hay adjunto

**Files:**
- Modify: `backend/app/services/reply_classifier.py`
- Modify: `backend/tests/test_reply_classifier.py`

**Interfaces:**
- Produces: `classify(msg) -> tuple[EstadoEnvio, bool]` (antes devolvía solo `EstadoEnvio`) — el segundo valor es `tiene_adjunto`.

- [ ] **Step 1: Ver los tests actuales para saber qué firma están usando**

Run (PowerShell): `Get-Content backend\tests\test_reply_classifier.py`

Actualizar cada `assert classify(msg) == EstadoEnvio.X` por `assert classify(msg) == (EstadoEnvio.X, <True|False>)` según corresponda (ver Step 2 para los valores exactos esperados).

- [ ] **Step 2: Reescribir el test completo con la nueva firma**

```python
# backend/tests/test_reply_classifier.py
from email.message import EmailMessage
from app.models.envio import EstadoEnvio
from app.services.reply_classifier import classify


def test_classify_mailer_daemon_es_rebotado():
    msg = EmailMessage()
    msg["From"] = "MAILER-DAEMON@yahoo.com"
    msg.set_content("Delivery failed")
    assert classify(msg) == (EstadoEnvio.REBOTADO, False)


def test_classify_postmaster_es_rebotado():
    msg = EmailMessage()
    msg["From"] = "postmaster@dominio.com"
    msg.set_content("Undeliverable")
    assert classify(msg) == (EstadoEnvio.REBOTADO, False)


def test_classify_con_adjunto_pdf_es_pago():
    msg = EmailMessage()
    msg["From"] = "cliente@mail.com"
    msg.set_content("Adjunto comprobante")
    msg.add_attachment(b"%PDF-1.4 fake", maintype="application", subtype="pdf", filename="comprobante.pdf")
    assert classify(msg) == (EstadoEnvio.PAGO, True)


def test_classify_con_adjunto_imagen_es_pago():
    msg = EmailMessage()
    msg["From"] = "cliente@mail.com"
    msg.set_content("Foto del pago")
    msg.add_attachment(b"fake-image-bytes", maintype="image", subtype="png", filename="pago.png")
    assert classify(msg) == (EstadoEnvio.PAGO, True)


def test_classify_solo_texto_es_contestado():
    msg = EmailMessage()
    msg["From"] = "cliente@mail.com"
    msg.set_content("Ya voy a pagar la semana que viene")
    assert classify(msg) == (EstadoEnvio.CONTESTADO, False)
```

- [ ] **Step 3: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_reply_classifier.py -v`
Expected: FAIL — `classify` todavía devuelve solo `EstadoEnvio`, no la tupla.

- [ ] **Step 4: Implementar el cambio de firma**

Reemplazar `backend/app/services/reply_classifier.py` completo:

```python
import email.message
from app.models.envio import EstadoEnvio


def classify(msg: email.message.Message) -> tuple[EstadoEnvio, bool]:
    """
    Clasifica una respuesta de email en estados de envío.

    Lógica:
    1. Si From contiene 'mailer-daemon' o 'postmaster' → REBOTADO
    2. Si tiene adjunto (image/* o application/pdf) → PAGO
    3. Si solo texto → CONTESTADO

    Devuelve (estado, tiene_adjunto).
    """
    from_addr = str(msg.get("From", "")).lower()
    if "mailer-daemon" in from_addr or "postmaster" in from_addr:
        return EstadoEnvio.REBOTADO, False

    for part in msg.walk():
        ct = part.get_content_type()
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in disposition or ct.startswith("image/") or ct == "application/pdf":
            return EstadoEnvio.PAGO, True

    return EstadoEnvio.CONTESTADO, False
```

- [ ] **Step 5: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_reply_classifier.py -v`
Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/reply_classifier.py backend/tests/test_reply_classifier.py
git commit -m "feat: classify() también informa si la respuesta tiene adjunto"
```

---

### Task 3: `imap_watcher` setea los campos nuevos

**Files:**
- Modify: `backend/app/services/imap_watcher.py`

**Interfaces:**
- Consumes: `classify(msg) -> tuple[EstadoEnvio, bool]` (Task 2)

- [ ] **Step 1: Actualizar el uso de `classify` en `_poll_inbox`**

En `backend/app/services/imap_watcher.py`, reemplazar las líneas 79-83:
```python
                new_estado = classify(msg)
                snippet = _extract_snippet(msg)
                matched_envio.estado = new_estado
                matched_envio.reply_snippet = snippet
                matched_envio.actualizado_en = datetime.now(timezone.utc)
```
por:
```python
                new_estado, tiene_adjunto = classify(msg)
                snippet = _extract_snippet(msg)
                matched_envio.estado = new_estado
                matched_envio.reply_snippet = snippet
                matched_envio.reply_en = datetime.now(timezone.utc)
                matched_envio.tiene_adjunto = tiene_adjunto
                matched_envio.actualizado_en = datetime.now(timezone.utc)
```

- [ ] **Step 2: Verificar si hay un test de `imap_watcher` que llame a `classify` y actualizar su firma si hace falta**

Run (PowerShell): `Get-ChildItem backend\tests | Select-String -Pattern "imap_watcher" -List`

Si existe un test que mockea o llama `classify` directamente, actualizarlo para esperar la tupla `(estado, tiene_adjunto)` en vez de solo `estado`, siguiendo el mismo patrón del Step 2 de Task 2.

- [ ] **Step 3: Correr toda la suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos pasan

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/imap_watcher.py
git commit -m "feat: imap_watcher setea reply_en y tiene_adjunto al clasificar respuestas"
```

---

### Task 4: Exponer los campos en la API y el frontend

**Files:**
- Modify: `backend/app/schemas/envio.py`
- Modify: `frontend/src/types/domain.ts`
- Modify: `frontend/src/components/envios/EnvioDrawer.tsx`

**Interfaces:**
- Produces: `EnvioSchema.reply_en: datetime | None`, `EnvioSchema.tiene_adjunto: bool`; `Envio.reply_en`/`tiene_adjunto` en el tipo TS

- [ ] **Step 1: Agregar los campos al schema de respuesta**

En `backend/app/schemas/envio.py`, agregar después de `reply_snippet: Optional[str]` (línea 22):
```python
    reply_snippet: Optional[str]
    reply_en: Optional[datetime]
    tiene_adjunto: bool
```

- [ ] **Step 2: Correr los tests de ciclos (usan `EnvioSchema` para serializar)**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_ciclos.py -v`
Expected: todos pasan (pydantic con `from_attributes=True` toma los campos nuevos del modelo automáticamente, sin cambios en los routers)

- [ ] **Step 3: Agregar los campos al tipo TypeScript**

En `frontend/src/types/domain.ts`, dentro de `interface Envio`, agregar después de `reply_snippet: string | null;`:
```ts
  reply_snippet: string | null;
  reply_en: string | null;
  tiene_adjunto: boolean;
```

- [ ] **Step 4: Mostrar `reply_en` en el drawer**

En `frontend/src/components/envios/EnvioDrawer.tsx`, dentro de la sección `<section className="mt-6 space-y-1">` que tiene `Row` de Email/Monto/Enviado, agregar una fila más justo antes del bloque de "Respuesta" (después del `Row` de "Enviado"):

```tsx
              {envio.reply_en && (
                <Row label="Respondido" value={new Date(envio.reply_en).toLocaleString("es-AR")} />
              )}
```

(Insertar dentro del mismo `<section>` que ya tiene los otros `<Row>`, siguiendo la estructura existente del archivo.)

- [ ] **Step 5: Verificar tipos y build**

Run: `cd frontend && npx tsc --noEmit -p . && npm run build`
Expected: sin errores

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/envio.py frontend/src/types/domain.ts frontend/src/components/envios/EnvioDrawer.tsx
git commit -m "feat: exponer reply_en y tiene_adjunto en API y UI"
```

---

## Self-Review

**Spec coverage:** cubre el punto "Menor" #6 de `docs/PENDIENTES.md` completo — modelo, migración, poblado desde IMAP, y visibilidad en la UI.

**Placeholder scan:** sin TBD.

**Type consistency:** `classify()` cambia de firma (`EstadoEnvio` → `tuple[EstadoEnvio, bool]`) en Task 2 — Task 3 es el único otro lugar que la llama y se actualiza en el mismo plan, con un step explícito (Task 3, Step 2) para buscar cualquier otro consumidor que se me haya escapado.

**Nota de diseño:** el override manual `CONTESTADO → PAGO` (`PATCH /envios/{id}/estado`, en `routers/ciclos.py`) no toca `tiene_adjunto` — queda `False` si el operario lo marcó a mano sin que haya llegado un adjunto real por IMAP. Esto es intencional: es justamente la distinción que el spec pedía poder hacer.
