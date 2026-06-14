# ADR-0001: Excel como único punto de entrada de datos en Fase 1

## Estado
Aceptado

## Contexto
Las órdenes bursátiles se originan en una plataforma bursátil externa. Middle Office descarga el Excel de operaciones de esa plataforma y necesita un mecanismo para ingresarlo al sistema. Se evaluaron dos alternativas: integración API directa con la plataforma, o carga manual de Excel.

## Decisión
El sistema acepta un Excel de estructura fija como único punto de entrada en Fase 1. No hay integración API con la plataforma bursátil.

## Consecuencias
- **Positivo:** Implementación simple y rápida para el MVP. No requiere negociar acceso API con la plataforma bursátil.
- **Positivo:** Middle Office ya conoce el proceso de exportar el Excel — curva de adopción mínima.
- **Negativo:** Dependencia de que el formato del Excel no cambie. Si la plataforma cambia columnas, hay que actualizar el parser.
- **Futuro:** Cuando el broker confirme acceso a la API de la plataforma, se puede reemplazar la carga de Excel por sincronización automática sin cambiar el resto del sistema.
