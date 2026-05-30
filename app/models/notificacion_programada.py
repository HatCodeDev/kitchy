"""
Modelo de datos para la entidad NotificacionProgramada.

Representa las alertas y recordatorios que el motor de Kitchy programa para
enviarse de forma asíncrona (ej. a través de WhatsApp o notificaciones internas).
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, CheckConstraint, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


class NotificacionProgramada(Base):
    """
    Modelo ORM que representa la tabla 'notificaciones_programadas'.

    Almacena eventos de notificación programados para ser procesados por un job en segundo plano.

    Atributos:
        id (UUID): Identificador único de la notificación (Primary Key).
        usuario_id (UUID): ID del usuario receptor de la notificación (Foreign Key).
        pedido_id (UUID, opcional): ID del pedido referenciado (Foreign Key lógica).
        insumo_id (UUID, opcional): ID del insumo referenciado (Foreign Key lógica).
        tipo (str): Tipo de alerta ('recordatorio_entrega', 'alerta_desabasto', 'margen_en_riesgo').
        fecha_programada (datetime): Fecha y hora en la que debe dispararse la alerta.
        enviada (bool): Estado de despacho de la notificación.
        fecha_envio (datetime, opcional): Estampa de tiempo exacta de cuando se despachó.
    """
    __tablename__ = "notificaciones_programadas"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # FK lógicos (sin constraint restrictivo físico en la BD para mayor flexibilidad)
    pedido_id = Column(UUID(as_uuid=True), nullable=True)
    insumo_id = Column(UUID(as_uuid=True), nullable=True)

    tipo = Column(String(30), nullable=False)

    fecha_programada = Column(DateTime(timezone=True), nullable=False)
    enviada = Column(Boolean, default=False, nullable=False)
    fecha_envio = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "tipo IN ('recordatorio_entrega', 'alerta_desabasto', 'margen_en_riesgo')",
            name="check_tipo_notificacion"
        ),
        # Simplificación para el MVP: al menos uno debe tener valor (según instrucción)
        CheckConstraint(
            "pedido_id IS NOT NULL OR insumo_id IS NOT NULL",
            name="check_entidad_referenciada"
        ),
        Index("ix_notif_enviada_fecha", "enviada", "fecha_programada"),
    )
