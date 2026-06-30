# ADR-0002: Envío automático vía Yahoo SMTP

## Estado
Aceptado

## Contexto
El cliente necesita enviar mails de cobro a ~600 consorcios cada ~15 días. Actualmente lo hace manualmente. Se evaluaron: envío manual (copia texto + pega en cliente de correo), servicio transaccional (SendGrid/Mailgun), y envío automático desde la cuenta Yahoo del cliente.

## Decisión
Envío automático desde la cuenta Yahoo del cliente usando SMTP (`smtp.mail.yahoo.com:587`). El cliente quiere que los mails salgan desde su propia cuenta para poder ver y gestionar las respuestas directamente.

## Consecuencias
- **Positivo:** Las respuestas llegan a la bandeja del cliente, donde el IMAP Watcher también las monitorea.
- **Positivo:** Los consorcios ven el mail de una dirección conocida, no de un servicio tercero.
- **Negativo:** Yahoo tiene límites de envío diario; mitigado con rate limiting de 5 mails / 30 segundos.
- **Negativo:** Requiere App Password de Yahoo (no la contraseña personal) — paso de configuración inicial.
- **Restricción innegociable:** El rate limiting (5/30s) no puede saltearse bajo ninguna circunstancia para evitar que Yahoo bloquee la cuenta.
