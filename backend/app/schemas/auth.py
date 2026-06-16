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


class PendingTokenResponse(BaseModel):
    pending_token: str
    message: str


class VerifyTOTPRequest(BaseModel):
    pending_token: str
    code: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ADR-0008: registro e invite tokens
class RegisterRequest(BaseModel):
    token: str
    username: str
    password: str

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class RegisterResponse(BaseModel):
    totp_uri: str
    setup_token: str


class ConfirmRegisterRequest(BaseModel):
    setup_token: str
    totp_code: str


class ResetPasswordRequest(BaseModel):
    token: str
    password: str

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class RegenerateTOTPRequest(BaseModel):
    totp_code: str


class RegenerateTOTPResponse(BaseModel):
    totp_uri: str
