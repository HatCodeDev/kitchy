"""
Esquemas de validación Pydantic para Insumos.

Este módulo define las estructuras de entrada y salida utilizadas para la creación,
actualización, consulta y registro de movimientos de stock para la gestión de insumos.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID


class InsumoBase(BaseModel):
    """
    Atributos base compartidos para representar un insumo de cocina.
    """
    nombre: str = Field(
        ..., 
        max_length=200, 
        description="Nombre descriptivo del insumo (ej. Harina de Trigo, Leche Entera)."
    )
    unidad: Literal['kg', 'g', 'l', 'ml', 'pz', 'caja', 'taza'] = Field(
        ..., 
        description="Unidad de medida estándar utilizada para recetas y control de stock."
    )
    precio_compra: Decimal = Field(
        ..., 
        gt=0, 
        description="Precio total pagado en la última compra (en MXN). Debe ser mayor estricto que 0."
    )
    cantidad_comprada: Decimal = Field(
        ..., 
        gt=0, 
        description="Cantidad del insumo adquirida en la última compra. Debe ser mayor estricto que 0."
    )
    alerta_minimo: Decimal = Field(
        default=Decimal('0.0'), 
        ge=0, 
        description="Umbral mínimo de inventario que activa una alerta visual de desabasto. Debe ser >= 0."
    )


class InsumoCreate(InsumoBase):
    """
    Datos requeridos para la creación de un nuevo insumo (POST).
    Hereda todos los atributos definidos en InsumoBase.
    """
    pass


class InsumoUpdate(BaseModel):
    """
    Datos para la actualización parcial de un insumo (PATCH).
    Permite modificar atributos individuales sin requerir el envío del objeto completo.
    """
    nombre: Optional[str] = Field(
        default=None, 
        max_length=200, 
        description="Nuevo nombre descriptivo del insumo si se desea actualizar."
    )
    unidad: Optional[Literal['kg', 'g', 'l', 'ml', 'pz', 'caja', 'taza']] = Field(
        default=None, 
        description="Nueva unidad de medida estándar si se requiere cambiar."
    )
    precio_compra: Optional[Decimal] = Field(
        default=None, 
        gt=0, 
        description="Nuevo precio de compra (en MXN) para actualizar el costo unitario base."
    )
    cantidad_comprada: Optional[Decimal] = Field(
        default=None, 
        gt=0, 
        description="Nueva cantidad de compra para asociar al nuevo precio."
    )
    alerta_minimo: Optional[Decimal] = Field(
        default=None, 
        ge=0, 
        description="Nuevo umbral de alerta mínimo para control de existencias."
    )


class InsumoResponse(InsumoBase):
    """
    Representación completa de un insumo persistido entregada en las respuestas de la API.
    """
    id: UUID = Field(
        ..., 
        description="Identificador único (UUID) del insumo en la base de datos."
    )
    usuario_id: UUID = Field(
        ..., 
        description="UUID del usuario propietario del insumo (aislamiento multi-tenancy)."
    )
    cantidad_actual: Decimal = Field(
        ..., 
        description="Inventario neto actual calculado automáticamente tras compras y consumos."
    )
    fecha_ultimo_precio: date = Field(
        ..., 
        description="Fecha en la cual se registró el último precio de compra."
    )
    activo: bool = Field(
        ..., 
        description="Estado de activación lógica. False indica eliminación lógica o suspensión de uso."
    )

    model_config = ConfigDict(from_attributes=True)


class MovimientoCreate(BaseModel):
    """
    Esquema de entrada para registrar un ajuste manual o movimiento de stock de un insumo.
    """
    tipo: Literal['entrada', 'salida'] = Field(
        ..., 
        description="Dirección del flujo de stock: 'entrada' (suma al inventario) o 'salida' (descuenta)."
    )
    cantidad: Decimal = Field(
        ..., 
        gt=0, 
        description="Cantidad física de producto a mover. Debe ser mayor a 0."
    )
    motivo: Literal['compra', 'uso_produccion', 'merma'] = Field(
        ..., 
        description="Clasificación de negocio para justificar la alteración de existencias."
    )


class MovimientoResponse(MovimientoCreate):
    """
    Representación detallada de un registro de movimiento de stock devuelto por la API.
    """
    id: UUID = Field(
        ..., 
        description="Identificador único del registro de movimiento."
    )
    insumo_id: UUID = Field(
        ..., 
        description="UUID del insumo afectado por el movimiento."
    )
    usuario_id: UUID = Field(
        ..., 
        description="UUID del usuario propietario del recurso."
    )
    fecha: datetime = Field(
        ..., 
        description="Fecha y hora exactas en que se registró la transacción en el sistema."
    )

    model_config = ConfigDict(from_attributes=True)