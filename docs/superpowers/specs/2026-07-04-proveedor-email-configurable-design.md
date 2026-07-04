# Spec — Proveedor de email configurable (Yahoo / Gmail)

**Fecha:** 2026-07-04
**Estado:** Aprobado — listo para planificación de implementación
**Relacionado:** ADR-0005 (IMAP Watcher), `docs/PENDIENTES.md` #2 (Configuración incompleta)

---

## 1. Problema

Hoy el sistema tiene el proveedor de email (Yahoo) hardcodeado en dos lugares: `smtp_sender.py` (`smtp.mail.yahoo.com:587`) e `imap_watcher.py` (`imap.mail.yahoo.com:993`). Las credenciales se resuelven vía `config_service.get_yahoo_credentials(db)`, con la DB (`ConfiguracionSistema`) como fuente primaria y `.env` como fallback.

Motivo inmediato: el desarrollador no puede obtener un app password de Yahoo en su cuenta (creada recientemente) y necesita poder testear el flujo completo (envío + tracking de respuestas) usando Gmail en su entorno local.

Motivo adicional, de valor permanente: el Operario final va a usar Yahoo, pero puede en el futuro querer usar un mail dedicado en Gmail, o verse forzado a cambiar de proveedor si tiene problemas con la cuenta de Yahoo. Conviene que el cambio de proveedor sea una acción de configuración del Operario (vía UI), no un cambio de código ni de variables de entorno.

---

## 2. Solución

Se agrega Gmail como segundo proveedor soportado, seleccionable desde la página de Configuración (`GET/PUT /configuracion/proveedor`), con sus propias credenciales (`GET/PUT /configuracion/gmail`), replicando exactamente el patrón que ya existe para Yahoo (`GET/PUT /configuracion/yahoo`). El sistema ejecuta un único proveedor a la vez — el que esté marcado como activo en `ConfiguracionSistema.proveedor_activo` — nunca ambos en simultáneo. Yahoo sigue siendo el default y su comportamiento actual queda sin modificar: si nadie toca nada, el sistema se comporta exactamente igual que hoy.

**No objetivo:** no se construye una arquitectura de plugins ni soporte para proveedores arbitrarios. Son dos proveedores conocidos (Yahoo, Gmail), con una tabla de configuración estática de dos filas (host/puerto SMTP e IMAP) y un flag que indica cuál está activa.

---

## 3. Arquitectura

### Componente nuevo: `app/core/email_providers.py`

Registro estático, sin I/O, con la configuración de host/puerto de cada proveedor:

```python
@dataclass(frozen=True)
class ProviderConfig:
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    message_id_domain: str

PROVIDERS: dict[str, ProviderConfig] = {
    "yahoo": ProviderConfig("smtp.mail.yahoo.com", 587, "imap.mail.yahoo.com", 993, "yahoo.com"),
    "gmail": ProviderConfig("smtp.gmail.com", 587, "imap.gmail.com", 993, "gmail.com"),
}
DEFAULT_PROVIDER = "yahoo"
```

### Modelo de datos

`ConfiguracionSistema` (tabla ya existente, se agregan columnas — migración Alembic nueva con `batch_alter_table`):

```python
proveedor_activo               = Column(String(20), nullable=False, default="yahoo")
gmail_email                    = Column(String(255), nullable=True)
gmail_app_password_encrypted   = Column(String(512), nullable=True)
```

No se renombra ni se elimina ninguna columna existente. `yahoo_email` y `yahoo_app_password_encrypted` quedan exactamente como están.

### `config_service.py` — funciones nuevas (las existentes no se tocan)

| Función | Comportamiento |
|---------|----------------|
| `get_active_provider(db) -> str` | Lee `proveedor_activo`. Si el valor no está en `PROVIDERS` (dato corrupto/manual), loggea un warning y devuelve `DEFAULT_PROVIDER` ("yahoo"). |
| `save_active_provider(db, proveedor: str) -> ConfiguracionSistema` | Guarda `proveedor_activo`. El router valida contra `Literal["yahoo", "gmail"]` antes de llamar a esta función, así que acá no hace falta revalidar. |
| `get_gmail_credentials(db) -> tuple[str, str]` | Mismo patrón que `get_yahoo_credentials`: si hay `gmail_email` + `gmail_app_password_encrypted` en DB, los devuelve descifrados; si no, cae a `settings.GMAIL_EMAIL` / `settings.GMAIL_APP_PASSWORD` del `.env` (valor semilla opcional, igual que hoy con Yahoo). |
| `save_gmail_credentials(db, gmail_email, gmail_app_password) -> ConfiguracionSistema` | Análogo a `save_yahoo_credentials`, cifra con el mismo Fernet (`ENCRYPTION_KEY`). |
| `get_active_credentials(db) -> tuple[str, str]` | Dispatcher: según `get_active_provider(db)`, delega en `get_yahoo_credentials(db)` o `get_gmail_credentials(db)`. |

