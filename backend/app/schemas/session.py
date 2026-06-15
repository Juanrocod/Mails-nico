from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Optional, List, Literal
from datetime import datetime

_CAMPOS_PERMITIDOS = {"cantidad", "precio", "moneda", "liquidacion", "tipo", "instrumento"}
_OPERADORES_PERMITIDOS = {">", "<", "=", "!=", ">=", "<="}


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


class ReglaDJSchema(BaseModel):
    campo: str
    operador: str
    valor: str

    @field_validator("campo")
    @classmethod
    def campo_valido(cls, v: str) -> str:
        if v not in _CAMPOS_PERMITIDOS:
            raise ValueError(
                f"campo '{v}' no permitido. Opciones: {sorted(_CAMPOS_PERMITIDOS)}"
            )
        return v

    @field_validator("operador")
    @classmethod
    def operador_valido(cls, v: str) -> str:
        if v not in _OPERADORES_PERMITIDOS:
            raise ValueError(
                f"operador '{v}' no permitido. Opciones: {sorted(_OPERADORES_PERMITIDOS)}"
            )
        return v


class ConfigDJSchema(BaseModel):
    activa: bool
    incluir_texto_en_minuta: bool = False
    texto_alerta: str
    reglas: List[ReglaDJSchema] = []
    logica: Literal["OR", "AND"] = "OR"
