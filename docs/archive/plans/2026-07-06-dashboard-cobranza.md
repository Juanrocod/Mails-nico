# Dashboard de Cobranza e Historial de Ciclos — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dashboard de cobranza (KPIs, rankings, evolución), perfil histórico por cliente, historial de ciclos navegable y aviso de respuestas tardías — sobre una inferencia de pago por ausencia (`saldado_en`).

**Architecture:** Una columna nueva (`envios.saldado_en`) se completa al confirmar cada ciclo comparando contra el anterior. Sobre esos datos: un servicio de agregación (`dashboard_service`) con 2 endpoints, endpoints de historial (ciclos y por cliente), y páginas nuevas de frontend (Dashboard, Perfil) más extensiones a Seguimiento y al preview.

**Tech Stack:** FastAPI + SQLAlchemy 2 + Alembic + pytest (backend); React 19 + TypeScript + Vite + recharts (frontend, `recharts` es la única dependencia nueva).

**Spec:** `docs/superpowers/specs/2026-07-06-dashboard-cobranza-design.md` — leerlo ante cualquier duda de comportamiento.

## Global Constraints

- NO modificar el enum `EstadoEnvio` de Postgres (nada de `ALTER TYPE`). La inferencia usa solo la columna nueva `saldado_en`.
- Lógica de negocio va en `app/services/`, NO en routers (`.claude/rules/backend.md`).
- Todos los endpoints nuevos llevan `Depends(get_current_user)` y `Depends(get_db)`.
- Migraciones con `op.batch_alter_table` (compatibilidad SQLite/Postgres).
- El rate limiting SMTP (5 mails/30s) no se toca.
- Textos de UI en español rioplatense, consistentes con los existentes (voseo: "revisá", "tenés").
- La "efectividad de recordatorios" se presenta como correlación, no causalidad: el texto exacto de la UI es **"saldaron tras el recordatorio"**.
- Tests backend: `cd backend && venv/Scripts/python -m pytest -q` debe quedar 100% en verde al final de cada tarea. Los tests comparten una SQLite en memoria de sesión: todo test que commitee `Ciclo`/`Envio`/`ClienteMaestro` debe borrarlos al final (patrón existente en `tests/test_ciclos.py::test_confirmar_ciclo`).
- Frontend: `cd frontend && npx tsc -b` sin errores al final de cada tarea de frontend.
- Ojo Windows: los comandos de test corren con `venv/Scripts/python -m pytest` (no `pytest` a secas).

---

## Mapa de archivos

| Archivo | Rol |
|---|---|
| `backend/alembic/versions/0006_envio_saldado_en.py` | Create — migración columna `saldado_en` |
| `backend/app/models/envio.py` | Modify — columna `saldado_en` |
| `backend/app/schemas/envio.py` | Modify — `saldado_en` en `EnvioSchema` |
| `backend/app/services/ciclo_service.py` | Create — `marcar_saldados()` |
| `backend/app/services/excel_joiner.py` | Modify — reset de racha con `saldado_en` |
| `backend/app/services/excel_parser.py` | Modify — `dedupe_deudores()` |
| `backend/app/schemas/ciclo.py` | Modify — campos de diff en `PreviewResponse` + `CicloResumenSchema` |
| `backend/app/routers/ciclos.py` | Modify — diff en preview, saldados en confirmar, `GET /ciclos`, `GET /ciclos/{id}/envios` |
| `backend/app/schemas/maestro.py` | Modify — `HistorialItemSchema`, `HistorialClienteResponse` |
| `backend/app/routers/maestro.py` | Modify — `GET /maestro/{clave_union}/historial` |
| `backend/app/schemas/seguimiento.py` | Create — `RespuestasTardiasResponse` |
| `backend/app/routers/seguimiento.py` | Modify — `GET /seguimiento/respuestas-tardias` |
| `backend/app/services/dashboard_service.py` | Create — `resumen()`, `evolucion()` |
| `backend/app/schemas/dashboard.py` | Create — schemas de respuesta del dashboard |
| `backend/app/routers/dashboard.py` | Create — `GET /dashboard/resumen`, `GET /dashboard/evolucion` |
| `backend/app/main.py` | Modify — registrar router dashboard |
| `backend/tests/test_saldado.py` | Create — inferencia + racha |
| `backend/tests/test_dashboard.py` | Create — resumen + evolución |
| `backend/tests/test_ciclos.py` | Modify — diff/dedupe de preview, endpoints de historial |
| `backend/tests/test_maestro.py` | Modify — historial por cliente |
| `backend/tests/test_seguimiento_router.py` | Modify — respuestas tardías |
| `frontend/src/types/domain.ts` | Modify — tipos nuevos |
| `frontend/src/services/dashboard.ts` | Create — API dashboard |
| `frontend/src/services/ciclos.ts` | Modify — `getCiclos`, `getEnviosDeCiclo` |
| `frontend/src/services/maestro.ts` | Modify — `getHistorialCliente` |
| `frontend/src/services/seguimiento.ts` | Modify — `getRespuestasTardias` |
| `frontend/src/pages/DashboardPage.tsx` | Create — KPIs + rankings + gráfico |
| `frontend/src/pages/ClientePerfilPage.tsx` | Create — perfil por cliente |
| `frontend/src/pages/SeguimientoPage.tsx` | Modify — selector de ciclo + banner tardías |
| `frontend/src/pages/MaestroPage.tsx` | Modify — nombre clickeable → perfil |
| `frontend/src/pages/NuevoEnvioPage.tsx` | Modify — diff/advertencias del preview |
| `frontend/src/App.tsx` | Modify — rutas `/dashboard`, `/clientes/:clave`, home |
| `frontend/src/components/layout/Sidebar.tsx` | Modify — entrada Dashboard |
| `frontend/package.json` | Modify — dependencia `recharts` |

---

### Task 1: Migración y modelo — `envios.saldado_en`

**Files:**
- Create: `backend/alembic/versions/0006_envio_saldado_en.py`
- Modify: `backend/app/models/envio.py`
- Modify: `backend/app/schemas/envio.py`
- Test: `backend/tests/test_models.py` (solo correr; sin test nuevo — la columna se ejercita en Task 2)

**Interfaces:**
- Produces: `Envio.saldado_en: DateTime nullable`; `EnvioSchema.saldado_en: Optional[datetime] = None`.

- [ ] **Step 1: Crear la migración**

```python
# backend/alembic/versions/0006_envio_saldado_en.py
"""envio_saldado_en

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-06
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.add_column(sa.Column("saldado_en", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("envios") as batch_op:
        batch_op.drop_column("saldado_en")
```

- [ ] **Step 2: Agregar la columna al modelo**

En `backend/app/models/envio.py`, después de la línea `proveedor = Column(String(20), nullable=True)`:

```python
    saldado_en = Column(DateTime, nullable=True)
```

- [ ] **Step 3: Exponerla en el schema**

En `backend/app/schemas/envio.py`, dentro de `EnvioSchema`, después de `enviado_en: Optional[datetime]`:

```python
    saldado_en: Optional[datetime] = None
```

- [ ] **Step 4: Aplicar migración local y correr suite**

Run: `cd backend && venv/Scripts/python -m alembic upgrade head && venv/Scripts/python -m pytest -q`
Expected: `Running upgrade 0005 -> 0006` y suite completa PASS (los tests usan `Base.metadata.create_all`, así que toman la columna del modelo).

- [ ] **Step 5: Commit**

```bash
git add backend/alembic/versions/0006_envio_saldado_en.py backend/app/models/envio.py backend/app/schemas/envio.py
git commit -m "feat: columna saldado_en en envios (migracion 0006)"
```

---

### Task 2: Inferencia de saldado + reset de racha

**Files:**
- Create: `backend/app/services/ciclo_service.py`
- Modify: `backend/app/services/excel_joiner.py` (función `_ciclos_consecutivos_deudor`)
- Modify: `backend/app/routers/ciclos.py` (dentro de `confirmar_ciclo`)
- Test: `backend/tests/test_saldado.py` (create)

**Interfaces:**
- Consumes: `Envio.saldado_en` (Task 1).
- Produces: `ciclo_service.marcar_saldados(db: Session, ciclo_anterior_id, claves_nuevas: set[str]) -> int` (setea `saldado_en` en memoria/sesión, NO commitea — el caller commitea).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# backend/tests/test_saldado.py
from datetime import datetime, timezone
from decimal import Decimal

from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio
from app.models.cliente_maestro import ClienteMaestro


