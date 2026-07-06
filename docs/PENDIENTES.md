# PENDIENTES.md — Gaps de implementación vs. spec

Auditoría del código real contra `docs/superpowers/specs/2026-06-30-mails-nico-design.md` y `docs/adr/`. Fecha: 2026-07-05.

El flujo core (subir Excel → preview → confirmar → SMTP con rate limit → IMAP watcher → seguimiento → override manual) está completo, y pasó una revisión integral pre-producción: 145 tests automatizados en verde, code review + security review sin hallazgos pendientes, y un checklist manual end-to-end (Fases 1-6: configuración, Maestro, ciclo de envío completo, reenvío de fallidos, seguimiento/respuestas, unsubscribe) confirmado funcionando en producción con volumen real (hasta 60 mails en un solo ciclo).

---

## Resuelto desde la última auditoría

- **Endpoint de unsubscribe** (`GET /unsubscribe/{token}`) — existe en `routers/unsubscribe.py`, setea `prefiere_no_recibir_email=true`. Probado en producción: el link de baja marca correctamente al cliente y la reincorporación (reactivar) también funciona.
- **Página Configuración** — completa: selector de proveedor (Yahoo/Gmail), credenciales de ambos, cambio de contraseña, aviso de envíos pendientes/intrackeables por proveedor (con email de origen y botón para cerrarlo).
- **Validación de palabras prohibidas en Plantilla** — implementada en `schemas/plantilla.py` (`PALABRAS_PROHIBIDAS`, validador `sin_palabras_prohibidas`).
- **Validación de formato de email antes de enviar** — `excel_joiner.join_deudores` usa `is_valid_email` antes de mandar a `para_enviar`.
- **Logo del mail** — `POST /plantilla/logo` sube el archivo, `PlantillaPage.tsx` tiene input de archivo.
- **Campos `reply_en` y `tiene_adjunto` en `Envio`** — existen en `models/envio.py` y se usan en `imap_watcher.py`/`reply_classifier.py`.
- **App password real de Yahoo/Gmail** — el sistema soporta ambos proveedores intercambiables desde Configuración, con seguimiento de cuál mandó cada Envio (`Envio.proveedor`).
- **Estructura del Excel de deudores y maestro** — confirmada con archivos reales: `nro cliente` (numérico, 8 dígitos con ceros a la izquierda, ej. `00000001`), `nombre`, `localidad`, `monto`.
- **Maestro: dados de baja y eliminados unificados** — "Mostrar inactivos" agrupa ambos casos con motivo visible ("Baja" / "Eliminado"), reactivar limpia los dos flags a la vez.
- **Refresco manual de Seguimiento** — botón "Refrescar ahora" dispara un poll IMAP al toque (ventana de 1 día, rápido) en vez de esperar los 10 min del poll automático (que sigue escaneando 30 días completos).
- **Envío robusto a desconexión del cliente** — el envío de fondo sobrevive a un F5/navegación (no se corta), la barra de progreso se reconstruye sola desde el estado real si se pierde la conexión en vivo, y los envíos todavía en cola durante un envío masivo no aparecen como "fallidos para reenviar" (evita reenvíos duplicados accidentales).
- **Aviso de "envío completado"** — cartel verde con el conteo real de enviados (no el intentado) al terminar un envío masivo o un reenvío en bloque, distinguiendo éxito total de parcial.
- **Dashboard de cobranza e historial** — KPIs (deuda, deudores, cobrado, efectividad), rankings (monto / morosos crónicos), evolución por ciclo, perfil histórico por cliente (`/clientes/:clave`), selector de ciclos pasados en Seguimiento, aviso de respuestas tardías, inferencia de pago por ausencia (`saldado_en`, migración 0006), dedupe de claves duplicadas y diff del Excel contra el ciclo activo en el preview. Spec: `docs/superpowers/specs/2026-07-06-dashboard-cobranza-design.md`.

---

## Importante

### 1. Render free tier bloqueaba el puerto SMTP — resuelto pasando a plan Starter
El 2026-07-05 se detectó que el envío nunca completaba en producción (`OSError: Network is unreachable`). Causa: Render bloquea tráfico saliente a los puertos SMTP (25/465/587) en el plan gratuito desde septiembre 2025. Se resolvió pasando el servicio a un plan Starter ($7/mes), que además elimina el "spin down" a los 15 min de inactividad — relevante porque el IMAP Watcher corre en background sin generar tráfico HTTP propio, así que en el plan free tampoco corría de forma confiable. De paso se agregó un timeout de 15s a la conexión SMTP (`smtp_sender.py`) para que un proveedor mal configurado falle rápido y visible en vez de trabar el ciclo entero.

**Si en algún momento se vuelve a un plan gratuito o se cambia de hosting, este problema reaparece.**

---

## Menor

### 2. Sin test de integración continuo del flujo "falla → se corrige Maestro → se reenvía → aparece en Enviados"
Cada paso individual está testeado, pero no hay un único test que atraviese las cuatro etapas en una corrida.

### 3. "Mail activo" en Configuración no verifica la conexión real
El cartel verde solo confirma que hay un email + contraseña guardados, no que el login SMTP/IMAP realmente funcione con esas credenciales. Queda como mejora a futuro (agregar una verificación real de conexión, ej. botón "Probar conexión").

---

## Pendientes bloqueantes de datos

Todos resueltos — ver sección "Resuelto" arriba.
