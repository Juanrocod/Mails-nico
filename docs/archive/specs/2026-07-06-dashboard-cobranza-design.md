# Dashboard de Cobranza e Historial de Ciclos — Diseño

Fecha: 2026-07-06. Estado: aprobado por secciones en brainstorming; incluye los ajustes surgidos del análisis de huecos operativos (ver sección "Análisis de huecos").

---

## Contexto y problema de negocio

El cliente final administra una empresa de mantenimiento de ascensores con ~600 consorcios. Cobra un abono mensual más servicios adicionales. Todos los meses arrastra deudores: algunos con días de atraso, otros con meses. Su problema real no es mandar mails — es **cobrar**.

El sistema actual automatiza los recordatorios, pero el operario no tiene visión del negocio: cuánto le deben hoy, quién debe más, quién es moroso crónico, si los recordatorios funcionan. Además, al confirmar un ciclo nuevo, los datos del ciclo anterior dejan de verse en la interfaz (aunque nunca se borran de la DB — regla de negocio del spec original).

Este diseño resuelve ambas cosas con una sola base: hacer **visibles y computables** los datos históricos que ya se guardan.

## Decisiones clave

1. **Pago inferido por ausencia**: si un deudor del ciclo N no aparece en el Excel del ciclo N+1, se considera que saldó esa deuda. Se registra en un campo nuevo `saldado_en` (no se toca el enum `EstadoEnvio` de Postgres). El PAGO manual con comprobante sigue siendo la confirmación fuerte; la inferencia es la red automática.
2. **Todo dentro de la app actual**: mismo backend, frontend y deploy. Sin servicios nuevos.
3. **v1 solo con los datos existentes** (Excel maestro + Excels de deudores). El dashboard sirve además como demo para pedirle al cliente más fuentes (pagos reales, API de su sistema) — puntos de extensión listados al final.

---

## Capa de datos

### Migración 0006: `envios.saldado_en`

- Columna `saldado_en` (DateTime, nullable) en `envios`.

### Inferencia al confirmar un ciclo

En `confirmar_ciclo`, después de crear los envíos del ciclo nuevo: para cada Envio del ciclo que se desactiva cuya `clave_union` **no** figura entre los deudores del Excel nuevo → `saldado_en = now()`.

- Aplica a **todos** los estados (NO_CONTESTADO, CONTESTADO, PAGO, REBOTADO, SIN_EMAIL, FILTRADO): el Excel de deudores es la fuente de verdad de quién debe; si no está más, esa deuda se saldó, se le haya mandado mail o no.
- La lógica vive en `services/` (no en el router), junto a `excel_joiner` o en un servicio propio.

### Corrección de `ciclo_numero` (bug latente)

`_ciclos_consecutivos_deudor` hoy solo resetea la racha si el último envío quedó en PAGO. Con `saldado_en`, también resetea cuando el último envío de esa clave tiene `saldado_en` seteado: saldó = racha rota. Sin esto, un consorcio que pagó (inferido) y vuelve a deber meses después seguiría sumando racha como moroso crónico.

### Limitación aceptada (documentar en la UI con lenguaje neutro)

"Saldado" significa "dejó de aparecer como deudor". En la práctica casi siempre es "pagó", pero puede ser renegociación o baja del servicio. No prometer más precisión de la que hay.

---

## Dashboard

Nueva entrada "Dashboard" **primera** en el sidebar. La ruta `/` pasa a redirigir al dashboard (hoy va a Seguimiento).

### KPIs (4 tarjetas)

| KPI | Cálculo |
|---|---|
| Deuda total actual | Σ montos del ciclo activo, con variación en $ y % vs. ciclo anterior. |
| Deudores actuales | Cantidad de envíos del ciclo activo, con variación. |
| Cobrado desde el ciclo anterior | Σ montos de envíos del ciclo anterior con `saldado_en` **+** Σ reducciones de monto de los que repiten (`max(0, monto_anterior − monto_actual)` por clave). Los pagos parciales cuentan; los aumentos de deuda no restan (es deuda nueva, no des-cobro). |
| Efectividad de recordatorios | De los deudores del ciclo anterior que recibieron mail (`message_id` no nulo), % que saldó. Presentar como correlación, no causalidad ("saldaron tras el recordatorio"), porque no hay grupo de control. |

