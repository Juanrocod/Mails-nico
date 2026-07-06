# Dashboard v2 — Antigüedad de deuda y mejoras — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) o superpowers:executing-plans. Steps usan checkbox (`- [ ]`).

**Goal:** Agregar una métrica de antigüedad de deuda (tiempo real, reconstruida del historial de ciclos) al dashboard y al perfil de cliente, más los ajustes de KPIs y estética pedidos.

**Architecture:** Todo se deriva de columnas que ya existen (`saldado_en`, `ciclo_numero`, `Ciclo.creado_en`) — sin migración. Una función de servicio `deudor_desde_por_clave` computa, con una sola query cross-ciclo, la fecha de inicio de la racha vigente de cada consorcio; el dashboard y el perfil la consumen. Se restylea el gráfico (recharts, mismo look que el repo app-peluqueria del usuario) en un componente compartido.

**Tech Stack:** FastAPI + SQLAlchemy 2 + pytest (backend); React 19 + TypeScript + Vite + recharts + date-fns (frontend).

**Spec:** `docs/superpowers/specs/2026-07-06-dashboard-v2-antiguedad-design.md`.

## Global Constraints

- **Sin migración** — no hay columnas nuevas; todo se deriva de `saldado_en`, `ciclo_numero`, `Ciclo.creado_en`.
- Lógica de negocio en `app/services/`, NO en routers.
- Todos los endpoints con `Depends(get_current_user)` y `Depends(get_db)`.
- Se **elimina** el KPI "efectividad / saldaron tras el recordatorio" (campo `efectividad`) y se agrega `deuda_mas_90`.
- **Comparaciones de fecha tz-safe**: `Ciclo.creado_en` vuelve **naive** desde Postgres (prod) pero puede ser **aware** en la sesión de test. Toda comparación en Python normaliza con el helper `_a_naive_utc` (definido en Task 1). Nunca comparar aware vs naive directo.
- Umbral de deuda vencida: **90 días** (`_UMBRAL_VENCIDA_DIAS = 90`).
- Antigüedad se presenta como tiempo relativo ("hace X") con `date-fns` locale `es`; **rojo si supera 90 días**.
- Textos UI en español rioplatense (voseo).
- Tests backend: `cd backend && venv/Scripts/python -m pytest -q` (Windows Git Bash), 100% verde al final de cada tarea. Cleanup obligatorio de Ciclo/Envio/ClienteMaestro creados (SQLite compartida de sesión) — patrón en `tests/test_saldado.py`.
- Frontend: `cd frontend && npx tsc -b` (y `npm run build` donde el plan lo indique) sin errores.

---

## Mapa de archivos

| Archivo | Rol |
|---|---|
| `backend/app/services/dashboard_service.py` | Modify — `deudor_desde_por_clave`, `_a_naive_utc`, `morosos`, `resumen` (deuda_mas_90, quita efectividad) |
| `backend/app/schemas/dashboard.py` | Modify — `DashboardResumenResponse` (deuda_mas_90), `MorosoSchema` nuevo |
| `backend/app/routers/dashboard.py` | Modify — `GET /dashboard/morosos`, resumen actualizado |
| `backend/app/schemas/maestro.py` | Modify — `deudor_desde` en `HistorialClienteResponse` |
| `backend/app/routers/maestro.py` | Modify — `historial_cliente` computa `deudor_desde` |
| `backend/tests/test_antiguedad.py` | Create — tests de `deudor_desde_por_clave` |
| `backend/tests/test_dashboard.py` | Modify — deuda_mas_90 y morosos; quitar asserts de efectividad |
| `backend/tests/test_maestro.py` | Modify — `deudor_desde` en el perfil |
| `frontend/src/types/domain.ts` | Modify — tipos |
| `frontend/src/services/dashboard.ts` | Modify — `getMorosos` |
| `frontend/src/components/dashboard/EvolucionChart.tsx` | Create — gráfico de área compartido |
| `frontend/src/pages/DashboardPage.tsx` | Modify — KPIs, gráfico, morosos |
| `frontend/src/pages/ClientePerfilPage.tsx` | Modify — antigüedad + gráfico |
| `docs/PENDIENTES.md` | Modify — registrar v2 |

---

### Task 1: `deudor_desde_por_clave` (servicio + helper tz-safe)

**Files:**
- Modify: `backend/app/services/dashboard_service.py`
- Test: `backend/tests/test_antiguedad.py` (create)

**Interfaces:**
- Produces: `_a_naive_utc(dt: datetime) -> datetime`; `deudor_desde_por_clave(db: Session, claves: set[str]) -> dict[str, datetime]` (clave → fecha del primer ciclo de la racha vigente; claves sin deuda vigente NO aparecen).

- [ ] **Step 1: Escribir los tests que fallan**

