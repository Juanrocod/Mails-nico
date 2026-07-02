# Validaciones de Email y Plantilla — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Sin dependencias:** este plan no toca ningún archivo que los demás planes pendientes toquen. Puede ejecutarse en paralelo con cualquiera de los otros (`config-yahoo`, `unsubscribe-endpoint`, `logo-upload`, `envio-reply-fields`).

**Goal:** Dos validaciones puntuales que el spec pide y hoy no existen: formato de email antes de mandar un mail, y palabras prohibidas al guardar la Plantilla.

**Architecture:** Ambas son validaciones puras, sin estado ni I/O — una función de regex en `excel_joiner.py` y un `field_validator` de Pydantic en el schema de Plantilla.

**Tech Stack:** `re` (stdlib), Pydantic v2 `field_validator`.

## Global Constraints

- Nada de dependencias nuevas — las dos validaciones se resuelven con la librería estándar y Pydantic, que ya están.
- Correr tests: `cd backend && venv\Scripts\python -m pytest -v`

---

## File Structure

- Modify: `backend/app/services/excel_joiner.py` — regex de validación de formato de email
- Modify: `backend/tests/test_excel_joiner.py`
- Modify: `backend/app/schemas/plantilla.py` — lista de palabras prohibidas + `field_validator`
- Modify: `backend/tests/test_plantilla.py`

---

### Task 1: Validación de formato de email en `excel_joiner.py`

**Files:**
- Modify: `backend/app/services/excel_joiner.py`
- Modify: `backend/tests/test_excel_joiner.py`

**Interfaces:**
- Produces: comportamiento nuevo en `join_deudores` — un `ClienteMaestro` con `email` de formato inválido cae en `sin_email`, igual que si no tuviera email cargado.

- [ ] **Step 1: Escribir el test (falla primero)**

Agregar a `backend/tests/test_excel_joiner.py`:

```python
def test_join_email_con_formato_invalido_cae_en_sin_email(db):
    _add_cliente(db, "C010", "Consorcio Diez", email="esto-no-es-un-email")
    deudores = [DeudorRow("C010", "Consorcio Diez", "CABA", Decimal("3000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.sin_email) == 1
    assert len(preview.para_enviar) == 0


def test_join_email_valido_pasa_a_para_enviar(db):
    _add_cliente(db, "C011", "Consorcio Once", email="valido@dominio.com.ar")
    deudores = [DeudorRow("C011", "Consorcio Once", "CABA", Decimal("3000"))]
    preview = join_deudores(db, deudores, monto_minimo=Decimal("0"))
    assert len(preview.para_enviar) == 1
    assert len(preview.sin_email) == 0
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_excel_joiner.py -v -k formato_invalido`
Expected: FAIL — hoy `join_deudores` no valida formato, así que `"esto-no-es-un-email"` termina en `para_enviar`.

- [ ] **Step 3: Implementar la validación**

En `backend/app/services/excel_joiner.py`, agregar el import y la regex al principio del archivo (después de los imports existentes, línea 9):

```python
import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))
```

Y reemplazar la línea 63:
```python
        if not cliente.email:
```
por:
```python
        if not cliente.email or not _is_valid_email(cliente.email):
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_excel_joiner.py -v`
Expected: todos los tests del archivo pasan (7 originales + 2 nuevos = 9)

- [ ] **Step 5: Correr toda la suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos pasan

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/excel_joiner.py backend/tests/test_excel_joiner.py
git commit -m "feat: validar formato de email antes de incluir en para_enviar"
```

---

### Task 2: Palabras prohibidas al guardar Plantilla

**Files:**
- Modify: `backend/app/schemas/plantilla.py`
- Modify: `backend/tests/test_plantilla.py`

**Interfaces:**
- Produces: `PALABRAS_PROHIBIDAS: list[str]` (constante exportada, para que el operario o un test puedan ver/extender la lista), validación en `PlantillaSchema` que rechaza `asunto`/`cuerpo_html` con 422 si contienen alguna.

- [ ] **Step 1: Escribir el test (falla primero)**

Agregar a `backend/tests/test_plantilla.py`:

```python
def test_put_plantilla_rechaza_palabra_prohibida_en_asunto(client, auth_headers):
    r = client.put("/plantilla", json={
        "asunto": "GRATIS: recordatorio de deuda",
        "cuerpo_html": "<p>texto normal</p>",
        "nombre_empresa": "SA",
        "color_primario": "#000000",
        "monto_minimo": 0,
    }, headers=auth_headers)
    assert r.status_code == 422


