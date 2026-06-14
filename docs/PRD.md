# PRD — Sistema de Gestión de Órdenes Bursátiles (Fase 1 / MVP)

**Versión:** 1.0  
**Fecha:** 2026-06-13  
**Estado:** Listo para desarrollo

---

## Problem Statement

El proceso actual de autorización de órdenes bursátiles es completamente manual: Middle Office recibe el Excel de operaciones de la plataforma bursátil, redacta cada mail de minuta a mano, lo envía al Cliente y gestiona las confirmaciones sin ningún sistema de trazabilidad. Este proceso es lento, propenso a errores, no auditable formalmente y no escala con el volumen de operaciones. Ante una inspección de la CNV, no existe un registro estructurado de quién aprobó qué, cuándo, ni si el contenido del mail fue el correcto.

---

## Solution

Un sistema web que automatiza la generación de Minutas a partir del Excel exportado de la plataforma bursátil, centraliza la revisión y aprobación en un Dashboard de Middle Office, y mantiene un Audit Trail completo y exportable de todas las acciones sobre cada Orden.

En Fase 1 (MVP), el envío al Cliente sigue siendo manual. El sistema aporta generación automática de contenido, control de calidad centralizado y trazabilidad completa.

---

## User Stories

### Autenticación

1. Como Middle Office, quiero iniciar sesión con usuario, contraseña y segundo factor (2FA), para que solo usuarios autorizados accedan al sistema.
2. Como Middle Office, quiero que mi sesión expire automáticamente tras un período de inactividad, para reducir el riesgo de acceso no autorizado desde una terminal desatendida.
3. Como Middle Office, quiero recibir un mensaje claro si ingreso credenciales incorrectas, para saber si debo recuperar mi contraseña.
4. Como Middle Office, quiero poder cerrar sesión explícitamente desde cualquier pantalla, para proteger el acceso en equipos compartidos.

### Carga del Excel de Operaciones

5. Como Middle Office, quiero subir el Excel de operaciones exportado de la plataforma bursátil mediante un botón de carga en el sistema, para iniciar el flujo de generación de Minutas.
6. Como Middle Office, quiero que el sistema valide la estructura del Excel antes de procesarlo, para recibir un error claro si el archivo no tiene el formato esperado.
7. Como Middle Office, quiero ver un resumen de cuántas Órdenes fueron detectadas en el Excel antes de confirmar el procesamiento, para verificar que el archivo es correcto.
8. Como Middle Office, quiero que el sistema me informe si alguna fila del Excel tiene datos incompletos o inválidos, para poder corregir el archivo y volver a subirlo.
9. Como Middle Office, quiero que el sistema procese el Excel completo en una sola operación y genere todos los Borradores de Minuta en el Dashboard, para no tener que cargar las operaciones una por una.

### Dashboard — Gestión de Minutas

10. Como Middle Office, quiero ver todas las Minutas en estado BORRADOR en una solapa dedicada del Dashboard, para tener visibilidad inmediata de lo que está pendiente de revisión.
11. Como Middle Office, quiero ver el detalle completo de cada Minuta (cliente, instrumento, tipo, cantidad, precio, moneda, liquidación, cuentas, DJ si aplica) antes de aprobarla, para verificar que el contenido es correcto.
12. Como Middle Office, quiero editar el texto de la Minuta generada antes de aprobarla, para corregir cualquier error o agregar contexto adicional.
13. Como Middle Office, quiero que el sistema registre si edité una Minuta antes de aprobarla, para que quede constancia en el Audit Trail.
14. Como Middle Office, quiero aprobar una Minuta con un solo clic tras revisar su contenido, para habilitar su envío manual al Cliente.
15. Como Middle Office, quiero ver las Minutas aprobadas en una solapa separada del Dashboard, para distinguir claramente lo que está listo para enviar de lo que aún está pendiente.
16. Como Middle Office, quiero marcar manualmente una Minuta como ENVIADA una vez que la envié al Cliente desde mi cliente de correo, para mantener el estado del Dashboard actualizado.
17. Como Middle Office, quiero ver las Minutas en estado CONFIRMADO en una solapa dedicada, para tener visibilidad de qué operaciones ya tienen la autorización del Cliente.
18. Como Middle Office, quiero marcar manualmente una Minuta como CONFIRMADA cuando el Cliente responde el mail, para registrar la confirmación en el sistema.
19. Como Middle Office, quiero ver visualmente destacadas las Minutas que llevan más de 24 horas sin respuesta del Cliente, para identificar rápidamente los casos que requieren seguimiento.
20. Como Middle Office, quiero poder copiar el texto de la Minuta desde el Dashboard para pegarlo en mi cliente de correo, para agilizar el envío manual.

### Declaración Jurada

