# ADR-0001: Excel como entrada de datos

## Estado
Aceptado

## Contexto
Los deudores se originan en el sistema de facturación del cliente. Se evaluaron dos alternativas: integración API directa con el sistema de facturación, o carga manual de Excel exportado.

## Decisión
El sistema acepta dos Excels como entrada: uno de deudores (carga periódica ~15 días) y uno maestro de clientes (carga estable). No hay integración API con el sistema de facturación en Fase 1.

## Consecuencias
- **Positivo:** Implementación rápida sin negociar acceso API con el sistema de facturación.
- **Positivo:** El operario ya conoce el proceso de exportar el Excel — curva de adopción mínima.
- **Negativo:** Dependencia de que el formato del Excel no cambie entre versiones del sistema de facturación.
- **Futuro (Fase 3):** El endpoint `POST /ciclos/desde-api` está reservado para reemplazar la carga de Excel por integración directa. Ver ADR-0007.
