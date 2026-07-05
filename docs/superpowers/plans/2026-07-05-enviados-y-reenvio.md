# Enviados y Reenvío de Fallidos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Agregar una pestaña "Enviados" que muestre lo que realmente salió por mail (no lo que quedó `NO_CONTESTADO`), redefinir "Para Enviar" para que después de confirmar un ciclo muestre solo lo que falló al enviar, y permitir reenviar esos fallidos (uno por uno o todos juntos) revalidando contra el Maestro de Clientes actualizado.

**Architecture:** Se distingue "se mandó" de "falló al mandar" usando los campos `message_id`/`enviado_en` que ya existen en `Envio` — sin agregar ningún estado nuevo al enum. Una función nueva (`revalidar_para_reenvio`) vuelve a chequear un envío contra el Maestro antes de reintentarlo. Dos endpoints nuevos reusan `smtp_sender.enviar_ciclo` sin modificarlo (uno para un envío, otro en bloque vía SSE, reusando el mismo helper de streaming que ya usa la confirmación).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, pytest, React 18 + TypeScript.

## Global Constraints

- No se agrega ningún valor nuevo a `EstadoEnvio` ni a `MotivoFiltrado` — cero migraciones Alembic en este plan.
- Un envío se considera "enviado" si y solo si `message_id` no es null (sin importar su `estado`).
- Un envío se considera "fallido, pendiente de reenvío" si `estado == NO_CONTESTADO` y `message_id` es null.
- "Enviados" es un registro permanente: un envío que después pasa a Contestado/Pago/Rebotado sigue apareciendo en Enviados.
- Los Rebotados nunca se reenvían (regla ya existente del sistema) — el reenvío solo aplica a envíos fallidos, nunca a rebotes.
- `smtp_sender.enviar_ciclo` no se modifica — se reusa tal cual.
- Tests backend: `cd backend && venv/Scripts/python -m pytest -v`.
- Tests frontend: no hay infraestructura automatizada; verificación con `cd frontend && npx tsc -b` + prueba manual en el navegador.

## Contexto importante para quien implemente

**Este repo NO limpia `envios`/`ciclos`/`clientes_maestro` entre tests** (el fixture `db` en `backend/tests/conftest.py` solo limpia `configuracion_sistema`). La base de test es un SQLite en memoria compartido entre todos los tests de la corrida. Cualquier `clave_union` nueva que uses tiene que ser única en todo el archivo de test donde la agregues. Además, si un test necesita "el ciclo activo" y depende de que sea *el suyo*, tiene que desactivar explícitamente cualquier otro ciclo activo dejado por tests anteriores (`db.query(Ciclo).update({"activo": False})`) antes de crear el propio — no alcanza con crear uno nuevo con `activo=True` y asumir que es el único.

Claves ya usadas en los archivos que vas a tocar (no las reutilices): `test_excel_joiner.py` usa `C001-C005`, `C010-C011`; `test_ciclos.py` usa `C101`, `C102`, `C199`.

---

### Task 1: Backend — revalidar un envío contra el Maestro antes de reenviarlo

**Files:**
- Modify: `backend/app/services/excel_joiner.py`
- Test: `backend/tests/test_excel_joiner.py`