### `app/core/config.py`

Se agregan dos settings opcionales (valor semilla para Gmail, igual rol que `YAHOO_EMAIL`/`YAHOO_APP_PASSWORD` hoy):

```python
GMAIL_EMAIL: str = ""
GMAIL_APP_PASSWORD: str = ""
```

No se agrega ninguna variable `EMAIL_PROVIDER` — la fuente de verdad de cuál proveedor está activo es la base de datos (`proveedor_activo`), no el entorno.

### `smtp_sender.py`

- `enviar_ciclo`: en vez de leer `config_service.get_yahoo_credentials(db)` directo, resuelve `provider = email_providers.PROVIDERS[config_service.get_active_provider(db)]` y `from_email, app_password = config_service.get_active_credentials(db)`.
- `_send_single_email` recibe `smtp_host: str, smtp_port: int` como parámetros en vez de tener `"smtp.mail.yahoo.com", 587` hardcodeado.
- El `Message-ID` generado (`smtp_sender.py:61`) usa `provider.message_id_domain` en vez de `@yahoo.com` fijo (cosmético, para que el dominio en los logs sea coherente con el proveedor real usado).

### `imap_watcher.py`

- `_poll_inbox`: resuelve el mismo `provider = email_providers.PROVIDERS[config_service.get_active_provider(db)]` y usa `provider.imap_host, provider.imap_port` en vez del string hardcodeado. Reemplaza el llamado a `config_service.get_yahoo_credentials(db)` por `config_service.get_active_credentials(db)`.
- `reply_classifier.classify()` no cambia — ya es agnóstico al proveedor (solo mira headers MIME estándar y el patrón `mailer-daemon`/`postmaster`, presente en cualquier proveedor IMAP estándar).

### API — `routers/configuracion.py`

Se agregan tres endpoints; `GET/PUT /configuracion/yahoo` queda sin cambios:

| Endpoint | Request | Response |
|----------|---------|----------|
| `GET /configuracion/proveedor` | — | `{"proveedor": "yahoo" \| "gmail"}` |
| `PUT /configuracion/proveedor` | `{"proveedor": "yahoo" \| "gmail"}` | `{"proveedor": "yahoo" \| "gmail"}` |
| `GET /configuracion/gmail` | — | `{"gmail_email": str \| null, "configurado": bool}` |
| `PUT /configuracion/gmail` | `{"gmail_email": str, "gmail_app_password": str}` | `{"gmail_email": str, "configurado": true}` |

Todos requieren `current_user` (mismo `Depends(get_current_user)` que ya usa `/configuracion/yahoo`). `PUT /configuracion/proveedor` valida el valor contra `Literal["yahoo", "gmail"]` en el schema Pydantic — un valor fuera de esa lista devuelve `422` automático de FastAPI, sin lógica manual.

### Schemas — `schemas/configuracion.py`

```python
class ConfiguracionGmailRequest(BaseModel):
    gmail_email: EmailStr
    gmail_app_password: str = Field(min_length=1)

class ConfiguracionGmailResponse(BaseModel):
    gmail_email: Optional[str] = None
    configurado: bool
    model_config = {"from_attributes": True}

class ConfiguracionProveedorRequest(BaseModel):
    proveedor: Literal["yahoo", "gmail"]

class ConfiguracionProveedorResponse(BaseModel):
    proveedor: Literal["yahoo", "gmail"]
```

### Frontend

**`types/domain.ts`** — se agrega:
```ts
type ProveedorEmail = "yahoo" | "gmail"
interface ConfiguracionProveedor { proveedor: ProveedorEmail }
interface ConfiguracionGmail { gmail_email: string | null; configurado: boolean }
```

**`services/configuracion.ts`** — se agregan `getProveedorActivo`, `updateProveedorActivo`, `getConfiguracionGmail`, `updateConfiguracionGmail`, mismo patrón que las funciones de Yahoo existentes (usa `apiFetch`, lanza `Error` con `detail` del backend en fallos).

