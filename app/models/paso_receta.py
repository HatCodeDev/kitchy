import uuid
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class PasoReceta(Base):
    __tablename__ = "pasos_receta"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    receta_id = Column(UUID(as_uuid=True), ForeignKey("recetas.id", ondelete="CASCADE"), nullable=False)

    orden = Column(Integer, nullable=False)
    descripcion = Column(Text, nullable=False)
    duracion_segundos = Column(Integer, nullable=True)
    es_critico = Column(Boolean, default=False)

    receta = relationship("Receta", back_populates="pasos")

    __table_args__ = (
        UniqueConstraint("receta_id", "orden", name="uix_receta_orden_paso"),
    )