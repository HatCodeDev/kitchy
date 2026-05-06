from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict

class NotificacionBase(BaseModel):
    tipo: str
    fecha_programada: datetime
    pedido_id: Optional[UUID] = None
    insumo_id: Optional[UUID] = None

class NotificacionRead(NotificacionBase):
    id: UUID
    enviada: bool
    fecha_envio: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
