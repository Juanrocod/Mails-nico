# Diseño: Adaptación al Excel Real del Broker

**Fecha:** 2026-06-16  
**Estado:** Aprobado — pendiente de implementación

---

## Contexto

El sistema tenía un `excel_parser.py` con columnas placeholder. El broker entregó el Excel real (`Operaciones_modelo.xlsx`). Este spec documenta todos los cambios necesarios para adaptar el sistema a ese formato, más las nuevas funcionalidades que surgieron del análisis.

---

## Resumen de cambios

| Área | Tipo |
|------|------|
| `excel_parser.py` | Reescritura del mapping y validaciones |
| `OrdenParsed` | Nuevos campos, eliminar email/tipo/liquidacion |
| `MinutaSession` | Nuevos campos, nuevo estado FILTRADA |
| `minuta_generator.py` | Nueva firma, N/A para -1, nueva plantilla default |
| `dj_engine.py` | Nuevos campos permitidos + toggle RequiereConformidad |
| `models/config_dj.py` | Nueva columna `activar_si_requiere_conformidad` |
| `models/config_filtros.py` | Nueva tabla (nuevo archivo) |
| `db_config.py` | Soporte para ConfigFiltros + toggle DJ |
| `schemas/session.py` | MinutaSchema actualizado, nuevos schemas |
| `routers/session.py` | Nuevos endpoints filtros + agregar filtrada |
| `routers/uploads.py` | Aplicar filtros, generar FILTRADA |
| `alembic/versions/0005` | Nueva migración |
| Frontend | Nueva tab Filtradas, nueva tab Filtros de Minutas, tab order, MinutaCard |

---

## 1. Nuevo mapping de columnas Excel

El Excel real (`Sheet1`, 27 columnas, filas 2-N) mapea así:

| Campo interno | Columna Excel | Tipo Python | Notas |
|---|---|---|---|
| `cliente_nombre` | `Descripcion` | str | obligatorio |
| `cuenta_comitente` | `Comitente` | str | obligatorio |
| `cuenta_cotapartista` | `Cuotapartista` | str | opcional, puede ser `''` |
| `id_orden` | `Orden` | int | obligatorio |
| `fecha_operacion` | `Fecha` + `Hora` | datetime | combinar con `strptime("%d/%m/%Y %H:%M:%S")` |
| `fecha_liquidacion` | `FechaLiquidacion` | str | tal cual del Excel |
| `operacion` | `Operacion` | str | texto libre, ej: "Compra CI" |
| `instrumento` | `Ticker` | str | opcional, vacío en Transferencias |
| `moneda` | `Moneda` | str | obligatorio |
| `cantidad` | `Cantidad` | float | puede ser -1 |
| `precio` | `Precio` | float | puede ser -1 |
| `monto` | `Monto` | float | obligatorio |
| `estado` | `Estado` | str | ej: "Ejecutada", "En Ejecución" |
| `cantidad_operada` | `CantidadOperada` | float | puede ser -1 |
| `precio_operado` | `PrecioOperado` | float | puede ser -1 |
| `operador` | `Operador` | str | username o email interno |
| `origen` | `Origen` | str | "User" o "Cliente" |
| `asesor` | `Asesor` | str | nombre del asesor |
| `requiere_conformidad` | `RequiereConformidad` | int | 0 o 1 |

**Campos eliminados:** `cliente_email`, `tipo`, `liquidacion` (eran del formato placeholder).

**Validaciones actualizadas:**
- `cantidad`, `precio`, `cantidad_operada`, `precio_operado`: aceptar -1 (sentinel de "no aplica")
- `cuenta_cotapartista`, `instrumento`: permitir string vacío
- Filas completamente vacías: skip silencioso (comportamiento actual se mantiene)

---

## 2. OrdenParsed actualizado

```python
@dataclass
class OrdenParsed:
    cliente_nombre: str
    cuenta_comitente: str
    cuenta_cotapartista: str        # puede ser ''
    id_orden: int
    fecha_operacion: datetime
    fecha_liquidacion: str
    operacion: str
    instrumento: str                # puede ser ''
    moneda: str
    cantidad: float                 # puede ser -1
    precio: float                   # puede ser -1
    monto: float
    estado: str
    cantidad_operada: float         # puede ser -1
    precio_operado: float           # puede ser -1
    operador: str
    origen: str
    asesor: str
    requiere_conformidad: int       # 0 o 1
```