def test_put_plantilla_rechaza_palabra_prohibida_en_cuerpo(client, auth_headers):
    r = client.put("/plantilla", json={
        "asunto": "Recordatorio de deuda",
        "cuerpo_html": "<p>Haga clic ya para regularizar su situación</p>",
        "nombre_empresa": "SA",
        "color_primario": "#000000",
        "monto_minimo": 0,
    }, headers=auth_headers)
    assert r.status_code == 422


def test_put_plantilla_acepta_texto_sin_palabras_prohibidas(client, auth_headers):
    r = client.put("/plantilla", json={
        "asunto": "Recordatorio de deuda pendiente",
        "cuerpo_html": "<p>Le informamos que registra una deuda con nuestra empresa.</p>",
        "nombre_empresa": "SA",
        "color_primario": "#000000",
        "monto_minimo": 0,
    }, headers=auth_headers)
    assert r.status_code == 200
```

- [ ] **Step 2: Correr el test para verificar que falla**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_plantilla.py -v -k prohibida`
Expected: FAIL — hoy no hay ninguna validación, los tres devuelven 200 (los dos primeros deberían dar 422).

- [ ] **Step 3: Implementar el validador**

En `backend/app/schemas/plantilla.py`, reemplazar el contenido completo por:

```python
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, field_validator

# Lista inicial de palabras/frases típicas de spam en cobranzas. Extensible — no
# viene fijada por el spec, es un punto de partida razonable a revisar con el cliente.
PALABRAS_PROHIBIDAS: list[str] = [
    "gratis",
    "urgente",
    "haga clic ya",
    "gane dinero",
    "100% gratis",
    "oferta exclusiva",
]


class PlantillaSchema(BaseModel):
    asunto: str
    cuerpo_html: str
    nombre_empresa: str
    logo_url: Optional[str] = None
    color_primario: str = "#1a56db"
    monto_minimo: Decimal

    model_config = {"from_attributes": True}

    @field_validator("asunto", "cuerpo_html")
    @classmethod
    def sin_palabras_prohibidas(cls, v: str) -> str:
        lower = v.lower()
        for palabra in PALABRAS_PROHIBIDAS:
            if palabra in lower:
                raise ValueError(f"El texto contiene una palabra no permitida: '{palabra}'")
        return v
```

- [ ] **Step 4: Correr el test para verificar que pasa**

Run: `cd backend && venv\Scripts\python -m pytest tests/test_plantilla.py -v`
Expected: todos los tests del archivo pasan (3 originales + 3 nuevos = 6)

- [ ] **Step 5: Correr toda la suite**

Run: `cd backend && venv\Scripts\python -m pytest -v`
Expected: todos pasan

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/plantilla.py backend/tests/test_plantilla.py
git commit -m "feat: validar palabras prohibidas al guardar Plantilla"
```

---

## Self-Review

**Spec coverage:** cubre los puntos "Importante" #3 y #4 de `docs/PENDIENTES.md` completos.

**Placeholder scan:** sin TBD. La lista de `PALABRAS_PROHIBIDAS` es un punto de partida deliberadamente señalado como revisable (no es un placeholder — es una constante real, funcional, y editable).

**Type consistency:** `_is_valid_email` es privada a `excel_joiner.py`, no se expone ni se consume en otro lado — sin riesgo de firma inconsistente. `PALABRAS_PROHIBIDAS` es una lista de strings simple, usada solo dentro del mismo archivo.
