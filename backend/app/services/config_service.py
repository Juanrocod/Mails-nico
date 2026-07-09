import imaplib
import logging
import smtplib
import ssl
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.email_providers import PROVIDERS, DEFAULT_PROVIDER, ProviderConfig
from app.models.configuracion_sistema import ConfiguracionSistema

_logger = logging.getLogger("mails_nico.config")

_CONEXION_TIMEOUT_SECONDS = 15  # login colgado no debe trabar la request entera


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


def get_active_provider(db: Session) -> str:
    """Proveedor activo configurado por el operario. Si el valor guardado no es uno
    conocido (ej. dato corrupto o editado a mano en DB), cae al default sin romper."""
    config = load_config(db)
    if config.proveedor_activo in PROVIDERS:
        return config.proveedor_activo
    _logger.warning(
        "proveedor_activo invalido en DB (%s), usando default %s", config.proveedor_activo, DEFAULT_PROVIDER
    )
    return DEFAULT_PROVIDER


def save_active_provider(db: Session, proveedor: str) -> ConfiguracionSistema:
    config = load_config(db)
    config.proveedor_activo = proveedor
    config.actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


def save_gmail_credentials(db: Session, gmail_email: str, gmail_app_password: str) -> ConfiguracionSistema:
    config = load_config(db)
    config.gmail_email = gmail_email
    config.gmail_app_password_encrypted = encrypt(gmail_app_password)
    config.actualizado_en = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return config


def get_gmail_credentials(db: Session) -> tuple[str, str]:
    """Credenciales de Gmail desde la DB; si el operario todavía no cargó nada, cae al .env."""
    config = load_config(db)
    if config.gmail_email and config.gmail_app_password_encrypted:
        return config.gmail_email, decrypt(config.gmail_app_password_encrypted)
    return settings.GMAIL_EMAIL, settings.GMAIL_APP_PASSWORD


def get_active_credentials(db: Session) -> tuple[str, str]:
    """Credenciales del proveedor activo (Yahoo o Gmail)."""
    if get_active_provider(db) == "gmail":
        return get_gmail_credentials(db)
    return get_yahoo_credentials(db)


def _probar_smtp(provider: ProviderConfig, email: str, password: str) -> tuple[bool, str | None]:
    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(provider.smtp_host, provider.smtp_port, timeout=_CONEXION_TIMEOUT_SECONDS) as server:
            server.starttls(context=context)
            server.login(email, password)
        return True, None
    except Exception as exc:  # noqa: BLE001 — cualquier fallo de red/auth es un "no conecta"
        return False, str(exc)[:300]


def _probar_imap(provider: ProviderConfig, email: str, password: str) -> tuple[bool, str | None]:
    server = None
    try:
        server = imaplib.IMAP4_SSL(provider.imap_host, provider.imap_port, timeout=_CONEXION_TIMEOUT_SECONDS)
        server.login(email, password)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)[:300]
    finally:
        if server is not None:
            try:
                server.logout()
            except Exception:  # noqa: BLE001 — cerrar es best-effort
                pass


def probar_conexion(db: Session, proveedor: str) -> dict:
    """Verifica de verdad que las credenciales guardadas del proveedor logueen
    contra SMTP e IMAP. No envía ni lee mails; solo abre y cierra la sesión."""
    provider = PROVIDERS.get(proveedor)
    if provider is None:
        return {"configurado": False, "smtp_ok": False, "imap_ok": False,
                "error": f"Proveedor desconocido: {proveedor}"}

    config = load_config(db)
    if proveedor == "gmail":
        email, encrypted = config.gmail_email, config.gmail_app_password_encrypted
    else:
        email, encrypted = config.yahoo_email, config.yahoo_app_password_encrypted

    if not (email and encrypted):
        return {"configurado": False, "smtp_ok": False, "imap_ok": False,
                "error": "No hay credenciales guardadas para este proveedor."}

    password = decrypt(encrypted)
    smtp_ok, smtp_error = _probar_smtp(provider, email, password)
    imap_ok, imap_error = _probar_imap(provider, email, password)
    return {"configurado": True, "smtp_ok": smtp_ok, "imap_ok": imap_ok,
            "smtp_error": smtp_error, "imap_error": imap_error}
