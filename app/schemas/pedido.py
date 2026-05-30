"""
Esquemas de validación Pydantic para Pedidos y Líneas de Pedidos.

Este módulo define las estructuras de datos (entrada, actualización y salida)
para gestionar el flujo transaccional de los pedidos, sus líneas individuales,
y la resolución de colisiones en los horarios de entrega.
"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal


# ==============================================================================
# SCHEMAS DE LÍNEAS DE PEDIDO
# ==============================================================================

class LineaPedidoCreate(BaseModel):
    """
    Datos requeridos para añadir un producto o artículo a un pedido.
    """
    nombre_producto: str = Field(
        ..., 
        min_length=1, 
        max_length=200,
        description="Nombre comercial del producto terminado (ej. Pastel de Tres Leches)."
    )
    cantidad_porciones: int = Field(
        ..., 
        gt=0, 
        description="Cantidad física de unidades o porciones a producir. Debe ser mayor a 0."
    )
    precio_acordado_mxn: Decimal = Field(
        ..., 
        ge=0, 
        description="Precio de venta unitario acordado con el cliente (en MXN). Debe ser >= 0."
    )
    receta_id: Optional[UUID] = Field(
        default=None, 
        description="UUID de la receta si el producto está vinculado a una receta para cálculo automático de costos e inventario."
    )


class LineaPedidoResponse(LineaPedidoCreate):
    """
    Representación completa de una línea de pedido persistida devuelta por la API.
    """
    id: UUID = Field(
        ..., 
        description="Identificador único (UUID) de la línea de pedido."
    )
    pedido_id: UUID = Field(
        ..., 
        description="UUID del pedido padre al que pertenece esta línea."
    )

    model_config = ConfigDict(from_attributes=True)


class ColisionHoraResponse(BaseModel):
    """
    Estructura de respuesta que detalla si existe una superposición horaria en la entrega de pedidos.
    """
    hay_colision: bool = Field(
        ..., 
        description="Indica si existe conflicto de horario con otros pedidos en el mismo rango de tiempo."
    )
    cantidad: int = Field(
        ..., 
        description="Número total de pedidos en conflicto detectados dentro del rango horario."
    )
    hora_inicio: str = Field(
        ..., 
        description="Hora de inicio del rango horario evaluado (ej. '14:00')."
    )
    hora_fin: str = Field(
        ..., 
        description="Hora de finalización del rango horario evaluado (ej. '16:00')."
    )


# ==============================================================================
# SCHEMAS DE PEDIDO
# ==============================================================================

class PedidoCreate(BaseModel):
    """
    Estructura de entrada requerida para registrar un pedido completo con sus respectivas líneas.
    """
    cliente_nombre: str = Field(
        ..., 
        min_length=1, 
        max_length=150,
        description="Nombre completo del cliente."
    )
    cliente_whatsapp: Optional[str] = Field(
        default=None, 
        pattern=r'^[0-9]{10}$',
        description="Número de WhatsApp del cliente. Debe constar exactamente de 10 dígitos numéricos.",
        examples=["5512345678"]
    )
    fecha_entrega: datetime = Field(
        ...,
        description="Fecha y hora pactada para la entrega del pedido. Debe especificarse en el futuro."
    )
    punto_entrega: Optional[str] = Field(
        default=None, 
        max_length=255,
        description="Descripción corta o nombre descriptivo del punto de entrega informal."
    )
    punto_entrega_id: Optional[UUID] = Field(
        default=None, 
        description="UUID de un Punto de Entrega formal registrado previamente (si aplica)."
    )
    notas: Optional[str] = Field(
        default=None,
        description="Comentarios adicionales o anotaciones especiales del pedido (ej. 'Sin nueces')."
    )
    lineas: List[LineaPedidoCreate] = Field(
        ..., 
        min_length=1,
        description="Listado con al menos una línea de producto que compone el pedido."
    )

    @field_validator('fecha_entrega')
    @classmethod
    def validar_fecha_futura(cls, v: datetime) -> datetime:
        """
        Garantiza que no se puedan agendar pedidos con fecha/hora de entrega en el pasado.
        """
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)

        if v < datetime.now(timezone.utc):
            raise ValueError('La fecha de entrega debe ser en el futuro')
        return v


class PedidoUpdate(BaseModel):
    """
    Estructura de entrada para la actualización parcial o total de los datos de un pedido.
    """
    cliente_nombre: Optional[str] = Field(
        default=None, 
        min_length=1, 
        max_length=150,
        description="Nuevo nombre completo del cliente."
    )
    cliente_whatsapp: Optional[str] = Field(
        default=None, 
        pattern=r'^[0-9]{10}$',
        description="Nuevo número de WhatsApp de 10 dígitos numéricos."
    )
    fecha_entrega: Optional[datetime] = Field(
        default=None,
        description="Nueva fecha y hora de entrega para reprogramación."
    )
    punto_entrega: Optional[str] = Field(
        default=None, 
        max_length=255,
        description="Nueva descripción del punto de entrega informal."
    )
    punto_entrega_id: Optional[UUID] = Field(
        default=None, 
        description="UUID del punto de entrega formal si se desea asociar uno registrado."
    )
    notas: Optional[str] = Field(
        default=None,
        description="Notas de preparación modificadas."
    )
    lineas: Optional[List[LineaPedidoCreate]] = Field(
        default=None,
        description="Nueva colección completa de líneas de pedido. Si se envía, reemplaza las líneas anteriores."
    )

    @field_validator('fecha_entrega')
    @classmethod
    def validar_fecha_futura(cls, v: Optional[datetime]) -> Optional[datetime]:
        """
        Normaliza la zona horaria del campo fecha de entrega a UTC.
        """
        if v is not None:
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
        return v


class PedidoResponse(BaseModel):
    """
    Representación completa de un pedido detallado devuelto en las respuestas de la API.
    """
    id: UUID = Field(
        ..., 
        description="Identificador único (UUID) del pedido."
    )
    usuario_id: UUID = Field(
        ..., 
        description="UUID del usuario propietario (aislamiento multi-tenancy)."
    )
    cliente_nombre: str = Field(
        ..., 
        description="Nombre completo del cliente."
    )
    cliente_whatsapp: Optional[str] = Field(
        default=None, 
        description="Número telefónico de WhatsApp de 10 dígitos."
    )
    fecha_entrega: datetime = Field(
        ..., 
        description="Fecha y hora pactada para la entrega en formato ISO-8601."
    )
    punto_entrega: Optional[str] = Field(
        default=None, 
        description="Descripción corta del punto de entrega informal."
    )
    estado: str = Field(
        ..., 
        description="Estado operativo actual del pedido (ej. 'pendiente', 'en_produccion', 'completado', 'cancelado')."
    )
    notas: Optional[str] = Field(
        default=None, 
        description="Comentarios, requerimientos de alérgenos o notas de personalización."
    )
    lineas: List[LineaPedidoResponse] = Field(
        ..., 
        description="Listado detallado de todas las líneas de productos añadidas a este pedido."
    )
    whatsapp_url: Optional[str] = Field(
        default=None, 
        description="Enlace dinámico pregenerado para iniciar conversación directa en WhatsApp con el mensaje de confirmación."
    )
    punto_entrega_display: Optional[str] = Field(
        default=None, 
        description="Texto amigable que representa el punto de entrega (nombre del punto formal o descripción del informal)."
    )
    punto_entrega_direccion: Optional[str] = Field(
        default=None, 
        description="Dirección física completa asociada al punto de entrega formal (si aplica)."
    )

    model_config = ConfigDict(from_attributes=True)