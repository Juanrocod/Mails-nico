from decimal import Decimal
from pydantic import BaseModel


class PreviewResponse(BaseModel):
    para_enviar: int
    sin_email: int
    filtrados: int
    total_deudores: int
    monto_total_enviar: Decimal