---

## 3. MinutaSession actualizado

Mismos campos que `OrdenParsed` más los campos de sesión existentes:

```python
@dataclass
class MinutaSession:
    id: str
    # --- campos del Excel ---
    cliente_nombre: str
    cuenta_comitente: str
    cuenta_cotapartista: str
    id_orden: int
    fecha_operacion: datetime
    fecha_liquidacion: str
    operacion: str
    instrumento: str
    moneda: str
    cantidad: float
    precio: float
    monto: float
    estado_orden: str               # renombrado para no chocar con estado de Minuta
    cantidad_operada: float
    precio_operado: float
    operador: str
    origen: str
    asesor: str
    requiere_conformidad: int
    # --- campos de sesión ---
    dj_aplicada: bool
    dj_texto: Optional[str]
    estado: str                     # "BORRADOR" | "ENVIADO" | "FILTRADA"
    texto_minuta: str
    texto_editado: bool
    creado_en: datetime
```

**Nuevo estado:** `FILTRADA` — filas excluidas por Filtros de Minutas. Se genera el texto de Minuta igualmente.

---

## 4. minuta_generator.py

**Nueva firma:** recibe un dict con todos los campos de `OrdenParsed` (mismo patrón que `dj_engine.evaluar_reglas`).

**Formateo de valores -1:** cualquier campo numérico con valor `-1` se muestra como `N/A` en el texto.

**Nueva DEFAULT_PLANTILLA:**

```
MINUTA DE OPERACIÓN
Fecha y hora: {fecha_operacion}
Fecha liquidación: {fecha_liquidacion}

Cliente: {cliente_nombre}
Cuenta Comitente: {cuenta_comitente}
Cuenta Cotapartista: {cuenta_cotapartista}

DETALLE DE LA OPERACIÓN
Operación: {operacion}
Instrumento: {instrumento}
Moneda: {moneda}
Cantidad: {cantidad}
Precio: {precio}
Monto: {monto}
Estado: {estado}

Asesor: {asesor}

Quedo a su disposición ante cualquier consulta.
Saludos cordiales.
```

**Variables disponibles en la plantilla** (todas opcionales, el usuario las incluye o no):

`{cliente_nombre}` `{cuenta_comitente}` `{cuenta_cotapartista}` `{id_orden}` `{fecha_operacion}` `{fecha_liquidacion}` `{operacion}` `{instrumento}` `{moneda}` `{cantidad}` `{precio}` `{monto}` `{estado}` `{cantidad_operada}` `{precio_operado}` `{asesor}` `{operador}` `{origen}` `{requiere_conformidad}`

El `_SafeDict` existente ya maneja variables no encontradas dejándolas como texto literal `{variable}`.

---

## 5. DJ Engine — campos actualizados

**Campos de texto:** `operacion`, `operador`, `origen`, `estado`, `moneda`, `instrumento`  
**Campos numéricos:** `cantidad`, `precio`, `monto`, `cantidad_operada`, `precio_operado`, `requiere_conformidad`

Los campos viejos (`tipo`, `liquidacion`) se eliminan de `_CAMPOS_PERMITIDOS`.

**Nuevo toggle — RequiereConformidad:**

En la evaluación del DJ se agrega una condición previa a las reglas manuales:

```
si config.activar_si_requiere_conformidad AND datos["requiere_conformidad"] == 1:
    → DJ aplica (sin evaluar reglas)
sino:
    → evaluar reglas como antes
```

---

## 6. Config DJ — cambio en DB

**Nueva columna en tabla `config_dj`:**

```python
activar_si_requiere_conformidad = Column(Boolean, nullable=False, default=True)
```

Se muestra en la solapa "Config DJ" como:
> ☑ Activar DJ automáticamente si la plataforma indica RequiereConformidad = 1

Activo por defecto.

---

## 7. Filtros de Minutas — nuevo módulo

### Modelo DB (`models/config_filtros.py`)

