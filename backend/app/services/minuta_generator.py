from datetime import datetime
from typing import Optional


def generate_minuta_text(
    cliente_nombre: str,
    cuenta_comitente: str,
    cuenta_cotapartista: str,
    instrumento: str,
    tipo: str,
    cantidad: float,
    precio: float,
    moneda: str,
    liquidacion: str,
    fecha_operacion: datetime,
    dj_texto: Optional[str] = None,
) -> str:
    fecha_str = fecha_operacion.strftime("%d/%m/%Y %H:%M")
    cantidad_str = f"{cantidad:,.0f}".replace(",", ".")
    precio_str = f"{precio:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    lines = [
        f"MINUTA DE OPERACIÓN",
        f"Fecha y hora: {fecha_str}",
        f"",
        f"Cliente: {cliente_nombre}",
        f"Cuenta Comitente: {cuenta_comitente}",
        f"Cuenta Cotapartista: {cuenta_cotapartista}",
        f"",
        f"DETALLE DE LA OPERACIÓN",
        f"Instrumento: {instrumento}",
        f"Tipo: {tipo}",
        f"Cantidad: {cantidad_str}",
        f"Precio: {precio_str} {moneda}",
        f"Condición de Liquidación: {liquidacion}",
        f"",
        f"Quedo a su disposición ante cualquier consulta.",
        f"Saludos cordiales.",
    ]

    if dj_texto:
        lines += [
            f"",
            f"---",
            f"DECLARACIÓN JURADA",
            f"",
            dj_texto,
        ]

    return "\n".join(lines)
