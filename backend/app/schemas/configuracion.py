from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


class ConfiguracionYahooRequest(BaseModel):
    yahoo_email: EmailStr
    yahoo_app_password: str = Field(min_length=1)


class ConfiguracionYahooResponse(BaseModel):
    yahoo_email: Optional[str] = None
    configurado: bool

    model_config = {"from_attributes": True}


class ConfiguracionGmailRequest(BaseModel):
    gmail_email: EmailStr
    gmail_app_password: str = Field(min_length=1)


class ConfiguracionGmailResponse(BaseModel):
    gmail_email: Optional[str] = None
    configurado: bool

    model_config = {"from_attributes": True}


class ConfiguracionProveedorRequest(BaseModel):
    proveedor: Literal["yahoo", "gmail"]


class ConfiguracionProveedorResponse(BaseModel):
    proveedor: Literal["yahoo", "gmail"]


class ConfiguracionEnviosPendientesResponse(BaseModel):
    pendientes_proveedor_activo: int
    intrackeados_otro_proveedor: int
    otro_proveedor_email: Optional[str] = None
