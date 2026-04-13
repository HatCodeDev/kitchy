from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User

from app.schemas.insumo import InsumoCreate, InsumoUpdate, InsumoResponse
from app.schemas.movimiento_insumo import MovimientoCreate
from app.services.insumo_service import InsumoService

# Inicializamos el router. El prefijo se define en main.py, así que aquí lo dejamos vacío.
router = APIRouter()

@router.get("/", response_model=List[InsumoResponse])
async def get_insumos(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene la lista de insumos del usuario autenticado."""
    return await InsumoService.get_insumos(db, usuario_id=current_user.id)

@router.post("/", response_model=InsumoResponse, status_code=status.HTTP_201_CREATED)
async def create_insumo(
    data: InsumoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea un nuevo insumo y registra el stock inicial."""
    return await InsumoService.create_insumo(db, data=data, usuario_id=current_user.id)

@router.get("/{id}", response_model=InsumoResponse)
async def get_insumo(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene los detalles de un insumo específico."""
    return await InsumoService.get_by_id(db, insumo_id=id, usuario_id=current_user.id)

@router.put("/{id}", response_model=InsumoResponse)
async def update_insumo(
    id: UUID,
    data: InsumoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualiza parcialmente los datos de un insumo."""
    return await InsumoService.update_insumo(db, insumo_id=id, data=data, usuario_id=current_user.id)

@router.delete("/{id}")
async def delete_insumo(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Desactiva un insumo (Soft Delete) si no está en uso."""
    await InsumoService.soft_delete(db, insumo_id=id, usuario_id=current_user.id)
    return {"mensaje": "Insumo desactivado correctamente"}

@router.post("/{id}/movimientos", response_model=InsumoResponse)
async def registrar_movimiento(
    id: UUID,
    data: MovimientoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Registra una entrada o salida de inventario transaccionalmente."""
    return await InsumoService.registrar_movimiento(db, insumo_id=id, data=data, usuario_id=current_user.id)