from __future__ import annotations
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class MinutaSchema(BaseModel):
    id: str
    cliente_nombre: str
    cliente_email: str
    cuenta_comitente: str
    cuenta_cotapartista: str
    instrumento: str
    tipo: str
    cantidad: float
    precio: float
    moneda: str
    liquidacion: str
    fecha_operacion: datetime
    dj_aplicada: bool
    dj_texto: Optional[str]
    estado: str
    texto_minuta: str
    texto_editado: bool
    creado_en: datetime


class SessionMinutasResponse(BaseModel):
    items: List[MinutaSchema]
    total: int


class RowErrorSchema(BaseModel):
    fila: int
    mensaje: str


class UploadMVPResponse(BaseModel):
    nombre_archivo: str
    total_ordenes: int
    ordenes_validas: int
    ordenes_con_error: int
    errors: List[RowErrorSchema]
    minutas: List[MinutaSchema]


class EditTextoRequest(BaseModel):
    texto_minuta: str


class PlantillaSchema(BaseModel):
    texto: str


class ConfigDJSchema(BaseModel):
    activa: bool
    texto_alerta: str
