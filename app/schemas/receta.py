"""
Esquemas de validación Pydantic para Recetas y sus Componentes.

Este módulo define los esquemas necesarios para estructurar las recetas, sus ingredientes,
los pasos del procedimiento, la configuración de gastos ocultos asociados, y las respuestas
con cálculos financieros incorporados (costo por porción y precio sugerido).
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Literal, Optional, List
from decimal import Decimal
from uuid import UUID
from .insumo import InsumoResponse


# ==============================================================================
# COMPONENTES ANIDADOS DE LA RECETA
# ==============================================================================

class IngredienteCreate(BaseModel):
    """
    Datos requeridos para añadir un insumo específico a una receta.
    """
    insumo_id: UUID = Field(
        ...,
        description="UUID del insumo de cocina a vincular."
    )
    cantidad_usada: Decimal = Field(
        ..., 
        gt=0, 
        description="Cantidad física del insumo requerida para la receta entera. Debe ser mayor a 0."
    )
    unidad: str = Field(
        ..., 
        description="Unidad de medida empleada (ej. g, ml, pz, taza) que se convertirá automáticamente al calcular costos."
    )


class IngredienteResponse(BaseModel):
    """
    Representación detallada de un ingrediente dentro de una receta, incluyendo metadatos del insumo.
    """
    id: UUID = Field(
        ...,
        description="UUID único del registro de ingrediente de receta."
    )
    insumo: InsumoResponse = Field(
        ...,
        description="Relación completa con el objeto Insumo asociado para visualizar nombres y costos actualizados."
    )
    cantidad_usada: Decimal = Field(
        ...,
        description="Cantidad física de insumo consumida."
    )
    unidad: str = Field(
        ...,
        description="Unidad de medida empleada en la receta."
    )

    model_config = ConfigDict(from_attributes=True)


class PasoCreate(BaseModel):
    """
    Datos requeridos para definir un paso del procedimiento de preparación de la receta.
    """
    orden: int = Field(
        ..., 
        gt=0, 
        description="Número correlativo de orden secuencial del paso (1, 2, 3...)."
    )
    descripcion: str = Field(
        ..., 
        min_length=5, 
        description="Instrucciones paso a paso del procedimiento de cocina."
    )
    duracion: Optional[Decimal] = Field(
        default=None, 
        ge=0,
        description="Valor numérico de duración en la unidad temporal indicada (ej. 15.5)."
    )
    unidad: Optional[str] = Field(
        default="seg", 
        description="Unidad de medida de tiempo (seg = segundos, min = minutos, hr = horas)."
    )
    duracion_segundos: Optional[int] = Field(
        default=None, 
        ge=0,
        description="Cálculo normalizado en segundos (ej. para programar alarmas de temporizador)."
    )
    es_critico: bool = Field(
        default=False,
        description="Marca true si el paso es un Punto de Control Crítico que requiere supervisión estrecha o alarma obligatoria."
    )


class GastoOcultoCreate(BaseModel):
    """
    Datos para configurar un recargo por concepto de empaque, servicios u otros costos indirectos.
    """
    tipo: Literal['empaque', 'gas_luz'] = Field(
        ...,
        description="Clasificación del costo oculto."
    )
    valor: Decimal = Field(
        ..., 
        ge=0,
        description="Valor nominal del gasto (puede ser monto fijo en MXN o tasa porcentual)."
    )
    es_porcentaje: bool = Field(
        ..., 
        description="True si el costo se calcula como un porcentaje sobre el costo de ingredientes; False si es una cuota fija en pesos."
    )
    activo: bool = Field(
        default=False,
        description="Determina si el gasto oculto está activo y se incluye en el cálculo actual de la receta."
    )


class GastoOcultoResponse(GastoOcultoCreate):
    """
    Representación de salida de un gasto oculto asociado a la receta.
    """
    id: UUID = Field(
        ...,
        description="Identificador único (UUID) de la regla de costo oculto."
    )

    model_config = ConfigDict(from_attributes=True)


class PasoResponse(PasoCreate):
    """
    Representación de salida de un paso del procedimiento.
    """
    id: UUID = Field(
        ...,
        description="Identificador único (UUID) del paso de la receta."
    )

    model_config = ConfigDict(from_attributes=True)


# ==============================================================================
# SCHEMAS PRINCIPALES DE RECETA
# ==============================================================================

class RecetaCreate(BaseModel):
    """
    Esquema de entrada para crear una nueva receta completa con ingredientes y pasos.
    """
    nombre: str = Field(
        ..., 
        max_length=200,
        description="Nombre descriptivo de la receta (ej. Pastel Fudge de Chocolate)."
    )
    porciones: int = Field(
        ..., 
        gt=0,
        description="Rendimiento neto de la receta medido en porciones (rebanadas, piezas, kg)."
    )
    margen_pct: Decimal = Field(
        default=Decimal('0.0'), 
        ge=0, 
        le=200,
        description="Porcentaje de ganancia deseado (sobre el costo total de insumos y gastos ocultos) para fijar el precio sugerido."
    )
    ingredientes: List[IngredienteCreate] = Field(
        ..., 
        min_length=1,
        description="Listado obligatorio con al menos un insumo para costear la receta."
    )
    pasos: List[PasoCreate] = Field(
        default=[],
        description="Procedimiento ordenado de cocina opcional para el control de temporizadores."
    )


class RecetaResponse(BaseModel):
    """
    Esquema de salida detallado de una receta incluyendo el desglose financiero en tiempo real.
    """
    id: UUID = Field(
        ..., 
        description="Identificador único (UUID) de la receta."
    )
    usuario_id: UUID = Field(
        ..., 
        description="UUID del usuario propietario de la receta (aislamiento multi-tenancy)."
    )
    nombre: str = Field(
        ..., 
        description="Nombre descriptivo de la receta."
    )
    porciones: int = Field(
        ..., 
        description="Rendimiento o número total de porciones de la preparación."
    )
    margen_pct: Decimal = Field(
        ..., 
        description="Porcentaje de utilidad neta configurado para costeo de margen de ganancia."
    )
    activa: bool = Field(
        ..., 
        description="Indica si la receta se encuentra activa para su venta y producción."
    )
    ingredientes: List[IngredienteResponse] = Field(
        ..., 
        description="Detalle de ingredientes asociados con costo dinámico de mercado."
    )
    pasos: List[PasoResponse] = Field(
        ..., 
        description="Listado secuencial de pasos de preparación."
    )
    gastos_ocultos: List[GastoOcultoResponse] = Field(
        ..., 
        description="Desglose de recargos activos por empaque y desgaste aplicados."
    )
    costo_por_porcion: Optional[Decimal] = Field(
        default=None, 
        description="Costo unitario calculado en tiempo real (Costo Total de Receta / Porciones)."
    )
    precio_sugerido: Optional[Decimal] = Field(
        default=None, 
        description="Precio de venta mínimo recomendado aplicando el margen_pct y gastos ocultos."
    )

    model_config = ConfigDict(from_attributes=True)


class ToggleGastoRequest(BaseModel):
    """
    Esquema de entrada para activar o desactivar dinámicamente un gasto oculto de la receta.
    """
    activo: bool = Field(
        ...,
        description="Establece a true para aplicar el cargo en los cálculos financieros o false para ignorarlo."
    )


class RecetaUpdate(BaseModel):
    """
    Esquema de entrada para realizar actualizaciones parciales en la configuración de la receta.
    """
    nombre: Optional[str] = Field(
        default=None,
        description="Nombre descriptivo actualizado."
    )
    porciones: Optional[int] = Field(
        default=None, 
        gt=0,
        description="Nuevo número de porciones."
    )
    margen_pct: Optional[Decimal] = Field(
        default=None, 
        ge=0, 
        le=200,
        description="Nuevo porcentaje de ganancia."
    )
    ingredientes: Optional[List[IngredienteCreate]] = Field(
        default=None,
        description="Nueva lista completa de ingredientes. Reemplaza la anterior si se especifica."
    )
    pasos: Optional[List[PasoCreate]] = Field(
        default=None,
        description="Nuevo procedimiento ordenado de cocina. Reemplaza los pasos anteriores si se especifica."
    )