```python
# backend/tests/test_antiguedad.py
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.models.ciclo import Ciclo
from app.models.envio import Envio, EstadoEnvio


def _ciclo(db, numero, dias_atras):
    c = Ciclo(numero=numero, activo=False,
              creado_en=datetime.now(timezone.utc) - timedelta(days=dias_atras))
    db.add(c)
    db.flush()
    return c


def _envio(db, ciclo, clave, racha, estado=EstadoEnvio.NO_CONTESTADO, saldado=False):
    e = Envio(
        ciclo_id=ciclo.id, ciclo_numero=racha, clave_union=clave,
        nombre_consorcio=f"Cons {clave}", email=f"{clave}@mail.com",
        monto=Decimal("1000"), estado=estado,
        saldado_en=datetime.now(timezone.utc) if saldado else None,
        actualizado_en=datetime.now(timezone.utc),
    )
    db.add(e)
    db.flush()
    return e


def _limpiar(db, ciclos):
    db.query(Envio).filter(Envio.ciclo_id.in_([c.id for c in ciclos])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([c.id for c in ciclos])).delete(synchronize_session=False)
    db.commit()


def test_deudor_desde_racha_simple(db):
    from app.services.dashboard_service import deudor_desde_por_clave

    c1 = _ciclo(db, 8801, 40)
    c2 = _ciclo(db, 8802, 10)
    _envio(db, c1, "ANT-A", 1)
    _envio(db, c2, "ANT-A", 2)
    db.commit()

    desde = deudor_desde_por_clave(db, {"ANT-A"})
    assert "ANT-A" in desde
    # arranco a deber en el ciclo mas viejo de la racha (c1, ~40 dias atras)
    assert (datetime.now(timezone.utc).replace(tzinfo=None) - desde["ANT-A"].replace(tzinfo=None)).days >= 39

    _limpiar(db, [c1, c2])


def test_deudor_desde_corta_por_saldado(db):
    from app.services.dashboard_service import deudor_desde_por_clave

    c1 = _ciclo(db, 8811, 90)
    c2 = _ciclo(db, 8812, 40)
    c3 = _ciclo(db, 8813, 10)
    _envio(db, c1, "ANT-B", 3, saldado=True)   # racha vieja cerrada
    _envio(db, c2, "ANT-B", 1)                  # arranca racha nueva
    _envio(db, c3, "ANT-B", 2)
    db.commit()

    desde = deudor_desde_por_clave(db, {"ANT-B"})
    # la racha vigente arranca en c2 (~40 dias), no en c1 (~90)
    dias = (datetime.now(timezone.utc).replace(tzinfo=None) - desde["ANT-B"].replace(tzinfo=None)).days
    assert 39 <= dias <= 45

    _limpiar(db, [c1, c2, c3])


def test_deudor_desde_corta_por_pago(db):
    from app.services.dashboard_service import deudor_desde_por_clave

    c1 = _ciclo(db, 8821, 60)
    c2 = _ciclo(db, 8822, 10)
    _envio(db, c1, "ANT-C", 4, estado=EstadoEnvio.PAGO)
    _envio(db, c2, "ANT-C", 1)
    db.commit()

    desde = deudor_desde_por_clave(db, {"ANT-C"})
    dias = (datetime.now(timezone.utc).replace(tzinfo=None) - desde["ANT-C"].replace(tzinfo=None)).days
    assert dias <= 12  # arranca en c2

    _limpiar(db, [c1, c2])


def test_deudor_desde_sin_deuda_vigente(db):
    """Si el envio mas reciente esta saldado, no hay deuda vigente -> no aparece."""
    from app.services.dashboard_service import deudor_desde_por_clave

    c1 = _ciclo(db, 8831, 30)
    _envio(db, c1, "ANT-D", 2, saldado=True)
    db.commit()

    desde = deudor_desde_por_clave(db, {"ANT-D"})
    assert "ANT-D" not in desde

    _limpiar(db, [c1])


def test_deudor_desde_claves_vacias(db):
    from app.services.dashboard_service import deudor_desde_por_clave
    assert deudor_desde_por_clave(db, set()) == {}
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_antiguedad.py`
Expected: FAIL — `cannot import name 'deudor_desde_por_clave'`.

- [ ] **Step 3: Implementar el helper y la función**

En `backend/app/services/dashboard_service.py`, cambiar el import de datetime (línea 2) por:

```python
from datetime import datetime, timedelta, timezone
```

y el import de modelos (línea 9) por:

```python
from app.models.envio import Envio, EstadoEnvio
```

Agregar al final del archivo:

```python
_UMBRAL_VENCIDA_DIAS = 90


def _a_naive_utc(dt: datetime) -> datetime:
    """Normaliza a naive-UTC. Ciclo.creado_en vuelve naive desde Postgres pero
    puede ser aware en la sesion de test; asi las comparaciones nunca mezclan."""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def deudor_desde_por_clave(db: Session, claves: set[str]) -> dict[str, datetime]:
    """Para cada clave con deuda vigente, la fecha del primer ciclo de su racha
    actual ('deudor desde'). Claves sin deuda vigente (envio mas reciente PAGO o
    saldado) no aparecen. Una sola query cross-ciclo."""
    if not claves:
        return {}
    rows = (
        db.query(Envio.clave_union, Ciclo.creado_en, Envio.estado, Envio.saldado_en)
        .join(Ciclo, Envio.ciclo_id == Ciclo.id)
        .filter(Envio.clave_union.in_(claves))
        .order_by(Ciclo.numero.desc())
        .all()
    )
    por_clave: dict[str, list] = {}
    for clave, creado_en, estado, saldado_en in rows:
        por_clave.setdefault(clave, []).append((creado_en, estado, saldado_en))

    resultado: dict[str, datetime] = {}
    for clave, envios in por_clave.items():
        streak_start = None
        for creado_en, estado, saldado_en in envios:  # mas reciente primero
            if estado == EstadoEnvio.PAGO or saldado_en is not None:
                break  # cierra una racha anterior; no es parte de la vigente
            streak_start = creado_en
        if streak_start is not None:
            resultado[clave] = streak_start
    return resultado
```

