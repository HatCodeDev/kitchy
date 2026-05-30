"""
Controlador de Puntos de Entrega.

Este router expone los endpoints CRUD para gestionar los puntos de entrega física del usuario,
permitiendo la creación, consulta, edición completa/parcial y desactivación lógica (soft delete).
"""
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
    """
    Obtiene todos los puntos de entrega activos del usuario autenticado.

    ### Ordenamiento:
    * Se retornan ordenados alfabéticamente por su nombre.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PuntoEntregaService.list_activos(db, current_user.id)


@router.post("/", response_model=PuntoEntregaRead, status_code=status.HTTP_201_CREATED)
async def crear_punto_entrega(
    data: PuntoEntregaCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Registra una nueva ubicación o punto de entrega recurrente.

    ### Regla de negocio (R2):
    * Valida que el nombre de la ubicación no esté duplicado con otro punto de entrega activo del usuario.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PuntoEntregaService.create(db, current_user.id, data)


@router.get("/{punto_entrega_id}", response_model=PuntoEntregaRead)
async def obtener_punto_entrega(
    punto_entrega_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene el detalle completo de un punto de entrega específico.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).

    ### Respuestas:
    * **404 Not Found**: Si la ubicación no existe, está inactiva o pertenece a otro usuario.
    """
    return await PuntoEntregaService.get_or_404(db, punto_entrega_id, current_user.id)


@router.put("/{punto_entrega_id}", response_model=PuntoEntregaRead)
async def actualizar_punto_entrega(
    punto_entrega_id: UUID,
    data: PuntoEntregaUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza de forma completa las propiedades de un punto de entrega específico.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PuntoEntregaService.update(db, punto_entrega_id, current_user.id, data)


@router.patch("/{punto_entrega_id}", response_model=PuntoEntregaRead)
async def parchear_punto_entrega(
    punto_entrega_id: UUID,
    data: PuntoEntregaPatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza de forma parcial (PATCH) uno o más campos de un punto de entrega específico.

    Solo se procesan y modifican los campos provistos en la petición.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    return await PuntoEntregaService.patch(db, punto_entrega_id, current_user.id, data)


@router.delete("/{punto_entrega_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_punto_entrega(
    punto_entrega_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Desactiva lógicamente un punto de entrega (Soft Delete).

    Establece `activo=False` permitiendo que los pedidos históricos mantengan sus referencias,
    y liberando el nombre para futuros puntos de entrega del usuario.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    await PuntoEntregaService.soft_delete(db, punto_entrega_id, current_user.id)