```python
class ConfigFiltros(Base):
    __tablename__ = "config_filtros_minutas"
    id = Column(Integer, primary_key=True, default=1)
    reglas = Column(Text, nullable=False, default="[]")   # JSON
    logica = Column(String(3), nullable=False, default="OR")
    actualizado_en = Column(DateTime, ...)
```

### Campos y operadores permitidos

Mismos que el DJ engine actualizado:
- **Texto:** `=`, `!=`
- **Numérico:** `=`, `!=`, `>`, `<`, `>=`, `<=`

### Comportamiento

- **Default:** sin reglas = todas las filas generan Minuta (lista negra)
- Cada regla es una condición de exclusión: si la fila matchea → estado `FILTRADA`
- Lógica AND/OR entre reglas (igual que DJ)
- La config persiste en DB

### Endpoints nuevos

```
GET  /config/filtros-minutas          → devuelve config actual
PATCH /config/filtros-minutas         → guarda config
POST /session/minutas/{id}/agregar           → FILTRADA → BORRADOR (sin limpiar otros borradores)
POST /session/minutas-filtradas/agregar-todas → todas las FILTRADAS → BORRADOR
```

---

## 8. Upload flow actualizado

```
POST /uploads/excel
  1. Parsear Excel → list[OrdenParsed] + errors
  2. Cargar config_filtros desde DB
  3. Para cada OrdenParsed:
     a. Evaluar filtros → excluida o no
     b. Evaluar DJ (incluyendo requiere_conformidad)
     c. Generar texto Minuta (igual que antes)
     d. Crear MinutaSession con estado = "BORRADOR" o "FILTRADA"
  4. clear_borradores_y_filtradas(user_id)  ← limpia BORRADOR y FILTRADA del upload anterior
  5. add_minutas(user_id, todas)
  6. Retornar UploadMVPResponse con:
     - ordenes_validas
     - ordenes_con_error
     - ordenes_filtradas   ← nuevo campo
     - errors
     - minutas             ← solo las BORRADOR
```

**Nota:** `clear_borradores_y_filtradas` elimina tanto `BORRADOR` como `FILTRADA` al subir un nuevo Excel. Las Minutas con estado `ENVIADO` nunca se limpian.

---

## 9. Dashboard — solapas

**Nuevo orden:**

`Borradores | Enviados | Filtradas | Plantilla | Config DJ | Filtros de Minutas`

### Solapa "Filtradas"

- Lista de Minutas con estado `FILTRADA`
- Muestra los mismos campos que la tarjeta de Borradores
- Botón **"Agregar"** por fila → `POST /session/minutas/{id}/agregar`
- Botón **"Agregar todas"** en el header → `POST /session/minutas/agregar-todas-filtradas`
- Al agregar, la Minuta pasa a `BORRADOR` y desaparece de Filtradas

### Solapa "Filtros de Minutas"

- Misma UI que "Config DJ"
- Tabla de reglas activas: campo | operador | valor | [eliminar]
- Dropdown campo: `operacion`, `operador`, `origen`, `estado`, `moneda`, `instrumento`, `cantidad`, `precio`, `monto`, `cantidad_operada`, `precio_operado`, `requiere_conformidad`
- Dropdown operador: `=` / `!=` (texto) o `=` / `!=` / `>` / `<` / `>=` / `<=` (numérico)
- Selector AND/OR entre reglas
- Guardar persiste en DB

### MinutaCard

Campos fijos visibles en la tarjeta:
`cliente_nombre`, `cuenta_comitente`, `operacion`, `instrumento`, `monto`, `fecha_operacion`

---

## 10. Migración Alembic 0005

Una sola migración que hace:

1. **ALTER TABLE `config_dj`**: agrega columna `activar_si_requiere_conformidad BOOLEAN NOT NULL DEFAULT TRUE`
2. **CREATE TABLE `config_filtros_minutas`**: con columnas `id`, `reglas`, `logica`, `actualizado_en`

---

## Qué NO cambia

- Máquina de estados BORRADOR → ENVIADO
- Botón "Copiar contenido" y botón "Enviado"
- Lógica de auth (login, 2FA, reset password)
- Session TTL (12h)
- Comportamiento de `_SafeDict` en la plantilla
- Estructura de errores por fila del parser
