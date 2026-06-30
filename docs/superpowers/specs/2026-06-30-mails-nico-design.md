# Spec — Sistema de Cobro Automático por Mail (Mails-nico)

**Fecha:** 2026-06-30  
**Estado:** Aprobado — listo para planificación de implementación  
**Base:** Adaptación del proyecto Mails-finanzas (broker), enfoque B — borrado quirúrgico

---

## 1. Problema

El dueño de una empresa de mantenimiento de ascensores (~600 clientes / consorcios) necesita enviar recordatorios de deuda de forma periódica (~cada 15 días). Hoy lo hace manualmente. Quiere un sistema que tome un Excel exportado de su sistema de facturación, genere mails personalizados y los envíe automáticamente desde su cuenta de Yahoo Mail, con seguimiento de respuestas.

---

## 2. Solución

Sistema web de ciclo-envío: el usuario sube un Excel de deudores, el sistema lo cruza con un maestro de clientes, genera los mails y los envía con rate limiting. Un IMAP watcher monitorea las respuestas y actualiza el dashboard automáticamente.

---

## 3. Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12 + FastAPI |
| Frontend | React 18 + TypeScript |
| Base de datos | PostgreSQL (Neon free tier) |
| Auth | JWT + bcrypt (sin 2FA) |
| Email envío | Yahoo SMTP (`smtp.mail.yahoo.com:587`) |
| Email lectura | Yahoo IMAP (`imap.mail.yahoo.com:993`) |
| Excel | openpyxl / pandas |
| Real-time | Server-Sent Events (SSE) para progreso de envío |

---

## 4. Arquitectura — módulos

### Lo que se elimina del broker (Mails-finanzas)

- TOTP / 2FA completo (pyotp, QR codes, pantalla TwoFactor)
- DJ engine (`dj_engine.py`)
- Filtros engine (`filtros_engine.py`) — reemplazado por lógica de monto mínimo más simple
- Session store en RAM (`session_store.py`) — reemplazado por persistencia en DB
- Modelos: `InviteToken`, `ConfigDJ`, `ConfigFiltros`
- Migraciones 0001–0006 (se arranca con una migración inicial limpia)
- Páginas frontend: TwoFactor, Register, ConfigDJ, FiltrosMinutas

### Módulos que se adaptan

| Módulo | Origen | Cambio |
|--------|--------|--------|
| `auth` | broker | Quitar TOTP; mantener login JWT + bcrypt + rate limiting |
| `excel_parser` | broker | Adaptar para dos formatos: maestro y deudores |
| `email_generator` | broker (`minuta_generator`) | Adaptar para template de cobro con variables nuevas |
| `db_config` | broker | Simplificar: solo gestión de Plantilla |

### Módulos nuevos

| Módulo | Responsabilidad |
|--------|----------------|
| `smtp_sender` | Envía mails vía Yahoo SMTP con cola y rate limiting |
| `imap_watcher` | Polling cada 10 min al inbox; detecta respuestas y rebotes |
| `reply_classifier` | Clasifica respuestas: adjunto → PAGO, texto → CONTESTADO, mailer-daemon → REBOTADO |
| `excel_joiner` | Cruza deudores con ClienteMaestro por clave de unión; detecta sin mail y filtrados |

---

## 5. Modelo de datos

```
User
  id, email, hashed_password, activo

ClienteMaestro
  id
  clave_union        ← campo a confirmar cuando el cliente entregue el Excel (probablemente nro_cliente)
  nombre
  email
  activo
  prefiere_no_recibir_email   ← se setea cuando el cliente hace click en unsubscribe; nunca se sobreescribe con merge
  actualizado_en

Plantilla
  id
  asunto             ← subject del mail; soporta variables
  cuerpo             ← texto HTML con variables: {{nombre}}, {{monto}}, {{localidad}}, {{clave_union}}
  monto_minimo       ← deudores debajo de este valor → motivo MONTO_MINIMO
  logo_url
  color_primario
  nombre_empresa
  pie_email          ← datos de contacto + texto legal del footer
  usuario_id

Ciclo
  id
  usuario_id
  nombre_archivo
  total_deudores
  para_enviar
  sin_email
  filtrados
  activo             ← solo uno activo a la vez; el anterior se archiva al crear uno nuevo
  creado_en

Envio
  id
  ciclo_id
  clave_union
  nombre
  localidad
  monto
  email
  estado             ← enum: NO_CONTESTADO | CONTESTADO | PAGO | REBOTADO | SIN_EMAIL | FILTRADO
  motivo_filtrado    ← enum: MONTO_MINIMO | DADO_DE_BAJA (solo cuando estado = FILTRADO)
  message_id         ← SMTP Message-ID; índice para matching con IMAP
  enviado_en
  reply_en
  reply_snippet      ← primeras líneas del texto de respuesta
  tiene_adjunto
  ciclo_numero       ← contador de ciclos consecutivos sin respuesta (base para Fase 2)
```

