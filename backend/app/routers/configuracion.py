from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.envio import Envio, EstadoEnvio
from app.schemas.configuracion import (
    ConfiguracionYahooRequest,
    ConfiguracionYahooResponse,
    ConfiguracionGmailRequest,
    ConfiguracionGmailResponse,
    ConfiguracionProveedorRequest,
    ConfiguracionProveedorResponse,
    ConfiguracionEnviosPendientesResponse,
)
from app.services import config_service

router = APIRouter(prefix="/configuracion", tags=["configuracion"])


@router.get("/yahoo", response_model=ConfiguracionYahooResponse)
def get_yahoo_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = config_service.load_config(db)
    return ConfiguracionYahooResponse(
        yahoo_email=config.yahoo_email,
        configurado=bool(config.yahoo_email and config.yahoo_app_password_encrypted),
    )


@router.put("/yahoo", response_model=ConfiguracionYahooResponse)
def put_yahoo_config(
    body: ConfiguracionYahooRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = config_service.save_yahoo_credentials(db, body.yahoo_email, body.yahoo_app_password)
    return ConfiguracionYahooResponse(yahoo_email=config.yahoo_email, configurado=True)


@router.get("/gmail", response_model=ConfiguracionGmailResponse)
def get_gmail_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = config_service.load_config(db)
    return ConfiguracionGmailResponse(
        gmail_email=config.gmail_email,
        configurado=bool(config.gmail_email and config.gmail_app_password_encrypted),
    )


@router.put("/gmail", response_model=ConfiguracionGmailResponse)
def put_gmail_config(
    body: ConfiguracionGmailRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = config_service.save_gmail_credentials(db, body.gmail_email, body.gmail_app_password)
    return ConfiguracionGmailResponse(gmail_email=config.gmail_email, configurado=True)


@router.get("/proveedor", response_model=ConfiguracionProveedorResponse)
def get_proveedor(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return ConfiguracionProveedorResponse(proveedor=config_service.get_active_provider(db))


@router.put("/proveedor", response_model=ConfiguracionProveedorResponse)
def put_proveedor(
    body: ConfiguracionProveedorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config_service.save_active_provider(db, body.proveedor)
    return ConfiguracionProveedorResponse(proveedor=body.proveedor)


@router.get("/envios-no-contestados-count", response_model=ConfiguracionEnviosPendientesResponse)
def get_envios_no_contestados_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    count = db.query(Envio).filter(Envio.estado == EstadoEnvio.NO_CONTESTADO).count()
    return ConfiguracionEnviosPendientesResponse(count=count)
