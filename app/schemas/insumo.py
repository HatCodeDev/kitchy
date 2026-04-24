from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID


class InsumoBase(BaseModel):
    """Atributos base que comparten la creación y la respuesta"""
    nombre: str = Field(..., max_length=200, description="Nombre descriptivo del insumo")
    unidad: Literal['kg', 'g', 'l', 'ml', 'pz', 'caja', 'taza'] = Field(
        ..., description="Unidad de medida estandarizada"
    )

    # Usamos Decimal para exactitud financiera. gt=0 significa "Greater Than 0" (mayor estricto que 0).
    # Esto es 'Defensa en Profundidad': Pydantic bloquea un -5 aquí antes de que toque la BD.
    precio_compra: Decimal = Field(..., gt=0, description="Precio total de la compra (mayor a 0)")
    cantidad_comprada: Decimal = Field(..., gt=0, description="Cantidad adquirida (mayor a 0)")

    # ge=0 significa "Greater or Equal to 0" (puede ser 0 si no quieren usar alertas)
    alerta_minimo: Decimal = Field(default=Decimal('0.0'), ge=0, description="Cantidad mínima para disparar alerta")


class InsumoCreate(InsumoBase):
    """Datos requeridos para crear un insumo nuevo (POST)"""
    pass  # Hereda todo tal cual de InsumoBase


class InsumoUpdate(BaseModel):
    """
    Datos para actualizar un insumo (PATCH).
    Todos los campos son Opcionales porque el cliente podría querer actualizar
    solo el precio, sin enviar de nuevo el nombre o la unidad.
    """
    nombre: Optional[str] = Field(default=None, max_length=200)
    unidad: Optional[Literal['kg', 'g', 'l', 'ml', 'pz', 'caja', 'taza']] = Field(default=None)
    precio_compra: Optional[Decimal] = Field(default=None, gt=0)
    cantidad_comprada: Optional[Decimal] = Field(default=None, gt=0)
    alerta_minimo: Optional[Decimal] = Field(default=None, ge=0)


class InsumoResponse(InsumoBase):
    """Datos que el servidor le devuelve al cliente (GET, respuesta de POST/PATCH)"""
    id: UUID = Field(..., description="ID único del insumo")
    usuario_id: UUID = Field(..., description="Dueño del insumo")
    cantidad_actual: Decimal = Field(..., description="Inventario actual en bodega")
    fecha_ultimo_precio: date = Field(..., description="Fecha del registro o última actualización")
    activo: bool = Field(..., description="Estado lógico del insumo")

    # Esto le dice a Pydantic: "Puedes leer datos de un objeto SQLAlchemy directo"
    model_config = ConfigDict(from_attributes=True)

class MovimientoCreate(BaseModel):
    tipo: Literal['entrada', 'salida']
    cantidad: Decimal
    motivo: Literal['compra', 'uso_produccion', 'merma']

# AGREGAR ESTO:
class MovimientoResponse(MovimientoCreate):
    id: UUID
    insumo_id: UUID
    usuario_id: UUID
    fecha: datetime

    model_config = ConfigDict(from_attributes=True)