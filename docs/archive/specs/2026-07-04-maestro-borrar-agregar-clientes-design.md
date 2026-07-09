# Spec — Borrar y agregar clientes manualmente en Maestro de Clientes

**Fecha:** 2026-07-04
**Estado:** Aprobado — listo para planificación de implementación
**Relacionado:** `docs/superpowers/specs/2026-06-30-mails-nico-design.md` (modelo `ClienteMaestro`), `docs/PENDIENTES.md`

---

## 1. Problema

En la página Maestro de Clientes hoy se puede editar un cliente (inline, con lápiz) pero no hay forma de:
1. Eliminar un cliente que ya no corresponde gestionar.
2. Agregar un cliente nuevo a mano, sin esperar a subir un Excel maestro.

Al analizar el modelo se encontró que `ClienteMaestro.activo` (columna y schema) ya existe desde la migración inicial pero **no se usa en ningún lado**: ni el listado (`GET /maestro`) ni el cruce con el Excel de deudores (`excel_joiner.join_deudores`) lo filtran. Esto es relevante porque cualquier solución de "borrado" tiene que decidir qué hacer con este campo huérfano, y porque un borrado mal diseñado puede chocar con la regla crítica ya existente del sistema: **el merge del Excel maestro nunca debe revivir a un cliente que el operario decidió sacar de circulación** (mismo principio que ya protege a `prefiere_no_recibir_email`).

---

## 2. Solución

**Borrado = borrado suave**, reusando el campo `activo` ya existente:
- "Eliminar" un cliente pone `activo=False`. No se borra la fila.
- Reaparece en un Excel maestro futuro → sigue inactivo (el merge nunca toca `activo`, igual que nunca toca `prefiere_no_recibir_email`).
- Un cliente inactivo **también queda excluido de los próximos ciclos de envío** (mismo bucket `FILTRADO/DADO_DE_BAJA` que ya usa `prefiere_no_recibir_email`, sin agregar un motivo nuevo — ver sección 5 para por qué).
- Para recuperarlo: un filtro "Mostrar inactivos" en la página, con un botón "Reactivar" (pone `activo=True` de nuevo). Es una acción explícita del operario, nunca automática por re-subir el Excel.

**Alta manual**: un formulario (clave de unión, nombre, email, localidad) que crea un `ClienteMaestro` nuevo. La clave de unión es obligatoria — sin ella el cliente nunca va a matchear con un deudor real. Si la clave ya existe (activo o inactivo), se rechaza con un mensaje claro en vez de crear un duplicado.

**No objetivo:** no se agrega un motivo de filtrado nuevo (`CLIENTE_INACTIVO` o similar). `motivo_filtrado` es un enum nativo de Postgres; agregar un valor requiere una migración `ALTER TYPE` fuera de transacción que no es trivialmente portable a SQLite (el motor de desarrollo local). Se decidió reusar `DADO_DE_BAJA` para ambos casos — la distinción real (baja voluntaria vs. eliminado por el operario) queda visible en el estado `activo` del Maestro, no en el motivo del ciclo.

---

## 3. Backend

### `schemas/maestro.py`

```python
class ClienteMaestroUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    localidad: Optional[str] = None
    prefiere_no_recibir_email: Optional[bool] = None
    activo: Optional[bool] = None          # NUEVO
    # (validators existentes de nombre/email sin cambios)


class ClienteMaestroCreate(BaseModel):     # NUEVO
    clave_union: str
    nombre: str
    email: Optional[str] = None
    localidad: Optional[str] = None
    # mismos validators que ClienteMaestroUpdate: nombre no vacío, email con formato válido si viene
    # + clave_union no vacía (strip)
```

### `routers/maestro.py`

- `update_cliente`: agregar `if "activo" in data: cliente.activo = data["activo"]` al bloque existente. Sin cambios en el resto del handler (auth, 404, commit/refresh).
- Nuevo endpoint:

```python
@router.post("", response_model=ClienteMaestroSchema, status_code=201)
def crear_cliente(
    payload: ClienteMaestroCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clave = payload.clave_union.strip()
    existing = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == clave).first()
    if existing:
        if existing.activo:
            detail = f"Ya existe un cliente activo con la clave '{clave}'."
        else:
            detail = f"Ya existe un cliente con la clave '{clave}', pero está inactivo. Reactivalo en vez de crear uno nuevo."
        raise HTTPException(status_code=409, detail=detail)

    cliente = ClienteMaestro(
        clave_union=clave,
        nombre=payload.nombre.strip(),
        email=(payload.email or "").strip() or None,
        localidad=(payload.localidad or "").strip() or None,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente
```

