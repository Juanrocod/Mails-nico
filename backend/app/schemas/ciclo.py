from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PreviewItem(BaseModel):
    clave_union: str
    nombre_consorcio: str
    email: Optional[str] = None
    monto: Decimal
    localidad: Optional[str] = None
    motivo_filtrado: Optional[str] = None


class PreviewResponse(BaseModel):
    para_enviar: int
    sin_email: int
    filtrados: int
    total_deudores: int
    monto_total_enviar: Decimal
    items_para_enviar: list[PreviewItem]
    items_sin_email: list[PreviewItem]
    items_filtrados: list[PreviewItem]