**Índices:**
- `ClienteMaestro.clave_union` — unión con Excel de deudores
- `Envio.message_id` — lookup del IMAP watcher en cada poll
- `Envio.ciclo_id` + `Envio.estado` — filtrado por solapa en dashboard

**Política de retención:** Los `Envio` de ciclos anteriores NO se borran. Sirven para:
1. Detectar respuestas a mails de ciclos anteriores vía IMAP (ventana: 30 días)
2. Calcular `ciclo_numero` (base para multi-plantilla en Fase 2)

---

## 6. Flujo completo

### 6.1 Maestro de clientes (una vez, o cuando cambia)

1. Usuario sube Excel maestro
2. Sistema hace merge con `ClienteMaestro`:
   - Cliente nuevo → se agrega (`activo=true`, `prefiere_no_recibir_email=false`)
   - Cliente existente + mail cambió → actualiza mail; preserva `prefiere_no_recibir_email`
   - Cliente existente + mismo mail → no toca nada
   - Cliente en DB pero no en Excel → queda en DB sin cambios

### 6.2 Ciclo de envío (~cada 15 días)

**Fase 1 — Upload y preview (nada se guarda en DB, nada se envía):**

1. Usuario sube Excel de deudores
2. `excel_joiner` cruza con `ClienteMaestro` por `clave_union`
3. Aplica filtros:
   - Sin match en maestro → `SIN_EMAIL`
   - `prefiere_no_recibir_email = true` → `FILTRADO` / `DADO_DE_BAJA`
   - `monto < monto_minimo` → `FILTRADO` / `MONTO_MINIMO`
   - Resto → `para_enviar`
4. Muestra modal de preview:
   ```
   Para enviar:  72
   Sin email:     5
   Filtrados:     3
   ```
5. Usuario puede cerrar, corregir maestro y re-subir sin consecuencias

**Fase 2 — Confirmación y envío (recién acá se escribe en DB):**

6. Usuario hace click en "Enviar 72 mails"
7. Se crea `Ciclo` + todos los `Envio` en DB — incluyendo `SIN_EMAIL` y `FILTRADO` (sin mail enviado, solo registro para que las solapas de Nuevo Envío muestren datos persistentes)
8. Ciclo anterior se marca `activo=false`
9. `smtp_sender` encola los mails y los envía con rate limiting: **5 mails cada 30 segundos**
10. Por cada mail enviado, SSE emite evento → frontend actualiza barra de progreso en tiempo real
11. Al finalizar: pantalla de completado → redirect automático a Seguimiento

### 6.3 Seguimiento de respuestas

- `imap_watcher` hace polling cada 10 minutos al inbox de Yahoo
- Por cada mail recibido:
  - Si `From` contiene `mailer-daemon` o `postmaster` → busca `message_id` referenciado → marca `REBOTADO`
  - Si tiene header `In-Reply-To` o `References` que matchea un `message_id` guardado:
    - Tiene adjunto (imagen o PDF) → marca `PAGO`
    - Solo texto → marca `CONTESTADO`
- El usuario puede mover manualmente de `CONTESTADO` → `PAGO` desde el dashboard

---

## 7. Rate limiting y anti-spam

- **Velocidad de envío:** 5 mails cada 30 segundos (~600 mails en 60 min)
- **Contenido personalizado:** cada mail incluye nombre y monto del destinatario específico
- **Sin palabras prohibidas** en asunto y cuerpo (validación al guardar plantilla)
- **Validación de formato** de mail antes de enviar; rebotes se registran y no se reintentan
- **Unsubscribe link** en el footer de cada mail (requerimiento Ley 25.326); click → `prefiere_no_recibir_email=true` + notificación al operario
- Yahoo DKIM/SPF ya configurado para cuentas `@yahoo.com`
- **App password de Yahoo** (no la contraseña personal) almacenada en `.env`

> **Nota para entregar al cliente:** Los rebotes repetidos (mails a direcciones inexistentes) dañan la reputación del remitente. Se recomienda mantener el maestro de clientes actualizado y revisar periódicamente la solapa "Rebotados" para depurar direcciones inválidas.