(`activo` y `prefiere_no_recibir_email` quedan en sus defaults del modelo: `True` y `False`.)

### `services/excel_joiner.py`

Único cambio, en `join_deudores`:

```python
# antes:
if cliente.prefiere_no_recibir_email:
    filtrados.append((deudor, "DADO_DE_BAJA"))
    continue

# después:
if cliente.prefiere_no_recibir_email or not cliente.activo:
    filtrados.append((deudor, "DADO_DE_BAJA"))
    continue
```

### Migraciones

Ninguna. `clientes_maestro.activo` ya existe desde `0001_initial.py`.

---

## 4. Frontend

### `services/maestro.ts`

Agregar:

```ts
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
    throw new Error(err.detail ?? "Error creando el cliente");
  }
  return r.json();
}
```

Borrar y reactivar no necesitan función nueva: usan `updateCliente(id, { activo: false })` / `updateCliente(id, { activo: true })`, que ya existe.

### `components/maestro/AgregarClienteModal.tsx` (nuevo)

Modal con 4 campos (clave de unión, nombre, email, localidad), validación mínima en el cliente (clave y nombre no vacíos antes de habilitar el botón — el formato de email y la unicidad de clave los valida el backend), muestra el `detail` del error 409 tal cual si la clave ya existe.

### `MaestroPage.tsx`

- Nuevo estado `mostrarInactivos: boolean` (default `false`). La tabla renderiza `clientes.filter(c => c.activo !== mostrarInactivos)` — activos cuando `mostrarInactivos` es `false`, inactivos cuando es `true`. Checkbox visible junto al conteo de clientes.
- El conteo del header (`"N clientes registrados"`) refleja el largo de la lista ya filtrada, no el total absoluto.
- Columna de acciones:
  - Cliente activo, no en edición: lápiz (existente) + ícono de borrar (`Trash2` de lucide-react). Borrar pide confirmación (`window.confirm`) antes de llamar `updateCliente(id, { activo: false })`.
  - Cliente inactivo: en vez de lápiz + borrar, un botón "Reactivar" (`RotateCcw` de lucide-react) que llama `updateCliente(id, { activo: true })` sin confirmación (acción no destructiva).
- Botón "Agregar cliente" junto a "Actualizar Maestro", abre `AgregarClienteModal`. Al crear con éxito, el cliente nuevo se agrega al estado `clientes` local (sin recargar toda la lista).

---

## 5. Manejo de errores

- `POST /maestro` con clave duplicada → `409`, mensaje distingue si el existente está activo o inactivo (ver sección 3).
- `POST /maestro` con `nombre` vacío o `email` con formato inválido → `422` (mismos validators que `ClienteMaestroUpdate` ya usa).
- `PUT /maestro/{id}` con `activo` en un cliente inexistente → `404` (comportamiento ya existente del endpoint, sin cambios).
- Borrar/reactivar reusan el endpoint y manejo de errores ya probado de `update_cliente` — no hay lógica nueva de errores ahí, solo un campo más.

---

## 6. Testing

- `test_maestro.py`:
  - `PUT` con `{"activo": false}` → cliente queda inactivo.
  - `PUT` con `{"activo": true}` sobre un cliente inactivo → vuelve a activo.
  - `POST /maestro` crea cliente con clave nueva → `201`, `activo=True`.
  - `POST /maestro` con clave ya activa → `409`.
  - `POST /maestro` con clave ya inactiva → `409` (mensaje distinto, menciona reactivar).
  - `POST /maestro` con `nombre` vacío → `422`.
- `test_excel_joiner.py`: cliente con `activo=False` y `prefiere_no_recibir_email=False` → cae en `filtrados` con motivo `DADO_DE_BAJA` (antes de este cambio, este cliente hubiera ido a `para_enviar`).
- Frontend: sin infraestructura de tests automatizados (consistente con el resto del proyecto) — verificación manual en el navegador (dev server ya corriendo).

---

## 7. Fuera de alcance

- Un motivo de filtrado distinto para "eliminado por el operario" vs. "dado de baja" (ver sección 2, No objetivo).
- Confirmación interactiva durante la carga del Excel maestro para clientes previamente eliminados que reaparecen (se descartó explícitamente por complejidad; el operario reactiva a mano si quiere revertir un borrado).
- Borrado definitivo (hard delete) de la fila en base — no se ofrece como opción en la UI.
