# Pasos de Automatización Posterior (Fase 2)

Funcionalidades fuera del alcance del MVP que deben implementarse una vez validada la Fase 1.

---

## 1. Envío Automático de Minutas via Microsoft Graph API

**Prerequisito:** Acceso a la cuenta Microsoft 365 del broker y configuración de permisos en Azure AD.

- Al aprobar una Minuta en el Dashboard, el sistema envía el mail automáticamente al Cliente
- El mail queda en la bandeja de enviados del broker para trazabilidad
- Se registra en el Audit Trail: timestamp de envío, dirección de destino, ID del mensaje

---

## 2. Monitoreo de Respuestas Entrantes del Cliente

**Prerequisito:** Permisos de lectura de bandeja de entrada en Microsoft Graph API.

- El sistema monitorea la casilla de correo del broker en busca de respuestas de Clientes
- Polling o webhook según las capacidades del tenant de Microsoft 365
- Detecta respuestas vinculadas a Minutas enviadas (por hilo de conversación o referencia de orden)

---

## 3. Detección Automática de Confirmaciones

- El sistema analiza el contenido de la respuesta del Cliente
- Detecta frases de confirmación ("confirmo", "de acuerdo", "autorizo", etc.)
- Marca la Minuta como CONFIRMADA automáticamente
- Notifica a Middle Office en el Dashboard
- Para respuestas ambiguas, Middle Office puede confirmar manualmente desde el Dashboard

---

## 4. Alertas de Seguimiento por Falta de Respuesta

- Si un Cliente no responde dentro de un umbral configurable (ej: 24hs hábiles), la Minuta se marca con estado ALERTA en el Dashboard
- Middle Office recibe notificación visual en el Dashboard (color diferenciado)
- Middle Office gestiona el seguimiento manualmente (llamada, reenvío, etc.)

---

## 5. Integración con Sistema de Back-Office del Broker

**Prerequisito:** Negociar acceso API con el broker (sistema Núcleo, FIRE u otro).

- Los datos de Clientes (nombre, mail, cuentas) se sincronizan desde el back-office como fuente de verdad
- Elimina la gestión manual de clientes en el sistema
- Reemplaza la opción A (carga manual) por la opción B (sincronización automática)

---

## 6. Integración API con la Plataforma Bursátil

**Prerequisito:** Acceso API a la plataforma bursátil del broker.

- Las Órdenes ingresan automáticamente al sistema desde la plataforma, sin necesidad de exportar/subir Excel
- Reemplaza el flujo de carga de Excel por sincronización en tiempo real

---

## Notas

- Cada paso de esta lista es independiente y puede implementarse en cualquier orden
- La arquitectura del MVP está diseñada para incorporar estos pasos sin reestructuración mayor
- Consultar los ADRs correspondientes antes de iniciar cada integración
