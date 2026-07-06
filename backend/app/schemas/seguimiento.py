from uuid import UUID

from pydantic import BaseModel


class RespuestasTardiasCiclo(BaseModel):
    ciclo_id: UUID
    numero: int
    count: int


class RespuestasTardiasResponse(BaseModel):
    count: int
    ciclos: list[RespuestasTardiasCiclo]
