from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime


class PuntoEntregaCreate(BaseModel):
    """Payload para crear un punto de entrega."""
    nombre: str = Field(..., min_length=1, max_length=150, description="Nombre del punto de entrega")
    descripcion: Optional[str] = Field(default=None, description="Descripción opcional")
    direccion: Optional[str] = Field(default=None, max_length=500, description="Dirección opcional")

    @field_validator("direccion", mode="before")
    @classmethod
    def coerce_blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        """Convierte strings vacíos o solo espacios a None."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v


class PuntoEntregaUpdate(PuntoEntregaCreate):
    """Payload para actualizar completamente un punto de entrega (PUT)."""
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=150)


class PuntoEntregaPatch(BaseModel):
    """Payload para actualización parcial de un punto de entrega (PATCH)."""
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=150)
    descripcion: Optional[str] = Field(default=None)
    direccion: Optional[str] = Field(default=None, max_length=500)

    @field_validator("direccion", mode="before")
    @classmethod
    def coerce_blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        """Convierte strings vacíos o solo espacios a None."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v


class PuntoEntregaRead(BaseModel):
    """Respuesta al cliente — no expone 'activo' ni 'deleted_at'."""
    id: UUID
    usuario_id: UUID
    nombre: str
    descripcion: Optional[str] = None
    direccion: Optional[str] = None
    fecha_creacion: datetime
    fecha_modificacion: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
