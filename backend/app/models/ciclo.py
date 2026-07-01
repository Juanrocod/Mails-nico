import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class Ciclo(Base):
    __tablename__ = "ciclos"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero = Column(Integer, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    creado_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    envios = relationship("Envio", back_populates="ciclo", lazy="dynamic")
