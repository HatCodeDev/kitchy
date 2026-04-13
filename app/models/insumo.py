import uuid
from sqlalchemy import Column, String, Numeric, Date, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from decimal import Decimal
from app.core.database import Base


class Insumo(Base):
    __tablename__ = 'insumos'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # CASCADE asegura que si el usuario se elimina,
    # sus insumos también lo hagan para no dejar huérfanos.
    # Index = True mejora las búsquedas al filtrar por usuario.
    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    nombre = Column(String(200), nullable=False)
    unidad = Column(String(10), nullable=False)

    # Numeric es ideal para divisas y cantidades exactas para evitar problemas de redondeo de punto flotante.
    # Los CheckConstraints son reglas a nivel BD. Garantizan consistencia de datos
    # previniendo que código o integraciones defectuosas metan datos inválidos.
    precio_compra = Column(Numeric(10, 2), CheckConstraint('precio_compra > 0'), nullable=False)
    cantidad_comprada = Column(Numeric(12, 4), CheckConstraint('cantidad_comprada > 0'), nullable=False)
    cantidad_actual = Column(Numeric(12, 4), CheckConstraint('cantidad_actual >= 0'), nullable=False, default=0)
    alerta_minimo = Column(Numeric(12, 4), nullable=False, default=0)

    fecha_ultimo_precio = Column(Date, nullable=False)

    # En lugar de borrar registros físicamente, lo desactivamos.
    # Muy importante para históricos y auditoría en SaaS.
    activo = Column(Boolean, default=True)

    # Relación bidireccional. Permitirá acceder a user.insumos o insumo.usuario.
    usuario = relationship('User', backref='insumos')

    @property
    def precio_unitario(self) -> Decimal:
        """Calcula el precio por unidad al vuelo."""
        if self.cantidad_comprada and self.cantidad_comprada > 0:
            return (self.precio_compra / self.cantidad_comprada).quantize(Decimal('0.0001'))
        return Decimal('0.0000')