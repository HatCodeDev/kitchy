from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.temporizador import Temporizador

class TemporizadorService:
    @staticmethod
    def iniciar(db: Session, paso_receta_id: UUID, duracion_segundos: int, usuario_id: UUID) -> Temporizador:
        existente = db.query(Temporizador).filter(
            Temporizador.usuario_id == usuario_id,
            Temporizador.estado == 'corriendo'
        ).first()

        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="Ya tienes un temporizador en curso. Cancélalo primero."
            )

        nuevo_temporizador = Temporizador(
            paso_receta_id=paso_receta_id,
            usuario_id=usuario_id,
            duracion_segundos=duracion_segundos,
            estado='corriendo',
            fecha_inicio=datetime.now(timezone.utc)
        )

        db.add(nuevo_temporizador)
        db.commit()
        db.refresh(nuevo_temporizador)
        return nuevo_temporizador

    @staticmethod
    def cancelar(db: Session, temporizador_id: UUID, usuario_id: UUID) -> Temporizador:
        temporizador = db.query(Temporizador).filter(Temporizador.id == temporizador_id).first()
        if not temporizador:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Temporizador no encontrado")
            
        if temporizador.usuario_id != usuario_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para cancelar este temporizador")

        temporizador.estado = 'inactivo'
        db.commit()
        db.refresh(temporizador)
        return temporizador

    @staticmethod
    def confirmar_alarma(db: Session, temporizador_id: UUID, usuario_id: UUID) -> Temporizador:
        temporizador = db.query(Temporizador).filter(Temporizador.id == temporizador_id).first()
        if not temporizador:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Temporizador no encontrado")

        if temporizador.usuario_id != usuario_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para confirmar este temporizador")

        temporizador.estado = 'completado'
        temporizador.fecha_confirmacion = datetime.now(timezone.utc)
        db.commit()
        db.refresh(temporizador)
        return temporizador
