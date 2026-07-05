# PENDIENTES.md — Gaps de implementación vs. spec

Auditoría del código real contra `docs/superpowers/specs/2026-06-30-mails-nico-design.md` y `docs/adr/`. Fecha: 2026-07-05 (actualizado — la versión anterior, del 2026-07-01, estaba desactualizada: casi todo lo que marcaba como pendiente ya se resolvió).

El flujo core (subir Excel → preview → confirmar → SMTP con rate limit → IMAP watcher → seguimiento → override manual) está completo y probado, incluyendo las features agregadas hoy: proveedor de email configurable (Yahoo/Gmail), borrar/reactivar/agregar clientes en Maestro, pestaña Enviados + reenvío de fallidos.

---

## Resuelto desde la última auditoría

- **Endpoint de unsubscribe** (`GET /unsubscribe/{token}`) — existe en `routers/unsubscribe.py`, setea `prefiere_no_recibir_email=true`.
- **Página Configuración** — completa: selector de proveedor (Yahoo/Gmail), credenciales de ambos, cambio de contraseña.
- **Validación de palabras prohibidas en Plantilla** — implementada en `schemas/plantilla.py` (`PALABRAS_PROHIBIDAS`, validador `sin_palabras_prohibidas`).
- **Validación de formato de email antes de enviar** — `excel_joiner.join_deudores` usa `is_valid_email` antes de mandar a `para_enviar`.
- **Logo del mail** — `POST /plantilla/logo` sube el archivo, `PlantillaPage.tsx` tiene input de archivo.
- **Campos `reply_en` y `tiene_adjunto` en `Envio`** — existen en `models/envio.py` y se usan en `imap_watcher.py`/`reply_classifier.py`.
- **App password real de Yahoo/Gmail** — resuelto en la práctica: el sistema ahora soporta ambos proveedores intercambiables desde Configuración: si Yahoo da problemas, Gmail funciona como alternativa completa (probado end-to-end en producción).
- **Estructura del Excel de deudores y maestro** — confirmada con archivos reales: `nro cliente` (numérico, 8 dígitos con ceros a la izquierda, ej. `00000001`), `nombre`, `localidad`, `monto`.

---

## Importante

### 1. Render free tier bloqueaba el puerto SMTP — resuelto pasando a plan Starter
El 2026-07-05 se detectó que el envío nunca completaba en producción (`OSError: Network is unreachable`). Causa: Render bloquea tráfico saliente a los puertos SMTP (25/465/587) en el plan gratuito desde septiembre 2025. Se resolvió pasando el servicio a un plan Starter ($7/mes), que además elimina el "spin down" a los 15 min de inactividad — relevante porque el IMAP Watcher corre en background sin generar tráfico HTTP propio, así que en el plan free tampoco corría de forma confiable. De paso se agregó un timeout de 15s a la conexión SMTP (`smtp_sender.py`) para que un proveedor mal configurado falle rápido y visible en vez de trabar el ciclo entero.

**Si en algún momento se vuelve a un plan gratuito o se cambia de hosting, este problema reaparece.**

---

## Menor

### 2. Reenvío en bloque — pequeños detalles de UX
- El botón "Reenviar todos (N)" muestra el total de fallidos candidatos, no el total que efectivamente se reintenta (los que no pasan la revalidación contra Maestro quedan afuera del conteo de progreso). Cosmético.
- Un cliente creado manualmente en Maestro mientras el filtro "Mostrar inactivos" está tildado no aparece hasta destildar el filtro (el nuevo cliente es activo por default).

### 3. Sin test de integración continuo del flujo "falla → se corrige Maestro → se reenvía → aparece en Enviados"
Cada paso individual está testeado, pero no hay un único test que atraviese las cuatro etapas en una corrida.

---

## Pendientes bloqueantes de datos

Todos resueltos — ver sección "Resuelto" arriba.
