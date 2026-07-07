from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, field_validator

from app.core.validators import is_valid_email
from app.models.envio import EstadoEnvio, MotivoFiltrado


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


class ClienteMaestroUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    localidad: Optional[str] = None
    prefiere_no_recibir_email: Optional[bool] = None
    activo: Optional[bool] = None

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() and not is_valid_email(v.strip()):
            raise ValueError("El email no tiene un formato válido")
        return v


class HistorialItemSchema(BaseModel):
    envio_id: UUID
    ciclo: int
    ciclo_activo: bool
    fecha: datetime
    monto: Decimal
    estado: EstadoEnvio
    motivo_filtrado: Optional[MotivoFiltrado] = None
    recibio_mail: bool
    reply_en: Optional[datetime] = None
    saldado_en: Optional[datetime] = None
    racha: int


class HistorialClienteResponse(BaseModel):
    cliente: Optional[ClienteMaestroSchema] = None
    clave_union: str
    deudor_desde: Optional[datetime] = None
    items: list[HistorialItemSchema]


class ClienteMaestroCreate(BaseModel):
    clave_union: str
    nombre: str
    email: Optional[str] = None
    localidad: Optional[str] = None

    @field_validator("clave_union")
    @classmethod
    def clave_no_vacia(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("La clave de unión no puede estar vacía")
        return v.strip()

    @field_validator("nombre")
    @classmethod
    def nombre_no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("El nombre no puede estar vacío")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() and not is_valid_email(v.strip()):
            raise ValueError("El email no tiene un formato válido")
        return v