21. Como Middle Office, quiero que el sistema incluya automáticamente la Declaración Jurada correspondiente en la Minuta cuando la operación lo requiera, para no tener que redactarla manualmente.
22. Como Middle Office, quiero poder ver qué tipo de Declaración Jurada se incluyó en una Minuta, para verificar que sea la correcta antes de aprobar.
23. Como administrador del sistema, quiero poder configurar los templates de Declaración Jurada y las reglas de activación, para que el sistema los aplique automáticamente sin necesidad de modificar código.

### Audit Trail

24. Como Middle Office, quiero que cada acción sobre una Orden quede registrada automáticamente (creación, edición, aprobación, envío, confirmación), para disponer de un historial completo sin esfuerzo adicional.
25. Como Middle Office, quiero poder exportar el Audit Trail de una Orden o de un período a PDF o Excel, para presentarlo ante auditorías internas o inspecciones de la CNV.
26. Como Middle Office, quiero ver en el historial de una Minuta quién la aprobó y en qué momento, para identificar responsabilidades en caso de disputa.

### Seguridad y Accesos

27. Como administrador del sistema, quiero que todos los intentos de login (exitosos y fallidos) queden registrados con usuario, IP y timestamp, para detectar accesos sospechosos.
28. Como administrador del sistema, quiero que las credenciales y tokens de acceso estén almacenados de forma segura (cifrados), para minimizar el impacto ante una eventual brecha.

---

## Implementation Decisions

### Arquitectura General

- **Backend:** Python 3.12 + FastAPI. API REST con autenticación JWT.
- **Frontend:** React 18 + TypeScript. SPA con React Router para navegación entre solapas del Dashboard.
- **Base de datos:** PostgreSQL con cifrado de datos sensibles a nivel de columna para mails de clientes y números de cuenta.
- **Hosting:** Azure App Service (backend) + Azure Static Web Apps (frontend) + Azure Database for PostgreSQL. A confirmar con el broker. Ver ADR-0003.

### Módulos del Backend

| Módulo | Responsabilidad |
|--------|----------------|
| `auth` | Login, 2FA (TOTP), JWT, refresh tokens, log de accesos, expiración de sesión |
| `excel_parser` | Lectura y validación del Excel de Operaciones. Mapeo de columnas a modelo de Orden |
| `minuta_generator` | Generación de texto plano estructurado de la Minuta a partir de los datos de la Orden |
| `dj_engine` | Evaluación de reglas de activación de DJ y selección del template correspondiente |
| `orders` | CRUD de Órdenes y Minutas. Máquina de estados (BORRADOR→APROBADO→ENVIADO→CONFIRMADO→ALERTA) |
| `audit` | Registro inmutable de eventos. Generación de reportes PDF/Excel del Audit Trail |
| `dashboard_api` | Endpoints agregados para las solapas del Dashboard (Borradores, Aprobados, Enviados, Confirmados, Alertas) |

### Máquina de Estados de la Minuta

```
BORRADOR → APROBADO → ENVIADO → CONFIRMADO
                                     ↑
                              (Fase 1: transición manual)
                              (Fase 2: automática via Graph API)
```

Transiciones válidas:
- `BORRADOR` → `APROBADO` (Middle Office aprueba desde Dashboard)
- `APROBADO` → `ENVIADO` (Middle Office marca como enviado)
- `ENVIADO` → `CONFIRMADO` (Middle Office registra confirmación manual)
- `ENVIADO` → `ALERTA` (sistema marca automáticamente tras umbral de tiempo sin confirmación)
- `ALERTA` → `CONFIRMADO` (Middle Office registra confirmación manual)

No se permiten transiciones hacia atrás. Una Minuta aprobada no puede volver a BORRADOR — si tiene errores, Middle Office la edita antes de aprobar.

### Modelo de Datos — Orden

```
Orden {
  id: UUID
  excel_upload_id: UUID          # lote de carga al que pertenece
  cliente_nombre: string
  cliente_email: string (cifrado)
  cuenta_comitente: string (cifrado)
  cuenta_cotapartista: string (cifrado)
  instrumento: string
  tipo: enum(COMPRA, VENTA)
  cantidad: decimal
  precio: decimal
  moneda: string
  liquidacion: enum(CI, 24HS, 48HS)
  fecha_operacion: datetime
  dj_aplicada: boolean
  dj_tipo: string | null
  estado: enum(BORRADOR, APROBADO, ENVIADO, CONFIRMADO, ALERTA)
  texto_minuta: text             # generado por minuta_generator, editable por Middle Office
  texto_editado: boolean         # true si Middle Office modificó el texto generado
  creado_en: datetime
  actualizado_en: datetime
}
```

### Modelo de Datos — Evento de Audit Trail

```
AuditEvent {
  id: UUID
  orden_id: UUID
  usuario_id: UUID
  accion: enum(CREADA, EDITADA, APROBADA, ENVIADA, CONFIRMADA, ALERTA_GENERADA)
  ip_origen: string
  timestamp: datetime
  detalle: json | null           # metadata adicional (ej: campos editados)
}
```

