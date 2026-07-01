from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Numeric, DateTime
from app.core.database import Base


class Plantilla(Base):
    __tablename__ = "plantilla"
    id = Column(Integer, primary_key=True, default=1)
    asunto = Column(String(255), nullable=False, default="Recordatorio de deuda")
    cuerpo_html = Column(Text, nullable=False, default="")
    nombre_empresa = Column(String(255), nullable=False, default="")
    logo_url = Column(String(512), nullable=True)
    color_primario = Column(String(7), nullable=False, default="#1a56db")
    monto_minimo = Column(Numeric(12, 2), nullable=False, default=0)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
