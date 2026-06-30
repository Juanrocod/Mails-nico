# ADR-0007: Endpoint stub para integración API en Fase 3

## Estado
Aceptado — pendiente de implementación

## Contexto
En Fase 3, el sistema de facturación del cliente podría enviar los deudores directamente via API, reemplazando la carga manual de Excel. Para no tener que refactorizar las rutas cuando llegue ese momento, se reserva el endpoint desde el MVP.

## Decisión
El endpoint `POST /ciclos/desde-api` existe en el router pero retorna `HTTP 501 Not Implemented`. Tiene la firma esperada documentada en el código como comentario.

## Referencia de implementación futura
Cuando se implemente en Fase 3, este endpoint debe:
1. Recibir la lista de deudores en JSON (misma estructura que `EnvioParsed`)
2. Ejecutar el mismo flujo que la confirmación del ciclo (excel_joiner → smtp_sender)
3. Opcionalmente recibir parámetros de filtrado y plantilla

## Consecuencias
- **Positivo:** La integración Fase 3 no requiere cambios en rutas ni en el frontend.
- **Neutro:** El endpoint retorna 501 claramente; no hay riesgo de uso accidental.
