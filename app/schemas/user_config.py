from pydantic import BaseModel, Field
from typing import Optional
from decimal import Decimal


class UserConfigUpdate(BaseModel):
    """
    Esquema para actualización parcial de la configuración global de costos ocultos del usuario.
    """
    empaque_mxn_default: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Costo de empaque global por defecto (debe ser mayor o igual a 0)"
    )
    desgaste_pct_default: Optional[Decimal] = Field(
        default=None,
        ge=0,
        le=100,
        description="Porcentaje de desgaste/gas/luz global por defecto (entre 0 y 100)"
    )
