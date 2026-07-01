import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class ClienteMaestro(Base):
    __tablename__ = "clientes_maestro"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clave_union = Column(String(100), unique=True, nullable=False, index=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    localidad = Column(String(255), nullable=True)
    prefiere_no_recibir_email = Column(Boolean, default=False, nullable=False)
    activo = Column(Boolean, default=True, nullable=False)
    actualizado_en = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