- [ ] **Step 4: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/dashboard_service.py backend/tests/test_antiguedad.py
git commit -m "feat: servicio deudor_desde_por_clave (antiguedad de deuda)"
```

---

### Task 2: KPI deuda +90 días + endpoint morosos

**Files:**
- Modify: `backend/app/services/dashboard_service.py`
- Modify: `backend/app/schemas/dashboard.py`
- Modify: `backend/app/routers/dashboard.py`
- Test: `backend/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `deudor_desde_por_clave`, `_a_naive_utc`, `_UMBRAL_VENCIDA_DIAS` (Task 1).
- Produces: `ResumenData` con `deuda_mas_90: Decimal` (sin `efectividad`); `MorosoItem` dataclass; `morosos(db, limite=10) -> list[MorosoItem]`; `GET /dashboard/morosos` → `list[MorosoSchema]`; `DashboardResumenResponse.deuda_mas_90`.
- `MorosoItem` / `MorosoSchema` campos: `clave_union: str, nombre_consorcio: str, monto: Decimal, deudor_desde: datetime, ciclos_debiendo: int, estado: EstadoEnvio`.

- [ ] **Step 1: Actualizar los tests existentes + agregar los nuevos**

En `backend/tests/test_dashboard.py`: en `test_resumen_calcula_kpis` reemplazar la línea `assert data["efectividad"] == 50.0` por:

```python
    assert "efectividad" not in data
    assert float(data["deuda_mas_90"]) == 0.0  # todas las fechas son recientes
```

En `test_resumen_sin_ciclo_activo` reemplazar `assert data["efectividad"] is None` por:

```python
    assert float(data["deuda_mas_90"]) == 0.0
```

En `test_resumen_primer_ciclo_sin_anterior` reemplazar `assert data["efectividad"] is None` por:

```python
    assert float(data["deuda_mas_90"]) == 0.0
```

Agregar al final de `backend/tests/test_dashboard.py`:

```python
def test_resumen_deuda_mas_90(client, auth_headers, db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    viejo = Ciclo(numero=8901, activo=False,
                  creado_en=datetime.now(timezone.utc) - timedelta(days=120))
    activo = Ciclo(numero=8902, activo=True, creado_en=datetime.now(timezone.utc))
    db.add_all([viejo, activo])
    db.flush()
    # DSH90 debe hace 120 dias (racha viene del ciclo viejo, sin saldar)
    for ciclo, racha in ((viejo, 1), (activo, 2)):
        db.add(Envio(
            ciclo_id=ciclo.id, ciclo_numero=racha, clave_union="DSH90",
            nombre_consorcio="Viejo", email="dsh90@mail.com", monto=Decimal("5000"),
            estado=EstadoEnvio.NO_CONTESTADO, actualizado_en=datetime.now(timezone.utc),
        ))
    # DSHNEW debe recien este ciclo (no cuenta para +90)
    db.add(Envio(
        ciclo_id=activo.id, ciclo_numero=1, clave_union="DSHNEW",
        nombre_consorcio="Nuevo", email="dshnew@mail.com", monto=Decimal("3000"),
        estado=EstadoEnvio.NO_CONTESTADO, actualizado_en=datetime.now(timezone.utc),
    ))
    db.commit()

    r = client.get("/dashboard/resumen", headers=auth_headers)
    assert float(r.json()["deuda_mas_90"]) == 5000.0

    db.query(Envio).filter(Envio.ciclo_id.in_([viejo.id, activo.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([viejo.id, activo.id])).delete(synchronize_session=False)
    db.commit()


def test_morosos_ordena_por_antiguedad(client, auth_headers, db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    c1 = Ciclo(numero=8911, activo=False, creado_en=datetime.now(timezone.utc) - timedelta(days=70))
    c2 = Ciclo(numero=8912, activo=True, creado_en=datetime.now(timezone.utc))
    db.add_all([c1, c2])
    db.flush()
    # VIEJO: racha desde c1 (~70 dias). NUEVO: recien c2.
    db.add(Envio(ciclo_id=c1.id, ciclo_numero=1, clave_union="MOR-VIEJO", nombre_consorcio="Viejo",
                 email="v@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
                 actualizado_en=datetime.now(timezone.utc)))
    db.add(Envio(ciclo_id=c2.id, ciclo_numero=2, clave_union="MOR-VIEJO", nombre_consorcio="Viejo",
                 email="v@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
                 actualizado_en=datetime.now(timezone.utc)))
    db.add(Envio(ciclo_id=c2.id, ciclo_numero=1, clave_union="MOR-NUEVO", nombre_consorcio="Nuevo",
                 email="n@mail.com", monto=Decimal("2000"), estado=EstadoEnvio.NO_CONTESTADO,
                 actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/dashboard/morosos", headers=auth_headers)
    assert r.status_code == 200
    data = r.json()
    claves = [m["clave_union"] for m in data]
    assert claves.index("MOR-VIEJO") < claves.index("MOR-NUEVO")  # mas viejo primero
    viejo = next(m for m in data if m["clave_union"] == "MOR-VIEJO")
    assert viejo["ciclos_debiendo"] == 2

    db.query(Envio).filter(Envio.ciclo_id.in_([c1.id, c2.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([c1.id, c2.id])).delete(synchronize_session=False)
    db.commit()


def test_morosos_excluye_pagados(client, auth_headers, db):
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.query(Ciclo).update({"activo": False})
    c = Ciclo(numero=8921, activo=True, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    db.add(Envio(ciclo_id=c.id, ciclo_numero=1, clave_union="MOR-PAGO", nombre_consorcio="Pago",
                 email="p@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.PAGO,
                 actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/dashboard/morosos", headers=auth_headers)
    assert all(m["clave_union"] != "MOR-PAGO" for m in r.json())

    db.query(Envio).filter(Envio.ciclo_id == c.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == c.id).delete(synchronize_session=False)
    db.commit()


def test_morosos_requiere_auth(client):
    r = client.get("/dashboard/morosos")
    assert r.status_code in (401, 403)
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_dashboard.py`
Expected: FAIL — `deuda_mas_90` KeyError / `/dashboard/morosos` 404.

