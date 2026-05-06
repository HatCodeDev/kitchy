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
    return await TemporizadorService.confirmar_alarma(
        db=db,
        temporizador_id=id,
        usuario_id=current_user.id
    )
