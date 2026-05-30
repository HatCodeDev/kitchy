"""
Esquemas de validación Pydantic para Notificaciones.

Este módulo define los esquemas de transferencia de datos utilizados para la consulta,
programación y visualización del estado de las alertas y notificaciones del sistema.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class NotificacionBase(BaseModel):
    """
    Atributos base que definen una notificación programada en el sistema.
    """
    tipo: str = Field(
        ...,
        description="Tipo de notificación o canal a emplear (ej. 'alerta_insumo', 'whatsapp_pedido')."
    )
    fecha_programada: datetime = Field(
        ...,
        description="Fecha y hora en la que el job asíncrono debe procesar y enviar la alerta."
    )
    pedido_id: Optional[UUID] = Field(
        default=None,
        description="UUID del pedido asociado a la notificación (si aplica)."
    )
    insumo_id: Optional[UUID] = Field(
        default=None,
        description="UUID del insumo asociado a la alerta de desabasto (si aplica)."
    )


class NotificacionRead(NotificacionBase):
    """
    Esquema de salida para la visualización detallada del estado de una notificación.
    """
    id: UUID = Field(
        ...,
        description="Identificador único (UUID) de la notificación."
    )
    enviada: bool = Field(
        ...,
        description="Indica si la notificación ya fue procesada y enviada de forma exitosa."
    )
    fecha_envio: Optional[datetime] = Field(
        default=None,
        description="Fecha y hora exactas en que se realizó el envío efectivo."
    )
    
    model_config = ConfigDict(from_attributes=True)

