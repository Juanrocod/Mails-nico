import re
from pydantic import BaseModel, field_validator


def _validate_password(v: str) -> str:
    if not (8 <= len(v) <= 72):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[A-Z]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[0-9]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    if not re.search(r'[^a-zA-Z0-9]', v):
        raise ValueError("La contraseña no cumple los requisitos de seguridad")
    return v


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)
