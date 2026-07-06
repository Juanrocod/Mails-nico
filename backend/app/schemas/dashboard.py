from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel


class DashboardResumenResponse(BaseModel):
    hay_ciclo_activo: bool
    deuda_total: Decimal
    deuda_total_anterior: Optional[Decimal] = None
    deudores: int
    deudores_anterior: Optional[int] = None
    cobrado: Optional[Decimal] = None
    efectividad: Optional[float] = None


class EvolucionCicloSchema(BaseModel):
    numero: int
    fecha: datetime
    deuda_total: Decimal
    deudores: int
    cobrado: Optional[Decimal] = None
