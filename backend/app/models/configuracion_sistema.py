from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime
from app.core.database import Base


class ConfiguracionSistema(Base):
    __tablename__ = "configuracion_sistema"
    id = Column(Integer, primary_key=True, default=1)
    proveedor_activo = Column(String(20), nullable=False, default="yahoo")
    yahoo_email = Column(String(255), nullable=True)
    yahoo_app_password_encrypted = Column(String(512), nullable=True)
    gmail_email = Column(String(255), nullable=True)
    gmail_app_password_encrypted = Column(String(512), nullable=True)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
