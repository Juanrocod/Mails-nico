from pydantic import BaseModel, ConfigDict
from typing import Optional, Any
from uuid import UUID
from datetime import datetime


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    orden_id: UUID
    usuario_id: Optional[UUID] = None
    accion: str
    ip_origen: Optional[str] = None
    timestamp: datetime
    detalle: Optional[Any] = None
