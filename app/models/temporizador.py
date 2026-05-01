import uuid
from sqlalchemy import Column, String, Integer, ForeignKey, CheckConstraint, Index, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class Temporizador(Base):
    __tablename__ = 'temporizadores'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    paso_receta_id = Column(UUID(as_uuid=True), ForeignKey('pasos_receta.id'), nullable=False)
    usuario_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    
    duracion_segundos = Column(Integer, CheckConstraint('duracion_segundos > 0'), nullable=False)
    estado = Column(
        String(15),
        CheckConstraint("estado IN ('inactivo', 'corriendo', 'pausado', 'completado')"),
        default='inactivo',
        nullable=False
    )
    
    fecha_inicio = Column(TIMESTAMP(timezone=True), nullable=True)
    fecha_confirmacion = Column(TIMESTAMP(timezone=True), nullable=True)

    __table_args__ = (
        Index('ix_temporizador_usuario_estado', 'usuario_id', 'estado'),
    )
