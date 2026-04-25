from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Literal
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.receta import (
    RecetaCreate,
    RecetaResponse,
    GastoOcultoCreate,
    GastoOcultoResponse,
    ToggleGastoRequest,
    RecetaUpdate
)
from app.services.receta_service import RecetaService
from app.services.hidden_cost_service import HiddenCostService

router = APIRouter()

@router.get("/", response_model=List[RecetaResponse])
async def get_recetas(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista las recetas activas del usuario."""
    return await RecetaService.get_all(db, current_user.id)

@router.post("/", response_model=RecetaResponse, status_code=status.HTTP_201_CREATED)
async def create_receta(
    data: RecetaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea una receta con ingredientes, pasos y gastos por defecto en una sola transacción."""
    return await RecetaService.create_receta(db, data, current_user.id)

@router.get("/{id}", response_model=RecetaResponse)
async def get_receta(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene el detalle completo de una receta."""
    return await RecetaService.get_by_id(db, id, current_user.id)

@router.put("/{id}", response_model=RecetaResponse)
async def update_receta(
    id: UUID,
    data: RecetaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualiza datos básicos de la receta y sus relaciones (ingredientes/pasos)."""
    return await RecetaService.update_receta(db, id, data, current_user.id)

@router.delete("/{id}")
async def delete_receta(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete de la receta."""
    await RecetaService.delete_receta(db, id, current_user.id)
    return {"mensaje": "Receta desactivada correctamente"}

@router.get("/{id}/costeo", response_model=Dict[str, Any])
async def calcular_costo_receta(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Ejecuta el Core Financiero y retorna el desglose exacto de rentabilidad."""
    return await RecetaService.calcular_costeo(db, id, current_user.id)

@router.post("/{id}/gastos-ocultos", response_model=GastoOcultoResponse)
async def upsert_gasto_oculto(
    id: UUID,
    data: GastoOcultoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea o actualiza los valores (monto/porcentaje) de un gasto oculto."""
    # Reutilizamos el método toggle_gasto que armamos en la E6-09,
    # pasándole los valores completos del schema.
    return await HiddenCostService.toggle_gasto(
        db=db,
        receta_id=id,
        tipo=data.tipo,
        activo=data.activo,
        usuario_id=current_user.id,
        valor=data.valor,
        es_porcentaje=data.es_porcentaje
    )

@router.patch("/{id}/gastos-ocultos/{tipo}/toggle", response_model=GastoOcultoResponse)
async def toggle_gasto_oculto(
    id: UUID,
    tipo: Literal['empaque', 'gas_luz'],
    data: ToggleGastoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Activa o desactiva un gasto oculto (Fallback Upsert)."""
    return await HiddenCostService.toggle_gasto(db, id, tipo, data.activo, current_user.id)