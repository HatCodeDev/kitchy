import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PuntoEntrega(Base):
    __tablename__ = "puntos_entrega"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    direccion = Column(String(500), nullable=True)

    # Soft delete pattern: activo=False instead of deleted_at
    activo = Column(Boolean, default=True)

    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_modificacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación bidireccional
    usuario = relationship("User", backref="puntos_entrega")
    pedidos = relationship("Pedido", back_populates="punto_entrega_rel")