**Interfaces:**
- Produces: `revalidar_para_reenvio(db: Session, envio: Envio) -> tuple[bool, Optional[str]]`. Si es válido, actualiza `envio.email` y `envio.nombre_consorcio` en memoria (sin commitear) y devuelve `(True, None)`. Si no, devuelve `(False, "<motivo>")` sin tocar el envío.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_excel_joiner.py`:

```python
def test_revalidar_para_reenvio_cliente_no_encontrado(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.services.excel_joiner import revalidar_para_reenvio

    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C030", nombre_consorcio="X",
        email=None, monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is False
    assert "no existe" in motivo


def test_revalidar_para_reenvio_dado_de_baja(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.services.excel_joiner import revalidar_para_reenvio

    _add_cliente(db, "C031", "Consorcio Baja", email="baja@mail.com", baja=True)
    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C031", nombre_consorcio="Consorcio Baja",
        email="baja@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is False
    assert "baja" in motivo.lower()


def test_revalidar_para_reenvio_inactivo(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.cliente_maestro import ClienteMaestro
    from app.services.excel_joiner import revalidar_para_reenvio

    _add_cliente(db, "C032", "Consorcio Inactivo", email="inactivo@mail.com")
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C032").first()
    cliente.activo = False
    db.flush()

    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C032", nombre_consorcio="Consorcio Inactivo",
        email="inactivo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is False
    assert "inactivo" in motivo.lower()


def test_revalidar_para_reenvio_email_invalido(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.services.excel_joiner import revalidar_para_reenvio

    _add_cliente(db, "C033", "Consorcio Email Malo", email="no-es-un-email")
    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C033", nombre_consorcio="Consorcio Email Malo",
        email="no-es-un-email", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is False
    assert "email" in motivo.lower()


def test_revalidar_para_reenvio_valido_actualiza_datos(db):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.services.excel_joiner import revalidar_para_reenvio

    _add_cliente(db, "C034", "Consorcio Corregido", email="corregido@mail.com")
    ciclo = Ciclo(numero=1, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="C034", nombre_consorcio="Nombre Viejo",
        email="viejo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.flush()

    ok, motivo = revalidar_para_reenvio(db, envio)
    assert ok is True
    assert motivo is None
    assert envio.email == "corregido@mail.com"
    assert envio.nombre_consorcio == "Consorcio Corregido"
```

This needs `Envio` and `EstadoEnvio` importable at the top of the test file — add this import line at the top of `backend/tests/test_excel_joiner.py`, right after the existing `from app.models.cliente_maestro import ClienteMaestro` line:

```python
from app.models.envio import Envio, EstadoEnvio
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_excel_joiner.py -v`
Expected: FAIL with `ImportError: cannot import name 'revalidar_para_reenvio' from 'app.services.excel_joiner'`

- [ ] **Step 3: Implement `revalidar_para_reenvio`**

Append this function to the end of `backend/app/services/excel_joiner.py` (the file already imports `Envio` and `Optional` at the top, no new imports needed):

```python
def revalidar_para_reenvio(db: Session, envio: Envio) -> tuple[bool, Optional[str]]:
    """
    Vuelve a validar un Envio contra el Maestro de Clientes antes de reenviarlo.
    Si es valido, actualiza envio.email y envio.nombre_consorcio con los datos
    actuales del Maestro (sin commitear) y devuelve (True, None). Si no es
    valido, no toca el envio y devuelve (False, "<motivo>").
    """
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == envio.clave_union).first()
    if cliente is None:
        return False, "El cliente ya no existe en el Maestro."
    if cliente.prefiere_no_recibir_email:
        return False, "El cliente está dado de baja."
    if not cliente.activo:
        return False, "El cliente está inactivo en el Maestro."
    if not cliente.email or not is_valid_email(cliente.email):
        return False, "El cliente no tiene un email válido en el Maestro."

    envio.email = cliente.email
    envio.nombre_consorcio = cliente.nombre
    return True, None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_excel_joiner.py -v`
Expected: PASS (todos, incluidos los 8 tests pre-existentes de este archivo)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && venv/Scripts/python -m pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/excel_joiner.py backend/tests/test_excel_joiner.py
git commit -m "feat: revalidar envio contra el maestro antes de reenviarlo"
```

---

### Task 2: Backend — endpoint de reenvío individual

**Files:**
- Modify: `backend/app/routers/ciclos.py`
- Test: `backend/tests/test_ciclos.py`

**Interfaces:**
- Consumes: `revalidar_para_reenvio` (Task 1), `enviar_ciclo` (ya existe, sin cambios).
- Produces: `POST /envios/{envio_id}/reenviar` → `200` con el `Envio` actualizado, o `400`/`404`/`502` según el caso.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_ciclos.py`:

```python
def test_reenviar_envio_no_elegible_400(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    ciclo = Ciclo(numero=201, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=201, clave_union="C201", nombre_consorcio="Ya Enviado",
        email="ya@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        message_id="<abc@yahoo.com>", enviado_en=datetime.now(timezone.utc),
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    r = client.post(f"/envios/{envio.id}/reenviar", headers=auth_headers)
    assert r.status_code == 400


def test_reenviar_envio_cliente_invalido_400(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    ciclo = Ciclo(numero=202, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=202, clave_union="C202", nombre_consorcio="Sin Maestro",
        email="viejo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    r = client.post(f"/envios/{envio.id}/reenviar", headers=auth_headers)
    assert r.status_code == 400
    assert "Maestro" in r.json()["detail"]


def test_reenviar_envio_exitoso(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from unittest.mock import patch
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    from app.models.cliente_maestro import ClienteMaestro

    db.add(ClienteMaestro(
        clave_union="C203", nombre="Consorcio Corregido", email="corregido@mail.com",
        actualizado_en=datetime.now(timezone.utc),
    ))
    ciclo = Ciclo(numero=203, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=203, clave_union="C203", nombre_consorcio="Nombre Viejo",
        email="viejo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<nuevo@yahoo.com>"
        r = client.post(f"/envios/{envio.id}/reenviar", headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "corregido@mail.com"
    assert data["message_id"] == "<nuevo@yahoo.com>"


def test_reenviar_envio_inexistente_404(client, auth_headers):
    import uuid
    r = client.post(f"/envios/{uuid.uuid4()}/reenviar", headers=auth_headers)
    assert r.status_code == 404
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_ciclos.py -v`
Expected: FAIL — `404 Not Found` en las 4 pruebas nuevas (la ruta no existe todavía)

- [ ] **Step 3: Add the endpoint**

In `backend/app/routers/ciclos.py`, change this import line:

```python
from app.services.excel_joiner import join_deudores
```

to:

```python
from app.services.excel_joiner import join_deudores, revalidar_para_reenvio
```

Then add this endpoint right after `update_envio_estado` (at the end of the file):

```python
@router.post("/envios/{envio_id}/reenviar", response_model=EnvioSchema)
async def reenviar_envio(
    envio_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    envio = db.get(Envio, envio_id)
    if envio is None:
        raise HTTPException(status_code=404, detail="Envio no encontrado")
    if envio.estado != EstadoEnvio.NO_CONTESTADO or envio.message_id:
        raise HTTPException(status_code=400, detail="Este envio no esta pendiente de reenvio")

    ok, motivo = revalidar_para_reenvio(db, envio)
    if not ok:
        raise HTTPException(status_code=400, detail=motivo)

    async def _noop(_envio: Envio) -> None:
        pass

    await enviar_ciclo([envio], db, _noop)
    db.refresh(envio)
    if not envio.message_id:
        raise HTTPException(
            status_code=502,
            detail="No se pudo enviar el mail. Revisá las credenciales del proveedor de email.",
        )
    return envio
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_ciclos.py -v`
Expected: PASS (todas, incluidas las pre-existentes)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && venv/Scripts/python -m pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/ciclos.py backend/tests/test_ciclos.py
git commit -m "feat: endpoint de reenvio individual para envios fallidos"
```

---

### Task 3: Backend — reenvío en bloque de todos los fallidos del ciclo activo

**Files:**
- Modify: `backend/app/routers/ciclos.py`
- Test: `backend/tests/test_ciclos.py`

**Interfaces:**
- Consumes: `revalidar_para_reenvio` (Task 1), `_stream_envios` (ya existe en este archivo, sin cambios).
- Produces: `POST /ciclos/activo/reenviar-fallidos` → SSE stream igual al de `/ciclos/confirmar`, con un chunk final `{"done": true, "total": N, "saltados": [{"id": "...", "motivo": "..."}]}`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_ciclos.py`:

```python
def test_reenviar_fallidos_mezcla_elegibles_e_inelegibles(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from unittest.mock import patch
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio
    from app.models.cliente_maestro import ClienteMaestro

    db.add(ClienteMaestro(
        clave_union="C210", nombre="Consorcio Valido", email="valido@mail.com",
        actualizado_en=datetime.now(timezone.utc),
    ))

    # Este test depende de "el" ciclo activo — desactivar cualquier otro que
    # haya quedado activo de un test anterior en esta misma corrida.
    db.query(Ciclo).update({"activo": False})
    db.flush()

    ciclo = Ciclo(numero=299, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()

    envio_ok = Envio(
        ciclo_id=ciclo.id, ciclo_numero=299, clave_union="C210", nombre_consorcio="Nombre Viejo",
        email="viejo@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    envio_sin_maestro = Envio(
        ciclo_id=ciclo.id, ciclo_numero=299, clave_union="C211", nombre_consorcio="Sin Maestro",
        email="x@mail.com", monto=Decimal("2000"), estado=EstadoEnvio.NO_CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio_ok)
    db.add(envio_sin_maestro)
    db.commit()

    with patch("app.services.smtp_sender._send_single_email") as mock_send:
        mock_send.return_value = "<reenv@yahoo.com>"
        r = client.post("/ciclos/activo/reenviar-fallidos", headers=auth_headers)

    assert r.status_code == 200
    body = r.text
    assert '"done"' in body
    assert '"saltados"' in body
    assert str(envio_sin_maestro.id) in body
    assert "no existe" in body

    db.expire_all()
    db.refresh(envio_ok)
    db.refresh(envio_sin_maestro)
    assert envio_ok.message_id == "<reenv@yahoo.com>"
    assert envio_sin_maestro.message_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_ciclos.py::test_reenviar_fallidos_mezcla_elegibles_e_inelegibles -v`
Expected: FAIL with `404 Not Found` (la ruta no existe todavía)

- [ ] **Step 3: Add the bulk resend endpoint**

Append this endpoint to the end of `backend/app/routers/ciclos.py` (after the `reenviar_envio` endpoint added in Task 2):

```python
@router.post("/ciclos/activo/reenviar-fallidos")
async def reenviar_fallidos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ciclo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if not ciclo:
        raise HTTPException(status_code=404, detail="No hay un ciclo activo")

    fallidos = (
        db.query(Envio)
        .filter(
            Envio.ciclo_id == ciclo.id,
            Envio.estado == EstadoEnvio.NO_CONTESTADO,
            Envio.message_id.is_(None),
        )
        .all()
    )

    listos: list[Envio] = []
    saltados: list[dict] = []
    for envio in fallidos:
        ok, motivo = revalidar_para_reenvio(db, envio)
        if ok:
            listos.append(envio)
        else:
            saltados.append({"id": str(envio.id), "motivo": motivo})

    async def event_generator():
        async for chunk in _stream_envios(listos, db):
            yield chunk
        total = len(listos)
        yield f"data: {json.dumps({'done': True, 'total': total, 'saltados': saltados})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_ciclos.py -v`
Expected: PASS (todas)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && venv/Scripts/python -m pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/ciclos.py backend/tests/test_ciclos.py
git commit -m "feat: endpoint de reenvio en bloque de fallidos del ciclo activo"
```

---

### Task 4: Frontend — servicio de reenvío

**Files:**
- Modify: `frontend/src/services/ciclos.ts`

**Interfaces:**
- Consumes: `POST /envios/{id}/reenviar`, `POST /ciclos/activo/reenviar-fallidos` (Tasks 2-3).
- Produces: `reenviarEnvio(id: string) => Promise<Envio>`, `reenviarFallidos(onProgress) => () => void` (mismo patrón de cancelación que `confirmarCiclo`).

- [ ] **Step 1: Add the two functions**

Replace the full content of `frontend/src/services/ciclos.ts`:

```ts
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

export async function reenviarEnvio(id: string): Promise<Envio> {
  const r = await apiFetch(`/envios/${id}/reenviar`, { method: "POST" });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error al reenviar el mail");
  }
  return r.json();
}

export function reenviarFallidos(
  onProgress: (data: {
    enviado: number;
    total: number;
    id?: string;
    done?: boolean;
    saltados?: { id: string; motivo: string }[];
  }) => void,
): () => void {
  const token = localStorage.getItem("access_token");
  const controller = new AbortController();

  fetch(`${import.meta.env.VITE_API_URL ?? "http://localhost:8000"}/ciclos/activo/reenviar-fallidos`, {
    method: "POST",
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
```

- [ ] **Step 2: Verify the frontend typechecks**

Run: `cd frontend && npx tsc -b`
Expected: no output, no errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/services/ciclos.ts
git commit -m "feat: servicio de reenvio individual y en bloque"
```

---

### Task 5: Frontend — pestaña Enviados y reenvío en `NuevoEnvioPage.tsx`

**Files:**
- Modify: `frontend/src/pages/NuevoEnvioPage.tsx`

**Interfaces:**
- Consumes: `reenviarEnvio`, `reenviarFallidos` (Task 4), `Envio` type (ya tiene `message_id`, sin cambios necesarios).

- [ ] **Step 1: Implement the new tab, redefined filters, and resend UI**

Replace the full content of `frontend/src/pages/NuevoEnvioPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Send, MailX, Filter, CheckCircle2 } from "lucide-react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { ProgresoEnvio } from "../components/upload/ProgresoEnvio";
import { useCicloContext } from "../contexts/useCicloContext";
import { reenviarEnvio, reenviarFallidos } from "../services/ciclos";
import type { Envio, MotivoFiltrado } from "../types/domain";
import { cn } from "../lib/utils";
import { MOTIVO_LABEL, MOTIVO_DOT } from "../lib/estado";

const PATH_TO_TAB: Record<string, string> = {
  "/nuevo-envio/para-enviar": "para_enviar",
  "/nuevo-envio/enviados": "enviados",
  "/nuevo-envio/sin-email": "sin_email",
  "/nuevo-envio/filtrados": "filtrados",
};

interface TableRow {
  key: string;
  nombre_consorcio: string;
  email: string | null;
  monto: number;
  motivo_filtrado: MotivoFiltrado | null;
}

export default function NuevoEnvioPage() {
  const {
    enviosActivo,
    previewData,
    clearPreview,
    confirmarPreview,
    isLoading,
    progreso,
    loadEnviosActivo,
  } = useCicloContext();
  const [initialLoading, setInitialLoading] = useState(true);
  const [reenviandoId, setReenviandoId] = useState<string | null>(null);
  const [reenviandoTodos, setReenviandoTodos] = useState(false);
  const [reenvioProgreso, setReenvioProgreso] = useState<{ enviado: number; total: number } | null>(null);
  const [reenvioError, setReenvioError] = useState("");
  const location = useLocation();
  const navigate = useNavigate();

  const activeTab = PATH_TO_TAB[location.pathname] ?? "para_enviar";
  const revisando = !!previewData && !isLoading;

  useEffect(() => {
    loadEnviosActivo().finally(() => setInitialLoading(false));
  }, [loadEnviosActivo]);

  const paraEnviarPreview: TableRow[] = revisando
    ? previewData!.items_para_enviar.map((i) => ({ key: i.clave_union, ...i }))
    : [];
  const fallidos: Envio[] = !revisando
    ? enviosActivo.filter((e) => e.estado === "NO_CONTESTADO" && e.email && !e.message_id)
    : [];
  const enviados: Envio[] = enviosActivo.filter((e) => e.message_id);
  const sinEmail: TableRow[] = revisando
    ? previewData!.items_sin_email.map((i) => ({ key: i.clave_union, ...i }))
    : enviosActivo.filter((e) => e.estado === "SIN_EMAIL").map((e) => ({ key: e.id, ...e }));
  const filtrados: TableRow[] = revisando
    ? previewData!.items_filtrados.map((i) => ({ key: i.clave_union, ...i }))
    : enviosActivo.filter((e) => e.estado === "FILTRADO").map((e) => ({ key: e.id, ...e }));

  const paraEnviarCount = revisando ? paraEnviarPreview.length : fallidos.length;

  function handleTabChange(value: string) {
    const paths: Record<string, string> = {
      para_enviar: "/nuevo-envio/para-enviar",
      enviados: "/nuevo-envio/enviados",
      sin_email: "/nuevo-envio/sin-email",
      filtrados: "/nuevo-envio/filtrados",
    };
    navigate(paths[value] ?? "/nuevo-envio/para-enviar");
  }

  async function handleReenviar(id: string) {
    setReenviandoId(id);
    setReenvioError("");
    try {
      await reenviarEnvio(id);
      await loadEnviosActivo();
    } catch (e: unknown) {
      setReenvioError(e instanceof Error ? e.message : "Error al reenviar el mail");
    } finally {
      setReenviandoId(null);
    }
  }

  function handleReenviarTodos() {
    setReenviandoTodos(true);
    setReenvioError("");
    setReenvioProgreso({ enviado: 0, total: 0 });
    reenviarFallidos((data) => {
      if (data.done) {
        setReenviandoTodos(false);
        setReenvioProgreso(null);
        loadEnviosActivo();
      } else {
        setReenvioProgreso({ enviado: data.enviado ?? 0, total: data.total ?? 0 });
      }
    });
  }

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-foreground">Nuevo Envío</h1>
        <span className="text-sm text-muted-foreground">
          {revisando
            ? "Revisá el ciclo antes de confirmar el envío"
            : "Ciclo actual antes de confirmar el envío de mails"}
        </span>
      </div>

      {revisando && (
        <div className="flex items-center justify-between gap-4 rounded-md border border-border bg-secondary/40 p-3">
          <p className="text-sm text-muted-foreground">
            Sin confirmar todavía — revisá las 3 solapas y confirmá cuando esté todo bien.
          </p>
          <div className="flex gap-2 shrink-0">
            <Button variant="outline" size="sm" onClick={clearPreview}>
              Cancelar
            </Button>
            <Button size="sm" onClick={() => confirmarPreview()}>
              Enviar {previewData!.para_enviar} mails
            </Button>
          </div>
        </div>
      )}

      {progreso && isLoading && (
        <div className="rounded-md border border-border bg-secondary/60 p-4">
          <ProgresoEnvio enviado={progreso.enviado} total={progreso.total} />
        </div>
      )}

      {reenvioProgreso && reenviandoTodos && (
        <div className="rounded-md border border-border bg-secondary/60 p-4">
          <ProgresoEnvio enviado={reenvioProgreso.enviado} total={reenvioProgreso.total} />
        </div>
      )}

      {reenvioError && <p className="text-sm text-destructive">{reenvioError}</p>}

      <Tabs value={activeTab} onValueChange={handleTabChange}>
        <TabsList>
          <TabsTrigger value="para_enviar" className="gap-1.5">
            <Send className="h-3.5 w-3.5" />
            Para enviar
            {paraEnviarCount > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {paraEnviarCount}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="enviados" className="gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Enviados
            {enviados.length > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {enviados.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="sin_email" className="gap-1.5">
            <MailX className="h-3.5 w-3.5" />
            Sin Email
            {sinEmail.length > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {sinEmail.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="filtrados" className="gap-1.5">
            <Filter className="h-3.5 w-3.5" />
            Filtrados
            {filtrados.length > 0 && (
              <Badge variant="secondary" className="text-xs tabular-nums">
                {filtrados.length}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="para_enviar">
          {revisando ? (
            <EnvioTable
              envios={paraEnviarPreview}
              loading={false}
              emptyState={
                <EmptyState
                  title="No hay deudores para enviar"
                  description="Subí el Excel de deudores para armar el próximo ciclo de envío."
                />
              }
            />
          ) : (
            <FallidosTable
              envios={fallidos}
              loading={initialLoading}
              reenviandoId={reenviandoId}
              onReenviar={handleReenviar}
              onReenviarTodos={handleReenviarTodos}
              reenviandoTodos={reenviandoTodos}
            />
          )}
        </TabsContent>
        <TabsContent value="enviados">
          <EnviadosTable envios={enviados} loading={!revisando && initialLoading} />
        </TabsContent>
        <TabsContent value="sin_email">
          <EnvioTable
            envios={sinEmail}
            loading={!revisando && initialLoading}
            emptyState={
              <EmptyState
                title="Todos los deudores tienen email"
                description="Ninguno quedó sin match en el maestro de clientes."
              />
            }
          />
        </TabsContent>
        <TabsContent value="filtrados">
          <EnvioTable
            envios={filtrados}
            loading={!revisando && initialLoading}
            emptyState={
              <EmptyState
                title="No hay deudores filtrados"
                description="Nadie quedó afuera por monto mínimo o baja voluntaria en este ciclo."
              />
            }
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-md border border-dashed border-border py-12 text-center">
      <p className="text-sm font-medium text-foreground">{title}</p>
      <p className="text-sm text-muted-foreground max-w-sm">{description}</p>
    </div>
  );
}

function EnvioTable({
  envios,
  loading,
  emptyState,
}: {
  envios: TableRow[];
  loading?: boolean;
  emptyState: React.ReactNode;
}) {
  if (loading) {
    return (
      <div className="space-y-2 pt-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    );
  }

  if (envios.length === 0) {
    return <div className="pt-2">{emptyState}</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm table-fixed">
        <colgroup>
          <col className="w-[35%]" />
          <col className="w-[30%]" />
          <col className="w-[20%]" />
          <col className="w-[15%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-border text-left">
            <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Consorcio
            </th>
            <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Email
            </th>
            <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Monto
            </th>
            <th className="py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Motivo
            </th>
          </tr>
        </thead>
        <tbody>
          {envios.map((e) => (
            <tr key={e.key} className="border-b border-border last:border-0 hover:bg-muted/50">
              <td className="py-2.5 pr-4 text-foreground truncate">{e.nombre_consorcio}</td>
              <td className="py-2.5 pr-4 text-muted-foreground truncate">{e.email ?? "—"}</td>
              <td className="py-2.5 pr-4 text-right tabular-nums text-foreground">
                ${Number(e.monto).toLocaleString("es-AR")}
              </td>
              <td className="py-2.5">
                {e.motivo_filtrado ? (
                  <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                    <span
                      className={cn("h-1.5 w-1.5 rounded-full shrink-0", MOTIVO_DOT[e.motivo_filtrado])}
                      aria-hidden
                    />
                    {MOTIVO_LABEL[e.motivo_filtrado]}
                  </span>
                ) : (
                  <span className="text-muted-foreground">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EnviadosTable({ envios, loading }: { envios: Envio[]; loading?: boolean }) {
  if (loading) {
    return (
      <div className="space-y-2 pt-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    );
  }

  if (envios.length === 0) {
    return (
      <div className="pt-2">
        <EmptyState
          title="Todavía no se mandó ningún mail en este ciclo"
          description="Confirmá el envío desde Para Enviar para que empiecen a aparecer acá."
        />
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm table-fixed">
        <colgroup>
          <col className="w-[40%]" />
          <col className="w-[35%]" />
          <col className="w-[25%]" />
        </colgroup>
        <thead>
          <tr className="border-b border-border text-left">
            <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Consorcio
            </th>
            <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Email
            </th>
            <th className="py-2 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Monto
            </th>
          </tr>
        </thead>
        <tbody>
          {envios.map((e) => (
            <tr key={e.id} className="border-b border-border last:border-0 hover:bg-muted/50">
              <td className="py-2.5 pr-4 text-foreground truncate">{e.nombre_consorcio}</td>
              <td className="py-2.5 pr-4 text-muted-foreground truncate">{e.email ?? "—"}</td>
              <td className="py-2.5 text-right tabular-nums text-foreground">
                ${Number(e.monto).toLocaleString("es-AR")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function FallidosTable({
  envios,
  loading,
  reenviandoId,
  onReenviar,
  onReenviarTodos,
  reenviandoTodos,
}: {
  envios: Envio[];
  loading?: boolean;
  reenviandoId: string | null;
  onReenviar: (id: string) => void;
  onReenviarTodos: () => void;
  reenviandoTodos: boolean;
}) {
  if (loading) {
    return (
      <div className="space-y-2 pt-2">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-9 w-full" />
        ))}
      </div>
    );
  }

  if (envios.length === 0) {
    return (
      <div className="pt-2">
        <EmptyState
          title="No hay envíos pendientes de reenvío"
          description="Todo lo de este ciclo se mandó bien, o todavía no confirmaste el envío."
        />
      </div>
    );
  }

  return (
    <div className="space-y-2 pt-2">
      <div className="flex justify-end">
        <Button size="sm" onClick={onReenviarTodos} disabled={reenviandoTodos}>
          {reenviandoTodos ? "Reenviando..." : `Reenviar todos (${envios.length})`}
        </Button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm table-fixed">
          <colgroup>
            <col className="w-[35%]" />
            <col className="w-[30%]" />
            <col className="w-[15%]" />
            <col className="w-[20%]" />
          </colgroup>
          <thead>
            <tr className="border-b border-border text-left">
              <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Consorcio
              </th>
              <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Email
              </th>
              <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Monto
              </th>
              <th aria-hidden />
            </tr>
          </thead>
          <tbody>
            {envios.map((e) => (
              <tr key={e.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                <td className="py-2.5 pr-4 text-foreground truncate">{e.nombre_consorcio}</td>
                <td className="py-2.5 pr-4 text-muted-foreground truncate">{e.email ?? "—"}</td>
                <td className="py-2.5 pr-4 text-right tabular-nums text-foreground">
                  ${Number(e.monto).toLocaleString("es-AR")}
                </td>
                <td className="py-2.5">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={reenviandoId === e.id || reenviandoTodos}
                    onClick={() => onReenviar(e.id)}
                  >
                    {reenviandoId === e.id ? "Reenviando..." : "Reenviar"}
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify the frontend builds**

Run: `cd frontend && npx tsc -b`
Expected: no output, no errors

- [ ] **Step 3: Manual verification**

With the backend and frontend dev servers running:
1. Navigate a `/nuevo-envio/para-enviar` con un ciclo activo que tenga al menos un envío sin `message_id` (podés forzar esto con una credencial de proveedor rota momentáneamente, o revisando un ciclo real donde algo haya fallado).
2. Confirmá que "Para Enviar" ahora solo muestra los fallidos, no todo lo `NO_CONTESTADO`.
3. Confirmá que la pestaña "Enviados" muestra los que sí tienen `message_id`.
4. Tocá "Reenviar" en una fila — confirmá que si el Maestro tiene un email válido, el envío desaparece de "Para Enviar" y aparece en "Enviados".
5. Tocá "Reenviar todos" con más de un fallido — confirmá que aparece la barra de progreso y que al terminar se actualizan ambas pestañas.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/NuevoEnvioPage.tsx
git commit -m "feat: pestana Enviados y reenvio de fallidos en Nuevo Envio"
```

---

### Task 6: Frontend — "No Contestados" excluye los fallidos

**Files:**
- Modify: `frontend/src/pages/SeguimientoPage.tsx`

**Interfaces:**
- Consumes: `Envio.message_id` (ya existe en el tipo).

- [ ] **Step 1: Update the filter**

In `frontend/src/pages/SeguimientoPage.tsx`, change:

```tsx
  const noContestados = envios.filter((e) => e.estado === "NO_CONTESTADO");
```

to:

```tsx
  const noContestados = envios.filter((e) => e.estado === "NO_CONTESTADO" && e.message_id);
```

- [ ] **Step 2: Verify the frontend builds**

Run: `cd frontend && npx tsc -b`
Expected: no output, no errors

- [ ] **Step 3: Manual verification**

Navegá a `/seguimiento/no-contestados` — confirmá que ya no aparecen ahí los envíos que fallaron al mandar (esos ahora viven solo en "Para Enviar", en Nuevo Envío).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/SeguimientoPage.tsx
git commit -m "fix: No Contestados excluye envios que fallaron al enviar"
```
