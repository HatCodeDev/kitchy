"""
Esquemas de validación Pydantic para Temporizadores.

Este módulo define las estructuras de entrada y salida utilizadas para la creación
y el seguimiento del estado de los temporizadores activos en los procesos de producción.
"""
from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class TemporizadorCreate(BaseModel):
    """
    Datos requeridos para iniciar un nuevo temporizador de cocina.
    """
    paso_receta_id: UUID = Field(
        ...,
        description="UUID del paso de la receta asociado al temporizador."
    )
    duracion_segundos: int = Field(
        ...,
        gt=0, 
        description="Duración física programada para el temporizador (medida en segundos). Debe ser mayor a 0."
    )


class TemporizadorResponse(BaseModel):
    """
    Representación detallada de un temporizador devuelta por la API en las consultas y actualizaciones.
    """
    id: UUID = Field(
        ...,
        description="Identificador único (UUID) del temporizador."
    )
    paso_receta_id: UUID = Field(
        ...,
        description="UUID del paso de la receta asociado."
    )
    usuario_id: UUID = Field(
        ...,
        description="UUID del usuario propietario para aislamiento de datos (multi-tenancy)."
    )
    duracion_segundos: int = Field(
        ...,
        description="Duración física total programada en segundos."
    )
    estado: str = Field(
        ...,
        description="Estado operativo actual del temporizador (ej. 'activo', 'finalizado', 'cancelado', 'completado')."
    )
    fecha_inicio: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora exactas en que inició el temporizador."
    )
    fecha_confirmacion: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora exactas en que el usuario silencia o confirma la alarma (si aplica)."
    )

    model_config = ConfigDict(from_attributes=True)

