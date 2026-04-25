import uuid
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class LineaPedido(Base):
    __tablename__ = "lineas_pedido"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pedido_id = Column(UUID(as_uuid=True), ForeignKey("pedidos.id", ondelete="CASCADE"), nullable=False, index=True)

    # FK Lógica: No usamos ForeignKey("recetas.id") a propósito.
    # Si la receta se borra, el historial del pedido no se rompe.
    # Si es None, es un producto fuera del menú.
    receta_id = Column(UUID(as_uuid=True), nullable=True)

    nombre_producto = Column(String(200), nullable=False)
    cantidad_porciones = Column(Integer, nullable=False)
    precio_acordado_mxn = Column(Numeric(10, 2), nullable=False)

    # Validaciones a nivel DB para que no nos metan cantidades negativas
    __table_args__ = (
        CheckConstraint('cantidad_porciones > 0', name='chk_cantidad_porciones'),
        CheckConstraint('precio_acordado_mxn >= 0', name='chk_precio_acordado'),
    )

    # Relaciones
    pedido = relationship("Pedido", back_populates="lineas")