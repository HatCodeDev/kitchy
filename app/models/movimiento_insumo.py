import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class MovimientoInsumo(Base):
    __tablename__ = 'movimientos_insumo'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # FK a insumos
    insumo_id = Column(UUID(as_uuid=True), ForeignKey('insumos.id'), nullable=False, index=True)

    # FK a users
    usuario_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Restricciones CHECK para los 'enums'
    # Usar CheckConstraint a nivel de tabla es más rápido y portátil que usar tipos ENUM propios de PostgreSQL
    tipo = Column(
        String(10),
        CheckConstraint("tipo IN ('entrada', 'salida')", name='check_movimiento_tipo'),
        nullable=False
    )

    cantidad = Column(
        Numeric(12, 4),
        CheckConstraint('cantidad > 0', name='check_movimiento_cantidad'),
        nullable=False
    )

    motivo = Column(
        String(30),
        CheckConstraint("motivo IN ('compra', 'uso_produccion', 'merma')", name='check_movimiento_motivo'),
        nullable=False
    )

    # TIMESTAMP WITH TIMEZONE. 'server_default=func.now()' delega a la BD la generación
    # de la estampa de tiempo exacta en que se inserta el registro.
    fecha = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relaciones ORM para navegar entre objetos en Python
    insumo = relationship('Insumo', backref='movimientos')
    usuario = relationship('User', backref='movimientos')