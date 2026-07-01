import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_pending_2fa_token,
    create_refresh_token,
    create_totp_setup_token,
    decode_token,
    generate_totp_secret,
    get_totp_provisioning_uri,
    hash_password,
    verify_password,
    verify_totp,
)
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ConfirmRegisterRequest,
    LoginRequest,
    PendingTokenResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    RegenerateTOTPRequest,
    RegenerateTOTPResponse,
    ResetPasswordRequest,
    TokenResponse,
    VerifyTOTPRequest,
)
from app.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=PendingTokenResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(body.username, body.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    pending_token = create_pending_2fa_token(subject=str(user.id))
    return PendingTokenResponse(
        pending_token=pending_token,
        message="Ingrese el código de su autenticador",
    )


@router.post("/verify-totp", response_model=TokenResponse)
@limiter.limit("5/minute")
def verify_totp_endpoint(request: Request, body: VerifyTOTPRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.pending_token)
        if payload.get("type") != "pending_2fa":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Token pendiente inválido o expirado")

    user = db.query(User).filter(User.id == UUID(payload["sub"]), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")

    if not verify_totp(user.totp_secret, body.code):
        raise HTTPException(status_code=401, detail="Código 2FA inválido")

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@router.post("/logout", status_code=204)
def logout(current_user: User = Depends(get_current_user)):
    pass


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh(request: Request, body: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise ValueError
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Refresh token inválido")

    user = db.query(User).filter(User.id == UUID(payload["sub"]), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no autorizado")

    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )






@router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.old_password, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    db.commit()


@router.post("/regenerate-totp", response_model=RegenerateTOTPResponse)
def regenerate_totp(
    body: RegenerateTOTPRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_totp(current_user.totp_secret, body.totp_code):
        raise HTTPException(status_code=401, detail="Código del Authenticator incorrecto")
    new_secret = generate_totp_secret()
    current_user.totp_secret = new_secret
    db.add(current_user)
    db.commit()
    totp_uri = get_totp_provisioning_uri(new_secret, current_user.username, settings.TOTP_ISSUER)
    return RegenerateTOTPResponse(totp_uri=totp_uri)
