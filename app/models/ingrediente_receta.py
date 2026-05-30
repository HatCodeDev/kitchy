"""
Modelo de datos para la entidad IngredienteReceta.

Representa la asociación de muchos a muchos entre Recetas e Insumos, detallando
la cantidad y la unidad específicas de un insumo que requiere una receta dada.
"""
import uuid
from sqlalchemy import Column, Numeric, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class IngredienteReceta(Base):
    """
    Modelo ORM que representa la tabla de asociación 'ingredientes_receta'.

    Atributos:
        id (UUID): Identificador único del ingrediente de la receta (Primary Key).
        receta_id (UUID): ID de la receta contenedora (Foreign Key).
        insumo_id (UUID): ID del insumo requerido (Foreign Key, protegido por RESTRICT para evitar huérfanos).
        cantidad_usada (Decimal): Cantidad física necesaria en la elaboración.
        unidad (str): Unidad de medida de uso (puede diferir de la unidad de compra original).
        receta (Receta): Relación con el modelo Receta al que pertenece.
        insumo (Insumo): Relación con el modelo Insumo requerido.
    """
    __tablename__ = "ingredientes_receta"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receta_id = Column(UUID(as_uuid=True), ForeignKey("recetas.id", ondelete="CASCADE"), nullable=False)
    insumo_id = Column(UUID(as_uuid=True), ForeignKey("insumos.id", ondelete="RESTRICT"), nullable=False)

    cantidad_usada = Column(Numeric(12, 4), nullable=False)
    unidad = Column(String(10), nullable=False)

    # Relaciones
    receta = relationship("Receta", back_populates="ingredientes")
    insumo = relationship("Insumo")

    # Un insumo no puede estar repetido en la misma receta
    __table_args__ = (
        UniqueConstraint("receta_id", "insumo_id", name="uix_receta_insumo"),
    )