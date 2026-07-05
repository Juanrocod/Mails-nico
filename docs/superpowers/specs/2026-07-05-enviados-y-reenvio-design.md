# Spec — Pestaña "Enviados" y reenvío de fallidos

**Fecha:** 2026-07-05
**Estado:** Aprobado — listo para planificación de implementación
**Relacionado:** `docs/superpowers/specs/2026-06-30-mails-nico-design.md`, ADR-0002 (envío automático SMTP)

---

## 1. Problema

Hoy, una vez confirmado un ciclo, la solapa **Para Enviar** (en Nuevo Envío) y la solapa **No Contestados** (en Seguimiento) muestran exactamente el mismo conjunto: todo `Envio` con `estado = NO_CONTESTADO`. Esto pasa porque `estado` **nunca cambia cuando el mail se envía** — solo se completan `message_id` y `enviado_en` si el SMTP confirmó el envío. Si el envío falla (excepción en `smtp_sender.py`), hoy eso se registra únicamente en el log del servidor y el `Envio` queda idéntico a uno recién enviado con éxito: mismo estado, sin ningún indicio visual de la falla.

Consecuencia para el Operario: no hay forma de saber, mirando el dashboard, cuáles mails salieron de verdad y cuáles nunca se mandaron. Tampoco hay manera de corregir un dato (por ejemplo un mail mal cargado en el Maestro) y reintentar el envío de ese caso puntual — la única opción hoy sería rearmar todo el ciclo desde cero.

---

## 2. Solución

**Sin agregar un estado nuevo ni tocar el enum `EstadoEnvio`** (evita el mismo riesgo de migración de Postgres ya identificado en el trabajo de Maestro). En cambio, se usan los campos que ya existen:

- Un `Envio` con `message_id` seteado → se mandó con éxito, sin importar su `estado` actual.
- Un `Envio` con `estado = NO_CONTESTADO` y `message_id` vacío → nunca salió (falló el envío).

**Cambios de significado en las pestañas:**

| Pestaña | Ubicación | Antes | Después |
|---------|-----------|-------|---------|
| Para Enviar (post-confirmación) | Nuevo Envío | Todo `NO_CONTESTADO` | Solo lo que **falló al enviar** (`NO_CONTESTADO` sin `message_id`) |
| Enviados (nueva) | Nuevo Envío | — | Todo con `message_id` seteado — incluye los que después contestaron, pagaron o rebotaron. Es un registro permanente de "esto salió", no se vacía con el tiempo. |
| No Contestados | Seguimiento | Todo `NO_CONTESTADO` | Solo `NO_CONTESTADO` **con** `message_id` (se mandó, todavía sin respuesta) |

"Enviados" y "No Contestados" no son excluyentes entre sí — un envío recién mandado aparece en ambas pestañas a la vez (una trackea si salió, la otra si contestó). Eso es intencional.

**Reenvío**, disponible solo desde Para Enviar (solo para los que fallaron al enviar, nunca para Rebotados — esos ya se sabe que salieron y no se reintentan, regla existente del sistema):

- Por fila: botón "Reenviar" en cada envío fallido.
- En bloque: botón "Reenviar todos" arriba de la tabla, reintenta todos los fallidos del ciclo activo, respetando el rate limit de 5 cada 30 segundos (reusa `smtp_sender.enviar_ciclo` sin modificarlo).
- Antes de reintentar, se vuelve a consultar el Maestro de Clientes por la clave de unión del envío — si el operario corrigió el email ahí, el reenvío usa el dato corregido. Si al revalidar el cliente ya no tiene un email válido, está dado de baja, o está inactivo, el reenvío de ese envío se cancela con un motivo visible y el envío se queda en Para Enviar (nada cambia en su estado).

---

## 3. Arquitectura

### Backend

**`services/excel_joiner.py`** — nueva función, co-ubicada con `join_deudores` porque encapsula las mismas reglas de negocio (baja, inactivo, email válido):

```
revalidar_para_reenvio(db, envio) -> tuple[bool, str | None]
```

Busca `ClienteMaestro` por `envio.clave_union`. Si es válido para reenviar, actualiza `envio.email` y `envio.nombre_consorcio` con los datos actuales del Maestro (sin commitear todavía) y devuelve `(True, None)`. Si no — cliente no encontrado, `prefiere_no_recibir_email`, `not activo`, o email inválido/ausente — devuelve `(False, "<motivo legible>")` sin tocar el envío.

