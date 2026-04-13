from pydantic import BaseModel, Field, ConfigDict
from typing import Literal
from decimal import Decimal
from datetime import datetime
from uuid import UUID


class MovimientoCreate(BaseModel):
    """
    Schema para la entrada de datos.
    Validamos tipo y motivo usando Literal para que FastAPI devuelva
    un error 422 automático si el cliente envía algo diferente.
    """
    tipo: Literal['entrada', 'salida'] = Field(
        ...,
        description="Tipo de movimiento: entrada (suma stock) o salida (resta stock)"
    )

    cantidad: Decimal = Field(
        ...,
        gt=0,
        description="Cantidad del movimiento, debe ser mayor a cero"
    )

    motivo: Literal['compra', 'uso_produccion', 'merma'] = Field(
        ...,
        description="Motivo del movimiento para trazabilidad"
    )


class MovimientoResponse(BaseModel):
    """
    Schema para la salida de datos.
    Incluimos todos los campos necesarios para que el Frontend
    pueda mostrar el historial completo.
    """
    id: UUID
    insumo_id: UUID
    usuario_id: UUID
    tipo: str
    cantidad: Decimal
    motivo: str
    fecha: datetime

    # Permite mapear directamente desde el modelo SQLAlchemy MovimientoInsumo
    model_config = ConfigDict(from_attributes=True)