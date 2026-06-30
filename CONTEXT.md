# CONTEXT.md — Sistema de Cobro Automático por Mail

## Propósito

Glosario canónico del dominio. Sin detalles de implementación.

---

## Términos del Dominio

### Consorcio
Cliente de la empresa de mantenimiento de ascensores. Unidad destinataria de los mails de cobro. Tiene un nombre, un mail de contacto y una clave de unión que lo identifica en el sistema de facturación del cliente.

### Deudor
Un Consorcio que aparece en el Excel de deudores de un ciclo determinado. Tiene un monto adeudado y puede recibir un mail de recordatorio de cobro.

### Maestro de Clientes
Tabla persistente en la DB que contiene los datos de todos los Consorcios: clave de unión, nombre, mail, y estado de baja voluntaria. Es la fuente de verdad para los mails. Se actualiza cuando el operario sube el Excel maestro.

### Excel de Deudores
Archivo exportado del sistema de facturación del cliente. Contiene la lista de Consorcios que deben dinero en ese momento, con su monto. Se sube cada ~15 días para iniciar un nuevo Ciclo. Estructura a confirmar con el cliente.

### Excel Maestro
Archivo con la lista completa de Consorcios y sus mails. Relativamente estable; se sube una vez y se actualiza solo cuando cambian datos de clientes.

### Ciclo
Unidad de trabajo del sistema. Cada vez que el operario sube un Excel de deudores y confirma el envío, se crea un nuevo Ciclo. Solo hay un Ciclo activo a la vez. Los Ciclos anteriores se archivan pero sus Envios se conservan en la DB para tracking histórico.

### Preview
Resultado del procesamiento del Excel de deudores antes de confirmar el envío. Se calcula en memoria y muestra cuántos Envios quedan para enviar, cuántos no tienen mail y cuántos están filtrados. Nada se guarda en DB durante el preview.

### Envio
Registro de un mail a un Deudor dentro de un Ciclo. Tiene un estado, el `message_id` SMTP para tracking IMAP, y el snippet de respuesta si la hubo. Es la unidad central de seguimiento del sistema.

### Plantilla
Template HTML configurable del mail de cobro. Contiene asunto, cuerpo con variables, diseño (logo, color primario, nombre empresa) y el monto mínimo de filtrado. Variables disponibles: `{{nombre}}`, `{{monto}}`, `{{localidad}}`, `{{clave_union}}`, `{{fecha_envio}}`.

### Rate Limiting SMTP
Restricción de velocidad de envío impuesta por diseño: 5 mails cada 30 segundos. Evita que Yahoo bloquee la cuenta por envío masivo.

### IMAP Watcher
Proceso de background que hace polling al inbox de Yahoo cada 10 minutos para detectar respuestas a los Envios enviados. Usa el header `In-Reply-To` / `References` para vincular respuestas con Envios por `message_id`.

### Reply Classifier
Módulo que analiza cada respuesta detectada por el IMAP Watcher y determina su tipo: con adjunto (imagen o PDF) → PAGO, texto solo → CONTESTADO, remitente mailer-daemon/postmaster → REBOTADO.

### Rebote
Mail que no pudo ser entregado. El servidor destino envía un aviso automático al remitente (desde `mailer-daemon` o `postmaster`). El IMAP Watcher lo detecta y marca el Envio como REBOTADO. Los rebotes no se reintentan.

### Dado de Baja
Consorcio que clickeó el link de unsubscribe en un mail recibido. El flag `prefiere_no_recibir_email` se setea en el Maestro de Clientes y nunca se sobreescribe con uploads futuros. En cada nuevo Ciclo, estos Consorcios van automáticamente a FILTRADO con motivo DADO_DE_BAJA.

### ciclo_numero
Campo en Envio que registra en cuántos ciclos consecutivos ese Consorcio estuvo como deudor sin contestar. Base de datos para la funcionalidad de multi-plantilla de Fase 2 (escalado de tono según historial).

### Operario
El único usuario del sistema en el MVP. Dueño de la empresa de mantenimiento de ascensores. Gestiona el maestro, sube los Excels de deudores y supervisa el seguimiento de respuestas.

---

## Estados de un Envio

```
NO_CONTESTADO → CONTESTADO  (respuesta sin adjunto detectada por IMAP Watcher)
NO_CONTESTADO → PAGO        (respuesta con adjunto detectada por IMAP Watcher)
NO_CONTESTADO → REBOTADO    (bounce de mailer-daemon detectado por IMAP Watcher)
CONTESTADO    → PAGO        (override manual del Operario desde el dashboard)
```

Estados especiales (registrados en DB al confirmar el envío, sin mail enviado):

| Estado | Motivo |
|--------|--------|
| `FILTRADO` / `MONTO_MINIMO` | Monto debajo del umbral configurado en Plantilla |
| `FILTRADO` / `DADO_DE_BAJA` | Consorcio con `prefiere_no_recibir_email = true` |
| `SIN_EMAIL` | Clave de unión del Excel sin match en Maestro de Clientes |

---

## Secciones del Dashboard

| Sección | Solapas |
|---------|---------|
| Nuevo Envío | Para enviar · Sin Email · Filtrados |
| Seguimiento | No contestados · Contestados · Pagos · Rebotados |

---

## Pendientes de Definición

- Columnas exactas y nombre de la clave de unión del Excel de deudores
- Columnas exactas y nombre de la clave de unión del Excel maestro
- App password de Yahoo del cliente (generada desde la cuenta Yahoo)
