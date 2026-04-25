from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.pedido import PedidoCreate, PedidoUpdate, PedidoResponse
from app.services.pedido_service import PedidoService

router = APIRouter()

@router.post("/", response_model=PedidoResponse, status_code=status.HTTP_201_CREATED)
async def crear_pedido(
    data: PedidoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Crea un pedido nuevo con sus líneas de detalle."""
    return await PedidoService.create_pedido(db, data, current_user.id)

@router.get("/", response_model=List[PedidoResponse])
async def listar_pedidos(
    estado: Optional[str] = Query(None, description="Filtrar por estado: pendiente, en_preparacion, listo, entregado, cancelado"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene la agenda de pedidos ordenada cronológicamente."""
    return await PedidoService.get_pedidos(db, current_user.id, estado, limit, offset)

@router.get("/{pedido_id}", response_model=PedidoResponse)
async def obtener_pedido(
    pedido_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtiene el detalle completo de un pedido específico."""
    return await PedidoService.get_by_id(db, pedido_id, current_user.id)

@router.patch("/{pedido_id}/estado", response_model=PedidoResponse)
async def cambiar_estado_pedido(
    pedido_id: UUID,
    nuevo_estado: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ejecuta una transición en la máquina de estados.
    Gatilla el descuento de inventario si el estado pasa a 'entregado'.
    """
    return await PedidoService.cambiar_estado(db, pedido_id, nuevo_estado, current_user.id)

@router.delete("/{pedido_id}", response_model=PedidoResponse)
async def cancelar_pedido(
    pedido_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete: Cambia el estado del pedido a 'cancelado'."""
    return await PedidoService.cambiar_estado(db, pedido_id, "cancelado", current_user.id)