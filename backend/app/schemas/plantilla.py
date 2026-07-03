from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, field_validator

# Lista inicial de palabras/frases típicas de spam en cobranzas. Extensible — no
# viene fijada por el spec, es un punto de partida razonable a revisar con el cliente.
PALABRAS_PROHIBIDAS: list[str] = [
    "gratis",
    "urgente",
    "haga clic ya",
    "gane dinero",
    "100% gratis",
    "oferta exclusiva",
]


class PlantillaSchema(BaseModel):
    asunto: str
    cuerpo_html: str
    nombre_empresa: str
    logo_url: Optional[str] = None
    color_primario: str = "#1a56db"
    monto_minimo: Decimal

    model_config = {"from_attributes": True}

    @field_validator("asunto", "cuerpo_html")
    @classmethod
    def sin_palabras_prohibidas(cls, v: str) -> str:
        lower = v.lower()
        for palabra in PALABRAS_PROHIBIDAS:
            if palabra in lower:
                raise ValueError(f"El texto contiene una palabra no permitida: '{palabra}'")
        return v