- [ ] **Step 3: Servicio — resumen y morosos**

En `backend/app/services/dashboard_service.py`:

Reemplazar la dataclass `ResumenData` (líneas 19-27) por:

```python
@dataclass
class ResumenData:
    hay_ciclo_activo: bool
    deuda_total: Decimal
    deuda_total_anterior: Optional[Decimal]
    deudores: int
    deudores_anterior: Optional[int]
    cobrado: Optional[Decimal]
    deuda_mas_90: Decimal
```

Agregar la dataclass `MorosoItem` después de `EvolucionItem`:

```python
@dataclass
class MorosoItem:
    clave_union: str
    nombre_consorcio: str
    monto: Decimal
    deudor_desde: datetime
    ciclos_debiendo: int
    estado: EstadoEnvio
```

Borrar la función `_efectividad` completa (líneas 65-70).

Reemplazar la función `resumen` completa por:

```python
def resumen(db: Session) -> ResumenData:
    activo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if activo is None:
        return ResumenData(
            hay_ciclo_activo=False, deuda_total=Decimal("0"), deuda_total_anterior=None,
            deudores=0, deudores_anterior=None, cobrado=None, deuda_mas_90=Decimal("0"),
        )
    envios_activo = _envios_por_clave(db, activo.id)
    deuda_total = sum((e.monto for e in envios_activo.values()), start=Decimal("0"))

    desde = deudor_desde_por_clave(db, set(envios_activo.keys()))
    corte = _a_naive_utc(datetime.now(timezone.utc)) - timedelta(days=_UMBRAL_VENCIDA_DIAS)
    deuda_mas_90 = sum(
        (e.monto for clave, e in envios_activo.items()
         if clave in desde and _a_naive_utc(desde[clave]) < corte),
        start=Decimal("0"),
    )

    anterior = (
        db.query(Ciclo)
        .filter(Ciclo.numero < activo.numero)
        .order_by(Ciclo.numero.desc())
        .first()
    )
    if anterior is None:
        return ResumenData(
            hay_ciclo_activo=True, deuda_total=deuda_total, deuda_total_anterior=None,
            deudores=len(envios_activo), deudores_anterior=None, cobrado=None,
            deuda_mas_90=deuda_mas_90,
        )

    envios_anterior = _envios_por_clave(db, anterior.id)
    return ResumenData(
        hay_ciclo_activo=True,
        deuda_total=deuda_total,
        deuda_total_anterior=sum((e.monto for e in envios_anterior.values()), start=Decimal("0")),
        deudores=len(envios_activo),
        deudores_anterior=len(envios_anterior),
        cobrado=_cobrado_entre(envios_anterior, envios_activo),
        deuda_mas_90=deuda_mas_90,
    )
```

Agregar la función `morosos` al final del archivo:

```python
def morosos(db: Session, limite: int = 10) -> list[MorosoItem]:
    """Deudores del ciclo activo con deuda vigente, ordenados por antiguedad
    (deuda mas vieja primero). Excluye a quien figura pagado."""
    activo = db.query(Ciclo).filter(Ciclo.activo == True).first()
    if activo is None:
        return []
    envios = (
        db.query(Envio.clave_union, Envio.nombre_consorcio, Envio.monto,
                 Envio.ciclo_numero, Envio.estado)
        .filter(Envio.ciclo_id == activo.id)
        .all()
    )
    desde = deudor_desde_por_clave(db, {e.clave_union for e in envios})
    items = [
        MorosoItem(
            clave_union=clave, nombre_consorcio=nombre, monto=monto,
            deudor_desde=desde[clave], ciclos_debiendo=racha, estado=estado,
        )
        for clave, nombre, monto, racha, estado in envios
        if clave in desde
    ]
    items.sort(key=lambda m: _a_naive_utc(m.deudor_desde))
    return items[:limite]
```

- [ ] **Step 4: Schema**

En `backend/app/schemas/dashboard.py`, agregar el import y el schema, y cambiar el campo:

```python
from app.models.envio import EstadoEnvio
```

En `DashboardResumenResponse` reemplazar `efectividad: Optional[float] = None` por:

```python
    deuda_mas_90: Decimal
```

Agregar al final:

```python
class MorosoSchema(BaseModel):
    clave_union: str
    nombre_consorcio: str
    monto: Decimal
    deudor_desde: datetime
    ciclos_debiendo: int
    estado: EstadoEnvio
```

