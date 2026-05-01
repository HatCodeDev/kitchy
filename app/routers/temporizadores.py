from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.temporizador import TemporizadorResponse, TemporizadorCreate
from app.services.temporizador_service import TemporizadorService
from app.models.temporizador import Temporizador

router = APIRouter()

@router.get("/", response_model=List[TemporizadorResponse])
def listar_temporizadores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Lista los temporizadores del usuario (para sincronización).
    """
    temporizadores = db.query(Temporizador).filter(
        Temporizador.usuario_id == current_user.id
    ).all()
    return temporizadores

@router.post("/", response_model=TemporizadorResponse, status_code=status.HTTP_201_CREATED)
def iniciar_temporizador(
    temporizador_in: TemporizadorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inicia un nuevo temporizador.
    """
    return TemporizadorService.iniciar(
        db=db,
        paso_receta_id=temporizador_in.paso_receta_id,
        duracion_segundos=temporizador_in.duracion_segundos,
        usuario_id=current_user.id
    )

@router.patch("/{id}/cancelar", response_model=TemporizadorResponse)
def cancelar_temporizador(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cancela un temporizador en curso.
    """
    return TemporizadorService.cancelar(
        db=db,
        temporizador_id=id,
        usuario_id=current_user.id
    )

@router.patch("/{id}/confirmar", response_model=TemporizadorResponse)
def confirmar_alarma(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Confirma un temporizador (marca como completado).
    """
    return TemporizadorService.confirmar_alarma(
        db=db,
        temporizador_id=id,
        usuario_id=current_user.id
    )
