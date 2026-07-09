# Logo del Mail — Upload de Imagen Real — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Depende de:** `docs/superpowers/plans/2026-07-02-unsubscribe-endpoint.md` debe estar commiteado antes de arrancar (usa la misma variable `settings.BACKEND_PUBLIC_URL` que ese plan agrega, y ambos tocan `backend/app/main.py`).

**Goal:** Hoy `Plantilla.logo_url` es un campo de texto que ni siquiera tiene input en el frontend — el operario no tiene forma de poner un logo. Este plan agrega upload de imagen real: endpoint que recibe el archivo, lo guarda, y actualiza `logo_url` con la URL completa servida por el propio backend.

**Architecture:** El backend sirve archivos estáticos desde una carpeta `uploads/` montada en `/uploads` (`fastapi.staticfiles.StaticFiles`). El endpoint `POST /plantilla/logo` valida tipo y tamaño, guarda el archivo como `logo.<ext>` (un solo logo activo, se pisa al subir uno nuevo) y actualiza `Plantilla.logo_url` con la URL absoluta (`BACKEND_PUBLIC_URL` + `/uploads/logo.<ext>`) para que el logo cargue bien en el mail final, no solo en el navegador local. El frontend reutiliza `FileDropzone` (ya existe, se usa para los Excel) generalizándolo con una prop `accept`/`hint` para que también sirva para imágenes sin tocar su comportamiento actual en los otros dos lugares donde se usa.

**Tech Stack:** FastAPI `StaticFiles`, React + TypeScript.

## Global Constraints

- Formatos aceptados: PNG, JPEG, WEBP. Tamaño máximo: 2MB.
- Un solo logo activo por vez — subir uno nuevo pisa el anterior (el nombre de archivo es fijo, `logo.<ext>`, no un UUID).
- `FileDropzone.tsx` ya la usan `ExcelUploadModal.tsx` y `MaestroUploadModal.tsx` con el comportamiento actual (acepta `.xlsx,.xls`, texto "Solo .xlsx o .xls") — los cambios a ese componente deben ser **aditivos con defaults que preserven ese comportamiento**, no romper nada ahí.
- Correr tests: `cd backend && venv\Scripts\python -m pytest -v`

---

## File Structure

- Modify: `backend/app/main.py` — montar `/uploads` como archivos estáticos
- Modify: `backend/app/routers/plantilla.py` — endpoint `POST /plantilla/logo`
- Create: `backend/tests/test_plantilla_logo_upload.py`
- Modify: `frontend/src/components/upload/FileDropzone.tsx` — props `accept`/`hint` opcionales
- Modify: `frontend/src/services/plantilla.ts` — `uploadLogo(file)`
- Modify: `frontend/src/pages/PlantillaPage.tsx` — sección "Logo" con preview + dropzone

---

### Task 1: Servir archivos estáticos desde `/uploads`

**Files:**
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: cualquier archivo en la carpeta `backend/uploads/` queda accesible en `http://<host>/uploads/<nombre>`

- [ ] **Step 1: Montar el directorio estático**

En `backend/app/main.py`, agregar los imports (junto a los existentes, después de la línea 1 `import asyncio`):

```python
import os
```

Y agregar el import de `StaticFiles` (junto a `from fastapi import FastAPI`, línea 4):
```python
from fastapi.staticfiles import StaticFiles
```

Después de la línea `app.add_middleware(RequestLoggingMiddleware)` (línea 47) y antes de los `app.include_router(...)`, agregar:

```python
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
```

- [ ] **Step 2: Verificar manualmente que el server sigue levantando**

Run: `cd backend && venv\Scripts\python -m uvicorn app.main:app --port 8001` (puerto distinto para no chocar con el server que ya tengas corriendo), esperar el log "Application startup complete", después `Ctrl+C`.
Expected: arranca sin error. Si tira `RuntimeError: Directory 'uploads' does not exist`, revisar que el `os.makedirs` esté antes del `app.mount`.

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: servir archivos estáticos desde /uploads"
```

---

### Task 2: Endpoint `POST /plantilla/logo`

**Files:**
- Modify: `backend/app/routers/plantilla.py`
- Create: `backend/tests/test_plantilla_logo_upload.py`

**Interfaces:**
- Consumes: `db_config.load_plantilla` (ya existe), `settings.BACKEND_PUBLIC_URL` (del plan `unsubscribe-endpoint`)
- Produces: `POST /plantilla/logo` (multipart, campo `file`) → `PlantillaSchema` actualizado

- [ ] **Step 1: Escribir el test (falla primero)**

```python
# backend/tests/test_plantilla_logo_upload.py
import io
from PIL import Image