**`routers/ciclos.py`** — dos endpoints nuevos:

- `POST /envios/{id}/reenviar`: valida que el envío sea `NO_CONTESTADO` sin `message_id` (si no, `400`). Llama `revalidar_para_reenvio`; si falla, `400` con el motivo. Si es válido, llama `enviar_ciclo([envio], db, on_progress_noop)` (reusa la función existente, sin cambios) y después revisa si `envio.message_id` quedó seteado para determinar éxito. Devuelve el `Envio` actualizado o un error si el SMTP falló de nuevo.
- `POST /ciclos/activo/reenviar-fallidos`: junta todos los envíos fallidos del ciclo activo, corre `revalidar_para_reenvio` en cada uno (los que fallan la validación quedan afuera, con su motivo), y hace streaming SSE del reenvío de los que sí pasaron — reusa el mismo patrón de `_stream_envios` que ya usa `confirmar_ciclo`. Al final del stream incluye un resumen de los que se saltearon (id + motivo), para que el frontend los pueda mostrar.

### Frontend

**`NuevoEnvioPage.tsx`**:
- Nueva pestaña "Enviados" (ícono, badge de conteo, igual patrón que las otras 3).
- "Para Enviar" (fuera del modo revisión/preview) filtra por `estado === "NO_CONTESTADO" && !message_id` en vez de solo `estado === "NO_CONTESTADO"`.
- La tabla de "Para Enviar" gana una columna de acción: botón "Reenviar" por fila, más un botón "Reenviar todos" arriba de la tabla (reusa `ProgresoEnvio` para la barra de progreso del reenvío en bloque, igual que ya hace la confirmación).

**`SeguimientoPage.tsx`**: el filtro de "No Contestados" pasa a `estado === "NO_CONTESTADO" && message_id` en vez de solo `estado === "NO_CONTESTADO"`.

**`services/ciclos.ts`**: nuevas funciones `reenviarEnvio(id)` y `reenviarFallidos(onProgress)` (esta última con la misma forma de streaming por `fetch` + SSE manual que ya usa `confirmarCiclo`).

---

## 4. Manejo de errores

- Reenvío individual con envío que no está en estado fallido (ya se mandó, o nunca fue parte de para-enviar) → `400`.
- Revalidación contra Maestro falla (cliente no encontrado / baja / inactivo / email inválido) → el envío no se toca, se muestra el motivo en la fila, sigue en Para Enviar.
- Reenvío que vuelve a fallar en el SMTP (ej. credenciales del proveedor mal configuradas) → mismo comportamiento que un envío nuevo que falla: queda igual que estaba, sin `message_id`, se puede reintentar de nuevo más tarde.
- El reenvío en bloque nunca aborta por un ítem fallido — sigue con el resto y reporta un resumen al final (mismo criterio que ya usa `enviar_ciclo` con las excepciones por ítem).

---

## 5. Testing

- Backend: `revalidar_para_reenvio` — casos: cliente no encontrado, dado de baja, inactivo, sin email, email inválido, caso válido (actualiza email/nombre y devuelve `True`).
- Backend: `POST /envios/{id}/reenviar` — envío no elegible (400), reenvío exitoso (llega a tener `message_id`), reenvío que falla validación de Maestro (400 con motivo).
- Backend: `POST /ciclos/activo/reenviar-fallidos` — mezcla de envíos elegibles e inelegibles, confirma que los elegibles se mandan y los inelegibles aparecen en el resumen de saltados.
- Frontend: sin infraestructura de tests automatizados (consistente con el resto del proyecto) — verificación manual en el navegador.

---

## 6. Fuera de alcance

- Ningún estado nuevo en `EstadoEnvio` ni en `MotivoFiltrado`.
- Reintento automático/programado de fallidos — el reenvío siempre lo dispara el Operario a mano.
- Reenvío de Rebotados — esos ya se sabe que salieron (llegó un mailer-daemon) y la regla existente del sistema es que no se reintentan.
- Cambiar el monto del envío al revalidar contra Maestro — el monto viene del Excel de deudores original, no de Maestro, y no se toca en el reenvío.
