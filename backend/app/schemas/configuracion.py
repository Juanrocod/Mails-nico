from typing import Optional
from pydantic import BaseModel, EmailStr


class ConfiguracionYahooRequest(BaseModel):
    yahoo_email: EmailStr
    yahoo_app_password: str


class ConfiguracionYahooResponse(BaseModel):
    yahoo_email: Optional[str] = None
    configurado: bool

    model_config = {"from_attributes": True}
