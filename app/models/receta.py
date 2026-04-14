import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Receta(Base):
    __tablename__ = "recetas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    nombre = Column(String(200), nullable=False)
    porciones = Column(Integer, default=1, nullable=False)

    # Margen de ganancia deseado (ej. 30.00 para 30%)
    margen_pct = Column(Numeric(5, 2), default=0, nullable=False)
    activa = Column(Boolean, default=True)

    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_modificacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Relaciones
    usuario = relationship("User", backref="recetas")
    ingredientes = relationship("IngredienteReceta", back_populates="receta", cascade="all, delete-orphan")
    pasos = relationship("PasoReceta", back_populates="receta", cascade="all, delete-orphan",
                         order_by="PasoReceta.orden")
    gastos_ocultos = relationship("GastoOculto", back_populates="receta", cascade="all, delete-orphan")