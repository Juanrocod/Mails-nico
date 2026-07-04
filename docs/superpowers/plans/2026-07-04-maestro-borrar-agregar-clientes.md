# Maestro: Borrar y Agregar Clientes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir borrar (soft-delete) y agregar clientes manualmente en la página Maestro de Clientes, reusando el campo `activo` ya existente pero hoy sin uso, sin arriesgar una migración de enum nueva y sin que un cliente eliminado vuelva a recibir mails de cobro.

**Architecture:** `ClienteMaestro.activo` pasa a ser el interruptor real de "borrado" (nunca se borra la fila). `PUT /maestro/{id}` gana la capacidad de togglear `activo` (borrar = `false`, reactivar = `true`), reusando el endpoint que ya existe. Un `POST /maestro` nuevo permite alta manual. `excel_joiner.join_deudores` empieza a filtrar por `activo` además de `prefiere_no_recibir_email`, reusando el mismo motivo `DADO_DE_BAJA` (no se agrega un enum nuevo).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, pytest, React 18 + TypeScript.

## Global Constraints

- No se agrega ninguna migración Alembic — `clientes_maestro.activo` ya existe desde `0001_initial.py`.
- No se agrega un valor nuevo a `MotivoFiltrado` — los clientes inactivos caen en el mismo bucket `DADO_DE_BAJA` que ya usa `prefiere_no_recibir_email`.
- Borrar es soft-delete (`activo=False`), nunca se elimina la fila de la DB.
- Re-subir el Excel maestro nunca debe reactivar un cliente inactivo — `merge_maestro` no toca `activo` (ya es así hoy; no se modifica `merge_maestro` en este plan).
- Alta manual exige `clave_union` (obligatoria) — sin eso el cliente nunca matchea con un deudor real.
- Alta manual con una `clave_union` ya existente (activa o inactiva) se rechaza con `409`, nunca crea un duplicado.

## Contexto importante para quien implemente

**El fixture `db` de este proyecto NO limpia las tablas `clientes_maestro`/`envios`/`ciclos` entre tests** (solo limpia `configuracion_sistema` — ver `backend/tests/conftest.py:59-64`). La base de test es un SQLite en memoria compartido entre todos los tests de una corrida (`StaticPool`), así que cualquier `clave_union` que uses en un test nuevo tiene que ser única en todo el archivo de test, o vas a chocar con un `409`/constraint de otro test que corrió antes. Los tests existentes en `test_maestro.py` usan `C001-C003`, `C010-C012`; los de `test_excel_joiner.py` usan `C001-C004`, `C010-C011`. Usá claves que no choquen con esas (los pasos de abajo ya lo tienen en cuenta).

---

### Task 1: Backend — borrar/reactivar (`activo`) y alta manual de clientes

**Files:**
- Modify: `backend/app/schemas/maestro.py`
- Modify: `backend/app/routers/maestro.py`
- Test: `backend/tests/test_maestro.py`

