"""
Modelo de datos para la entidad MovimientoInsumo.

Registra el historial de auditoría de entradas y salidas de inventario, permitiendo
el control de stock, cálculo de mermas y auditorías de consumo en producción.
"""
import uuid
from sqlalchemy import Column, String, Numeric, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class MovimientoInsumo(Base):
    """
    Modelo ORM que representa la tabla 'movimientos_insumo'.

    Registra cada transacción que altera el nivel de stock físico de un insumo.

    Atributos:
        id (UUID): Identificador único del movimiento (Primary Key).
        insumo_id (UUID): ID del insumo afectado (Foreign Key, indexado).
        usuario_id (UUID): ID del usuario que generó el movimiento (Foreign Key).
        tipo (str): Tipo de movimiento ('entrada' o 'salida').
        cantidad (Decimal): Cantidad física movilizada (debe ser > 0).
        motivo (str): Motivo de la transacción ('compra', 'uso_produccion', 'merma').
        fecha (datetime): Fecha y hora exacta de inserción en base de datos.
        insumo (Insumo): Relación con el insumo modificado.
        usuario (User): Relación con el usuario autor del movimiento.
    """
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