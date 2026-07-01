from datetime import timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, RefreshRequest, TokenResponse
from app.services.auth import authenticate_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(body.username, body.password, db)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    access_token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS),
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


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
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


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