def _make_png_bytes(size=(10, 10)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color="red").save(buf, format="PNG")
    return buf.getvalue()


def test_upload_logo_actualiza_logo_url(client, auth_headers, plantilla_default):
    png_bytes = _make_png_bytes()
    r = client.post(
        "/plantilla/logo",
        files={"file": ("logo.png", png_bytes, "image/png")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["logo_url"].endswith("/uploads/logo.png")


def test_upload_logo_rechaza_formato_no_soportado(client, auth_headers, plantilla_default):
    r = client.post(
        "/plantilla/logo",
        files={"file": ("logo.gif", b"no-es-una-imagen-real", "image/gif")},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_upload_logo_rechaza_archivo_muy_grande(client, auth_headers, plantilla_default):
    big = b"0" * (3 * 1024 * 1024)  # 3MB > límite de 2MB
    r = client.post(
        "/plantilla/logo",
        files={"file": ("logo.png", big, "image/png")},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_upload_logo_requiere_auth(client):
    png_bytes = _make_png_bytes()
    r = client.post("/plantilla/logo", files={"file": ("logo.png", png_bytes, "image/png")})
    assert r.status_code in (401, 403)
```

Este test usa `Pillow` para generar un PNG válido de verdad. Verificar si ya está instalado:

Run: `cd backend && venv\Scripts\python -c "import PIL; print(PIL.__version__)"`

Si tira `ModuleNotFoundError`, instalar y agregar a `requirements.txt`:

Run: `cd backend && venv\Scripts\pip install Pillow==10.3.0`

Y agregar la línea `Pillow==10.3.0` a `backend/requirements.txt`.

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_plantilla_logo_upload.py -v`
Expected: FAIL con 404 (la ruta no existe todavía)

- [ ] **Step 3: Implementar el endpoint**

En `backend/app/routers/plantilla.py`, reemplazar el contenido completo por:

```python
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.plantilla import PlantillaSchema
from app.services import db_config

router = APIRouter(prefix="/plantilla", tags=["plantilla"])

_LOGO_CONTENT_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
_LOGO_MAX_BYTES = 2 * 1024 * 1024


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


@router.post("/logo", response_model=PlantillaSchema)
async def upload_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = _LOGO_CONTENT_TYPES.get(file.content_type)
    if ext is None:
        raise HTTPException(status_code=422, detail="Formato de imagen no soportado (usar PNG, JPG o WEBP)")

    content = await file.read()
    if len(content) > _LOGO_MAX_BYTES:
        raise HTTPException(status_code=422, detail="La imagen no puede superar los 2MB")

    os.makedirs("uploads", exist_ok=True)
    filename = f"logo.{ext}"
    with open(os.path.join("uploads", filename), "wb") as f:
        f.write(content)

    plantilla = db_config.load_plantilla(db)
    plantilla.logo_url = f"{settings.BACKEND_PUBLIC_URL}/uploads/{filename}"
    db.commit()
    db.refresh(plantilla)
    return plantilla
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_plantilla_logo_upload.py -v`
Expected: `4 passed`

- [ ] **Step 5: Correr toda la suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos pasan

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/plantilla.py backend/tests/test_plantilla_logo_upload.py backend/requirements.txt
git commit -m "feat: endpoint de upload de logo para la Plantilla"
```

---

### Task 3: Generalizar `FileDropzone` para aceptar imágenes

**Files:**
- Modify: `frontend/src/components/upload/FileDropzone.tsx`

**Interfaces:**
- Produces: `FileDropzone` acepta ahora `accept?: string` (default `".xlsx,.xls"`) y `hint?: string` (default `"Solo .xlsx o .xls"`) — comportamiento actual sin cambios si no se pasan.

- [ ] **Step 1: Modificar la interfaz de props**

En `frontend/src/components/upload/FileDropzone.tsx`, cambiar:

```tsx
interface Props {
  file: File | null;
  onSelect: (file: File) => void;
  disabled?: boolean;
}
```
por:
```tsx
interface Props {
  file: File | null;
  onSelect: (file: File) => void;
  disabled?: boolean;
  accept?: string;
  hint?: string;
}
```

- [ ] **Step 2: Usar los defaults en la desestructuración y en el JSX**

Cambiar:
```tsx
export function FileDropzone({ file, onSelect, disabled }: Props) {
```
por:
```tsx
export function FileDropzone({
  file,
  onSelect,
  disabled,
  accept = ".xlsx,.xls",
  hint = "Solo .xlsx o .xls",
}: Props) {
```

Y en el JSX, cambiar el `<input>`:
```tsx
        accept=".xlsx,.xls"
```
por:
```tsx
        accept={accept}
```

Y el texto de ayuda:
```tsx
        <p className="text-xs text-muted-foreground mt-1">Solo .xlsx o .xls</p>
```
por:
```tsx
        <p className="text-xs text-muted-foreground mt-1">{hint}</p>
```

- [ ] **Step 3: Verificar que los dos usos existentes no pasan estas props (siguen con el default de Excel)**

Run (PowerShell): `Select-String -Path frontend\src\components\upload\ExcelUploadModal.tsx,frontend\src\components\upload\MaestroUploadModal.tsx -Pattern "<FileDropzone"`
Expected: ninguna de las dos líneas pasa `accept=` ni `hint=` — siguen usando el default de Excel sin cambios.

- [ ] **Step 4: Verificar tipos**

Run: `cd frontend && npx tsc --noEmit -p .`
Expected: sin errores

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/upload/FileDropzone.tsx
git commit -m "feat: FileDropzone acepta accept/hint configurables"
```

---

### Task 4: Servicio + UI de logo en `PlantillaPage.tsx`

**Files:**
- Modify: `frontend/src/services/plantilla.ts`
- Modify: `frontend/src/pages/PlantillaPage.tsx`

**Interfaces:**
- Consumes: `FileDropzone` con `accept`/`hint` (Task 3)
- Produces: `uploadLogo(file: File): Promise<Plantilla>`

- [ ] **Step 1: Agregar `uploadLogo` al servicio**

En `frontend/src/services/plantilla.ts`, agregar al final:

```ts
export async function uploadLogo(file: File): Promise<Plantilla> {
  const form = new FormData();
  form.append("file", file);
  const r = await apiFetch("/plantilla/logo", { method: "POST", body: form });
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    throw new Error(err.detail ?? "Error subiendo el logo");
  }
  return r.json();
}
```

- [ ] **Step 2: Agregar la sección de logo a `PlantillaPage.tsx`**

Agregar el import de `FileDropzone` y `uploadLogo`:

```tsx
import { FileDropzone } from "../components/upload/FileDropzone";
import { getPlantilla, updatePlantilla, uploadLogo } from "../services/plantilla";
```

Agregar el handler dentro del componente, junto a `handleSave`:

```tsx
  async function handleLogoSelect(file: File) {
    setStatus("Subiendo logo...");
    try {
      const updated = await uploadLogo(file);
      setForm(updated);
      setStatus("Logo actualizado");
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : "Error al subir el logo");
    }
  }
```

Agregar la sección en el JSX, después del bloque "Nombre empresa" (antes de "Color primario"):

```tsx
        <div className="space-y-1.5">
          <label className="block text-sm font-medium text-foreground">Logo</label>
          {form.logo_url && (
            <img
              src={form.logo_url}
              alt="Logo actual"
              className="h-12 max-w-[200px] object-contain rounded border border-border bg-secondary/30 p-2"
            />
          )}
          <FileDropzone
            file={null}
            onSelect={handleLogoSelect}
            accept="image/png,image/jpeg,image/webp"
            hint="PNG, JPG o WEBP — máximo 2MB"
          />
        </div>
```

- [ ] **Step 3: Verificar tipos y build**

Run: `cd frontend && npx tsc --noEmit -p . && npm run build`
Expected: sin errores, build exitoso

- [ ] **Step 4: Commit**

```bash
git add frontend/src/services/plantilla.ts frontend/src/pages/PlantillaPage.tsx
git commit -m "feat: subir logo real desde Plantilla"
```

---

## Self-Review

**Spec coverage:** cubre el punto "Importante" #5 de `docs/PENDIENTES.md` (logo como upload de imagen real, no URL de texto) completo — backend + frontend.

**Placeholder scan:** sin TBD.

**Type consistency:** `uploadLogo(file: File): Promise<Plantilla>` en Task 4 coincide con el `response_model=PlantillaSchema` del endpoint de Task 2 (mismo shape que ya usa `updatePlantilla`). `FileDropzone`'s nuevas props (`accept`, `hint`, Task 3) se consumen con los nombres exactos en Task 4.

**Riesgo controlado:** Task 3 generaliza un componente compartido — el propio plan incluye un step (Task 3, Step 3) para verificar explícitamente que los dos usos existentes (Excel de deudores, Excel maestro) no se ven afectados.
