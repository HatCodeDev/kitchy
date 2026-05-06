import uuid
from sqlalchemy import Column, String, Boolean, DateTime, CheckConstraint, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class NotificacionProgramada(Base):
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
