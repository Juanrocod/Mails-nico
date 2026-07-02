# PENDIENTES.md — Gaps de implementación vs. spec

Auditoría del código real contra `docs/superpowers/specs/2026-06-30-mails-nico-design.md` y `docs/adr/`. Fecha: 2026-07-01.

El flujo core (subir Excel → preview → confirmar → SMTP con rate limit → IMAP watcher → seguimiento → override manual) está completo y probado. Lo que sigue es lo que falta para cerrar el spec.

---

## Crítico

### 1. Endpoint de unsubscribe
El mail genera el link (`email_generator.py`) y el modelo tiene `ClienteMaestro.prefiere_no_recibir_email`, pero **no existe ningún endpoint que reciba el click**. Hoy el link no hace nada. Falta:
- Ruta (ej. `GET /unsubscribe/{token}` o similar) que setee `prefiere_no_recibir_email=true`
- Notificación al operario (spec sección 7)
- Requisito legal (Ley 25.326) — no debería salir a producción sin esto

---

## Importante

### 2. Página Configuración incompleta
Hoy solo tiene cambio de contraseña. El spec pide gestión de credenciales Yahoo (SMTP/IMAP) y datos de empresa desde la UI; hoy viven fijas en `.env`.

### 3. Validación de palabras prohibidas en Plantilla
No implementada al guardar asunto/cuerpo (spec sección 7, anti-spam).

### 4. Validación de formato de email antes de enviar
Hoy solo se chequea que el campo no esté vacío (`excel_joiner.py`), no que sea un email válido.

### 5. Logo del mail — solo URL de texto
`Plantilla.logo_url` es un string; no hay endpoint de upload de imagen ni input de archivo en `PlantillaPage.tsx`.

---

## Menor

### 6. Campos `reply_en` y `tiene_adjunto` en `Envio`
El spec (sección 5, modelo de datos) los define pero no existen en `models/envio.py`. No rompen nada en runtime (el frontend tampoco los usa), pero sin ellos no se puede distinguir un `PAGO` por adjunto real de uno por override manual, ni separar fecha de respuesta del snippet.

---

## Pendientes bloqueantes de datos (ya conocidos, sin cambios)

Ver también `CLAUDE.md`:
- [ ] Estructura exacta y clave de unión del Excel de deudores
- [ ] Estructura exacta y clave de unión del Excel maestro
- [ ] App password real de Yahoo del cliente
