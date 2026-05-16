from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.punto_entrega import (
    PuntoEntregaCreate,
    PuntoEntregaUpdate,
    PuntoEntregaPatch,
    PuntoEntregaRead
)
from app.services.punto_entrega_service import PuntoEntregaService

router = APIRouter()


@router.get("/", response_model=List[PuntoEntregaRead])
async def listar_puntos_entrega(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene todos los puntos de entrega activos del usuario."""
    return await PuntoEntregaService.list_activos(db, current_user.id)


@router.post("/", response_model=PuntoEntregaRead, status_code=status.HTTP_201_CREATED)
async def crear_punto_entrega(
    data: PuntoEntregaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea un nuevo punto de entrega."""
    return await PuntoEntregaService.create(db, current_user.id, data)


@router.get("/{punto_entrega_id}", response_model=PuntoEntregaRead)
async def obtener_punto_entrega(
    punto_entrega_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene el detalle de un punto de entrega específico."""
    return await PuntoEntregaService.get_or_404(db, punto_entrega_id, current_user.id)


@router.put("/{punto_entrega_id}", response_model=PuntoEntregaRead)
async def actualizar_punto_entrega(
    punto_entrega_id: UUID,
    data: PuntoEntregaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualiza completamente un punto de entrega."""
    return await PuntoEntregaService.update(db, punto_entrega_id, current_user.id, data)


@router.patch("/{punto_entrega_id}", response_model=PuntoEntregaRead)
async def parchear_punto_entrega(
    punto_entrega_id: UUID,
    data: PuntoEntregaPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Actualiza parcialmente un punto de entrega."""
    return await PuntoEntregaService.patch(db, punto_entrega_id, current_user.id, data)


@router.delete("/{punto_entrega_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_punto_entrega(
    punto_entrega_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft-deletes un punto de entrega."""
    await PuntoEntregaService.soft_delete(db, punto_entrega_id, current_user.id)
