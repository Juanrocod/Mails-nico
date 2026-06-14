# CONTEXT.md — Sistema de Gestión de Órdenes Bursátiles

## Propósito

Glosario canónico del dominio. Sin detalles de implementación.

---

## Términos del Dominio

### Orden
Una instrucción de compra o venta de un instrumento financiero generada a partir del Excel de operaciones. Unidad central del sistema. Una Orden tiene un único Cliente destinatario.

### Minuta
El mail que el sistema genera a partir de los datos de una Orden. Contiene todos los campos de la operación en texto plano, bien estructurado. Puede incluir una Declaración Jurada si corresponde.

### Excel de Operaciones
Archivo exportado por Middle Office desde la plataforma bursátil. Tiene estructura de columnas fija. Es el único punto de entrada de datos al sistema en Fase 1.

### Middle Office
La persona interna responsable de todo el flujo: descarga el Excel de la plataforma bursátil, lo sube al sistema, audita y corrige los borradores de Minuta en el Dashboard, y los envía manualmente al Cliente.

### Sales Trader
Actor externo al sistema en Fase 1. Ejecuta las operaciones en la plataforma bursátil. No interactúa directamente con este sistema en el MVP.

### Cliente
Persona o entidad que recibe la Minuta por mail. Debe confirmar la operación respondiendo el mail. Tiene un número de Cuenta Comitente y un número de Cuenta Cotapartista asociados.

### Cuenta Comitente
Número de cuenta del Cliente en el broker. Identifica al cliente en el sistema bursátil.

### Cuenta Cotapartista
Número de cuenta de la contraparte del Cliente en la operación. Figura en la Minuta.

### Declaración Jurada (DJ)
Texto legal que se incluye en la Minuta cuando la operación cumple ciertas condiciones regulatorias. Los templates y reglas de activación se definen por configuración. Puede ser activada automáticamente por el sistema o manualmente.

### Dashboard
Interfaz web de Middle Office. Organizada en solapas por estado de las Minutas. Permite auditar, editar, aprobar y enviar cada Minuta.

### Borrador
Estado inicial de una Minuta recién generada por el sistema a partir del Excel. Visible en el Dashboard, pendiente de revisión por Middle Office.

### Aprobación
Acción de Middle Office en el Dashboard que habilita el envío manual de una Minuta al Cliente. Queda registrada en el Audit Trail con usuario, timestamp e indicador de si el contenido fue editado.

### Confirmación
Respuesta del Cliente al mail de la Minuta, indicando su aceptación de la operación. En Fase 1 se registra manualmente. En Fase 2 se detecta automáticamente.

### Audit Trail
Registro inmutable de todas las acciones sobre una Orden: creación, aprobación, edición, envío, confirmación. Incluye usuario, IP y timestamp. Exportable a PDF/Excel.

### Plataforma Bursátil
Sistema externo del que Middle Office exporta el Excel de Operaciones. No tiene integración API en Fase 1.

---

## Estados de una Minuta

```
BORRADOR → APROBADO → ENVIADO → CONFIRMADO
                                     ↑
                              (Fase 2: automático)
                              (Fase 1: manual)
```

| Estado | Descripción |
|--------|-------------|
| BORRADOR | Generado por el sistema, pendiente de revisión |
| APROBADO | Revisado y aprobado por Middle Office, listo para envío manual |
| ENVIADO | Enviado al Cliente, esperando confirmación |
| CONFIRMADO | Cliente respondió confirmando la operación |
| ALERTA | Sin respuesta del Cliente después del umbral de tiempo definido |

---

## Campos de una Orden / Minuta

- Cliente (nombre)
- Mail del Cliente
- N° Cuenta Comitente
- N° Cuenta Cotapartista
- Instrumento financiero
- Tipo de operación (Compra / Venta)
- Cantidad
- Precio
- Moneda
- Condición de liquidación (24hs / 48hs / CI)
- Declaración Jurada (si corresponde)
- Fecha y hora de la operación

---

## Pendientes de Definición

- Estructura exacta de columnas del Excel (compartir modelo cuando esté disponible)
- Templates y reglas de activación de la Declaración Jurada
- Infraestructura de hosting (Azure, a confirmar con el broker)
- Integración con back-office / API de clientes (Fase futura)