def _make_ciclo(db, numero):
    c = Ciclo(numero=numero, activo=False, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    return c


def _make_envio(db, ciclo, clave, estado=EstadoEnvio.NO_CONTESTADO, monto="1000", saldado_en=None, ciclo_numero=1):
    e = Envio(
        ciclo_id=ciclo.id, ciclo_numero=ciclo_numero, clave_union=clave, nombre_consorcio=f"Cons {clave}",
        email=f"{clave}@mail.com", monto=Decimal(monto), estado=estado,
        saldado_en=saldado_en, actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.flush()
    return e


def test_marcar_saldados_marca_ausentes_y_no_presentes(db):
    from app.services.ciclo_service import marcar_saldados

    ciclo = _make_ciclo(db, 9001)
    ausente = _make_envio(db, ciclo, "SAL-A")
    presente = _make_envio(db, ciclo, "SAL-B")
    db.commit()

    count = marcar_saldados(db, ciclo.id, {"SAL-B"})
    db.commit()

    assert count == 1
    db.refresh(ausente)
    db.refresh(presente)
    assert ausente.saldado_en is not None
    assert presente.saldado_en is None

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_marcar_saldados_cubre_todos_los_estados(db):
    from app.services.ciclo_service import marcar_saldados

    ciclo = _make_ciclo(db, 9002)
    estados = [EstadoEnvio.NO_CONTESTADO, EstadoEnvio.CONTESTADO, EstadoEnvio.PAGO,
               EstadoEnvio.REBOTADO, EstadoEnvio.SIN_EMAIL, EstadoEnvio.FILTRADO]
    envios = [_make_envio(db, ciclo, f"SAL-EST-{i}", estado=est) for i, est in enumerate(estados)]
    db.commit()

    count = marcar_saldados(db, ciclo.id, set())
    db.commit()

    assert count == len(estados)
    for e in envios:
        db.refresh(e)
        assert e.saldado_en is not None

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_marcar_saldados_no_pisa_saldados_previos(db):
    """Un envio ya saldado en una transicion anterior conserva su fecha original."""
    from app.services.ciclo_service import marcar_saldados

    ciclo = _make_ciclo(db, 9003)
    fecha_original = datetime(2026, 1, 1, tzinfo=timezone.utc)
    ya_saldado = _make_envio(db, ciclo, "SAL-C", saldado_en=fecha_original)
    db.commit()

    count = marcar_saldados(db, ciclo.id, set())
    db.commit()

    assert count == 0
    db.refresh(ya_saldado)
    assert ya_saldado.saldado_en.year == 2026 and ya_saldado.saldado_en.month == 1

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_racha_se_resetea_si_ultimo_envio_esta_saldado(db):
    """Un deudor que saldo (inferido) y reaparece arranca la racha de cero."""
    from app.services.excel_joiner import _ciclos_consecutivos_deudor

    ciclo = _make_ciclo(db, 9004)
    _make_envio(db, ciclo, "SAL-D", ciclo_numero=4, saldado_en=datetime.now(timezone.utc))
    db.commit()

    assert _ciclos_consecutivos_deudor(db, "SAL-D") == 0

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_racha_sigue_si_ultimo_envio_no_saldado(db):
    from app.services.excel_joiner import _ciclos_consecutivos_deudor

    ciclo = _make_ciclo(db, 9005)
    _make_envio(db, ciclo, "SAL-E", ciclo_numero=3)
    db.commit()

    assert _ciclos_consecutivos_deudor(db, "SAL-E") == 3

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_confirmar_ciclo_marca_saldados_del_anterior(client, auth_headers, db, plantilla_default):
    """Integracion: confirmar un ciclo nuevo marca saldado a quien no reaparece."""
    import io
    import openpyxl
    from unittest.mock import patch, AsyncMock

    db.query(Ciclo).update({"activo": False})
    ciclo_ant = Ciclo(numero=9006, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo_ant)
    db.flush()
    envio_que_salda = _make_envio(db, ciclo_ant, "SAL-F")
    envio_que_repite = _make_envio(db, ciclo_ant, "SAL-G")
    db.add(ClienteMaestro(clave_union="SAL-G", nombre="Repite", email="salg@mail.com",
                          actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["nro cliente", "nombre", "localidad", "monto"])
    ws.append(["SAL-G", "Repite", "CABA", 2000])
    buf = io.BytesIO()
    wb.save(buf)

    with patch("app.routers.ciclos.enviar_ciclo", new_callable=AsyncMock):
        r = client.post(
            "/ciclos/confirmar",
            files={"file": ("deudores.xlsx", buf.getvalue(),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=auth_headers,
        )
    assert r.status_code == 200

    db.expire_all()
    db.refresh(envio_que_salda)
    db.refresh(envio_que_repite)
    assert envio_que_salda.saldado_en is not None
    assert envio_que_repite.saldado_en is None

    ciclo_nuevo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    db.query(Envio).filter(Envio.ciclo_id.in_([ciclo_ant.id, ciclo_nuevo.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([ciclo_ant.id, ciclo_nuevo.id])).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "SAL-G").delete(synchronize_session=False)
    db.commit()
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_saldado.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.ciclo_service'` y falla de racha.

- [ ] **Step 3: Implementar el servicio**

```python
# backend/app/services/ciclo_service.py
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.envio import Envio


def marcar_saldados(db: Session, ciclo_anterior_id, claves_nuevas: set[str]) -> int:
    """
    Inferencia de pago por ausencia: todo Envio del ciclo anterior cuya clave
    no figura entre los deudores del Excel nuevo se marca saldado_en=now.
    Aplica a todos los estados (el Excel de deudores es la fuente de verdad de
    quien debe). No commitea — el caller decide cuando.
    Devuelve la cantidad de envios marcados.
    """
    envios_anteriores = (
        db.query(Envio)
        .filter(Envio.ciclo_id == ciclo_anterior_id, Envio.saldado_en.is_(None))
        .all()
    )
    ahora = datetime.now(timezone.utc)
    count = 0
    for envio in envios_anteriores:
        if envio.clave_union not in claves_nuevas:
            envio.saldado_en = ahora
            db.add(envio)
            count += 1
    return count
```

- [ ] **Step 4: Reset de racha en `excel_joiner.py`**

Reemplazar la función `_ciclos_consecutivos_deudor` (el cambio es la condición del `if`):

```python
def _ciclos_consecutivos_deudor(db: Session, clave_union: str) -> int:
    last = (
        db.query(Envio)
        .filter(Envio.clave_union == clave_union)
        .order_by(Envio.ciclo_numero.desc())
        .first()
    )
    # PAGO manual o saldado inferido = racha rota: la proxima deuda arranca de cero.
    if last is None or last.estado == EstadoEnvio.PAGO or last.saldado_en is not None:
        return 0
    return last.ciclo_numero
```

- [ ] **Step 5: Integrar en `confirmar_ciclo`**

En `backend/app/routers/ciclos.py`, agregar el import:

```python
from app.services.ciclo_service import marcar_saldados
```

Y dentro de `confirmar_ciclo`, reemplazar el bloque de desactivación del ciclo anterior:

```python
    # Desactivar ciclo anterior si existe
    ciclo_anterior = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if ciclo_anterior:
        ciclo_anterior.activo = False
        db.add(ciclo_anterior)
```

por:

```python
    # Desactivar ciclo anterior si existe, y marcar saldados a los deudores
    # que no reaparecen en el Excel nuevo (inferencia de pago por ausencia).
    ciclo_anterior = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if ciclo_anterior:
        ciclo_anterior.activo = False
        db.add(ciclo_anterior)
        marcar_saldados(db, ciclo_anterior.id, {d.clave_union for d in deudores})
```

(El `db.commit()` existente más abajo persiste todo junto.)

- [ ] **Step 6: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo (los tests existentes de `ciclo_numero` no cambian de resultado: ningún fixture actual setea `saldado_en`).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/ciclo_service.py backend/app/services/excel_joiner.py backend/app/routers/ciclos.py backend/tests/test_saldado.py
git commit -m "feat: inferencia de saldado por ausencia y reset de racha"
```

---

### Task 3: Dedupe de claves y diff del ciclo en el preview

**Files:**
- Modify: `backend/app/services/excel_parser.py`
- Modify: `backend/app/schemas/ciclo.py`
- Modify: `backend/app/routers/ciclos.py` (`preview_ciclo` y `confirmar_ciclo`)
- Test: `backend/tests/test_ciclos.py` (agregar tests)

**Interfaces:**
- Produces: `excel_parser.dedupe_deudores(rows: list[DeudorRow]) -> tuple[list[DeudorRow], int]`; `PreviewResponse` con campos `nuevos: int`, `repiten: int`, `a_saldar: int`, `duplicados: int`, `total_ciclo_anterior: int`.

- [ ] **Step 1: Tests que fallan (agregar al final de `backend/tests/test_ciclos.py`)**

```python
def test_dedupe_deudores_conserva_la_ultima_fila():
    from decimal import Decimal as D
    from app.services.excel_parser import DeudorRow, dedupe_deudores

    rows = [
        DeudorRow("DUP-1", "Primero", "CABA", D("100")),
        DeudorRow("DUP-2", "Otro", "CABA", D("200")),
        DeudorRow("DUP-1", "Ultimo", "CABA", D("300")),
    ]
    unicos, descartados = dedupe_deudores(rows)
    assert descartados == 1
    assert len(unicos) == 2
    por_clave = {r.clave_union: r for r in unicos}
    assert por_clave["DUP-1"].nombre == "Ultimo"
    assert por_clave["DUP-1"].monto == D("300")


def test_preview_informa_diff_contra_ciclo_activo(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    ciclo = Ciclo(numero=9101, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    for clave in ("DIF-A", "DIF-B"):
        db.add(Envio(
            ciclo_id=ciclo.id, ciclo_numero=1, clave_union=clave, nombre_consorcio=clave,
            email=f"{clave.lower()}@mail.com", monto=Decimal("1000"),
            estado=EstadoEnvio.NO_CONTESTADO, actualizado_en=datetime.now(timezone.utc),
        ))
    db.commit()

    # Nuevo excel: DIF-B repite, DIF-C es nuevo, DIF-A desapareceria (a saldar).
    # DIF-C va duplicado para verificar el conteo de duplicados.
    excel = _make_deudores_excel([
        ["DIF-B", "Repite", "CABA", 1000],
        ["DIF-C", "Nuevo", "CABA", 500],
        ["DIF-C", "Nuevo bis", "CABA", 700],
    ])
    r = client.post(
        "/ciclos/preview",
        files={"file": ("d.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["nuevos"] == 1
    assert data["repiten"] == 1
    assert data["a_saldar"] == 1
    assert data["duplicados"] == 1
    assert data["total_ciclo_anterior"] == 2
    assert data["total_deudores"] == 2  # despues del dedupe

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_preview_sin_ciclo_activo_diff_en_cero(client, auth_headers, db, plantilla_default):
    from app.models.ciclo import Ciclo

    db.query(Ciclo).update({"activo": False})
    db.commit()

    excel = _make_deudores_excel([["DIF-Z", "Solo", "CABA", 1000]])
    r = client.post(
        "/ciclos/preview",
        files={"file": ("d.xlsx", excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=auth_headers,
    )
    data = r.json()
    assert data["nuevos"] == 1
    assert data["repiten"] == 0
    assert data["a_saldar"] == 0
    assert data["total_ciclo_anterior"] == 0
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_ciclos.py -k "dedupe or diff or informa_diff or sin_ciclo_activo_diff"`
Expected: FAIL — `dedupe_deudores` no existe / KeyError `nuevos`.

- [ ] **Step 3: Implementar `dedupe_deudores`**

Al final de `backend/app/services/excel_parser.py`:

```python
def dedupe_deudores(rows: list[DeudorRow]) -> tuple[list[DeudorRow], int]:
    """
    Si una clave_union aparece mas de una vez en el Excel, conserva solo la
    ultima fila (criterio del spec: la ultima pisa a las anteriores).
    Devuelve (filas unicas en orden de primera aparicion, cantidad descartada).
    """
    por_clave: dict[str, DeudorRow] = {}
    for row in rows:
        por_clave[row.clave_union] = row
    return list(por_clave.values()), len(rows) - len(por_clave)
```

- [ ] **Step 4: Campos nuevos en `PreviewResponse`**

En `backend/app/schemas/ciclo.py`, agregar al final de `PreviewResponse`:

```python
    nuevos: int
    repiten: int
    a_saldar: int
    duplicados: int
    total_ciclo_anterior: int
```

- [ ] **Step 5: Integrar en `preview_ciclo` y `confirmar_ciclo`**

En `backend/app/routers/ciclos.py`:

Import: agregar `dedupe_deudores` al import existente de `excel_parser`:

```python
from app.services.excel_parser import parse_deudores, dedupe_deudores, ExcelParseError
```

En `preview_ciclo`, reemplazar:

```python
    try:
        deudores = parse_deudores(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    plantilla = db_config.load_plantilla(db)
    preview = join_deudores(db, deudores, plantilla.monto_minimo)
```

por:

```python
    try:
        deudores = parse_deudores(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    deudores, duplicados = dedupe_deudores(deudores)
    plantilla = db_config.load_plantilla(db)
    preview = join_deudores(db, deudores, plantilla.monto_minimo)

    # Diff contra el ciclo activo: que cambia si se confirma este Excel.
    ciclo_activo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    claves_nuevas = {d.clave_union for d in deudores}
    claves_anteriores = (
        {e.clave_union for e in ciclo_activo.envios} if ciclo_activo else set()
    )
```

Y en el `return PreviewResponse(...)` agregar los campos:

```python
        nuevos=len(claves_nuevas - claves_anteriores),
        repiten=len(claves_nuevas & claves_anteriores),
        a_saldar=len(claves_anteriores - claves_nuevas),
        duplicados=duplicados,
        total_ciclo_anterior=len(claves_anteriores),
```

En `confirmar_ciclo`, reemplazar el mismo bloque de parseo:

```python
    try:
        deudores = parse_deudores(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
```

por:

```python
    try:
        deudores = parse_deudores(content)
    except ExcelParseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    deudores, _ = dedupe_deudores(deudores)
```

- [ ] **Step 6: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/excel_parser.py backend/app/schemas/ciclo.py backend/app/routers/ciclos.py backend/tests/test_ciclos.py
git commit -m "feat: dedupe de claves y diff contra el ciclo activo en el preview"
```

---

### Task 4: Endpoints de historial de ciclos

**Files:**
- Modify: `backend/app/schemas/ciclo.py` (`CicloResumenSchema`)
- Modify: `backend/app/routers/ciclos.py`
- Test: `backend/tests/test_ciclos.py`

**Interfaces:**
- Produces: `GET /ciclos` → `list[CicloResumenSchema]` (`{id, numero, activo, creado_en, total_envios, deuda_total}`, orden `numero` desc); `GET /ciclos/{ciclo_id}/envios` → `list[EnvioSchema]` (mismo shape que `/ciclos/activo/envios`, con `en_proceso`).
- **IMPORTANTE**: las rutas nuevas se declaran DESPUÉS de `get_envios_activo` en el archivo, para que `/ciclos/activo/envios` matchee antes que `/ciclos/{ciclo_id}/envios`.

- [ ] **Step 1: Tests que fallan (agregar a `backend/tests/test_ciclos.py`)**

```python
def test_listar_ciclos_con_totales(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    ciclo = Ciclo(numero=9201, activo=False, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    for i, monto in enumerate(("1000", "2500")):
        db.add(Envio(
            ciclo_id=ciclo.id, ciclo_numero=1, clave_union=f"LST-{i}", nombre_consorcio="X",
            email=f"lst{i}@mail.com", monto=Decimal(monto), estado=EstadoEnvio.NO_CONTESTADO,
            actualizado_en=datetime.now(timezone.utc),
        ))
    db.commit()

    r = client.get("/ciclos", headers=auth_headers)
    assert r.status_code == 200
    por_numero = {c["numero"]: c for c in r.json()}
    assert por_numero[9201]["total_envios"] == 2
    assert float(por_numero[9201]["deuda_total"]) == 3500.0

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_envios_de_ciclo_especifico(client, auth_headers, db, plantilla_default):
    from datetime import datetime, timezone
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    ciclo = Ciclo(numero=9202, activo=False, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    envio = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="HIS-1", nombre_consorcio="Historico",
        email="his1@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.CONTESTADO,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(envio)
    db.commit()

    r = client.get(f"/ciclos/{ciclo.id}/envios", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["clave_union"] == "HIS-1"
    assert data[0]["en_proceso"] is False

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_envios_de_ciclo_inexistente_404(client, auth_headers):
    import uuid
    r = client.get(f"/ciclos/{uuid.uuid4()}/envios", headers=auth_headers)
    assert r.status_code == 404
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_ciclos.py -k "listar_ciclos or ciclo_especifico or ciclo_inexistente"`
Expected: FAIL (405/404 en `/ciclos`).

- [ ] **Step 3: Schema `CicloResumenSchema`**

Al final de `backend/app/schemas/ciclo.py`:

```python
from datetime import datetime
from uuid import UUID


class CicloResumenSchema(BaseModel):
    id: UUID
    numero: int
    activo: bool
    creado_en: datetime
    total_envios: int
    deuda_total: Decimal
```

(Mover los imports al bloque de imports del archivo: `from datetime import datetime`, `from uuid import UUID`.)

- [ ] **Step 4: Implementar endpoints y helper compartido**

En `backend/app/routers/ciclos.py`:

Imports: agregar `func` de SQLAlchemy y el schema:

```python
from sqlalchemy import func
from app.schemas.ciclo import PreviewItem, PreviewResponse, CicloResumenSchema
```

Extraer el cuerpo de `get_envios_activo` a un helper (arriba de `get_envios_activo`):

```python
def _envios_con_flags(ciclo: Ciclo) -> list[EnvioSchema]:
    """Serializa los envios de un ciclo marcando cuales estan en envio en curso."""
    en_proceso = ids_en_proceso()
    result = []
    for envio in ciclo.envios:
        schema = EnvioSchema.model_validate(envio)
        schema.en_proceso = envio.id in en_proceso
        result.append(schema)
    return result
```

Reescribir `get_envios_activo` usando el helper:

```python
@router.get("/ciclos/activo/envios", response_model=list[EnvioSchema])
def get_envios_activo(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ciclo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if not ciclo:
        return []
    return _envios_con_flags(ciclo)
```

Debajo de `get_envios_activo` (orden de declaración importa), agregar:

```python
@router.get("/ciclos", response_model=list[CicloResumenSchema])
def listar_ciclos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    aggs = {
        ciclo_id: (total, deuda)
        for ciclo_id, total, deuda in db.query(
            Envio.ciclo_id, func.count(Envio.id), func.coalesce(func.sum(Envio.monto), 0)
        ).group_by(Envio.ciclo_id)
    }
    ciclos = db.query(Ciclo).order_by(Ciclo.numero.desc()).all()
    return [
        CicloResumenSchema(
            id=c.id, numero=c.numero, activo=c.activo, creado_en=c.creado_en,
            total_envios=aggs.get(c.id, (0, 0))[0], deuda_total=aggs.get(c.id, (0, 0))[1],
        )
        for c in ciclos
    ]


@router.get("/ciclos/{ciclo_id}/envios", response_model=list[EnvioSchema])
def get_envios_de_ciclo(
    ciclo_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ciclo = db.get(Ciclo, ciclo_id)
    if ciclo is None:
        raise HTTPException(status_code=404, detail="Ciclo no encontrado")
    return _envios_con_flags(ciclo)
```

- [ ] **Step 5: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/ciclo.py backend/app/routers/ciclos.py backend/tests/test_ciclos.py
git commit -m "feat: endpoints de historial de ciclos (lista y envios por ciclo)"
```

---

### Task 5: Historial por cliente

**Files:**
- Modify: `backend/app/schemas/maestro.py`
- Modify: `backend/app/routers/maestro.py`
- Test: `backend/tests/test_maestro.py`

**Interfaces:**
- Produces: `GET /maestro/{clave_union}/historial` → `HistorialClienteResponse`:
  `{cliente: Optional[ClienteMaestroSchema], clave_union: str, items: list[HistorialItemSchema]}` con items ordenados por número de ciclo descendente. `HistorialItemSchema = {envio_id, ciclo, ciclo_activo, fecha, monto, estado, motivo_filtrado, recibio_mail, reply_en, saldado_en, racha}`.
- El path usa `clave_union` (string), NO el UUID del cliente: el perfil debe funcionar también para claves que nunca se cargaron en el Maestro (envíos SIN_EMAIL).

- [ ] **Step 1: Tests que fallan (agregar a `backend/tests/test_maestro.py`)**

```python
def test_historial_de_cliente_cross_ciclo(client, auth_headers, db):
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.cliente_maestro import ClienteMaestro
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.add(ClienteMaestro(clave_union="HIS-CLI", nombre="Consorcio Historial",
                          email="hiscli@mail.com", actualizado_en=datetime.now(timezone.utc)))
    ciclos = []
    for numero in (9301, 9302):
        c = Ciclo(numero=numero, activo=(numero == 9302), creado_en=datetime.now(timezone.utc))
        db.add(c)
        db.flush()
        ciclos.append(c)
        db.add(Envio(
            ciclo_id=c.id, ciclo_numero=numero - 9300, clave_union="HIS-CLI",
            nombre_consorcio="Consorcio Historial", email="hiscli@mail.com",
            monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
            message_id="<x@mail.com>" if numero == 9301 else None,
            actualizado_en=datetime.now(timezone.utc),
        ))
    db.commit()

    r = client.get("/maestro/HIS-CLI/historial", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["cliente"]["nombre"] == "Consorcio Historial"
    assert len(data["items"]) == 2
    assert data["items"][0]["ciclo"] == 9302  # descendente
    assert data["items"][0]["ciclo_activo"] is True
    assert data["items"][1]["recibio_mail"] is True

    for c in ciclos:
        db.query(Envio).filter(Envio.ciclo_id == c.id).delete(synchronize_session=False)
        db.query(Ciclo).filter(Ciclo.id == c.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "HIS-CLI").delete(synchronize_session=False)
    db.commit()


def test_historial_de_clave_sin_maestro(client, auth_headers, db):
    """Una clave con envios pero sin registro en el Maestro devuelve cliente=None."""
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    ciclo = Ciclo(numero=9303, activo=False, creado_en=datetime.now(timezone.utc))
    db.add(ciclo)
    db.flush()
    db.add(Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union="HIS-SIN", nombre_consorcio="Sin Maestro",
        monto=Decimal("500"), estado=EstadoEnvio.SIN_EMAIL,
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/maestro/HIS-SIN/historial", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["cliente"] is None
    assert data["clave_union"] == "HIS-SIN"
    assert len(data["items"]) == 1

    db.query(Envio).filter(Envio.ciclo_id == ciclo.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == ciclo.id).delete(synchronize_session=False)
    db.commit()


def test_historial_clave_inexistente_404(client, auth_headers):
    r = client.get("/maestro/NO-EXISTE-999/historial", headers=auth_headers)
    assert r.status_code == 404
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_maestro.py -k historial`
Expected: FAIL (404 en todos, incluso los que esperan 200).

- [ ] **Step 3: Schemas**

Al final de `backend/app/schemas/maestro.py`:

```python
from datetime import datetime
from decimal import Decimal

from app.models.envio import EstadoEnvio, MotivoFiltrado


class HistorialItemSchema(BaseModel):
    envio_id: UUID
    ciclo: int
    ciclo_activo: bool
    fecha: datetime
    monto: Decimal
    estado: EstadoEnvio
    motivo_filtrado: Optional[MotivoFiltrado] = None
    recibio_mail: bool
    reply_en: Optional[datetime] = None
    saldado_en: Optional[datetime] = None
    racha: int


class HistorialClienteResponse(BaseModel):
    cliente: Optional[ClienteMaestroSchema] = None
    clave_union: str
    items: list[HistorialItemSchema]
```

(Mover `from datetime import datetime` y `from decimal import Decimal` arriba con los demás imports.)

- [ ] **Step 4: Endpoint**

En `backend/app/routers/maestro.py`, imports:

```python
from app.models.ciclo import Ciclo
from app.models.envio import Envio
from app.schemas.maestro import (
    ClienteMaestroSchema,
    ClienteMaestroUpdate,
    ClienteMaestroCreate,
    MaestroUploadResponse,
    HistorialItemSchema,
    HistorialClienteResponse,
)
```

Endpoint (agregarlo ANTES de `update_cliente` para mantener los GET juntos; no hay conflicto de rutas porque tiene el segmento extra `/historial`):

```python
@router.get("/{clave_union}/historial", response_model=HistorialClienteResponse)
def historial_cliente(
    clave_union: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cliente = db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == clave_union).first()
    rows = (
        db.query(Envio, Ciclo)
        .join(Ciclo, Envio.ciclo_id == Ciclo.id)
        .filter(Envio.clave_union == clave_union)
        .order_by(Ciclo.numero.desc())
        .all()
    )
    if cliente is None and not rows:
        raise HTTPException(status_code=404, detail="No hay cliente ni envios con esa clave")

    items = [
        HistorialItemSchema(
            envio_id=envio.id,
            ciclo=ciclo.numero,
            ciclo_activo=ciclo.activo,
            fecha=ciclo.creado_en,
            monto=envio.monto,
            estado=envio.estado,
            motivo_filtrado=envio.motivo_filtrado,
            recibio_mail=envio.message_id is not None,
            reply_en=envio.reply_en,
            saldado_en=envio.saldado_en,
            racha=envio.ciclo_numero,
        )
        for envio, ciclo in rows
    ]
    return HistorialClienteResponse(cliente=cliente, clave_union=clave_union, items=items)
```

- [ ] **Step 5: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/maestro.py backend/app/routers/maestro.py backend/tests/test_maestro.py
git commit -m "feat: historial de envios por cliente cross-ciclo"
```

---

### Task 6: Respuestas tardías

**Files:**
- Create: `backend/app/schemas/seguimiento.py`
- Modify: `backend/app/routers/seguimiento.py`
- Test: `backend/tests/test_seguimiento_router.py`

**Interfaces:**
- Produces: `GET /seguimiento/respuestas-tardias` → `{count: int, ciclos: [{ciclo_id: UUID, numero: int, count: int}]}`. Respuesta tardía = envío con `ciclo_id ≠ ciclo activo` y `reply_en ≥ creado_en` del ciclo activo. Sin ciclo activo → `{count: 0, ciclos: []}`.

- [ ] **Step 1: Tests que fallan (agregar a `backend/tests/test_seguimiento_router.py`)**

```python
def test_respuestas_tardias_detecta_replies_de_ciclos_viejos(client, auth_headers, db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    viejo = Ciclo(numero=9401, activo=False, creado_en=datetime.now(timezone.utc) - timedelta(days=15))
    activo = Ciclo(numero=9402, activo=True, creado_en=datetime.now(timezone.utc) - timedelta(days=1))
    db.add_all([viejo, activo])
    db.flush()
    # Reply DESPUES de que arranco el ciclo activo -> tardia
    db.add(Envio(
        ciclo_id=viejo.id, ciclo_numero=1, clave_union="TAR-1", nombre_consorcio="Tardio",
        email="tar1@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.CONTESTADO,
        reply_en=datetime.now(timezone.utc), actualizado_en=datetime.now(timezone.utc),
    ))
    # Reply ANTES del ciclo activo -> no cuenta
    db.add(Envio(
        ciclo_id=viejo.id, ciclo_numero=1, clave_union="TAR-2", nombre_consorcio="Viejo",
        email="tar2@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.CONTESTADO,
        reply_en=datetime.now(timezone.utc) - timedelta(days=10),
        actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/seguimiento/respuestas-tardias", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["ciclos"][0]["numero"] == 9401
    assert data["ciclos"][0]["count"] == 1

    db.query(Envio).filter(Envio.ciclo_id.in_([viejo.id, activo.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([viejo.id, activo.id])).delete(synchronize_session=False)
    db.commit()


def test_respuestas_tardias_sin_ciclo_activo(client, auth_headers, db):
    from app.models.ciclo import Ciclo

    db.query(Ciclo).update({"activo": False})
    db.commit()

    r = client.get("/seguimiento/respuestas-tardias", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == {"count": 0, "ciclos": []}
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_seguimiento_router.py -k tardias`
Expected: FAIL (404).

- [ ] **Step 3: Schema**

```python
# backend/app/schemas/seguimiento.py
from uuid import UUID

from pydantic import BaseModel


class RespuestasTardiasCiclo(BaseModel):
    ciclo_id: UUID
    numero: int
    count: int


class RespuestasTardiasResponse(BaseModel):
    count: int
    ciclos: list[RespuestasTardiasCiclo]
```

- [ ] **Step 4: Endpoint**

En `backend/app/routers/seguimiento.py`, agregar imports:

```python
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.ciclo import Ciclo
from app.models.envio import Envio
from app.schemas.seguimiento import RespuestasTardiasCiclo, RespuestasTardiasResponse
```

Y el endpoint al final del archivo:

```python
@router.get("/respuestas-tardias", response_model=RespuestasTardiasResponse)
def respuestas_tardias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Respuestas que llegaron despues de que arranco el ciclo activo pero
    pertenecen a envios de ciclos anteriores (aterrizan en el envio viejo y
    serian invisibles desde la vista del ciclo actual)."""
    ciclo_activo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if ciclo_activo is None:
        return RespuestasTardiasResponse(count=0, ciclos=[])

    rows = (
        db.query(Envio.ciclo_id, Ciclo.numero, func.count(Envio.id))
        .join(Ciclo, Envio.ciclo_id == Ciclo.id)
        .filter(
            Envio.ciclo_id != ciclo_activo.id,
            Envio.reply_en.isnot(None),
            Envio.reply_en >= ciclo_activo.creado_en,
        )
        .group_by(Envio.ciclo_id, Ciclo.numero)
        .all()
    )
    ciclos = [RespuestasTardiasCiclo(ciclo_id=cid, numero=num, count=cnt) for cid, num, cnt in rows]
    return RespuestasTardiasResponse(count=sum(c.count for c in ciclos), ciclos=ciclos)
```

- [ ] **Step 5: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/seguimiento.py backend/app/routers/seguimiento.py backend/tests/test_seguimiento_router.py
git commit -m "feat: endpoint de respuestas tardias de ciclos anteriores"
```

---

### Task 7: Dashboard backend (servicio + endpoints)

**Files:**
- Create: `backend/app/services/dashboard_service.py`
- Create: `backend/app/schemas/dashboard.py`
- Create: `backend/app/routers/dashboard.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_dashboard.py` (create)

**Interfaces:**
- Consumes: `Envio.saldado_en` (Task 1).
- Produces: `GET /dashboard/resumen` → `DashboardResumenResponse`; `GET /dashboard/evolucion` → `list[EvolucionCicloSchema]` (orden `numero` ascendente).
- Regla del KPI "cobrado" (del spec): `Σ montos de envíos del ciclo anterior con saldado_en` **+** `Σ max(0, monto_anterior − monto_actual)` para claves que repiten. Los aumentos de deuda NO restan.
- "Efectividad": entre los envíos del ciclo anterior con `message_id`, % con `saldado_en`. `None` si no hay ciclo anterior o nadie recibió mail.

- [ ] **Step 1: Tests que fallan**

```python
# backend/tests/test_dashboard.py
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio


def _make_envio(db, ciclo, clave, monto, message_id=None, saldado_en=None):
    e = Envio(
        ciclo_id=ciclo.id, ciclo_numero=1, clave_union=clave, nombre_consorcio=f"Cons {clave}",
        email=f"{clave}@mail.com", monto=Decimal(monto), estado=EstadoEnvio.NO_CONTESTADO,
        message_id=message_id, saldado_en=saldado_en,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.flush()
    return e


def _seed_dos_ciclos(db):
    """Ciclo anterior: DSH-A ($1000, con mail, saldado), DSH-B ($2000, con mail, repite
    bajando a $500 = pago parcial de $1500), DSH-C ($300, sin mail, repite subiendo a $800).
    Ciclo activo: DSH-B ($500), DSH-C ($800), DSH-D ($900, nuevo).
    cobrado esperado = 1000 (saldado) + 1500 (parcial B) + 0 (C subio) = 2500.
    efectividad esperada = 1 de 2 con mail saldo = 50.0.
    deuda actual = 500 + 800 + 900 = 2200. deuda anterior = 3300.
    """
    db.query(Ciclo).update({"activo": False})
    anterior = Ciclo(numero=9501, activo=False, creado_en=datetime.now(timezone.utc) - timedelta(days=15))
    activo = Ciclo(numero=9502, activo=True, creado_en=datetime.now(timezone.utc))
    db.add_all([anterior, activo])
    db.flush()
    ahora = datetime.now(timezone.utc)
    _make_envio(db, anterior, "DSH-A", "1000", message_id="<a@x>", saldado_en=ahora)
    _make_envio(db, anterior, "DSH-B", "2000", message_id="<b@x>")
    _make_envio(db, anterior, "DSH-C", "300")
    _make_envio(db, activo, "DSH-B", "500")
    _make_envio(db, activo, "DSH-C", "800")
    _make_envio(db, activo, "DSH-D", "900")
    db.commit()
    return anterior, activo


def _cleanup(db, ciclos):
    db.query(Envio).filter(Envio.ciclo_id.in_([c.id for c in ciclos])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([c.id for c in ciclos])).delete(synchronize_session=False)
    db.commit()


def test_resumen_calcula_kpis(client, auth_headers, db):
    ciclos = _seed_dos_ciclos(db)

    r = client.get("/dashboard/resumen", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["hay_ciclo_activo"] is True
    assert float(data["deuda_total"]) == 2200.0
    assert float(data["deuda_total_anterior"]) == 3300.0
    assert data["deudores"] == 3
    assert data["deudores_anterior"] == 3
    assert float(data["cobrado"]) == 2500.0
    assert data["efectividad"] == 50.0

    _cleanup(db, ciclos)


def test_resumen_sin_ciclo_activo(client, auth_headers, db):
    db.query(Ciclo).update({"activo": False})
    db.commit()

    r = client.get("/dashboard/resumen", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["hay_ciclo_activo"] is False
    assert float(data["deuda_total"]) == 0.0
    assert data["cobrado"] is None
    assert data["efectividad"] is None


def test_resumen_primer_ciclo_sin_anterior(client, auth_headers, db):
    db.query(Ciclo).update({"activo": False})
    solo = Ciclo(numero=9503, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(solo)
    db.flush()
    _make_envio(db, solo, "DSH-SOLO", "1200")
    db.commit()

    r = client.get("/dashboard/resumen", headers=auth_headers)
    data = r.json()
    assert float(data["deuda_total"]) == 1200.0
    assert data["deuda_total_anterior"] is None
    assert data["cobrado"] is None
    assert data["efectividad"] is None

    _cleanup(db, [solo])


def test_evolucion_series_por_ciclo(client, auth_headers, db):
    ciclos = _seed_dos_ciclos(db)

    r = client.get("/dashboard/evolucion", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    por_numero = {item["numero"]: item for item in data}
    assert float(por_numero[9501]["deuda_total"]) == 3300.0
    assert por_numero[9501]["deudores"] == 3
    assert por_numero[9501]["cobrado"] is None or float(por_numero[9501]["cobrado"]) == 0.0
    assert float(por_numero[9502]["deuda_total"]) == 2200.0
    assert float(por_numero[9502]["cobrado"]) == 2500.0
    numeros = [item["numero"] for item in data]
    assert numeros == sorted(numeros)  # ascendente

    _cleanup(db, ciclos)
```

Nota para el implementador: el ciclo 9501 no tiene ciclo inmediatamente anterior **dentro del test**, pero la DB compartida puede contener ciclos de otros tests ya limpiados — por eso el assert de `cobrado` para 9501 acepta `None` o `0.0`.

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_dashboard.py`
Expected: FAIL (404 — el router no existe).

- [ ] **Step 3: Schemas**

```python
# backend/app/schemas/dashboard.py
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DashboardResumenResponse(BaseModel):
    hay_ciclo_activo: bool
    deuda_total: Decimal
    deuda_total_anterior: Optional[Decimal] = None
    deudores: int
    deudores_anterior: Optional[int] = None
    cobrado: Optional[Decimal] = None
    efectividad: Optional[float] = None


class EvolucionCicloSchema(BaseModel):
    numero: int
    fecha: datetime
    deuda_total: Decimal
    deudores: int
    cobrado: Optional[Decimal] = None
```

- [ ] **Step 4: Servicio**

```python
# backend/app/services/dashboard_service.py
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.models.ciclo import Ciclo
from app.models.envio import Envio


@dataclass
class EnvioResumen:
    monto: Decimal
    saldado: bool
    con_mail: bool


@dataclass
class ResumenData:
    hay_ciclo_activo: bool
    deuda_total: Decimal
    deuda_total_anterior: Optional[Decimal]
    deudores: int
    deudores_anterior: Optional[int]
    cobrado: Optional[Decimal]
    efectividad: Optional[float]


@dataclass
class EvolucionItem:
    numero: int
    fecha: datetime
    deuda_total: Decimal
    deudores: int
    cobrado: Optional[Decimal]


def _envios_por_clave(db: Session, ciclo_id) -> dict[str, EnvioResumen]:
    rows = (
        db.query(Envio.clave_union, Envio.monto, Envio.saldado_en, Envio.message_id)
        .filter(Envio.ciclo_id == ciclo_id)
        .all()
    )
    return {
        clave: EnvioResumen(monto=monto, saldado=saldado_en is not None, con_mail=message_id is not None)
        for clave, monto, saldado_en, message_id in rows
    }


def _cobrado_entre(anteriores: dict[str, EnvioResumen], actuales: dict[str, EnvioResumen]) -> Decimal:
    """Deuda eliminada entre dos ciclos: montos saldados completos + reducciones
    de monto de los que repiten (pagos parciales). Los aumentos no restan."""
    cobrado = Decimal("0")
    for clave, ant in anteriores.items():
        if ant.saldado:
            cobrado += ant.monto
        elif clave in actuales:
            reduccion = ant.monto - actuales[clave].monto
            if reduccion > 0:
                cobrado += reduccion
    return cobrado


def _efectividad(anteriores: dict[str, EnvioResumen]) -> Optional[float]:
    con_mail = [e for e in anteriores.values() if e.con_mail]
    if not con_mail:
        return None
    saldaron = sum(1 for e in con_mail if e.saldado)
    return round(100 * saldaron / len(con_mail), 1)


def resumen(db: Session) -> ResumenData:
    activo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if activo is None:
        return ResumenData(
            hay_ciclo_activo=False, deuda_total=Decimal("0"), deuda_total_anterior=None,
            deudores=0, deudores_anterior=None, cobrado=None, efectividad=None,
        )
    anterior = (
        db.query(Ciclo)
        .filter(Ciclo.numero < activo.numero)
        .order_by(Ciclo.numero.desc())
        .first()
    )
    envios_activo = _envios_por_clave(db, activo.id)
    deuda_total = sum((e.monto for e in envios_activo.values()), start=Decimal("0"))

    if anterior is None:
        return ResumenData(
            hay_ciclo_activo=True, deuda_total=deuda_total, deuda_total_anterior=None,
            deudores=len(envios_activo), deudores_anterior=None, cobrado=None, efectividad=None,
        )

    envios_anterior = _envios_por_clave(db, anterior.id)
    return ResumenData(
        hay_ciclo_activo=True,
        deuda_total=deuda_total,
        deuda_total_anterior=sum((e.monto for e in envios_anterior.values()), start=Decimal("0")),
        deudores=len(envios_activo),
        deudores_anterior=len(envios_anterior),
        cobrado=_cobrado_entre(envios_anterior, envios_activo),
        efectividad=_efectividad(envios_anterior),
    )


def evolucion(db: Session) -> list[EvolucionItem]:
    ciclos = db.query(Ciclo).order_by(Ciclo.numero).all()
    items: list[EvolucionItem] = []
    envios_previos: Optional[dict[str, EnvioResumen]] = None
    for ciclo in ciclos:
        envios = _envios_por_clave(db, ciclo.id)
        items.append(EvolucionItem(
            numero=ciclo.numero,
            fecha=ciclo.creado_en,
            deuda_total=sum((e.monto for e in envios.values()), start=Decimal("0")),
            deudores=len(envios),
            cobrado=_cobrado_entre(envios_previos, envios) if envios_previos is not None else None,
        ))
        envios_previos = envios
    return items
```

- [ ] **Step 5: Router + registro en main**

```python
# backend/app/routers/dashboard.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardResumenResponse, EvolucionCicloSchema
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/resumen", response_model=DashboardResumenResponse)
def get_resumen(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = dashboard_service.resumen(db)
    return DashboardResumenResponse(
        hay_ciclo_activo=data.hay_ciclo_activo,
        deuda_total=data.deuda_total,
        deuda_total_anterior=data.deuda_total_anterior,
        deudores=data.deudores,
        deudores_anterior=data.deudores_anterior,
        cobrado=data.cobrado,
        efectividad=data.efectividad,
    )


@router.get("/evolucion", response_model=list[EvolucionCicloSchema])
def get_evolucion(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        EvolucionCicloSchema(
            numero=item.numero, fecha=item.fecha, deuda_total=item.deuda_total,
            deudores=item.deudores, cobrado=item.cobrado,
        )
        for item in dashboard_service.evolucion(db)
    ]
```

En `backend/app/main.py`:

```python
from app.routers import auth, plantilla, maestro, ciclos, configuracion, unsubscribe, seguimiento, dashboard
```

y después de `app.include_router(seguimiento.router)`:

```python
app.include_router(dashboard.router)
```

- [ ] **Step 6: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/dashboard_service.py backend/app/schemas/dashboard.py backend/app/routers/dashboard.py backend/app/main.py backend/tests/test_dashboard.py
git commit -m "feat: servicio y endpoints del dashboard de cobranza"
```

---

### Task 8: Frontend — tipos y servicios API

**Files:**
- Modify: `frontend/src/types/domain.ts`
- Create: `frontend/src/services/dashboard.ts`
- Modify: `frontend/src/services/ciclos.ts`
- Modify: `frontend/src/services/maestro.ts`
- Modify: `frontend/src/services/seguimiento.ts`

**Interfaces:**
- Produces (consumidas por Tasks 9-12): `getDashboardResumen(): Promise<DashboardResumen>`, `getDashboardEvolucion(): Promise<EvolucionCiclo[]>`, `getCiclos(): Promise<CicloResumen[]>`, `getEnviosDeCiclo(id: string): Promise<Envio[]>`, `getHistorialCliente(clave: string): Promise<HistorialCliente>`, `getRespuestasTardias(): Promise<RespuestasTardias>`.

- [ ] **Step 1: Tipos en `frontend/src/types/domain.ts`**

Agregar `saldado_en` a `Envio` (después de `enviado_en`):

```ts
  saldado_en: string | null;
```

Agregar a `PreviewCiclo` (al final de la interfaz):

```ts
  nuevos: number;
  repiten: number;
  a_saldar: number;
  duplicados: number;
  total_ciclo_anterior: number;
```

Y al final del archivo:

```ts
export interface DashboardResumen {
  hay_ciclo_activo: boolean;
  deuda_total: number;
  deuda_total_anterior: number | null;
  deudores: number;
  deudores_anterior: number | null;
  cobrado: number | null;
  efectividad: number | null;
}

export interface EvolucionCiclo {
  numero: number;
  fecha: string;
  deuda_total: number;
  deudores: number;
  cobrado: number | null;
}

export interface CicloResumen {
  id: string;
  numero: number;
  activo: boolean;
  creado_en: string;
  total_envios: number;
  deuda_total: number;
}

export interface HistorialItem {
  envio_id: string;
  ciclo: number;
  ciclo_activo: boolean;
  fecha: string;
  monto: number;
  estado: EstadoEnvio;
  motivo_filtrado: MotivoFiltrado | null;
  recibio_mail: boolean;
  reply_en: string | null;
  saldado_en: string | null;
  racha: number;
}

export interface HistorialCliente {
  cliente: ClienteMaestro | null;
  clave_union: string;
  items: HistorialItem[];
}

export interface RespuestasTardias {
  count: number;
  ciclos: { ciclo_id: string; numero: number; count: number }[];
}
```

- [ ] **Step 2: Servicio dashboard**

```ts
// frontend/src/services/dashboard.ts
import { apiFetch } from "./api";
import type { DashboardResumen, EvolucionCiclo } from "../types/domain";

export async function getDashboardResumen(): Promise<DashboardResumen> {
  const r = await apiFetch("/dashboard/resumen");
  if (!r.ok) throw new Error("Error cargando el resumen del dashboard");
  return r.json();
}

export async function getDashboardEvolucion(): Promise<EvolucionCiclo[]> {
  const r = await apiFetch("/dashboard/evolucion");
  if (!r.ok) throw new Error("Error cargando la evolución");
  return r.json();
}
```

- [ ] **Step 3: Extensiones a servicios existentes**

Al final de `frontend/src/services/ciclos.ts` (y agregar `CicloResumen` al import de tipos):

```ts
export async function getCiclos(): Promise<CicloResumen[]> {
  const r = await apiFetch("/ciclos");
  if (!r.ok) throw new Error("Error cargando el historial de ciclos");
  return r.json();
}

export async function getEnviosDeCiclo(cicloId: string): Promise<Envio[]> {
  const r = await apiFetch(`/ciclos/${cicloId}/envios`);
  if (!r.ok) throw new Error("Error cargando los envíos del ciclo");
  return r.json();
}
```

Al final de `frontend/src/services/maestro.ts` (y agregar `HistorialCliente` al import de tipos):

```ts
export async function getHistorialCliente(claveUnion: string): Promise<HistorialCliente> {
  const r = await apiFetch(`/maestro/${encodeURIComponent(claveUnion)}/historial`);
  if (!r.ok) throw new Error("Error cargando el historial del cliente");
  return r.json();
}
```

Al final de `frontend/src/services/seguimiento.ts`:

```ts
import type { RespuestasTardias } from "../types/domain";

export async function getRespuestasTardias(): Promise<RespuestasTardias> {
  const r = await apiFetch("/seguimiento/respuestas-tardias");
  if (!r.ok) throw new Error("Error cargando respuestas tardías");
  return r.json();
}
```

(El `import type` va arriba del archivo junto al import existente de `apiFetch`.)

- [ ] **Step 4: Verificar compilación**

Run: `cd frontend && npx tsc -b`
Expected: sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/domain.ts frontend/src/services/dashboard.ts frontend/src/services/ciclos.ts frontend/src/services/maestro.ts frontend/src/services/seguimiento.ts
git commit -m "feat: tipos y servicios API para dashboard e historial"
```

---

### Task 9: Frontend — DashboardPage + sidebar + rutas

**Files:**
- Modify: `frontend/package.json` (via `npm install recharts`)
- Create: `frontend/src/pages/DashboardPage.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/layout/Sidebar.tsx`

**Interfaces:**
- Consumes: `getDashboardResumen`, `getDashboardEvolucion` (Task 8), `getEnviosActivo` (existente).
- Produces: ruta `/dashboard`; los rankings navegan a `/clientes/{clave_union}` (la página se crea en Task 10 — hasta entonces esa navegación cae en el redirect `*` → `/`, aceptable dentro de la misma rama).

- [ ] **Step 1: Instalar recharts**

Run: `cd frontend && npm install recharts`
Expected: agrega `recharts` (v3.x, compatible con React 19) a `package.json`.

- [ ] **Step 2: Crear `DashboardPage.tsx`**

```tsx
// frontend/src/pages/DashboardPage.tsx
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ResponsiveContainer, ComposedChart, Line, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend,
} from "recharts";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Skeleton } from "../components/ui/skeleton";
import { getDashboardResumen, getDashboardEvolucion } from "../services/dashboard";
import { getEnviosActivo } from "../services/ciclos";
import type { DashboardResumen, EvolucionCiclo, Envio } from "../types/domain";

function pesos(n: number | null): string {
  if (n === null) return "—";
  return `$${Number(n).toLocaleString("es-AR")}`;
}

function variacion(actual: number, anterior: number | null): string {
  if (anterior === null || anterior === 0) return "";
  const pct = ((actual - anterior) / anterior) * 100;
  const signo = pct > 0 ? "+" : "";
  return `${signo}${pct.toFixed(1)}% vs. ciclo anterior`;
}

function KpiCard({ titulo, valor, detalle }: { titulo: string; valor: string; detalle?: string }) {
  return (
    <div className="rounded-md border border-border bg-secondary/30 p-4">
      <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{titulo}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums text-foreground">{valor}</p>
      {detalle && <p className="mt-0.5 text-xs text-muted-foreground">{detalle}</p>}
    </div>
  );
}

const ESTADO_MAIL: Record<string, string> = {
  NO_CONTESTADO: "Sin respuesta",
  CONTESTADO: "Contestó",
  PAGO: "Pagó",
  REBOTADO: "Rebotó",
  SIN_EMAIL: "Sin email",
  FILTRADO: "Filtrado",
};

export default function DashboardPage() {
  const [resumen, setResumen] = useState<DashboardResumen | null>(null);
  const [evolucion, setEvolucion] = useState<EvolucionCiclo[]>([]);
  const [envios, setEnvios] = useState<Envio[]>([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([getDashboardResumen(), getDashboardEvolucion(), getEnviosActivo()])
      .then(([r, e, envs]) => {
        setResumen(r);
        setEvolucion(e);
        setEnvios(envs);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-24 w-full" />)}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  const topMonto = [...envios].sort((a, b) => Number(b.monto) - Number(a.monto)).slice(0, 10);
  const topCronicos = [...envios]
    .filter((e) => e.ciclo_numero > 1)
    .sort((a, b) => b.ciclo_numero - a.ciclo_numero || Number(b.monto) - Number(a.monto))
    .slice(0, 10);

  const chartData = evolucion.map((c) => ({
    nombre: `#${c.numero} ${format(new Date(c.fecha), "dd/MM", { locale: es })}`,
    deuda: Number(c.deuda_total),
    cobrado: c.cobrado === null ? 0 : Number(c.cobrado),
    deudores: c.deudores,
  }));

  return (
    <div className="max-w-5xl mx-auto space-y-5">
      <div className="flex items-baseline gap-3">
        <h1 className="text-xl font-semibold text-foreground">Dashboard</h1>
        <span className="text-sm text-muted-foreground">Estado de la cobranza según el último Excel</span>
      </div>

      {!resumen?.hay_ciclo_activo ? (
        <div className="rounded-md border border-dashed border-border py-12 text-center">
          <p className="text-sm font-medium text-foreground">Todavía no hay ciclos cargados</p>
          <p className="text-sm text-muted-foreground">Subí el primer Excel de deudores para empezar a medir.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <KpiCard
              titulo="Deuda total"
              valor={pesos(resumen.deuda_total)}
              detalle={variacion(resumen.deuda_total, resumen.deuda_total_anterior)}
            />
            <KpiCard
              titulo="Deudores"
              valor={String(resumen.deudores)}
              detalle={
                resumen.deudores_anterior !== null
                  ? `${resumen.deudores_anterior} en el ciclo anterior`
                  : undefined
              }
            />
            <KpiCard
              titulo="Cobrado desde el ciclo anterior"
              valor={pesos(resumen.cobrado)}
              detalle="Deuda saldada + pagos parciales"
            />
            <KpiCard
              titulo="Saldaron tras el recordatorio"
              valor={resumen.efectividad === null ? "—" : `${resumen.efectividad}%`}
              detalle="De los que recibieron mail el ciclo pasado"
            />
          </div>

          {chartData.length > 1 && (
            <div className="rounded-md border border-border p-4">
              <p className="mb-3 text-sm font-medium text-foreground">Evolución por ciclo</p>
              <ResponsiveContainer width="100%" height={280}>
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="nombre" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(value: number, name: string) =>
                    name === "Deudores" ? value : `$${Number(value).toLocaleString("es-AR")}`
                  } />
                  <Legend />
                  <Bar dataKey="cobrado" name="Cobrado" fill="hsl(var(--primary))" opacity={0.5} />
                  <Line type="monotone" dataKey="deuda" name="Deuda total" stroke="hsl(var(--primary))" strokeWidth={2} dot />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}

          <Tabs defaultValue="monto">
            <TabsList>
              <TabsTrigger value="monto">Top deudores por monto</TabsTrigger>
              <TabsTrigger value="cronicos">Morosos crónicos</TabsTrigger>
            </TabsList>
            {(["monto", "cronicos"] as const).map((tab) => {
              const list = tab === "monto" ? topMonto : topCronicos;
              return (
                <TabsContent key={tab} value={tab}>
                  {list.length === 0 ? (
                    <p className="py-8 text-center text-sm text-muted-foreground">
                      {tab === "cronicos"
                        ? "Nadie lleva más de un ciclo debiendo."
                        : "No hay deudores en el ciclo activo."}
                    </p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border text-left">
                          <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Consorcio</th>
                          <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Monto</th>
                          <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Ciclos debiendo</th>
                          <th className="py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Último mail</th>
                        </tr>
                      </thead>
                      <tbody>
                        {list.map((e) => (
                          <tr
                            key={e.id}
                            className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                            onClick={() => navigate(`/clientes/${encodeURIComponent(e.clave_union)}`)}
                          >
                            <td className="py-2.5 pr-4 text-foreground">{e.nombre_consorcio}</td>
                            <td className="py-2.5 pr-4 text-right tabular-nums">{pesos(Number(e.monto))}</td>
                            <td className="py-2.5 pr-4 text-right tabular-nums">{e.ciclo_numero}</td>
                            <td className="py-2.5 text-muted-foreground">{ESTADO_MAIL[e.estado] ?? e.estado}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </TabsContent>
              );
            })}
          </Tabs>
        </>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Ruta y home en `App.tsx`**

```tsx
import DashboardPage from './pages/DashboardPage'
```

Dentro del bloque de rutas con `AppLayout`, agregar y cambiar la home:

```tsx
          <Route path="/dashboard" element={<DashboardPage />} />
```

y reemplazar

```tsx
          <Route path="/" element={<Navigate to="/seguimiento/no-contestados" replace />} />
```

por

```tsx
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
```

- [ ] **Step 4: Sidebar**

En `frontend/src/components/layout/Sidebar.tsx`: agregar `LayoutDashboard` al import de lucide-react, y como PRIMERA entrada del `<nav>` (antes de "Nuevo Envío"):

```tsx
        <NavItem to="/dashboard" label="Dashboard" icon={LayoutDashboard} />

        <Separator className="my-2" />
```

- [ ] **Step 5: Verificar compilación y build**

Run: `cd frontend && npx tsc -b && npm run build`
Expected: sin errores.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/src/pages/DashboardPage.tsx frontend/src/App.tsx frontend/src/components/layout/Sidebar.tsx
git commit -m "feat: pagina de Dashboard con KPIs, rankings y evolucion"
```

---

### Task 10: Frontend — ClientePerfilPage + accesos

**Files:**
- Create: `frontend/src/pages/ClientePerfilPage.tsx`
- Modify: `frontend/src/App.tsx` (ruta `/clientes/:clave`)
- Modify: `frontend/src/pages/MaestroPage.tsx` (nombre clickeable)

**Interfaces:**
- Consumes: `getHistorialCliente(clave)` (Task 8); ruta `/clientes/:clave` consumida por los rankings de Task 9.

- [ ] **Step 1: Crear `ClientePerfilPage.tsx`**

```tsx
// frontend/src/pages/ClientePerfilPage.tsx
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { Button } from "../components/ui/button";
import { Skeleton } from "../components/ui/skeleton";
import { getHistorialCliente } from "../services/maestro";
import type { HistorialCliente } from "../types/domain";

const ESTADO_LABEL: Record<string, string> = {
  NO_CONTESTADO: "Sin respuesta",
  CONTESTADO: "Contestó",
  PAGO: "Pagó",
  REBOTADO: "Rebotó",
  SIN_EMAIL: "Sin email",
  FILTRADO: "Filtrado",
};

function pesos(n: number): string {
  return `$${Number(n).toLocaleString("es-AR")}`;
}

export default function ClientePerfilPage() {
  const { clave } = useParams<{ clave: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<HistorialCliente | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!clave) return;
    getHistorialCliente(clave)
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Error cargando el perfil"))
      .finally(() => setLoading(false));
  }, [clave]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="max-w-4xl mx-auto space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Volver
        </Button>
        <p className="text-sm text-destructive">{error || "No se encontró el cliente."}</p>
      </div>
    );
  }

  const items = data.items;
  const actual = items.find((i) => i.ciclo_activo);
  const totalSaldado = items.filter((i) => i.saldado_en).reduce((acc, i) => acc + Number(i.monto), 0);
  const conMail = items.filter((i) => i.recibio_mail);
  const contesto = conMail.filter((i) => i.reply_en).length;
  const estadoCliente = !data.cliente
    ? "No está en el Maestro"
    : data.cliente.prefiere_no_recibir_email
      ? "Dado de baja"
      : data.cliente.activo
        ? "Activo"
        : "Eliminado";

  return (
    <div className="max-w-4xl mx-auto space-y-5">
      <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
        <ArrowLeft className="mr-1.5 h-3.5 w-3.5" /> Volver
      </Button>

      <div>
        <div className="flex items-baseline gap-3">
          <h1 className="text-xl font-semibold text-foreground">
            {data.cliente?.nombre ?? `Clave ${data.clave_union}`}
          </h1>
          <span className="font-mono text-xs text-muted-foreground">{data.clave_union}</span>
        </div>
        <p className="mt-0.5 text-sm text-muted-foreground">
          {data.cliente?.email ?? "Sin email"} · {data.cliente?.localidad ?? "Sin localidad"} · {estadoCliente}
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Deuda actual</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{actual ? pesos(Number(actual.monto)) : "—"}</p>
        </div>
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Ciclos debiendo</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{actual ? actual.racha : "—"}</p>
        </div>
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Saldado histórico</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">{pesos(totalSaldado)}</p>
        </div>
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Respuesta a mails</p>
          <p className="mt-1 text-2xl font-semibold tabular-nums">
            {conMail.length === 0 ? "—" : `${contesto}/${conMail.length}`}
          </p>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-left">
              <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Ciclo</th>
              <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Fecha</th>
              <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Monto</th>
              <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Mail</th>
              <th className="py-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">Resultado</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.envio_id} className="border-b border-border last:border-0">
                <td className="py-2.5 pr-4 tabular-nums">#{i.ciclo}{i.ciclo_activo ? " (actual)" : ""}</td>
                <td className="py-2.5 pr-4 text-muted-foreground">
                  {format(new Date(i.fecha), "dd/MM/yyyy", { locale: es })}
                </td>
                <td className="py-2.5 pr-4 text-right tabular-nums">{pesos(Number(i.monto))}</td>
                <td className="py-2.5 pr-4 text-muted-foreground">
                  {i.recibio_mail ? ESTADO_LABEL[i.estado] ?? i.estado : "No se envió"}
                </td>
                <td className="py-2.5">
                  {i.saldado_en
                    ? `Saldado el ${format(new Date(i.saldado_en), "dd/MM/yyyy", { locale: es })}`
                    : i.ciclo_activo
                      ? "Deuda vigente"
                      : "Siguió debiendo"}
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

- [ ] **Step 2: Ruta en `App.tsx`**

```tsx
import ClientePerfilPage from './pages/ClientePerfilPage'
```

y dentro del bloque `AppLayout`:

```tsx
          <Route path="/clientes/:clave" element={<ClientePerfilPage />} />
```

- [ ] **Step 3: Nombre clickeable en `MaestroPage.tsx`**

Agregar `import { useNavigate } from "react-router-dom";` y `const navigate = useNavigate();` dentro del componente. En la celda del nombre, reemplazar la rama de no-edición:

```tsx
                    ) : (
                      c.nombre
                    )}
```

por:

```tsx
                    ) : (
                      <button
                        type="button"
                        className="text-left hover:underline"
                        onClick={() => navigate(`/clientes/${encodeURIComponent(c.clave_union)}`)}
                      >
                        {c.nombre}
                      </button>
                    )}
```

- [ ] **Step 4: Verificar compilación**

Run: `cd frontend && npx tsc -b`
Expected: sin errores.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ClientePerfilPage.tsx frontend/src/App.tsx frontend/src/pages/MaestroPage.tsx
git commit -m "feat: perfil historico por cliente con accesos desde dashboard y maestro"
```

---

### Task 11: Frontend — Seguimiento: selector de ciclo + banner de respuestas tardías

**Files:**
- Modify: `frontend/src/pages/SeguimientoPage.tsx`

**Interfaces:**
- Consumes: `getCiclos`, `getEnviosDeCiclo` (Task 8), `getRespuestasTardias` (Task 8), `getEnviosActivo`/`refrescarSeguimiento` (existentes).

- [ ] **Step 1: Modificar `SeguimientoPage.tsx`**

Imports nuevos (agregar a los existentes):

```tsx
import { getEnviosActivo, getCiclos, getEnviosDeCiclo } from "../services/ciclos";
import { refrescarSeguimiento, getRespuestasTardias } from "../services/seguimiento";
import type { Envio, CicloResumen, RespuestasTardias } from "../types/domain";
```

Estado nuevo dentro del componente (junto a los `useState` existentes):

```tsx
  const [ciclos, setCiclos] = useState<CicloResumen[]>([]);
  const [cicloSeleccionado, setCicloSeleccionado] = useState<string>("activo");
  const [tardias, setTardias] = useState<RespuestasTardias | null>(null);
  const [tardiasDismissed, setTardiasDismissed] = useState(false);
```

Reemplazar el `useEffect` de carga inicial:

```tsx
  useEffect(() => {
    getEnviosActivo().then(setEnvios).catch(console.error);
  }, []);
```

por:

```tsx
  useEffect(() => {
    getEnviosActivo().then(setEnvios).catch(console.error);
    getCiclos().then(setCiclos).catch(console.error);
    getRespuestasTardias()
      .then((t) => {
        setTardias(t);
        const firma = `tardias:${t.count}`;
        setTardiasDismissed(localStorage.getItem("seg_tardias_dismissed") === firma);
      })
      .catch(console.error);
  }, []);

  useEffect(() => {
    if (cicloSeleccionado === "activo") {
      getEnviosActivo().then(setEnvios).catch(console.error);
    } else {
      getEnviosDeCiclo(cicloSeleccionado).then(setEnvios).catch(console.error);
    }
  }, [cicloSeleccionado]);
```

Handler de dismiss (junto a los demás handlers):

```tsx
  function dismissTardias() {
    if (!tardias) return;
    localStorage.setItem("seg_tardias_dismissed", `tardias:${tardias.count}`);
    setTardiasDismissed(true);
  }
```

En el `handleRefrescar` existente, reemplazar `const data = await getEnviosActivo();` por una recarga coherente con la selección:

```tsx
      const data =
        cicloSeleccionado === "activo" ? await getEnviosActivo() : await getEnviosDeCiclo(cicloSeleccionado);
```

En el JSX, debajo del header (el `div` con el título y el botón "Refrescar ahora") y antes de `{refrescarError && ...}`, agregar el selector y el banner:

```tsx
      <div className="flex items-center gap-2">
        <label className="text-sm text-muted-foreground">Ciclo:</label>
        <select
          className="h-9 rounded-md border border-input bg-background px-2 text-sm"
          value={cicloSeleccionado}
          onChange={(e) => setCicloSeleccionado(e.target.value)}
        >
          <option value="activo">Ciclo actual</option>
          {ciclos
            .filter((c) => !c.activo)
            .map((c) => (
              <option key={c.id} value={c.id}>
                Ciclo #{c.numero} — {new Date(c.creado_en).toLocaleDateString("es-AR")}
              </option>
            ))}
        </select>
      </div>

      {tardias && tardias.count > 0 && !tardiasDismissed && (
        <div className="flex items-start justify-between gap-2 rounded-md border border-warning/30 bg-warning/10 px-3 py-2 text-sm text-warning-text">
          <span>
            {tardias.count} respuesta{tardias.count === 1 ? "" : "s"} nueva{tardias.count === 1 ? "" : "s"} en
            ciclos anteriores:{" "}
            {tardias.ciclos.map((c, idx) => (
              <button
                key={c.ciclo_id}
                type="button"
                className="underline"
                onClick={() => setCicloSeleccionado(c.ciclo_id)}
              >
                {idx > 0 ? ", " : ""}Ciclo #{c.numero} ({c.count})
              </button>
            ))}
          </span>
          <button type="button" onClick={dismissTardias} aria-label="Cerrar aviso" className="shrink-0">
            ✕
          </button>
        </div>
      )}
```

- [ ] **Step 2: Verificar compilación**

Run: `cd frontend && npx tsc -b`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/SeguimientoPage.tsx
git commit -m "feat: selector de ciclo historico y aviso de respuestas tardias en Seguimiento"
```

---

### Task 12: Frontend — diff y advertencias del preview

**Files:**
- Modify: `frontend/src/pages/NuevoEnvioPage.tsx`

**Interfaces:**
- Consumes: campos `nuevos/repiten/a_saldar/duplicados/total_ciclo_anterior` de `PreviewCiclo` (Tasks 3 y 8).

- [ ] **Step 1: Agregar el diff al banner de revisión**

En `NuevoEnvioPage.tsx`, dentro del bloque `{revisando && (...)}` — reemplazar:

```tsx
          <p className="text-sm text-muted-foreground">
            Sin confirmar todavía — revisá las 3 solapas y confirmá cuando esté todo bien.
          </p>
```

por:

```tsx
          <div className="space-y-1">
            <p className="text-sm text-muted-foreground">
              Sin confirmar todavía — revisá las 3 solapas y confirmá cuando esté todo bien.
            </p>
            <p className="text-sm text-muted-foreground">
              {previewData!.nuevos} nuevo{previewData!.nuevos === 1 ? "" : "s"} ·{" "}
              {previewData!.repiten} repite{previewData!.repiten === 1 ? "" : "n"} del ciclo anterior ·{" "}
              {previewData!.a_saldar} se dará{previewData!.a_saldar === 1 ? "" : "n"} por saldado
              {previewData!.a_saldar === 1 ? "" : "s"}
            </p>
            {previewData!.duplicados > 0 && (
              <p className="text-sm text-warning-text">
                ⚠ {previewData!.duplicados} fila{previewData!.duplicados === 1 ? "" : "s"} con clave repetida en
                el Excel — se usó la última de cada una.
              </p>
            )}
            {previewData!.total_ciclo_anterior > 0 &&
              previewData!.a_saldar > previewData!.total_ciclo_anterior / 2 && (
                <p className="text-sm font-medium text-warning-text">
                  ⚠ Más de la mitad de los deudores del ciclo anterior desaparecerían con este Excel. Si no es lo
                  esperado, revisá que no sea un archivo viejo o incompleto antes de confirmar.
                </p>
              )}
          </div>
```

- [ ] **Step 2: Verificar compilación y build**

Run: `cd frontend && npx tsc -b && npm run build`
Expected: sin errores.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/NuevoEnvioPage.tsx
git commit -m "feat: diff contra el ciclo anterior y advertencias en el preview"
```

---

### Task 13: Cierre — suite completa, migración en dev y docs

**Files:**
- Modify: `docs/PENDIENTES.md`

- [ ] **Step 1: Suite completa backend + frontend**

Run: `cd backend && venv/Scripts/python -m pytest -q` → PASS completo.
Run: `cd frontend && npx tsc -b && npm run build` → sin errores.

- [ ] **Step 2: Verificar migración aplicada en dev**

Run: `cd backend && venv/Scripts/python -m alembic current`
Expected: `0006 (head)`.

- [ ] **Step 3: Actualizar `docs/PENDIENTES.md`**

Agregar a la sección "Resuelto desde la última auditoría":

```markdown
- **Dashboard de cobranza e historial** — KPIs (deuda, deudores, cobrado, efectividad), rankings (monto / morosos crónicos), evolución por ciclo, perfil histórico por cliente (`/clientes/:clave`), selector de ciclos pasados en Seguimiento, aviso de respuestas tardías, inferencia de pago por ausencia (`saldado_en`, migración 0006), dedupe de claves duplicadas y diff del Excel contra el ciclo activo en el preview. Spec: `docs/superpowers/specs/2026-07-06-dashboard-cobranza-design.md`.
```

- [ ] **Step 4: Commit**

```bash
git add docs/PENDIENTES.md
git commit -m "docs: registrar dashboard de cobranza e historial en PENDIENTES"
```

---

## Notas de deploy (para después del merge, fuera del plan)

- La migración 0006 corre sola en Render (`entrypoint.sh` hace `alembic upgrade head`).
- Vercel toma el frontend automáticamente al pushear `master`; Render requiere redeploy manual (workflow habitual del proyecto).
- Los envíos históricos existentes en producción tienen `saldado_en = NULL`: la inferencia empieza a poblar el dato desde el próximo cambio de ciclo. Producción se limpió el 2026-07-05, así que las métricas arrancan consistentes desde el primer Excel real.
