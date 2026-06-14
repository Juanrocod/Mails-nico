# ADR-0002: Envío de mails manual en Fase 1, automatización en Fase 2

## Estado
Aceptado

## Contexto
El sistema necesita enviar Minutas por mail a los Clientes. La integración con Microsoft 365 via Graph API es posible pero agrega complejidad al MVP. La demo inicial no requiere conexión real a mail.

## Decisión
En Fase 1, Middle Office envía los mails manualmente desde su cliente de correo. El sistema genera el contenido de la Minuta y lo deja disponible en el Dashboard. No hay conexión directa a ningún servidor de mail en el MVP.

## Consecuencias
- **Positivo:** La demo funciona sin configurar credenciales ni permisos de Microsoft 365.
- **Positivo:** Reduce riesgos de seguridad en la etapa de desarrollo inicial.
- **Negativo:** El proceso sigue siendo parcialmente manual. Middle Office debe copiar/pegar o usar el mail generado como referencia.
- **Futuro:** Fase 2 integra Microsoft Graph API para envío automático al aprobar, monitoreo de respuestas entrantes y detección automática de Confirmaciones.
