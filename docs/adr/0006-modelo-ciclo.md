# ADR-0006: Modelo de Ciclo como unidad de trabajo

## Estado
Aceptado

## Contexto
El operario sube un Excel de deudores cada ~15 días. Se evaluaron: sobrescribir los datos en cada carga (stateless), mantener una única lista activa (reemplazar), y el modelo de ciclos con historial.

## Decisión
Cada carga de Excel confirmada crea un nuevo Ciclo en DB. Los Envios del ciclo anterior se archivan (ciclo.activo = false) pero no se borran. El dashboard muestra únicamente los Envios del Ciclo activo.

## Consecuencias
- **Positivo:** El IMAP Watcher puede seguir detectando respuestas a mails de ciclos anteriores (hasta 30 días).
- **Positivo:** El campo `ciclo_numero` en Envio permite calcular cuántos ciclos consecutivos estuvo un consorcio como deudor sin responder — base para la escalada de tono de Fase 2.
- **Positivo:** Preview de Excel no escribe nada en DB; solo la confirmación crea el Ciclo. El operario puede re-subir el Excel N veces sin efectos secundarios.
- **Neutro:** El volumen de datos es mínimo (~7 MB/año); no hay preocupación de storage.
- **UI:** El operario no ve datos de ciclos anteriores en el dashboard; si necesita consultar historial es una feature de Fase 2.
