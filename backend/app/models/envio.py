import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Numeric, Integer, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class EstadoEnvio(str, PyEnum):
    NO_CONTESTADO = "NO_CONTESTADO"
    CONTESTADO = "CONTESTADO"
    PAGO = "PAGO"
    REBOTADO = "REBOTADO"
    SIN_EMAIL = "SIN_EMAIL"
    FILTRADO = "FILTRADO"


class MotivoFiltrado(str, PyEnum):
    MONTO_MINIMO = "MONTO_MINIMO"
    DADO_DE_BAJA = "DADO_DE_BAJA"


class Envio(Base):
    __tablename__ = "envios"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ciclo_id = Column(UUID(as_uuid=True), ForeignKey("ciclos.id"), nullable=False, index=True)
    ciclo_numero = Column(Integer, nullable=False)
    clave_union = Column(String(100), nullable=False, index=True)
    nombre_consorcio = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    monto = Column(Numeric(12, 2), nullable=False)
    estado = Column(Enum(EstadoEnvio), nullable=False, default=EstadoEnvio.NO_CONTESTADO)
    motivo_filtrado = Column(Enum(MotivoFiltrado), nullable=True)
    message_id = Column(String(512), nullable=True, index=True)
    proveedor = Column(String(20), nullable=True)
    reply_snippet = Column(Text, nullable=True)
    reply_en = Column(DateTime, nullable=True)
    tiene_adjunto = Column(Boolean, nullable=False, default=False)
    enviado_en = Column(DateTime, nullable=True)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    ciclo = relationship("Ciclo", back_populates="envios")
