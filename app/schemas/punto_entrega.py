"""
Esquemas de validación Pydantic para Puntos de Entrega.

Este módulo define las estructuras de entrada y salida utilizadas para la creación,
actualización (PUT/PATCH) y consulta de los puntos de entrega formales de pedidos.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional
from uuid import UUID
from datetime import datetime


class PuntoEntregaCreate(BaseModel):
    """
    Datos requeridos para el registro de un nuevo punto de entrega formal.
    """
    nombre: str = Field(
        ..., 
        min_length=1, 
        max_length=150, 
        description="Nombre descriptivo del punto de entrega (ej. Sucursal Norte, Metro Bellas Artes)."
    )
    descripcion: Optional[str] = Field(
        default=None, 
        description="Notas informativas sobre el punto de entrega (ej. 'Entrega en torniquetes')."
    )
    direccion: Optional[str] = Field(
        default=None, 
        max_length=500, 
        description="Dirección física completa asociada al punto de entrega."
    )

    @field_validator("direccion", mode="before")
    @classmethod
    def coerce_blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        """
        Limpia espacios en blanco y convierte cadenas vacías en None.
        """
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v


class PuntoEntregaUpdate(PuntoEntregaCreate):
    """
    Datos para la actualización completa (PUT) de un punto de entrega.
    """
    nombre: Optional[str] = Field(
        default=None, 
        min_length=1, 
        max_length=150,
        description="Nombre descriptivo actualizado del punto de entrega."
    )


class PuntoEntregaPatch(BaseModel):
    """
    Datos para la actualización parcial (PATCH) de un punto de entrega.
    """
    nombre: Optional[str] = Field(
        default=None, 
        min_length=1, 
        max_length=150,
        description="Nombre descriptivo si se requiere modificar."
    )
    descripcion: Optional[str] = Field(
        default=None,
        description="Notas de entrega modificadas."
    )
    direccion: Optional[str] = Field(
        default=None, 
        max_length=500,
        description="Dirección física modificada."
    )

    @field_validator("direccion", mode="before")
    @classmethod
    def coerce_blank_to_none(cls, v: Optional[str]) -> Optional[str]:
        """
        Limpia espacios en blanco y convierte cadenas vacías en None.
        """
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return None
        return v


class PuntoEntregaRead(BaseModel):
    """
    Esquema de salida que representa los datos expuestos de un punto de entrega.
    """
    id: UUID = Field(
        ..., 
        description="Identificador único (UUID) del punto de entrega."
    )
    usuario_id: UUID = Field(
        ..., 
        description="UUID del usuario propietario del recurso (multi-tenancy)."
    )
    nombre: str = Field(
        ..., 
        description="Nombre descriptivo del punto de entrega."
    )
    descripcion: Optional[str] = Field(
        default=None, 
        description="Notas y referencias del punto de entrega."
    )
    direccion: Optional[str] = Field(
        default=None, 
        description="Dirección física completa asociada."
    )
    fecha_creacion: datetime = Field(
        ..., 
        description="Fecha y hora exactas de creación del recurso."
    )
    fecha_modificacion: Optional[datetime] = Field(
        default=None, 
        description="Fecha y hora de la última modificación (si aplica)."
    )

    model_config = ConfigDict(from_attributes=True)
