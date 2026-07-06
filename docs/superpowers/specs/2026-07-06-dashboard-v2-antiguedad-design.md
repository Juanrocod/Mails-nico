# Dashboard v2 — Antigüedad de deuda y mejoras de cobranza — Diseño

Fecha: 2026-07-06. Extiende `2026-07-06-dashboard-cobranza-design.md` (ya implementado y en producción). Aprobado en brainstorming.

## Motivación

El dashboard v1 mide la cobranza por **ciclos** (tandas de envío). Pero los ciclos son irregulares (cada 10/15/25 días según el operario), así que "N ciclos debiendo" es un proxy ruidoso de lo que importa a nivel de negocio: **hace cuánto tiempo** arrastra la deuda cada consorcio. Esta v2 agrega una métrica de **antigüedad** (tiempo real, no ciclos) reconstruida del historial de cargas, más varios ajustes de precisión y estética pedidos por el usuario.

## Decisión de fondo: antigüedad reconstruida del historial

Para cada consorcio del ciclo activo, "deudor desde" = fecha del **primer ciclo de su racha actual** (el ciclo donde arrancó a deber sin haber saldado desde entonces). La antigüedad es de esa fecha hasta hoy. Usa la misma lógica de racha que ya existe (`_ciclos_consecutivos_deudor`: la racha se corta con PAGO manual o `saldado_en`), pero devuelve la **fecha** en vez del conteo.

**Algoritmo (`deudor_desde` de una clave):** tomar los envíos de la clave ordenados por `Ciclo.numero` descendente. Si el más reciente es PAGO o tiene `saldado_en`, no hay deuda vigente → `None`. Si no, caminar hacia atrás incluyendo envíos consecutivos hasta toparse con uno que sea PAGO o tenga `saldado_en` (ese NO se incluye, cierra una racha anterior). `deudor_desde` = `creado_en` del ciclo más antiguo incluido.

**Limitaciones honestas (documentadas en la UI):** (a) cuenta desde que el sistema vio al consorcio deudor por primera vez, no desde el vencimiento real de la factura; (b) es ciego antes de la primera carga del operario; (c) su precisión depende de la regularidad de las cargas (si el operario se saltea meses, puede confundir "pagó y volvió a deber" con "debe seguido"). La precisión total llega recién con datos de vencimiento reales del sistema del cliente (extensión futura, ver abajo).

## Cambios pedidos (6) + antigüedad

### 1. "Deuda total" → "Deuda actual"
Solo la etiqueta de la KPI.

### 2. Indicador de variación verde/rojo en la KPI "Deuda actual"
Badge con el % vs. el ciclo anterior: **verde si la deuda bajó** (mejoró), **rojo si subió** (empeoró). Ojo con la semántica invertida respecto a un dashboard de ingresos: en deuda, bajar es bueno. El dato ya se calcula (`deuda_total` vs `deuda_total_anterior`); falta el color.

Aclaración de negocio (no es un cambio de fórmula): "Cobrado" NO es la resta simple `deuda_anterior − deuda_actual`. La resta simple esconde la plata que entró cuando hay deuda nueva. "Cobrado" usa la fórmula real ya implementada (`_cobrado_entre`: saldados completos + reducciones de monto), que es el "cuánto entró" honesto. Se mantiene sin cambios.

### 3. Quitar "Saldaron tras el recordatorio" → reemplazar por "Deuda +90 días"
La efectividad del recordatorio no es medible con los datos actuales (quien paga sin mandar mail no se registra), así que se saca. En su lugar, la KPI **"Deuda +90 días"**: suma de montos de los deudores del ciclo activo cuya antigüedad supera 90 días — la plata en riesgo real, la métrica AR estándar. Va a mostrar $0 al principio (el sistema es ciego antes de la primera carga) y se puebla con el tiempo; es correcto y honesto.

Backend: se elimina `efectividad` de `ResumenData`/`DashboardResumenResponse` y `_efectividad`; se agrega `deuda_mas_90: Decimal`.

### 4. Restyle del gráfico de evolución
El repo `app-peluqueria` del usuario usa la MISMA librería (recharts v3); la prolijidad viene del estilado. Adoptar ese lenguaje visual: área con degradado para la deuda por ciclo, ejes minimalistas (`axisLine={false}`, `tickLine={false}`, ticks chicos y grises), eje Y oculto o mínimo, tooltip oscuro custom, tarjeta con borde suave. Se reemplaza el `ComposedChart` con Legend/grilla punteada actual.

