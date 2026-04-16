from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional, List
from decimal import Decimal
from uuid import UUID
from .insumo import InsumoResponse  # Conexión con el Core de Insumos [cite: 1413, 1556]

# --- Componentes anidados de la Receta ---

class IngredienteCreate(BaseModel):
    """Schema para añadir un insumo a la receta"""
    insumo_id: UUID
    cantidad_usada: Decimal = Field(..., gt=0, description="Cantidad del insumo (mayor a 0)") # [cite: 1325, 1582]
    unidad: str = Field(..., description="Unidad de medida (ej. g, ml, pz)")

class IngredienteResponse(BaseModel):
    """Respuesta detallada para que Flutter vea el nombre y datos del insumo"""
    id: UUID
    insumo: InsumoResponse # Relación directa con el objeto Insumo [cite: 1565, 1584]
    cantidad_usada: Decimal
    unidad: str
    model_config = ConfigDict(from_attributes=True)

class PasoCreate(BaseModel):
    """Schema para los pasos del procedimiento"""
    orden: int = Field(..., gt=0, description="Número de paso (1, 2, 3...)") # [cite: 1326]
    descripcion: str = Field(..., min_length=5, description="Instrucciones del paso")
    duracion_segundos: Optional[int] = Field(default=None, gt=0)
    es_critico: bool = Field(default=False)

class GastoOcultoCreate(BaseModel):
    """Schema para empaques, gas, luz, etc."""
    tipo: Literal['empaque', 'gas_luz'] # [cite: 1326]
    valor: Decimal = Field(..., ge=0)
    es_porcentaje: bool = Field(..., description="True si es %, False si es monto fijo")
    activo: bool = Field(default=False) # Valor por defecto según instrucción [cite: 1326]

class GastoOcultoResponse(GastoOcultoCreate):
    id: UUID
    model_config = ConfigDict(from_attributes=True) # [cite: 1328]

class PasoResponse(PasoCreate):
    id: UUID
    model_config = ConfigDict(from_attributes=True)

# --- Schemas Principales de Receta ---

class RecetaCreate(BaseModel):
    """Datos para crear una receta nueva (POST)"""
    nombre: str = Field(..., max_length=200)
    porciones: int = Field(..., gt=0) # Rechaza porciones=0 [cite: 1327, 1330]
    margen_pct: Decimal = Field(default=Decimal('0.0'), ge=0, le=200) # Rango 0-200% [cite: 1327, 1329]
    ingredientes: List[IngredienteCreate] = Field(..., min_length=1) # Mínimo 1 ingrediente [cite: 1327, 1328]
    pasos: List[PasoCreate] = Field(default=[])

class RecetaResponse(BaseModel):
    """Datos que el servidor devuelve (GET) con el Core Financiero"""
    id: UUID
    usuario_id: UUID # Aislamiento multi-tenant [cite: 1327, 1343]
    nombre: str
    porciones: int
    margen_pct: Decimal
    activa: bool
    ingredientes: List[IngredienteResponse] # Usa respuesta detallada para Flutter [cite: 1327, 1584]
    pasos: List[PasoResponse]
    gastos_ocultos: List[GastoOcultoResponse]
    costo_calculado: Optional[Decimal] = Field(default=None) # Campo computado opcional [cite: 1324, 1327]

    model_config = ConfigDict(from_attributes=True) # Permite lectura desde DB [cite: 1327, 1331]