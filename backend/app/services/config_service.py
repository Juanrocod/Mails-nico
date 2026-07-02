from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.configuracion_sistema import ConfiguracionSistema


def _fernet() -> Fernet:
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    if not value:
        return ""
    return _fernet().decrypt(value.encode()).decode()


def load_config(db: Session) -> ConfiguracionSistema:
    config = db.get(ConfiguracionSistema, 1)
    if config is None:
        config = ConfiguracionSistema(id=1, actualizado_en=datetime.now(timezone.utc))
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def save_yahoo_credentials(db: Session, yahoo_email: str, yahoo_app_password: str) -> ConfiguracionSistema:
    config = load_config(db)
    config.yahoo_email = yahoo_email
    config.yahoo_app_password_encrypted = encrypt(yahoo_app_password)
    config.actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


def get_yahoo_credentials(db: Session) -> tuple[str, str]:
    """Credenciales de Yahoo desde la DB; si el operario todavía no cargó nada, cae al .env."""
    config = load_config(db)
    if config.yahoo_email and config.yahoo_app_password_encrypted:
        return config.yahoo_email, decrypt(config.yahoo_app_password_encrypted)
    return settings.YAHOO_EMAIL, settings.YAHOO_APP_PASSWORD