- [ ] **Step 5: Router**

En `backend/app/routers/dashboard.py`, cambiar el import de schemas por:

```python
from app.schemas.dashboard import DashboardResumenResponse, EvolucionCicloSchema, MorosoSchema
```

En `get_resumen`, reemplazar `efectividad=data.efectividad,` por:

```python
        deuda_mas_90=data.deuda_mas_90,
```

Agregar el endpoint al final:

```python
@router.get("/morosos", response_model=list[MorosoSchema])
def get_morosos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return [
        MorosoSchema(
            clave_union=m.clave_union, nombre_consorcio=m.nombre_consorcio, monto=m.monto,
            deudor_desde=m.deudor_desde, ciclos_debiendo=m.ciclos_debiendo, estado=m.estado,
        )
        for m in dashboard_service.morosos(db)
    ]
```

- [ ] **Step 6: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/dashboard_service.py backend/app/schemas/dashboard.py backend/app/routers/dashboard.py backend/tests/test_dashboard.py
git commit -m "feat: KPI deuda +90 dias y endpoint de morosos por antiguedad"
```

---

### Task 3: `deudor_desde` en el perfil del cliente

**Files:**
- Modify: `backend/app/schemas/maestro.py`
- Modify: `backend/app/routers/maestro.py`
- Test: `backend/tests/test_maestro.py`

**Interfaces:**
- Consumes: `dashboard_service.deudor_desde_por_clave` (Task 1).
- Produces: `HistorialClienteResponse.deudor_desde: Optional[datetime]`.

- [ ] **Step 1: Test que falla (agregar a `backend/tests/test_maestro.py`)**

```python
def test_historial_incluye_deudor_desde(client, auth_headers, db):
    from datetime import datetime, timedelta, timezone
    from decimal import Decimal
    from app.models.cliente_maestro import ClienteMaestro
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.add(ClienteMaestro(clave_union="DSD-1", nombre="Deudor Desde",
                          email="dsd1@mail.com", actualizado_en=datetime.now(timezone.utc)))
    c1 = Ciclo(numero=8941, activo=False, creado_en=datetime.now(timezone.utc) - timedelta(days=50))
    c2 = Ciclo(numero=8942, activo=True, creado_en=datetime.now(timezone.utc))
    db.add_all([c1, c2])
    db.flush()
    for ciclo, racha in ((c1, 1), (c2, 2)):
        db.add(Envio(ciclo_id=ciclo.id, ciclo_numero=racha, clave_union="DSD-1",
                     nombre_consorcio="Deudor Desde", email="dsd1@mail.com",
                     monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
                     actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/maestro/DSD-1/historial", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["deudor_desde"] is not None

    db.query(Envio).filter(Envio.ciclo_id.in_([c1.id, c2.id])).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id.in_([c1.id, c2.id])).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "DSD-1").delete(synchronize_session=False)
    db.commit()


def test_historial_deudor_desde_none_si_saldado(client, auth_headers, db):
    from datetime import datetime, timezone
    from decimal import Decimal
    from app.models.cliente_maestro import ClienteMaestro
    from app.models.ciclo import Ciclo
    from app.models.envio import Envio, EstadoEnvio

    db.add(ClienteMaestro(clave_union="DSD-2", nombre="Saldado",
                          email="dsd2@mail.com", actualizado_en=datetime.now(timezone.utc)))
    c = Ciclo(numero=8943, activo=False, creado_en=datetime.now(timezone.utc))
    db.add(c)
    db.flush()
    db.add(Envio(ciclo_id=c.id, ciclo_numero=1, clave_union="DSD-2", nombre_consorcio="Saldado",
                 email="dsd2@mail.com", monto=Decimal("1000"), estado=EstadoEnvio.NO_CONTESTADO,
                 saldado_en=datetime.now(timezone.utc), actualizado_en=datetime.now(timezone.utc)))
    db.commit()

    r = client.get("/maestro/DSD-2/historial", headers=auth_headers)
    assert r.json()["deudor_desde"] is None

    db.query(Envio).filter(Envio.ciclo_id == c.id).delete(synchronize_session=False)
    db.query(Ciclo).filter(Ciclo.id == c.id).delete(synchronize_session=False)
    db.query(ClienteMaestro).filter(ClienteMaestro.clave_union == "DSD-2").delete(synchronize_session=False)
    db.commit()
```

- [ ] **Step 2: Verificar que fallan**

Run: `cd backend && venv/Scripts/python -m pytest -q tests/test_maestro.py -k deudor_desde`
Expected: FAIL — la respuesta no tiene `deudor_desde`.

- [ ] **Step 3: Schema**

En `backend/app/schemas/maestro.py`, en `HistorialClienteResponse` agregar el campo:

```python
class HistorialClienteResponse(BaseModel):
    cliente: Optional[ClienteMaestroSchema] = None
    clave_union: str
    deudor_desde: Optional[datetime] = None
    items: list[HistorialItemSchema]
```

- [ ] **Step 4: Router**

En `backend/app/routers/maestro.py`, agregar el import:

```python
from app.services import dashboard_service
```

En `historial_cliente`, reemplazar el `return` final por:

```python
    deudor_desde = dashboard_service.deudor_desde_por_clave(db, {clave_union}).get(clave_union)
    return HistorialClienteResponse(
        cliente=cliente, clave_union=clave_union, deudor_desde=deudor_desde, items=items
    )
