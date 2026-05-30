"""
Modelo de datos para la entidad PasoReceta.

Define la secuencia ordenada de pasos e instrucciones de manufactura culinaria
requeridas para elaborar una receta, incluyendo tiempos y niveles de criticidad.
"""
import uuid
from sqlalchemy import Column, String, Integer, Text, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class PasoReceta(Base):
    """
    Modelo ORM que representa la tabla 'pasos_receta'.

    Representa una instrucción o etapa secuencial dentro del proceso de preparación de una receta.

    Atributos:
        id (UUID): Identificador único del paso de receta (Primary Key).
        receta_id (UUID): ID de la receta contenedora (Foreign Key).
        orden (int): Número secuencial de ejecución (ej. 1, 2, 3...).
        descripcion (str): Explicación detallada de la acción a realizar en este paso.
        duracion_segundos (int, opcional): Tiempo estimado en segundos para completar el paso.
        es_critico (bool): Flag que indica si es un paso con alta propensión a error o riesgos sanitarios.
        receta (Receta): Relación con el modelo Receta al que pertenece.
    """
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