### Rankings (tabla con dos pestañas)

- **Top deudores por monto**: nombre, monto, ciclos consecutivos debiendo, estado del último mail. Cada fila clickeable → perfil del cliente.
- **Morosos crónicos**: ordenado por `ciclo_numero` descendente.

Se computan **en el frontend** desde `GET /ciclos/activo/envios` (ya devuelve monto, `ciclo_numero` y estado; ~600 filas máximo). Sin backend nuevo.

### Gráfico de evolución

Serie por ciclo: deuda total, cantidad de deudores y monto cobrado en cada transición. Librería: `recharts` (única dependencia nueva del frontend).

### Backend

Router `app/routers/dashboard.py` + servicio `app/services/dashboard_service.py` (lógica en services, según `.claude/rules/backend.md`):

- `GET /dashboard/resumen` → los 4 KPIs.
- `GET /dashboard/evolucion` → `[{numero, fecha, deuda_total, deudores, cobrado}]` por ciclo.

Ambos con `Depends(get_current_user)`.

---

## Perfil por cliente

Página dedicada `/clientes/:id` (id de ClienteMaestro).

- **Cabecera**: nombre, clave, email, localidad, estado (activo / baja / eliminado).
- **KPIs personales**: deuda actual (si está en el ciclo activo), ciclos consecutivos debiendo, total saldado histórico, comportamiento de respuesta (contesta / ignora / rebota).
- **Tabla de historial**: una fila por ciclo en que apareció — fecha, monto, si recibió mail, qué pasó (contestó/no/rebotó/pagó) y si saldó.

**Acceso**: click en filas de los rankings del dashboard + ícono nuevo en cada fila del Maestro.

**Backend**: `GET /maestro/{cliente_id}/historial` → envíos de esa `clave_union` a través de todos los ciclos, con fecha de cada ciclo. (`clave_union` ya está indexada.)

---

## Historial de ciclos

Integrado en Seguimiento, no es página nueva.

- **Selector de ciclo** arriba de SeguimientoPage: default "Ciclo actual (#N — fecha)", desplegable con los anteriores.
- Al elegir uno pasado, las mismas 4 pestañas muestran ese ciclo. La vista histórica es **funcional**, no una foto muerta: el drawer y "marcar PAGO" siguen operativos (el backend ya lo permite; el watcher IMAP tampoco filtra por ciclo activo, así que respuestas tardías actualizan el envío del ciclo viejo).

**Backend**:

- `GET /ciclos` → lista `[{id, numero, creado_en, total_envios, deuda_total}]`.
- `GET /ciclos/{ciclo_id}/envios` → mismo shape que el endpoint del ciclo activo (que queda como está).

### Aviso de respuestas tardías

Las respuestas a mails de ciclos viejos aterrizan en el envío viejo — invisibles desde la vista del ciclo actual. Para que no pasen desapercibidas:

- Banner en Seguimiento (vista de ciclo actual): *"N respuestas nuevas en ciclos anteriores"*, clickeable → navega al ciclo correspondiente.
- Definición: envíos con `ciclo_id ≠ ciclo activo` y `reply_en ≥ creado_en` del ciclo activo. Acotado naturalmente: al subir el próximo Excel, el corte se mueve.
- Cerrable por el operario con el mismo patrón de dismiss firmado en localStorage que usa el aviso de Configuración (reaparece si cambia el conteo).
- Endpoint: `GET /seguimiento/respuestas-tardias` → `{count, ciclos: [{ciclo_id, numero, count}]}`.

---

## Cambios al Preview (salidos del análisis de huecos)

El preview del Excel de deudores gana una **comparación contra el ciclo activo**, visible antes de confirmar:

- "X deudores nuevos · Y repiten del ciclo anterior · **Z se darán por saldados** (estaban y ya no aparecen)".
- Si Z es alto en proporción (ej. >50% del ciclo anterior), el texto se muestra como advertencia destacada: es la señal típica de un Excel equivocado, viejo o filtrado por error. El operario decide — el sistema no bloquea, avisa.
- **Claves duplicadas dentro del Excel**: si una `clave_union` aparece más de una vez, el preview lo marca como advertencia y el sistema conserva solo la última fila (hoy se crearían dos envíos y se duplicaría la deuda en los totales).

