"""
Modelo de datos para la entidad Temporizador.

Representa un temporizador activo para controlar tiempos de cocción o preparación en tiempo
real de un determinado paso de una receta.
"""
import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, CheckConstraint, Index, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class Temporizador(Base):
    """
    Modelo ORM que representa la tabla 'temporizadores'.

    Lleva la trazabilidad del temporizador en procesos de manufactura activa de alimentos.

    Atributos:
        id (UUID): Identificador único del temporizador (Primary Key).
        paso_receta_id (UUID): ID del paso de la receta asociado (Foreign Key).
        usuario_id (UUID): ID del usuario dueño del temporizador (Foreign Key).
        duracion_segundos (int): Duración total programada en segundos (debe ser > 0).
        estado (str): Estado de avance ('inactivo', 'corriendo', 'pausado', 'completado').
        fecha_inicio (datetime, opcional): Momento exacto en el que comenzó a correr.
        fecha_confirmacion (datetime, opcional): Momento exacto de confirmación/conclusión.
    """
    __tablename__ = 'temporizadores'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paso_receta_id = Column(UUID(as_uuid=True), ForeignKey('pasos_receta.id'), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    duracion_segundos = Column(Integer, CheckConstraint('duracion_segundos > 0'), nullable=False)
    estado = Column(
        String(15),
        CheckConstraint("estado IN ('inactivo', 'corriendo', 'pausado', 'completado')"),
        default='inactivo',
        nullable=False
    )

    fecha_inicio = Column(TIMESTAMP(timezone=True), nullable=True)
    fecha_confirmacion = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_temporizador_usuario_estado', 'usuario_id', 'estado'),
    )
