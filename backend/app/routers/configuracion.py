from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.configuracion import ConfiguracionYahooRequest, ConfiguracionYahooResponse
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
