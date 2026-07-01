from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class PlantillaSchema(BaseModel):
    asunto: str
    cuerpo_html: str
    nombre_empresa: str
    logo_url: Optional[str] = None
    color_primario: str = "#1a56db"
    monto_minimo: Decimal

    model_config = {"from_attributes": True}
