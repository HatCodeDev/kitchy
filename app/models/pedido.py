import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    cliente_nombre = Column(String(150), nullable=False)
    cliente_whatsapp = Column(String(20), nullable=True)
    fecha_entrega = Column(DateTime(timezone=True), nullable=False)
    punto_entrega = Column(String(255), nullable=True)

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