**Interfaces:**
- Produces: `ClienteMaestroCreate` (schema: `clave_union: str`, `nombre: str`, `email: Optional[str] = None`, `localidad: Optional[str] = None`), `ClienteMaestroUpdate.activo: Optional[bool]`, endpoint `POST /maestro` (201, o 409 si la clave ya existe, o 422 si falta nombre/clave o el email es inválido).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_maestro.py`:

```python
def test_update_cliente_marca_inactivo(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(clave_union="C020", nombre="Consorcio Veinte", email="veinte@mail.com")
    db.add(cliente)
    db.commit()

    r = client.put(
        f"/maestro/{cliente.id}",
        json={"activo": False},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["activo"] is False


def test_update_cliente_reactiva(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    cliente = ClienteMaestro(clave_union="C021", nombre="Consorcio Veintiuno", email="21@mail.com", activo=False)
    db.add(cliente)
    db.commit()

    r = client.put(
        f"/maestro/{cliente.id}",
        json={"activo": True},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["activo"] is True


def test_crear_cliente_manual(client, auth_headers):
    r = client.post(
        "/maestro",
        json={"clave_union": "C030", "nombre": "Consorcio Treinta", "email": "treinta@mail.com"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["clave_union"] == "C030"
    assert data["activo"] is True
    assert data["prefiere_no_recibir_email"] is False


def test_crear_cliente_clave_duplicada_activa_rechaza(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    db.add(ClienteMaestro(clave_union="C031", nombre="Ya Existe", email="existe@mail.com"))
    db.commit()

    r = client.post(
        "/maestro",
        json={"clave_union": "C031", "nombre": "Otro Nombre"},
        headers=auth_headers,
    )
    assert r.status_code == 409
    assert "inactivo" not in r.json()["detail"]


def test_crear_cliente_clave_duplicada_inactiva_sugiere_reactivar(client, auth_headers, db):
    from app.models.cliente_maestro import ClienteMaestro
    db.add(ClienteMaestro(clave_union="C032", nombre="Inactivo", email="inactivo@mail.com", activo=False))
    db.commit()

    r = client.post(
        "/maestro",
        json={"clave_union": "C032", "nombre": "Otro Nombre"},
        headers=auth_headers,
    )
    assert r.status_code == 409
    assert "inactivo" in r.json()["detail"]


def test_crear_cliente_nombre_vacio_rechaza(client, auth_headers):
    r = client.post(
        "/maestro",
        json={"clave_union": "C033", "nombre": "   "},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_crear_cliente_requiere_auth(client):
    r = client.post("/maestro", json={"clave_union": "C034", "nombre": "X"})
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_maestro.py -v`
Expected: FAIL — `test_update_cliente_marca_inactivo`/`test_update_cliente_reactiva` fail because `activo` isn't accepted by `ClienteMaestroUpdate` yet (extra field is ignored by default in Pydantic, so `activo` silently does nothing → assertion fails); the `crear_cliente` tests fail with `404 Not Found` because `POST /maestro` doesn't exist yet.

- [ ] **Step 3: Add `activo` to `ClienteMaestroUpdate` and the new `ClienteMaestroCreate` schema**

Replace the full content of `backend/app/schemas/maestro.py`:

```python
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator

from app.core.validators import is_valid_email


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


class ClienteMaestroUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    localidad: Optional[str] = None
    prefiere_no_recibir_email: Optional[bool] = None
    activo: Optional[bool] = None

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() and not is_valid_email(v.strip()):
            raise ValueError("El email no tiene un formato válido")
        return v


class ClienteMaestroCreate(BaseModel):
    clave_union: str
    nombre: str
    email: Optional[str] = None
    localidad: Optional[str] = None

    @field_validator("clave_union")
    @classmethod
    def clave_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La clave de unión no puede estar vacía")
        return v.strip()

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() and not is_valid_email(v.strip()):
            raise ValueError("El email no tiene un formato válido")
        return v
```

- [ ] **Step 4: Add the `activo` toggle to `update_cliente` and the new `crear_cliente` endpoint**

Replace the full content of `backend/app/routers/maestro.py`:

```python
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.cliente_maestro import ClienteMaestro
from app.schemas.maestro import (
    ClienteMaestroSchema,
    ClienteMaestroUpdate,
    ClienteMaestroCreate,
    MaestroUploadResponse,
)
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


@router.post("", response_model=ClienteMaestroSchema, status_code=201)
def crear_cliente(
    payload: ClienteMaestroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == payload.clave_union).first()
    if existing:
        if existing.activo:
            detail = f"Ya existe un cliente activo con la clave '{payload.clave_union}'."
        else:
            detail = (
                f"Ya existe un cliente con la clave '{payload.clave_union}', pero está inactivo. "
                "Reactivalo en vez de crear uno nuevo."
            )
        raise HTTPException(status_code=409, detail=detail)

    cliente = ClienteMaestro(
        clave_union=payload.clave_union,
        nombre=payload.nombre,
        email=(payload.email or "").strip() or None,
        localidad=(payload.localidad or "").strip() or None,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@router.put("/{cliente_id}", response_model=ClienteMaestroSchema)
def update_cliente(
    cliente_id: UUID,
    payload: ClienteMaestroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cliente = db.get(ClienteMaestro, cliente_id)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    data = payload.model_dump(exclude_unset=True)
    if "nombre" in data:
        cliente.nombre = data["nombre"].strip()
    if "email" in data:
        cliente.email = data["email"].strip() or None
    if "localidad" in data:
        cliente.localidad = (data["localidad"] or "").strip() or None
    if "prefiere_no_recibir_email" in data:
        cliente.prefiere_no_recibir_email = data["prefiere_no_recibir_email"]
    if "activo" in data:
        cliente.activo = data["activo"]

    db.commit()
    db.refresh(cliente)
    return cliente
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_maestro.py -v`
Expected: PASS (todos, incluidos los 7 tests pre-existentes de este archivo)

- [ ] **Step 6: Run the full backend suite**

Run: `cd backend && venv/Scripts/python -m pytest -v`
Expected: PASS (ningún test pre-existente roto)

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/maestro.py backend/app/routers/maestro.py backend/tests/test_maestro.py
git commit -m "feat: permitir borrar (soft-delete), reactivar y crear clientes en Maestro"
```

---

### Task 2: Backend — excluir clientes inactivos de los próximos ciclos de envío

**Files:**
- Modify: `backend/app/services/excel_joiner.py`
- Test: `backend/tests/test_excel_joiner.py`

**Interfaces:**
- Consumes: `ClienteMaestro.activo` (ya existe desde Task 1 sin cambios de schema — este task solo lee el campo).

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_excel_joiner.py`:

```python
def test_join_filtrado_por_inactivo(db):
    _add_cliente(db, "C005", "Consorcio Inactivo", email="inactivo@mail.com")
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "C005").first()
    cliente.activo = False
    db.flush()

    deudores = [DeudorRow("C005", "Consorcio Inactivo", "CABA", Decimal("9000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.filtrados) == 1
    assert preview.filtrados[0][1] == "DADO_DE_BAJA"
    assert len(preview.para_enviar) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_excel_joiner.py::test_join_filtrado_por_inactivo -v`
Expected: FAIL — hoy el cliente inactivo cae en `para_enviar` porque `join_deudores` no mira `activo` (`len(preview.filtrados) == 1` falla, es 0).

- [ ] **Step 3: Filter by `activo` in `join_deudores`**

In `backend/app/services/excel_joiner.py`, change:

```python
        if cliente.prefiere_no_recibir_email:
            filtrados.append((deudor, "DADO_DE_BAJA"))
            continue
```

to:

```python
        if cliente.prefiere_no_recibir_email or not cliente.activo:
            filtrados.append((deudor, "DADO_DE_BAJA"))
            continue
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && venv/Scripts/python -m pytest tests/test_excel_joiner.py -v`
Expected: PASS (todos, incluidos los 7 tests pre-existentes de este archivo)

- [ ] **Step 5: Run the full backend suite**

Run: `cd backend && venv/Scripts/python -m pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/excel_joiner.py backend/tests/test_excel_joiner.py
git commit -m "fix: excluir clientes inactivos de los proximos ciclos de envio"
```

---

### Task 3: Frontend — servicio `createCliente` y modal de alta manual

**Files:**
- Modify: `frontend/src/services/maestro.ts`
- Create: `frontend/src/components/maestro/AgregarClienteModal.tsx`

**Interfaces:**
- Consumes: `POST /maestro` (Task 1), `ClienteMaestro` type (ya existe en `frontend/src/types/domain.ts`, sin cambios necesarios — ya tiene `activo`).
- Produces: `createCliente(data: {clave_union: string; nombre: string; email?: string; localidad?: string}) => Promise<ClienteMaestro>`; componente `AgregarClienteModal({ open, onClose, onCreated })`.

- [ ] **Step 1: Add `createCliente` and extend `updateCliente`'s accepted fields**

Replace the full content of `frontend/src/services/maestro.ts`:

```ts
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

export async function updateCliente(
  id: string,
  data: Partial<Pick<ClienteMaestro, "nombre" | "email" | "localidad" | "prefiere_no_recibir_email" | "activo">>
): Promise<ClienteMaestro> {
  const r = await apiFetch(`/maestro/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    const detail = Array.isArray(err.detail)
      ? err.detail.map((d: { msg?: string }) => d.msg).join("; ")
      : err.detail;
    throw new Error(detail ?? "Error guardando el cliente");
  }
  return r.json();
}

export async function createCliente(data: {
  clave_union: string;
  nombre: string;
  email?: string;
  localidad?: string;
}): Promise<ClienteMaestro> {
  const r = await apiFetch("/maestro", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    const detail = Array.isArray(err.detail)
      ? err.detail.map((d: { msg?: string }) => d.msg).join("; ")
      : err.detail;
    throw new Error(detail ?? "Error creando el cliente");
  }
  return r.json();
}
```

- [ ] **Step 2: Create the modal**

Create `frontend/src/components/maestro/AgregarClienteModal.tsx`:

```tsx
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { createCliente } from "../../services/maestro";
import type { ClienteMaestro } from "../../types/domain";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (cliente: ClienteMaestro) => void;
}

export function AgregarClienteModal({ open, onClose, onCreated }: Props) {
  const [claveUnion, setClaveUnion] = useState("");
  const [nombre, setNombre] = useState("");
  const [email, setEmail] = useState("");
  const [localidad, setLocalidad] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  function reset() {
    setClaveUnion("");
    setNombre("");
    setEmail("");
    setLocalidad("");
    setError("");
  }

  function handleClose() {
    reset();
    onClose();
  }

  async function handleCrear() {
    setIsLoading(true);
    setError("");
    try {
      const cliente = await createCliente({
        clave_union: claveUnion,
        nombre,
        email: email || undefined,
        localidad: localidad || undefined,
      });
      onCreated(cliente);
      handleClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error creando el cliente");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Agregar cliente</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Clave de unión</label>
            <Input value={claveUnion} onChange={(e) => setClaveUnion(e.target.value)} placeholder="C001" />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Nombre</label>
            <Input value={nombre} onChange={(e) => setNombre(e.target.value)} placeholder="Consorcio X" />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Email</label>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="consorcio@mail.com"
            />
          </div>
          <div className="space-y-1.5">
            <label className="block text-sm font-medium text-foreground">Localidad</label>
            <Input value={localidad} onChange={(e) => setLocalidad(e.target.value)} placeholder="CABA" />
          </div>

          {error && <p className="text-sm text-destructive">{error}</p>}

          <Button
            className="w-full"
            onClick={handleCrear}
            disabled={isLoading || !claveUnion.trim() || !nombre.trim()}
          >
            {isLoading ? "Creando..." : "Crear cliente"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

- [ ] **Step 3: Verify the frontend builds**

Run: `cd frontend && npx tsc -b`
Expected: no output, no errors

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/maestro.ts frontend/src/components/maestro/AgregarClienteModal.tsx
git commit -m "feat: servicio y modal de alta manual de clientes en Maestro"
```

---

### Task 4: Frontend — borrar/reactivar y alta manual en `MaestroPage.tsx`

**Files:**
- Modify: `frontend/src/pages/MaestroPage.tsx`

**Interfaces:**
- Consumes: `createCliente`, updated `updateCliente` (Task 3), `AgregarClienteModal` (Task 3).

- [ ] **Step 1: Implement the toggle, delete/reactivate actions, and the "Agregar cliente" button**

Replace the full content of `frontend/src/pages/MaestroPage.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Pencil, Check, X, Trash2, RotateCcw } from "lucide-react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { MaestroUploadModal } from "../components/upload/MaestroUploadModal";
import { AgregarClienteModal } from "../components/maestro/AgregarClienteModal";
import { getMaestro, updateCliente, uploadMaestro } from "../services/maestro";
import type { ClienteMaestro } from "../types/domain";

type EditForm = {
  nombre: string;
  email: string;
  prefiere_no_recibir_email: boolean;
};

export default function MaestroPage() {
  const [clientes, setClientes] = useState<ClienteMaestro[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [agregarModalOpen, setAgregarModalOpen] = useState(false);
  const [mostrarInactivos, setMostrarInactivos] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getMaestro().then(setClientes).catch(console.error);
  }, []);

  async function handleUpload(file: File) {
    const r = await uploadMaestro(file);
    getMaestro().then(setClientes).catch(console.error);
    return r;
  }

  function startEdit(c: ClienteMaestro) {
    setEditingId(c.id);
    setEditForm({
      nombre: c.nombre,
      email: c.email ?? "",
      prefiere_no_recibir_email: c.prefiere_no_recibir_email,
    });
    setError("");
  }

  function cancelEdit() {
    setEditingId(null);
    setEditForm(null);
    setError("");
  }

  async function saveEdit(id: string) {
    if (!editForm) return;
    setSaving(true);
    setError("");
    try {
      const updated = await updateCliente(id, editForm);
      setClientes((prev) => prev.map((c) => (c.id === id ? updated : c)));
      setEditingId(null);
      setEditForm(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error guardando el cliente");
    } finally {
      setSaving(false);
    }
  }

  async function handleEliminar(c: ClienteMaestro) {
    if (!window.confirm(`¿Eliminar a ${c.nombre}? Vas a poder reactivarlo despues desde "Mostrar inactivos".`)) {
      return;
    }
    setError("");
    try {
      const updated = await updateCliente(c.id, { activo: false });
      setClientes((prev) => prev.map((x) => (x.id === c.id ? updated : x)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error eliminando el cliente");
    }
  }

  async function handleReactivar(c: ClienteMaestro) {
    setError("");
    try {
      const updated = await updateCliente(c.id, { activo: true });
      setClientes((prev) => prev.map((x) => (x.id === c.id ? updated : x)));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Error reactivando el cliente");
    }
  }

  function handleClienteCreado(cliente: ClienteMaestro) {
    setClientes((prev) => [...prev, cliente]);
  }

  const clientesVisibles = clientes.filter((c) => c.activo !== mostrarInactivos);

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-semibold text-foreground">Maestro de Clientes</h1>
          <span className="text-sm text-muted-foreground">
            {clientesVisibles.length} clientes {mostrarInactivos ? "inactivos" : "registrados"}
          </span>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setAgregarModalOpen(true)}>
            Agregar cliente
          </Button>
          <Button onClick={() => setModalOpen(true)}>Actualizar Maestro</Button>
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-muted-foreground">
        <input
          type="checkbox"
          checked={mostrarInactivos}
          onChange={(e) => setMostrarInactivos(e.target.checked)}
          className="h-4 w-4 rounded border-border"
        />
        Mostrar inactivos
      </label>

      <MaestroUploadModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        onUpload={handleUpload}
      />

      <AgregarClienteModal
        open={agregarModalOpen}
        onClose={() => setAgregarModalOpen(false)}
        onCreated={handleClienteCreado}
      />

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="overflow-x-auto">
        <table className="w-full text-sm table-fixed">
          <colgroup>
            <col className="w-28" />
            <col className="w-64" />
            <col className="w-72" />
            <col className="w-20" />
            <col className="w-16" />
          </colgroup>
          <thead>
            <tr className="border-b border-border text-left">
              <th className="py-2 pr-6 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Clave
              </th>
              <th className="py-2 pr-6 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Nombre
              </th>
              <th className="py-2 pr-6 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Email
              </th>
              <th className="py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Baja
              </th>
              <th aria-hidden />
            </tr>
          </thead>
          <tbody>
            {clientesVisibles.map((c) => {
              const isEditing = editingId === c.id;
              return (
                <tr key={c.id} className="border-b border-border last:border-0 hover:bg-muted/50">
                  <td className="py-2.5 pr-6 font-mono text-xs text-muted-foreground truncate">
                    {c.clave_union}
                  </td>
                  <td className="py-2.5 pr-6 text-foreground truncate">
                    {isEditing && editForm ? (
                      <Input
                        value={editForm.nombre}
                        onChange={(e) => setEditForm({ ...editForm, nombre: e.target.value })}
                        className="h-8"
                      />
                    ) : (
                      c.nombre
                    )}
                  </td>
                  <td className="py-2.5 pr-6 text-muted-foreground truncate">
                    {isEditing && editForm ? (
                      <Input
                        type="email"
                        value={editForm.email}
                        onChange={(e) => setEditForm({ ...editForm, email: e.target.value })}
                        className="h-8"
                      />
                    ) : (
                      c.email ?? "—"
                    )}
                  </td>
                  <td className="py-2.5 text-muted-foreground">
                    {isEditing && editForm ? (
                      <input
                        type="checkbox"
                        checked={editForm.prefiere_no_recibir_email}
                        onChange={(e) =>
                          setEditForm({ ...editForm, prefiere_no_recibir_email: e.target.checked })
                        }
                        className="h-4 w-4 rounded border-border"
                      />
                    ) : c.prefiere_no_recibir_email ? (
                      "Sí"
                    ) : (
                      "No"
                    )}
                  </td>
                  <td className="py-2.5">
                    {isEditing ? (
                      <div className="flex gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          disabled={saving}
                          onClick={() => saveEdit(c.id)}
                          aria-label="Guardar"
                        >
                          <Check className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          disabled={saving}
                          onClick={cancelEdit}
                          aria-label="Cancelar"
                        >
                          <X className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : c.activo ? (
                      <div className="flex gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          onClick={() => startEdit(c)}
                          aria-label="Editar"
                        >
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-8 w-8"
                          onClick={() => handleEliminar(c)}
                          aria-label="Eliminar"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8"
                        onClick={() => handleReactivar(c)}
                        aria-label="Reactivar"
                      >
                        <RotateCcw className="h-4 w-4" />
                      </Button>
                    )}
                  </td>
                </tr>
              );
            })}
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
1. Navigate to `/maestro`.
2. Confirm the header shows only active clients by default, and "Mostrar inactivos" is unchecked.
3. Click the trash icon on a client, confirm the browser confirm dialog, accept it — the client disappears from the list.
4. Check "Mostrar inactivos" — the client you just deleted appears, with a "Reactivar" button instead of edit/delete.
5. Click "Reactivar" — the client disappears from the inactive view; uncheck "Mostrar inactivos" and confirm it's back in the active list.
6. Click "Agregar cliente", fill in a clave de unión that doesn't exist yet, plus nombre — submit. Confirm the new client appears in the table without a page reload.
7. Try "Agregar cliente" again with the same clave de unión — confirm the modal shows the backend's error message instead of silently failing.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/MaestroPage.tsx
git commit -m "feat: borrar, reactivar y agregar clientes desde la pagina de Maestro"
```
