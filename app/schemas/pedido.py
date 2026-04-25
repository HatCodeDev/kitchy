from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal


# SCHEMAS DE LÍNEAS DE PEDIDO

class LineaPedidoCreate(BaseModel):
    """Datos requeridos para añadir un producto al pedido"""
    nombre_producto: str = Field(..., min_length=1, max_length=200)
    cantidad_porciones: int = Field(..., gt=0, description="Debe ser mayor a 0")
    precio_acordado_mxn: Decimal = Field(..., ge=0, description="No puede ser negativo")
    receta_id: Optional[UUID] = Field(default=None, description="Opcional: Si está vinculado a una receta")


class LineaPedidoResponse(LineaPedidoCreate):
    """Respuesta con los datos guardados de la línea"""
    id: UUID
    pedido_id: UUID

    model_config = ConfigDict(from_attributes=True)


# SCHEMAS DE PEDIDO

class PedidoCreate(BaseModel):
    """Payload que envía el Frontend para crear un Pedido Completo"""
    cliente_nombre: str = Field(..., min_length=1, max_length=150)
    # Patrón estricto: Exactamente 10 dígitos del 0 al 9
    cliente_whatsapp: Optional[str] = Field(default=None, pattern=r'^[0-9]{10}$')
    fecha_entrega: datetime
    punto_entrega: Optional[str] = Field(default=None, max_length=255)
    notas: Optional[str] = None

    # Exige al menos 1 línea (no se puede crear un pedido vacío)
    lineas: List[LineaPedidoCreate] = Field(..., min_length=1)

    @field_validator('fecha_entrega')
    @classmethod
    def validar_fecha_futura(cls, v: datetime) -> datetime:
        """Asegura que no se puedan agendar pedidos en el pasado"""
        # Si la fecha viene "naive" (sin zona horaria), le forzamos UTC para comparar correctamente
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)

        if v < datetime.now(timezone.utc):
            raise ValueError('La fecha de entrega debe ser en el futuro')
        return v


class PedidoUpdate(BaseModel):
    """Payload para editar datos básicos (No incluye líneas ni estado)"""
    cliente_nombre: Optional[str] = Field(default=None, min_length=1, max_length=150)
    cliente_whatsapp: Optional[str] = Field(default=None, pattern=r'^[0-9]{10}$')
    fecha_entrega: Optional[datetime] = None
    punto_entrega: Optional[str] = Field(default=None, max_length=255)
    notas: Optional[str] = None

    @field_validator('fecha_entrega')
    @classmethod
    def validar_fecha_futura(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None:
            if v.tzinfo is None:
                v = v.replace(tzinfo=timezone.utc)
            if v < datetime.now(timezone.utc):
                raise ValueError('La fecha de entrega debe ser en el futuro')
        return v


class PedidoResponse(BaseModel):
    """El objeto completo que FastAPI devuelve al Frontend"""
    id: UUID
    usuario_id: UUID
    cliente_nombre: str
    cliente_whatsapp: Optional[str] = None
    fecha_entrega: datetime
    punto_entrega: Optional[str] = None
    estado: str
    notas: Optional[str] = None

    # Anidamos las líneas mapeadas de la DB
    lineas: List[LineaPedidoResponse]

    # Campo computado que llenaremos en el Router usando utils
    whatsapp_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)