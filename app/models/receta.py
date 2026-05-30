"""
Modelo de datos para la entidad Receta.

Representa las recetas o fórmulas creadas por los usuarios para producir porciones
de alimentos, definiendo el rendimiento, margen de ganancia esperado, ingredientes y pasos.
"""
import uuid
from sqlalchemy import Column, String, Integer, Numeric, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Receta(Base):
    """
    Modelo ORM que representa la tabla 'recetas' en la base de datos.

    Atributos:
        id (UUID): Identificador único de la receta (Primary Key).
        usuario_id (UUID): ID del usuario creador (Foreign Key, indexado).
        nombre (str): Nombre distintivo de la receta.
        porciones (int): Rendimiento de porciones obtenido con la receta. Por defecto 1.
        margen_pct (Decimal): Porcentaje de margen de ganancia deseado (ej. 30.00% = 30%).
        activa (bool): Flag de borrado lógico para desactivación.
        fecha_creacion (datetime): Fecha y hora de registro de la receta.
        fecha_modificacion (datetime): Fecha y hora de la última edición de la receta.
        usuario (User): Relación con el modelo User (creador de la receta).
        ingredientes (list[IngredienteReceta]): Lista de ingredientes requeridos.
        pasos (list[PasoReceta]): Lista de pasos del proceso de preparación ordenados.
        gastos_ocultos (list[GastoOculto]): Lista de gastos indirectos u ocultos.
    """
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