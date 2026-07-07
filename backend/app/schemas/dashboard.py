from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.models.envio import EstadoEnvio


class DashboardResumenResponse(BaseModel):
    hay_ciclo_activo: bool
    deuda_total: Decimal
    deuda_total_anterior: Optional[Decimal] = None
    deudores: int
    deudores_anterior: Optional[int] = None
    cobrado: Optional[Decimal] = None
    deuda_mas_90: Decimal


class EvolucionCicloSchema(BaseModel):
    numero: int
    fecha: datetime
    deuda_total: Decimal
    deudores: int
    cobrado: Optional[Decimal] = None


class MorosoSchema(BaseModel):
    clave_union: str
    nombre_consorcio: str
    monto: Decimal
    deudor_desde: datetime
    ciclos_debiendo: int
    estado: EstadoEnvio