```

- [ ] **Step 5: Verificar que pasan + suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q`
Expected: PASS completo.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/maestro.py backend/app/routers/maestro.py backend/tests/test_maestro.py
git commit -m "feat: deudor_desde en el perfil del cliente"
```

---

### Task 4: Frontend — tipos y servicio de morosos

**Files:**
- Modify: `frontend/src/types/domain.ts`
- Modify: `frontend/src/services/dashboard.ts`

**Interfaces:**
- Produces: `DashboardResumen` (sin `efectividad`, con `deuda_mas_90: number`); `Moroso`; `HistorialCliente.deudor_desde`; `getMorosos(): Promise<Moroso[]>`.

- [ ] **Step 1: Tipos**

En `frontend/src/types/domain.ts`, en `DashboardResumen` reemplazar `efectividad: number | null;` por:

```ts
  deuda_mas_90: number;
```

En `HistorialCliente` agregar (después de `clave_union`):

```ts
  deudor_desde: string | null;
```

Agregar al final del archivo:

```ts
export interface Moroso {
  clave_union: string;
  nombre_consorcio: string;
  monto: number;
  deudor_desde: string;
  ciclos_debiendo: number;
  estado: EstadoEnvio;
}
```

- [ ] **Step 2: Servicio**

En `frontend/src/services/dashboard.ts`, agregar `Moroso` al import de tipos y la función al final:

```ts
export async function getMorosos(): Promise<Moroso[]> {
  const r = await apiFetch("/dashboard/morosos");
  if (!r.ok) throw new Error("Error cargando los morosos");
  return r.json();
}
```

- [ ] **Step 3: Verificar compilación**

Run: `cd frontend && npx tsc -b`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/domain.ts frontend/src/services/dashboard.ts
git commit -m "feat: tipos y servicio de morosos + deuda_mas_90"
```

---

### Task 5: Frontend — KPIs del Dashboard (rename, variación, deuda +90)

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

**Interfaces:**
- Consumes: `DashboardResumen.deuda_mas_90` (Task 4).

- [ ] **Step 1: Reemplazar `variacion` y `KpiCard`**

En `frontend/src/pages/DashboardPage.tsx`, reemplazar la función `variacion` (líneas 19-24) por un componente que colorea (verde si la deuda bajó, rojo si subió):

```tsx
function VariacionDeuda({ actual, anterior }: { actual: number; anterior: number | null }) {
  if (anterior === null || Number(anterior) === 0) return null;
  const pct = ((actual - anterior) / anterior) * 100;
  const bajo = pct < 0;
  const signo = pct > 0 ? "+" : "";
  return (
    <span className={bajo ? "text-success-foreground" : "text-destructive"}>
      {signo}{pct.toFixed(1)}% vs. ciclo anterior
    </span>
  );
}
```

Cambiar la firma de `KpiCard` para aceptar detalle como nodo (línea 26):

```tsx
function KpiCard({ titulo, valor, detalle }: { titulo: string; valor: string; detalle?: React.ReactNode }) {
```

- [ ] **Step 2: Actualizar el bloque de KPIs**

Reemplazar las 4 `<KpiCard>` (líneas 109-132) por:

```tsx
            <KpiCard
              titulo="Deuda actual"
              valor={pesos(resumen.deuda_total)}
              detalle={<VariacionDeuda actual={resumen.deuda_total} anterior={resumen.deuda_total_anterior} />}
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
              titulo="Deuda +90 días"
              valor={pesos(resumen.deuda_mas_90)}
              detalle="Deuda de más de 90 días — en riesgo"
            />
```

- [ ] **Step 3: Verificar compilación y build**

Run: `cd frontend && npx tsc -b && npm run build`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: KPIs del dashboard (deuda actual, variacion verde/rojo, deuda +90)"
```

---

### Task 6: Frontend — gráfico de evolución (componente compartido + restyle)

**Files:**
- Create: `frontend/src/components/dashboard/EvolucionChart.tsx`
- Modify: `frontend/src/pages/DashboardPage.tsx`

**Interfaces:**
- Produces: `EvolucionChart({ data }: { data: { label: string; valor: number }[] })` — área con degradado y ejes minimalistas.

- [ ] **Step 1: Crear el componente compartido**

```tsx
// frontend/src/components/dashboard/EvolucionChart.tsx
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";
import type { TooltipProps } from "recharts";

function ChartTooltip({ active, payload, label }: TooltipProps<number, string>) {
  if (!active || !payload || payload.length === 0) return null;
  const valor = payload[0].value ?? 0;
  return (
    <div className="rounded-md border border-border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="font-medium text-foreground">{label}</p>
      <p className="tabular-nums text-muted-foreground">
        ${Number(valor).toLocaleString("es-AR")}
      </p>
    </div>
  );
}

