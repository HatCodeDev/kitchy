"""
Modelo de datos para la entidad PuntoEntrega.

Gestiona las ubicaciones o puntos de encuentro físicos habituales que los usuarios
registran para coordinar la entrega y logística de pedidos gastronómicos.
"""
import uuid
from sqlalchemy import Column, String, Text, Boolean, ForeignKey, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class PuntoEntrega(Base):
    """
    Modelo ORM que representa la tabla 'puntos_entrega'.

    Representa un punto de despacho físico (ej. local, estación de tren, parque).

    Atributos:
        id (UUID): Identificador único del punto de entrega (Primary Key).
        usuario_id (UUID): ID del usuario dueño del punto (Foreign Key, indexado).
        nombre (str): Nombre identificativo del punto de entrega.
        descripcion (str, opcional): Detalles u orientaciones sobre el punto de encuentro.
        direccion (str, opcional): Dirección física completa o geolocalización textual.
        activo (bool): Flag de borrado lógico (Soft delete). True si el punto está disponible.
        fecha_creacion (datetime): Fecha y hora de creación en base de datos.
        fecha_modificacion (datetime): Fecha y hora del último cambio.
        usuario (User): Relación con el usuario propietario.
        pedidos (list[Pedido]): Lista de pedidos que tienen agendada su entrega en esta ubicación.
    """
    __tablename__ = "puntos_entrega"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    usuario_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    nombre = Column(String(150), nullable=False)
    descripcion = Column(Text, nullable=True)
    direccion = Column(String(500), nullable=True)

    # Soft delete pattern: activo=False instead of deleted_at
    activo = Column(Boolean, default=True)

    fecha_creacion = Column(DateTime(timezone=True), server_default=func.now())
    fecha_modificacion = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación bidireccional
    usuario = relationship("User", backref="puntos_entrega")
    pedidos = relationship("Pedido", back_populates="punto_entrega_rel")
