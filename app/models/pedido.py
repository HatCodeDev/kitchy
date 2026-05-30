"""
Modelo de datos para la entidad Pedido.

Gestiona las ventas, el estado del pedido, datos de contacto del cliente
y los detalles específicos de entrega de los productos elaborados.
"""
import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Pedido(Base):
    """
    Modelo ORM que representa la tabla 'pedidos' en la base de datos.

    Representa un pedido de un cliente que incluye productos terminados
    (líneas de pedido), el estado de entrega y el destino.

    Atributos:
        id (UUID): Identificador único del pedido (Primary Key).
        usuario_id (UUID): ID del usuario dueño del pedido (Foreign Key).
        cliente_nombre (str): Nombre del cliente.
        cliente_whatsapp (str): Teléfono WhatsApp del cliente para enviar notificaciones.
        fecha_entrega (datetime): Fecha y hora comprometida para realizar la entrega.
        punto_entrega (str): Dirección física o punto de encuentro textual de entrega.
        punto_entrega_id (UUID): ID de la entidad PuntoEntrega si aplica (Foreign Key).
        estado (str): Estado actual del pedido ('pendiente', 'en_preparacion', 'listo',
            'entregado', 'cancelado').
        notas (str): Anotaciones o comentarios adicionales del pedido.
        fecha_creacion (datetime): Fecha y hora en la que se levantó el pedido.
        fecha_modificacion (datetime): Fecha y hora de la última actualización.
        usuario (User): Relación con el usuario propietario de la cuenta.
        lineas (list[LineaPedido]): Líneas detalladas del pedido (productos y porciones).
        punto_entrega_rel (PuntoEntrega): Relación con la entidad de Punto de Entrega física.
    """
    __tablename__ = "pedidos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    cliente_nombre = Column(String(150), nullable=False)
    cliente_whatsapp = Column(String(20), nullable=True)
    fecha_entrega = Column(DateTime(timezone=True), nullable=False)
    punto_entrega = Column(String(255), nullable=True)
    punto_entrega_id = Column(UUID(as_uuid=True), ForeignKey("puntos_entrega.id", ondelete="SET NULL"), nullable=True)

    # Máquina de Estados blindada
    estado = Column(String(25), default='pendiente', nullable=False)
    notas = Column(Text, nullable=True)

    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_modificacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Constraints e Índices
    __table_args__ = (
        CheckConstraint(
            estado.in_(['pendiente', 'en_preparacion', 'listo', 'entregado', 'cancelado']),
            name='chk_estado_pedido'
        ),
        # Índice compuesto para ordenar cronológicamente por usuario muy rápido
        Index('ix_pedidos_usuario_fecha', 'usuario_id', 'fecha_entrega'),
    )

    # Relaciones
    usuario = relationship("User", backref="pedidos")
    lineas = relationship("LineaPedido", back_populates="pedido", cascade="all, delete-orphan")
    punto_entrega_rel = relationship("PuntoEntrega", back_populates="pedidos")