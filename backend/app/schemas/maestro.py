from typing import Optional
from uuid import UUID
from pydantic import BaseModel


class ClienteMaestroSchema(BaseModel):
    id: UUID
    clave_union: str
    nombre: str
    email: Optional[str]
    localidad: Optional[str]
    prefiere_no_recibir_email: bool
    activo: bool

    model_config = {"from_attributes": True}


class MaestroUploadResponse(BaseModel):
    nuevos: int
    actualizados: int
    total: int