export function EvolucionChart({ data }: { data: { label: string; valor: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id="evoGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="hsl(var(--primary))" stopOpacity={0.35} />
            <stop offset="100%" stopColor="hsl(var(--primary))" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke="hsl(var(--border))" strokeOpacity={0.4} />
        <XAxis
          dataKey="label"
          tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          width={48}
          tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ stroke: "hsl(var(--border))" }} />
        <Area
          type="monotone"
          dataKey="valor"
          stroke="hsl(var(--primary))"
          strokeWidth={2}
          fill="url(#evoGrad)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Usarlo en el Dashboard**

En `frontend/src/pages/DashboardPage.tsx`:

Reemplazar el import de recharts (líneas 3-5) — se elimina, ya no se usa directo:

```tsx
import { EvolucionChart } from "../components/dashboard/EvolucionChart";
```

(Quitar también `Tabs`... NO — Tabs sigue. Solo se borra el import de `recharts`.)

Reemplazar el cálculo de `chartData` (líneas 85-90) por:

```tsx
  const chartData = evolucion.map((c) => ({
    label: `#${c.numero} ${format(new Date(c.fecha), "dd/MM", { locale: es })}`,
    valor: Number(c.deuda_total),
  }));
```

Reemplazar el bloque del gráfico (`{chartData.length > 1 && (...)}`, líneas 135-152) por:

```tsx
          {chartData.length > 1 && (
            <div className="rounded-md border border-border p-4">
              <p className="mb-3 text-sm font-medium text-foreground">Evolución de la deuda</p>
              <EvolucionChart data={chartData} />
            </div>
          )}
```

- [ ] **Step 3: Verificar compilación y build**

Run: `cd frontend && npx tsc -b && npm run build`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/dashboard/EvolucionChart.tsx frontend/src/pages/DashboardPage.tsx
git commit -m "feat: grafico de evolucion restyleado (area con degradado, ejes minimalistas)"
```

---

### Task 7: Frontend — ranking "Morosos crónicos" por antigüedad

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

**Interfaces:**
- Consumes: `getMorosos` (Task 4), `Moroso` (Task 4).

- [ ] **Step 1: Fetch + estado de morosos**

En `frontend/src/pages/DashboardPage.tsx`:

Ajustar los imports. La línea existente `import { format } from "date-fns";` pasa a incluir las dos funciones nuevas (NO agregar una segunda línea de `date-fns` — el linter marca imports duplicados):

```tsx
import { format, formatDistanceToNow, differenceInDays } from "date-fns";
```

Y reemplazar los imports existentes de `../services/dashboard` y de tipos por estas versiones ampliadas:

```tsx
import { getDashboardResumen, getDashboardEvolucion, getMorosos } from "../services/dashboard";
import type { DashboardResumen, EvolucionCiclo, Envio, Moroso } from "../types/domain";
```

Agregar estado (junto a los otros `useState`):

```tsx
  const [morosos, setMorosos] = useState<Moroso[]>([]);
```

En el `Promise.all` del `useEffect`, agregar `getMorosos()`:

```tsx
    Promise.all([getDashboardResumen(), getDashboardEvolucion(), getEnviosActivo(), getMorosos()])
      .then(([r, e, envs, mor]) => {
        setResumen(r);
        setEvolucion(e);
        setEnvios(envs);
        setMorosos(mor);
      })
```

Borrar el cálculo client-side de `topCronicos` (líneas 80-83); dejar solo `topMonto`.

- [ ] **Step 2: Render del ranking de morosos**

En el `Tabs`, reemplazar el `.map` de las dos pestañas por un render explícito de cada una (la de monto queda igual, la de crónicos usa `morosos`). Reemplazar todo el bloque `{(["monto", "cronicos"] as const).map(...)}` por:

```tsx
            <TabsContent value="monto">
              {topMonto.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No hay deudores en el ciclo activo.
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
                    {topMonto.map((e) => (
                      <tr key={e.id}
                        className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                        onClick={() => navigate(`/clientes/${encodeURIComponent(e.clave_union)}`)}>
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
            <TabsContent value="cronicos">
              {morosos.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  No hay deudores con deuda vigente.
                </p>
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-left">
                      <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Consorcio</th>
                      <th className="py-2 pr-4 text-xs font-medium uppercase tracking-wide text-muted-foreground">Debe hace</th>
                      <th className="py-2 pr-4 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Monto</th>
                      <th className="py-2 text-right text-xs font-medium uppercase tracking-wide text-muted-foreground">Recordatorios</th>
                    </tr>
                  </thead>
                  <tbody>
                    {morosos.map((m) => {
                      const dias = differenceInDays(new Date(), new Date(m.deudor_desde));
                      return (
                        <tr key={m.clave_union}
                          className="cursor-pointer border-b border-border last:border-0 hover:bg-muted/50"
                          onClick={() => navigate(`/clientes/${encodeURIComponent(m.clave_union)}`)}>
                          <td className="py-2.5 pr-4 text-foreground">{m.nombre_consorcio}</td>
                          <td className={`py-2.5 pr-4 ${dias > 90 ? "font-medium text-destructive" : "text-muted-foreground"}`}>
                            {formatDistanceToNow(new Date(m.deudor_desde), { locale: es })}
                          </td>
                          <td className="py-2.5 pr-4 text-right tabular-nums">{pesos(Number(m.monto))}</td>
                          <td className="py-2.5 text-right tabular-nums text-muted-foreground">{m.ciclos_debiendo}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </TabsContent>
```

- [ ] **Step 3: Verificar compilación y build**

