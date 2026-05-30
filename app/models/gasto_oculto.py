"""
Modelo de datos para la entidad GastoOculto.

Representa gastos indirectos y costos ocultos asociados a la elaboración de una receta
(ej. empaques, gas, electricidad, agua) o definidos por el usuario de forma global.
"""
import uuid
from sqlalchemy import Column, String, Numeric, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class GastoOculto(Base):
    """
    Modelo ORM que representa la tabla 'gastos_ocultos' en la base de datos.

    Atributos:
        id (UUID): Identificador único del gasto oculto (Primary Key).
        usuario_id (UUID): ID del usuario dueño del gasto (Foreign Key).
        receta_id (UUID): ID de la receta específica a la que se asocia (Foreign Key, opcional).
        tipo (str): Categoría del gasto (ej. 'empaque', 'gas_luz', 'otros').
        valor (Decimal): Monto monetario o valor porcentual asignado.
        es_porcentaje (bool): Si es True, el valor representa un porcentaje sobre el costo base.
        activo (bool): Flag de borrado lógico.
        receta (Receta): Relación con el modelo Receta al que pertenece.
    """
    __tablename__ = "gastos_ocultos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receta_id = Column(UUID(as_uuid=True), ForeignKey("recetas.id", ondelete="CASCADE"), nullable=True)

    tipo = Column(String(20), nullable=False)  # empaque, gas_luz, etc.
    valor = Column(Numeric(10, 2), nullable=False)
    es_porcentaje = Column(Boolean, default=False)
    activo = Column(Boolean, default=True)

    receta = relationship("Receta", back_populates="gastos_ocultos")