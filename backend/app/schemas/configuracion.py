from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class ConfiguracionYahooRequest(BaseModel):
    yahoo_email: EmailStr
    yahoo_app_password: str = Field(min_length=1)


class ConfiguracionYahooResponse(BaseModel):
    yahoo_email: Optional[str] = None
    configurado: bool

    model_config = {"from_attributes": True}
