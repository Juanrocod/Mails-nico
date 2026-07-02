# Product

## Register

product

## Users

El Operario: dueño de una empresa de mantenimiento de ascensores, único usuario del sistema (sin equipos, sin roles). Lo usa en jornada de trabajo, no en un momento de descubrimiento o venta — abre la herramienta para ejecutar una tarea concreta cada ~15 días (subir el Excel de deudores y confirmar el envío) y para revisar el estado de cobros el resto del tiempo. Es un usuario recurrente y experto en su propio flujo, no alguien que necesita ser guiado o convencido.

## Product Purpose

Automatizar el envío de recordatorios de deuda a consorcios clientes por mail y dar seguimiento a las respuestas (pagos, contestados, rebotes) sin que el operario tenga que hacerlo manualmente mail por mail. Éxito = el operario puede, en minutos, ver cuánto tiene para enviar, confirmar el envío, y después seguir el estado de cobro de cada consorcio sin ambigüedad.

## Brand Personality

Profesional y sobria. Es una herramienta administrativa/contable de uso diario, no un producto que necesita venderse a sí mismo. Prioriza claridad y velocidad de lectura de datos (montos, estados, conteos) por sobre personalidad visual. Tono: seria, confiable, sin fricción — como un buen sistema de gestión, no como un dashboard de SaaS.

## Anti-references

- Nada de "plantilla de dashboard SaaS": sin cards idénticas repetidas, sin gradientes decorativos, sin hero-metrics con degradé.
- Nada colorido o juguetón — es una herramienta de cobro de deuda, la seriedad importa (le habla, indirectamente, a consorcios que deben plata).
- Nada de densidad decorativa que compita con los datos: el monto adeudado y el estado de cada consorcio son lo único que importa en cada pantalla.

## Design Principles

1. **Los números mandan.** Montos, conteos y estados son la información que el operario necesita leer de un vistazo; todo lo demás (color, forma, espaciado) está para ordenar esa lectura, no para llamar la atención sobre sí mismo.
2. **Cero fricción en la tarea recurrente.** El flujo subir → preview → confirmar se repite cada 15 días; cada paso de más es costo real, no elegancia.
3. **Estado antes que estética.** Cada fila de datos debe comunicar su estado (para enviar / sin email / filtrado, y luego no contestado / contestado / pago / rebotado) sin que el operario tenga que leer texto para entenderlo.
4. **Sobriedad, no vacío.** Sobrio no es lo mismo que gris y plano — usar jerarquía tipográfica y un acento de color con criterio, no ausencia de diseño.

## Accessibility & Inclusion

WCAG AA estándar. Sin necesidades de accesibilidad específicas reportadas; mantener contraste ≥4.5:1 en texto de cuerpo y ≥3:1 en texto grande, soporte de `prefers-reduced-motion`, y foco visible en todos los elementos interactivos (tablas, tabs, modal).
