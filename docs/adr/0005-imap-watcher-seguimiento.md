# ADR-0005: IMAP Watcher para seguimiento de respuestas

## Estado
Aceptado

## Contexto
El cliente quiere saber qué consorcios respondieron sus mails de cobro y cómo (confirmación de pago, promesa de pago, etc.). Se evaluaron: monitoreo manual (el cliente revisa su inbox), webhook (no disponible en Yahoo), y polling IMAP.

## Decisión
Background task asyncio que hace polling al inbox de Yahoo cada 10 minutos via IMAP (`imap.mail.yahoo.com:993`). Detecta respuestas cruzando el header `In-Reply-To` con los `message_id` de los Envios guardados en DB. La ventana de búsqueda es 30 días (cubre el ciclo activo y el inmediatamente anterior).

## Consecuencias
- **Positivo:** Tracking automático sin intervención del operario.
- **Positivo:** Detecta respuestas a mails de ciclos anteriores (si el consorcio tarda en responder).
- **Negativo:** No es tiempo real — hay hasta 10 minutos de latencia. Aceptable para este caso de uso.
- **Clasificación:** Adjunto (imagen/PDF) → PAGO; solo texto → CONTESTADO; mailer-daemon → REBOTADO.
- **Override manual:** El operario puede mover manualmente un Envio de CONTESTADO a PAGO desde el dashboard.
