"""
Esquemas de validación Pydantic para Movimientos de Insumos.

Este módulo define los esquemas utilizados exclusivamente para validar la creación
de movimientos de stock e historiales de transacciones sobre los insumos.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from decimal import Decimal
from datetime import datetime
from uuid import UUID


class MovimientoCreate(BaseModel):
    """
    Esquema de entrada para registrar una transacción de stock manual (entrada/salida).
    """
    tipo: Literal['entrada', 'salida'] = Field(
        ...,
        description="Tipo de movimiento físico de inventario: 'entrada' para incrementos o 'salida' para decrementos."
    )

    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad neta a transaccionar. Debe ser mayor estricto a cero."
    )

    motivo: Literal['compra', 'uso_produccion', 'merma'] = Field(
        ...,
        description="Motivo o justificación comercial del movimiento para auditorías de inventario."
    )


class MovimientoResponse(BaseModel):
    """
    Esquema de salida que representa el registro completo de una transacción de stock.
    """
    id: UUID = Field(
        ...,
        description="Identificador único (UUID) de la transacción del movimiento."
    )
    insumo_id: UUID = Field(
        ...,
        description="Identificador único del insumo afectado."
    )
    usuario_id: UUID = Field(
        ...,
        description="UUID del usuario propietario para el aislamiento de datos multi-tenancy."
    )
    tipo: str = Field(
        ...,
        description="Tipo de movimiento registrado ('entrada' o 'salida')."
    )
    cantidad: Decimal = Field(
        ...,
        description="Cantidad física que fue alterada en el inventario."
    )
    motivo: str = Field(
        ...,
        description="Motivo registrado para justificar el movimiento."
    )
    fecha: datetime = Field(
        ...,
        description="Fecha y hora de creación de la transacción."
    )

    model_config = ConfigDict(from_attributes=True)