Run: `cd frontend && npx tsc -b && npm run build`
Expected: sin errores.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat: morosos cronicos ordenados por antiguedad con resaltado +90 dias"
```

---

### Task 8: Frontend — perfil del cliente (antigüedad + gráfico de su deuda)

**Files:**
- Modify: `frontend/src/pages/ClientePerfilPage.tsx`

**Interfaces:**
- Consumes: `HistorialCliente.deudor_desde` (Task 4), `EvolucionChart` (Task 6).

- [ ] **Step 1: Imports y antigüedad**

En `frontend/src/pages/ClientePerfilPage.tsx`, la línea existente `import { format } from "date-fns";` pasa a incluir las funciones nuevas (NO agregar una segunda línea de `date-fns`):

```tsx
import { format, formatDistanceToNow, differenceInDays } from "date-fns";
```

Y agregar el import del componente de gráfico:

```tsx
import { EvolucionChart } from "../components/dashboard/EvolucionChart";
```

(El import de `es` de `date-fns/locale` ya existe.)

Después de la línea `const items = data.items;` agregar:

```tsx
  const desde = data.deudor_desde ? new Date(data.deudor_desde) : null;
  const diasDebiendo = desde ? differenceInDays(new Date(), desde) : null;
```

- [ ] **Step 2: Mostrar "Deudor desde" en el header**

Reemplazar el `<p>` de la línea del email/localidad/estado por (agrega la antigüedad si corresponde):

```tsx
        <p className="mt-0.5 text-sm text-muted-foreground">
          {data.cliente?.email ?? "Sin email"} · {data.cliente?.localidad ?? "Sin localidad"} · {estadoCliente}
          {desde && (
            <>
              {" · "}
              <span className={diasDebiendo !== null && diasDebiendo > 90 ? "font-medium text-destructive" : ""}>
                Deudor desde {format(desde, "dd/MM/yyyy", { locale: es })} (hace {formatDistanceToNow(desde, { locale: es })})
              </span>
            </>
          )}
        </p>
```

- [ ] **Step 3: Reemplazar la KPI "Ciclos debiendo" por "Debe hace"**

Reemplazar la segunda KPI (la de "Ciclos debiendo", con `actual.racha`) por:

```tsx
        <div className="rounded-md border border-border bg-secondary/30 p-4">
          <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Debe hace</p>
          <p className={`mt-1 text-2xl font-semibold tabular-nums ${diasDebiendo !== null && diasDebiendo > 90 ? "text-destructive" : ""}`}>
            {desde ? formatDistanceToNow(desde, { locale: es }) : "—"}
          </p>
          {actual && <p className="mt-0.5 text-xs text-muted-foreground">{actual.racha} recordatorios enviados</p>}
        </div>
```

- [ ] **Step 4: Gráfico de evolución de su deuda**

Antes de la `<table>` del historial (el `<div className="overflow-x-auto">`), agregar el gráfico. Construir la serie en orden cronológico (los items vienen por ciclo desc, hay que invertir):

Agregar antes del `return`, después de `const diasDebiendo = ...`:

```tsx
  const serieDeuda = [...items]
    .reverse()
    .map((i) => ({ label: `#${i.ciclo}`, valor: Number(i.monto) }));
```

Y antes del `<div className="overflow-x-auto">`:

```tsx
      {serieDeuda.length > 1 && (
        <div className="rounded-md border border-border p-4">
          <p className="mb-3 text-sm font-medium text-foreground">Evolución de su deuda</p>
          <EvolucionChart data={serieDeuda} />
        </div>
      )}
```

- [ ] **Step 5: Verificar compilación y build**

Run: `cd frontend && npx tsc -b && npm run build`
Expected: sin errores.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ClientePerfilPage.tsx
git commit -m "feat: antiguedad de deuda y grafico de evolucion en el perfil del cliente"
```

---

### Task 9: Cierre — suite completa y docs

**Files:**
- Modify: `docs/PENDIENTES.md`

- [ ] **Step 1: Suite completa**

Run: `cd backend && venv/Scripts/python -m pytest -q` → PASS completo.
Run: `cd frontend && npx tsc -b && npm run build` → sin errores.

- [ ] **Step 2: Actualizar `docs/PENDIENTES.md`**

Agregar a la sección "Resuelto desde la última auditoría":

```markdown
- **Dashboard v2 — antigüedad de deuda** — "deudor desde / debe hace X" reconstruido del historial de ciclos, "Morosos crónicos" ordenado por antigüedad con resaltado +90 días, KPI "Deuda +90 días" (reemplaza a la efectividad del recordatorio, que se quitó por no ser medible sin datos de pago reales), variación de deuda verde/rojo, gráfico de evolución restyleado (área con degradado) reutilizado en dashboard y perfil, y gráfico de evolución de deuda por cliente. Spec: `docs/superpowers/specs/2026-07-06-dashboard-v2-antiguedad-design.md`. Sin migración (todo derivado de datos existentes).
```

- [ ] **Step 3: Commit**

```bash
git add docs/PENDIENTES.md
git commit -m "docs: registrar dashboard v2 (antiguedad) en PENDIENTES"
```

---

## Notas de deploy (post-merge, fuera del plan)

- **Sin migración** — no hay cambios de esquema; Render solo necesita el redeploy del código.
- Vercel toma el frontend al pushear `master`; Render requiere redeploy manual.
- La métrica "Deuda +90 días" arranca en $0 hasta que haya deuda con más de 90 días de antigüedad reconstruible (el sistema es ciego antes de la primera carga). Es el comportamiento correcto.
- Los datos demo sembrados en producción (2 ciclos, ~1 mes de spread) ya permiten ver la antigüedad ("debe hace ~1 mes") aunque "Deuda +90 días" quede en $0.