---

## Casos borde

- **Primer ciclo de la historia**: sin inferencia; KPIs comparativos muestran "—".
- **Re-subida de Excel corregido**: la inferencia corre contra el ciclo recién reemplazado; semánticamente correcto (quien no figura en el corregido, no debe).
- **PAGO manual y reaparece en el Excel siguiente**: no se marca `saldado_en` (reapareció); es deuda nueva o el Excel se exportó antes del pago. La racha se resetea igual porque PAGO ya resetea.
- **Cliente dado de baja/eliminado con deuda**: sus envíos FILTRADO cuentan en deuda total; si desaparece del Excel, se marca saldado como cualquier otro.
- **Respuestas tardías más allá de 30 días**: el watcher solo busca respuestas a envíos de los últimos 30 días (~2 ciclos). Una respuesta más tardía no se detecta. Limitación documentada, no se cambia en v1.
- **Cambio de `clave_union` de un cliente en el sistema origen**: aparece como cliente nuevo (SIN_EMAIL) y el viejo queda saldado; el historial se parte en dos. Limitación conocida — el operario lo resuelve en Maestro; fuera de alcance automatizarlo en v1.

## Testing

- **Backend (pytest)**: inferencia de saldado (marca exactamente a los ausentes, todos los estados, no marca presentes); reset de `ciclo_numero` con `saldado_en`; KPI "cobrado" con pagos parciales; endpoints `resumen`/`evolucion`/`historial`/`ciclos`/`respuestas-tardias` con datos multi-ciclo sembrados; advertencias de preview (diff y duplicados).
- **Frontend**: `tsc -b` + build (el proyecto no tiene test runner de front).

## Análisis de huecos operativos (día a día del operario)

Hallazgos del análisis y cómo se resolvieron:

| # | Hueco | Resolución |
|---|---|---|
| 1 | Subir un Excel equivocado/viejo marcaría saldados masivos y mandaría mails con montos viejos | Diff en preview + advertencia si desaparece una proporción alta (sección "Cambios al Preview") |
| 2 | Excel parcial (filtrado por zona) → saldados masivos | Misma advertencia del preview |
| 3 | Claves duplicadas en el Excel duplican deuda y envíos | Dedupe con advertencia en preview |
| 4 | Pagos parciales invisibles para el KPI "cobrado" | Fórmula incluye reducciones de monto de los que repiten |
| 5 | `ciclo_numero` no reseteaba tras pago inferido → morosos crónicos mal medidos | Reset con `saldado_en` |
| 6 | Respuestas tardías invisibles desde el ciclo actual | Banner de respuestas tardías |
| 7 | "Efectividad" leída como causalidad | Wording de correlación en la UI (sin cierre posible: requeriría grupo de control) |
| 8 | Respuesta a mail de >30 días no se detecta | Limitación documentada (v1) — cierre: subir `_SEARCH_WINDOW_DAYS`, ver Extensiones |
| 9 | Cambio de clave en el sistema origen parte el historial | Limitación documentada (v1) — cierre: fusión de clientes, ver Extensiones |
| 10 | "Saldado" es inferencia, no pago confirmado | Limitación documentada (v1) — cierre: datos de pagos reales del sistema del cliente, ver Extensiones |

## Extensiones futuras (fuera de alcance v1)

- Integración con el sistema del cliente (pagos reales con fecha exacta, API o Excel adicional) — reemplazaría la inferencia de "saldado" por datos duros (cierra el hueco #10).
- Ampliar la ventana de detección de respuestas tardías (`_SEARCH_WINDOW_DAYS` de 30 → 60/90 días) si en la práctica llegan respuestas fuera de ventana (cierra el hueco #8; costo: polls IMAP más lentos).
- Fusión de clientes en Maestro y/o detección asistida de cambios de clave (nombre igual, clave distinta) (cierra el hueco #9).
- Multi-plantilla con escalado de tono según antigüedad de la deuda (Fase 2 del spec original) — `ciclo_numero` + `saldado_en` la dejan lista.
- Export del dashboard (PDF/Excel) para compartir con el contador.