### Modelo de Datos — Lote de Carga (ExcelUpload)

```
ExcelUpload {
  id: UUID
  usuario_id: UUID
  nombre_archivo: string
  total_ordenes: int
  ordenes_validas: int
  ordenes_con_error: int
  creado_en: datetime
}
```

### Seguridad

- JWT con expiración de 8 horas (horario de mercado). Refresh token de 24 horas.
- 2FA con TOTP (Google Authenticator / Authy compatible). Obligatorio para todos los usuarios.
- Datos sensibles (email del cliente, números de cuenta) cifrados a nivel de columna en PostgreSQL.
- Contraseñas hasheadas con bcrypt (cost factor 12).
- Rate limiting en endpoints de login (máximo 5 intentos por minuto por IP).
- Log de todos los intentos de acceso (usuario, IP, timestamp, resultado).

### Generación de Minuta

El texto de la Minuta se genera en texto plano estructurado con todos los campos de la Orden. El formato sigue el estándar de minutas bursátiles, incluyendo fecha y hora de la operación, datos del cliente (nombre y cuentas), detalle del instrumento, precio, cantidad y condición de liquidación. Si aplica DJ, se incluye el texto completo del template configurado al final de la Minuta.

### Excel de Operaciones

- Estructura de columnas fija (a definir cuando el broker comparta el modelo).
- El parser valida columnas obligatorias, tipos de datos y rangos válidos antes de procesar.
- Las filas con errores se reportan individualmente sin bloquear el procesamiento de las filas válidas.
- Ver ADR-0001 para la decisión de usar Excel vs API directa.

### Templates de Declaración Jurada

- Almacenados en base de datos, editables por administrador sin deployar código.
- Cada template tiene: nombre, texto, y conjunto de reglas de activación (instrumento, moneda, tipo de operación, umbral de monto).
- El `dj_engine` evalúa las reglas en orden de prioridad y aplica el primer template que matchea.

---

## Testing Decisions

### Qué hace un buen test en este sistema

Un buen test verifica comportamiento observable externo, no implementación interna. Para este sistema, eso significa:

- Testear la API REST (endpoints, códigos HTTP, estructura de respuesta, estados de la Minuta)
- Testear el parser de Excel con archivos reales o fixtures que representen casos válidos e inválidos
- Testear la máquina de estados (transiciones válidas, transiciones inválidas rechazadas)
- Testear el generador de Minutas (campos correctos en el texto, inclusión/exclusión de DJ)
- NO testear detalles de implementación interna (qué función llama a qué, estructura de clases)

### Módulos a testear

| Módulo | Tipo de test | Prioridad |
|--------|-------------|-----------|
| `excel_parser` | Unit — fixtures de Excel válidos e inválidos | Alta |
| `minuta_generator` | Unit — snapshots de texto generado | Alta |
| `orders` (máquina de estados) | Unit — transiciones válidas e inválidas | Alta |
| `dj_engine` | Unit — reglas de activación con casos límite | Alta |
| `dashboard_api` | Integration — endpoints con DB de test | Alta |
| `auth` | Integration — login, 2FA, expiración de sesión | Media |
| `audit` | Integration — eventos generados por cada acción | Media |

### Cobertura mínima esperada

- Todas las transiciones de estado de la Minuta tienen test
- Todos los endpoints del Dashboard tienen test de integración
- El parser de Excel tiene tests para: archivo válido, columna faltante, tipo de dato incorrecto, fila vacía

---

## Out of Scope (Fase 1)

- Envío automático de mails via Microsoft Graph API
- Monitoreo de respuestas entrantes de Clientes
- Detección automática de Confirmaciones
- Alertas automáticas de seguimiento por falta de respuesta del Cliente
- Integración con sistema de back-office del broker para sincronización de Clientes
- Integración API directa con la plataforma bursátil (reemplazar carga de Excel)
- Roles adicionales (Admin, Compliance, Gerencia)
- Notificaciones al Sales Trader
- Aplicación mobile

Ver `docs/pasos-automatizacion-posterior.md` para el roadmap de Fase 2.

---

## Further Notes

- La estructura exacta de columnas del Excel queda pendiente hasta que el broker comparta el archivo modelo. El parser debe ser adaptable sin cambiar la lógica de negocio.
- Los templates de Declaración Jurada y sus reglas de activación se cargarán por configuración una vez que el broker los defina.
- La infraestructura de Azure debe confirmarse con el broker antes del deploy a producción. El desarrollo local no tiene dependencias de Azure.
- El sistema está diseñado para ser monousuario en Fase 1 (un único usuario Middle Office), pero la arquitectura de roles debe soportar la expansión futura sin refactoring.
- Ante una inspección de CNV, el Audit Trail exportable a PDF es el artefacto de compliance principal del sistema.