### 5. Gráfico "evolución de su deuda" en el perfil del cliente
Un área chica con el mismo estilo, mostrando el monto de ESE consorcio a lo largo de los ciclos en que apareció (orden cronológico). Deja ver de un vistazo si su deuda viene bajando o creciendo.

### 6. Antigüedad en la UI
- **Perfil del cliente:** dato "Deudor desde DD/MM/YYYY (hace X)" en el header o KPI; la KPI "Ciclos debiendo" pasa a "Debe hace X" (antigüedad), con la racha como dato secundario ("N recordatorios enviados").
- **Dashboard → "Morosos crónicos":** pasa a ordenarse por **antigüedad** (deuda más vieja primero), no por cantidad de ciclos. Columna "Debe hace X". Como necesita datos cross-ciclo (no disponibles client-side), este ranking pasa a calcularse en el backend con un endpoint nuevo.
- **Resaltado +90 días:** las antigüedades de más de 90 días se muestran en rojo (bandera de cobranza).

## Arquitectura

### Backend

- **`dashboard_service.py`:**
  - `deudor_desde_por_clave(db, claves: set[str]) -> dict[str, datetime]`: una sola query de los envíos (join a `Ciclo`) de esas claves ordenados por `Ciclo.numero` desc, agrupa en Python y aplica el algoritmo de racha por clave.
  - `resumen`: agrega `deuda_mas_90` (Σ montos de activos con antigüedad > 90 días), elimina `efectividad`.
  - `morosos(db, limite=10) -> list[MorosoItem]`: para las claves del ciclo activo, arma items `{clave_union, nombre_consorcio, monto, deudor_desde, ciclos_debiendo, estado}` ordenados por `deudor_desde` ascendente (más viejo primero), top N.
- **`routers/dashboard.py`:** nuevo `GET /dashboard/morosos` → `list[MorosoSchema]`. `GET /dashboard/resumen` cambia (deuda_mas_90 en vez de efectividad).
- **`routers/maestro.py`** (`historial_cliente`): agrega `deudor_desde: Optional[datetime]` a `HistorialClienteResponse`, computado de los `rows` que ya trae.
- **Schemas:** `DashboardResumenResponse` (deuda_mas_90), `MorosoSchema` nuevo, `HistorialClienteResponse` (deudor_desde). Sin migración (no hay columnas nuevas; todo se deriva de `saldado_en`/`ciclo_numero`/`Ciclo.creado_en` que ya existen).

### Frontend

- **Tipos (`domain.ts`):** `DashboardResumen` (quitar `efectividad`, sumar `deuda_mas_90`), `Moroso` nuevo, `HistorialCliente` (sumar `deudor_desde`).
- **Servicios:** `getMorosos()` nuevo en `dashboard.ts`.
- **`DashboardPage.tsx`:** rename KPI; badge de variación verde/rojo; reemplazo de efectividad por "Deuda +90 días"; "Morosos crónicos" desde el endpoint nuevo con columna "Debe hace X" (rojo si +90d); restyle del gráfico (área + degradado + ejes minimalistas + tooltip custom). "Top por monto" queda client-side.
- **`ClientePerfilPage.tsx`:** KPI "Debe hace X" (antigüedad) con racha secundaria; dato "Deudor desde" en el header; gráfico de evolución de su deuda con el mismo estilo.
- **Componente compartido de gráfico:** un `EvolucionChart` reutilizable (dashboard + perfil) con el estilo peluquería, para no duplicar el estilado de recharts.

## Testing

- Backend (pytest): `deudor_desde` (racha simple, corte por saldado, corte por PAGO, hueco de cargas, sin deuda vigente, el que distingue "más reciente" de "racha máxima"); `deuda_mas_90` (umbral); `morosos` (orden por antigüedad, top N); `deudor_desde` en el perfil; que `efectividad` ya no esté en la respuesta.
- Frontend: `tsc -b` + `npm run build`.

## Extensiones futuras (fuera de alcance)

- **Columna de vencimiento en el Excel de deudores** (`fecha de vencimiento` / `deudor desde`): el parser se diseñará para aceptarla opcionalmente en el futuro; si viene, reemplaza la reconstrucción por el dato exacto (independiente de la cadencia de carga, retroactivo). Cierra las limitaciones (a), (b) y (c). Requiere que el cliente exporte ese dato de su sistema.
- Buckets AR más finos (corriente / +30 / +60 / +90) una vez que haya datos de vencimiento reales.
- Integración con el sistema de facturación del cliente (API/export con aging real).
