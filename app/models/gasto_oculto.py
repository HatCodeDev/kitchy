import uuid
from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class GastoOculto(Base):
    __tablename__ = "gastos_ocultos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receta_id = Column(UUID(as_uuid=True), ForeignKey("recetas.id", ondelete="CASCADE"), nullable=True)

    tipo = Column(String(20), nullable=False)  # empaque, gas_luz, etc.
    valor = Column(Numeric(10, 2), nullable=False)
    es_porcentaje = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)

    receta = relationship("Receta", back_populates="gastos_ocultos")