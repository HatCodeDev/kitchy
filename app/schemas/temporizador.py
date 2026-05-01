from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class TemporizadorCreate(BaseModel):
    paso_receta_id: UUID
    duracion_segundos: int = Field(gt=0, description='Duración del temporizador en segundos, mayor a cero')

class TemporizadorResponse(BaseModel):
    id: UUID
    paso_receta_id: UUID
    usuario_id: UUID
    duracion_segundos: int
    estado: str
    fecha_inicio: Optional[datetime] = None
    fecha_confirmacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