**`ConfiguracionPage.tsx`**:
- Se agrega arriba de todo un `<select>` "Proveedor de email" (Yahoo / Gmail). Al cambiar de opción, guarda inmediatamente vía `updateProveedorActivo` (no requiere botón aparte) y muestra un status inline ("Guardado").
- Debajo, se muestra **solo** el bloque de credenciales correspondiente al proveedor seleccionado en el `<select>` (Yahoo o Gmail), reutilizando la estructura visual ya existente (label + Input email + Input password + botón "Guardar" + mensaje de estado). Cambiar de proveedor desmonta el bloque anterior y monta el otro con los inputs vacíos (salvo el email, que se repuebla desde `getConfiguracionYahoo`/`getConfiguracionGmail` si ya estaba guardado) — mismo comportamiento que ya tiene hoy el campo de password de Yahoo, que se limpia después de cada guardado exitoso.
- Carga inicial: `useEffect` pide `getProveedorActivo()` para saber qué bloque mostrar por default, además de los `getConfiguracionYahoo()`/`getConfiguracionGmail()` existentes para poblar el estado "configurado".

---

## 4. Flujo

1. Operario entra a Configuración → ve el proveedor activo actual (default: Yahoo) y, debajo, el formulario de credenciales de ese proveedor.
2. Si cambia el `<select>` a Gmail, el sistema guarda `proveedor_activo="gmail"` de inmediato y muestra el formulario de credenciales de Gmail (vacío si nunca se cargó nada, o el email ya guardado si existe).
3. Carga mail + app password de Gmail → `PUT /configuracion/gmail` → se cifra y guarda en DB.
4. A partir de ese momento, `smtp_sender` e `imap_watcher` resuelven host/puerto/credenciales de Gmail en cada envío/poll, sin reiniciar el server (la resolución es por-request/por-poll, no hay estado cacheado en memoria de proceso).
5. Para volver a Yahoo: cambiar el `<select>` de nuevo — las credenciales de Yahoo guardadas previamente no se pierden ni se sobreescriben, quedan en sus propias columnas.

---

## 5. Manejo de errores

- `proveedor_activo` con valor inesperado en DB (no debería pasar porque el endpoint valida con `Literal`, pero es defensivo ante edición manual de DB): `get_active_provider` cae a `"yahoo"` con `log.warning`, nunca rompe el envío/poll.
- Credenciales faltantes o inválidas para el proveedor activo (Gmail sin app password cargado, por ejemplo): el error de autenticación SMTP/IMAP sale por el mismo `try/except` que ya maneja esto hoy para Yahoo — no se agrega manejo especial nuevo.
- Nota operativa (no requiere código): Gmail exige tener verificación en 2 pasos activada en la cuenta de Google para poder generar un "App Password" — análogo al app password de Yahoo. Esto va en la ayuda visual de la UI (placeholder del input), igual que hoy el campo de Yahoo aclara "no la contraseña normal".

---

## 6. Testing

- `test_config_service.py`: agregar casos para `get_active_provider` (default yahoo, fallback ante valor inválido), `save_active_provider`, `get_gmail_credentials`/`save_gmail_credentials` (round-trip cifrado), `get_active_credentials` (dispatch correcto según proveedor).
- `test_configuracion_router.py`: agregar casos para los 3 endpoints nuevos — auth requerida (401 sin token), guardado exitoso, `422` ante `proveedor` inválido en el PUT.
- `test_smtp_sender.py` / tests de `imap_watcher` (si existen): no requieren cambios — mockean `_send_single_email` completo y no dependen del host real; el comportamiento default (`proveedor_activo="yahoo"` si la fixture de DB no lo setea) mantiene los tests existentes verdes sin tocarlos.

---

## 7. Fuera de alcance

- Soporte para proveedores más allá de Yahoo/Gmail (Outlook, IMAP genérico, etc.) — no hay ningún requerimiento concreto hoy.
- OAuth2 para Gmail — se usa app password (requiere 2FA activado en la cuenta de Google), igual mecanismo que Yahoo. Si Google deja de permitir app passwords en el futuro, es un problema aparte.
- Notificación o alerta si falla el envío/poll por credenciales mal cargadas — ya es una limitación existente del sistema con Yahoo, no se resuelve acá.
