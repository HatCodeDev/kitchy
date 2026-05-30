"""
Modelo de datos para la entidad LineaPedido.

Representa los ítems específicos de una orden o pedido de cliente (productos,
porciones contratadas y costos acordados para el desglose financiero).
"""
import uuid
from sqlalchemy import Column, String, Integer, Numeric, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class LineaPedido(Base):
    """
    Modelo ORM que representa la tabla 'lineas_pedido'.

    Define cada producto vendido en un pedido. Mantiene la trazabilidad de precios
    históricos pactados con el cliente independientemente de si la receta cambia de precio o se elimina.

    Atributos:
        id (UUID): Identificador único de la línea de pedido (Primary Key).
        pedido_id (UUID): ID del pedido padre (Foreign Key).
        receta_id (UUID, opcional): ID de la receta base. No cuenta con ForeignKey a nivel base
            de datos de forma intencional; si la receta se elimina, se conserva la línea del pedido.
        nombre_producto (str): Nombre comercial o descriptivo del producto vendido.
        cantidad_porciones (int): Cantidad de porciones vendidas (debe ser > 0).
        precio_acordado_mxn (Decimal): Precio unitario pactado con el cliente (debe ser >= 0).
        pedido (Pedido): Relación con el modelo Pedido padre al que pertenece.
    """
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