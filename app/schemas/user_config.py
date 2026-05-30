"""
Esquemas de validación Pydantic para Configuración de Usuario.

Este módulo define los esquemas necesarios para actualizar las preferencias y
parámetros globales de cálculo de costos de un usuario.
"""
from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class UserConfigUpdate(BaseModel):
    """
    Esquema para la actualización parcial de la configuración global de costos ocultos del usuario.
    """
    empaque_mxn_default: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Costo de empaque global predeterminado (en MXN) aplicado a nuevas recetas/pedidos. Debe ser >= 0."
    )
    desgaste_pct_default: Optional[Decimal] = Field(
        default=None,
        ge=0,
        le=100,
        description="Porcentaje de recargo global por defecto para cubrir desgaste de activos, servicios u otros costos indirectos (entre 0% y 100%)."
    )

