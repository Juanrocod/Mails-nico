from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.envio import EstadoEnvio, MotivoFiltrado


class EnvioSchema(BaseModel):
    id: UUID
    ciclo_id: UUID
    ciclo_numero: int
    clave_union: str
    nombre_consorcio: str
    email: Optional[str]
    monto: Decimal
    estado: EstadoEnvio
    motivo_filtrado: Optional[MotivoFiltrado]
    message_id: Optional[str]
    reply_snippet: Optional[str]
    reply_en: Optional[datetime]
    tiene_adjunto: bool
    enviado_en: Optional[datetime]
    saldado_en: Optional[datetime] = None
    actualizado_en: datetime
    en_proceso: bool = False

    model_config = {"from_attributes": True}


class EstadoUpdateRequest(BaseModel):
    estado: EstadoEnvio
