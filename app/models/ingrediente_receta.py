import uuid
from sqlalchemy import Column, Numeric, String, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class IngredienteReceta(Base):
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