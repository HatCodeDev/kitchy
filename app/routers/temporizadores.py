"""
Controlador de Temporizadores.

Este router expone los endpoints para gestionar temporizadores activos y el ciclo de vida
de las alarmas asociadas a los pasos de producción de recetas.
"""
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.temporizador import TemporizadorResponse, TemporizadorCreate
from app.services.temporizador_service import TemporizadorService
from app.models.temporizador import Temporizador

router = APIRouter()

@router.get("/", response_model=List[TemporizadorResponse])
async def listar_temporizadores(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtiene la lista completa de temporizadores activos e históricos del usuario.

    ### Multi-Tenancy:
    * Filtra estrictamente por el `usuario_id` obtenido del token JWT.

    ### Respuestas:
    * **200 OK**: Retorna una lista con todos los temporizadores asociados a la cuenta.
    """
    result = await db.execute(
        select(Temporizador).where(Temporizador.usuario_id == current_user.id)
    )
    return result.scalars().all()

@router.post("/", response_model=TemporizadorResponse, status_code=status.HTTP_201_CREATED)
async def iniciar_temporizador(
    temporizador_in: TemporizadorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inicia un nuevo temporizador de cocina asociado a un paso de receta.

    Resuelve la duración por defecto del paso si no se especifica explícitamente y calcula
    la fecha/hora exacta de finalización esperada (`fecha_fin`).

    ### Multi-Tenancy & Seguridad:
    * Asocia automáticamente el temporizador al `usuario_id` del usuario autenticado.
    * Valida que el paso de receta pertenezca al usuario para evitar filtrado de datos.

    ### Respuestas:
    * **201 Created**: Temporizador iniciado con éxito. Retorna la entidad creada.
    * **404 Not Found**: Si el paso de receta especificado no existe o no pertenece al usuario.
    """
    return await TemporizadorService.iniciar(
        db=db,
        paso_receta_id=temporizador_in.paso_receta_id,
        duracion_segundos=temporizador_in.duracion_segundos,
        usuario_id=current_user.id
    )

@router.patch("/{id}/cancelar", response_model=TemporizadorResponse)
async def cancelar_temporizador(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancela un temporizador activo de forma manual.

    Establece el estado a `cancelado`, deteniendo cualquier evento de alerta programado.

    ### Multi-Tenancy:
    * Valida propiedad: el temporizador debe pertenecer al usuario autenticado.

    ### Respuestas:
    * **200 OK**: Temporizador cancelado correctamente.
    * **400 Bad Request**: Si el temporizador no está en estado activo.
    * **404 Not Found**: Si el temporizador no existe o no pertenece al usuario.
    """
    return await TemporizadorService.cancelar(
        db=db,
        temporizador_id=id,
        usuario_id=current_user.id
    )

@router.patch("/{id}/confirmar", response_model=TemporizadorResponse)
async def confirmar_alarma(
    id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirma o silencia la alarma de un temporizador que ya ha finalizado.

    Cambia el estado del temporizador a `completado`, registrando el fin del ciclo de vida
    del proceso de cocción o preparación actual.

    ### Multi-Tenancy:
    * Valida propiedad: el temporizador debe pertenecer al usuario autenticado.

    ### Respuestas:
    * **200 OK**: Alarma confirmada y temporizador completado con éxito.
    * **400 Bad Request**: Si el temporizador aún está activo o ya fue completado/cancelado.
    * **404 Not Found**: Si el temporizador no existe o no pertenece al usuario.
    """
    return await TemporizadorService.confirmar_alarma(
        db=db,
        temporizador_id=id,
        usuario_id=current_user.id
    )