---

## 8. Frontend — pantallas y navegación

### Pantallas

| Pantalla | Descripción |
|----------|-------------|
| Login | Usuario + contraseña, sin 2FA |
| Nuevo Envío | Gestión del ciclo actual (pre-envío) |
| Seguimiento | Dashboard post-envío del ciclo activo |
| Maestro de clientes | Carga y gestión del Excel maestro |
| Plantilla | Editor de template + configuración de diseño + monto mínimo |
| Configuración | Credenciales Yahoo, datos de empresa |

### Sección 1 — Nuevo Envío

Tres solapas pre-envío:

```
[ Para enviar (72) ] [ Sin Email (5) ] [ Filtrados (3) ]
```

- **Para enviar:** lista de tarjetas con nombre, monto, localidad. Botón global "Enviar 72 mails".
- **Sin Email:** lista de deudores sin match en el maestro. Instrucción: "Actualizá el maestro y volvé a subir."
- **Filtrados:** lista con columna `motivo` — "Monto mínimo" o "Dado de baja" (este último con indicador visual diferenciado).

Pantalla de progreso (post-confirmación):
```
Enviando...  23 / 72
[████████░░░░░░░░] 32%
✓ Consorcio Belgrano 1234
✓ Admin Torres SA
⏳ Edificio Lavalle 890...
Tiempo estimado: ~4 minutos
```

### Sección 2 — Seguimiento

Cuatro solapas post-envío:

```
[ No contestados (65) ] [ Contestados (5) ] [ Pagos (2) ] [ Rebotados (1) ]
```

Cada tarjeta muestra: nombre, monto, localidad, fecha de envío. Al expandir (Contestados/Pagos): snippet de respuesta, fecha de respuesta, indicador de adjunto.

---

## 9. Template de mail

- **Formato:** HTML con estilos inline (compatible con Yahoo, Gmail, Outlook)
- **Configurable:** logo (upload), color primario, nombre de empresa, pie con datos de contacto
- **Variables disponibles:** `{{nombre}}`, `{{monto}}`, `{{localidad}}`, `{{clave_union}}`, `{{fecha_envio}}`
- **Footer fijo:** link de unsubscribe + dirección/teléfono de la empresa (configurable)
- **Generación:** Jinja2 en el backend; `premailer` para inlinear CSS antes del envío

---

## 10. Auth

- Login con usuario + contraseña
- JWT con expiración de 8 horas
- bcrypt (cost factor 12)
- Rate limiting en login: máximo 5 intentos por minuto por IP
- Un solo usuario operario en MVP (seed script)
- Sin 2FA, sin invite tokens, sin registro público

---

## 11. Pendientes bloqueantes

Estos ítems requieren información del cliente antes de implementarse:

- [ ] **Estructura exacta del Excel de deudores** — columnas, nombre de la clave de unión, formato de montos
- [ ] **Estructura exacta del Excel maestro** — confirmar si la clave de unión es `nro_cliente` u otro campo
- [ ] **App password de Yahoo** — el cliente debe generarla desde su cuenta Yahoo antes del deploy

---

## 12. Fuera de alcance (Fase 2 y 3)

### Fase 2
- Multi-plantillas por rango de monto (tono escalado según deuda)
- Uso de `ciclo_numero` para adaptar mensaje automáticamente
- Ver referencia de implementación en `Mails-finanzas`: `dj_engine.py` + `filtros_engine.py`

### Fase 3
- Integración API directa con sistema de facturación (reemplaza carga manual de Excel)
- Endpoint reservado: `POST /api/v1/ciclos/desde-api` → `HTTP 501 Not Implemented`
- Ver `docs/adr/0001-fase3-api-entry-point.md`

---

## 13. Costos operativos estimados

| Componente | Opción | Costo |
|------------|--------|-------|
| DB PostgreSQL | Neon free tier (~10 MB/año, límite 500 MB) | $0 |
| Backend hosting | Railway / Render starter | ~$5–10 USD/mes |
| Frontend hosting | Vercel / Netlify free tier | $0 |
| Dominio (opcional) | Namecheap / NIC Argentina | ~$15 USD/año |

**Total mensual estimado: $5–10 USD/mes**

El volumen de datos (600 clientes × 24 ciclos/año × ~500 bytes/envío) es ~7 MB/año. El free tier de Neon es suficiente por más de 10 años sin upgrade.
