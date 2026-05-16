from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.temporizador import Temporizador


class TemporizadorService:
    @staticmethod
    async def iniciar(db: AsyncSession, paso_receta_id: UUID, duracion_segundos: int, usuario_id: UUID) -> Temporizador:
        result = await db.execute(
            select(Temporizador).where(
                Temporizador.usuario_id == usuario_id,
                Temporizador.estado == 'corriendo'
            )
        )
        existente = result.scalar_one_or_none()

        if existente:
            existente.estado = 'inactivo'
            await db.flush()

        nuevo = Temporizador(
            paso_receta_id=paso_receta_id,
            usuario_id=usuario_id,
            duracion_segundos=duracion_segundos,
            estado='corriendo',
            fecha_inicio=datetime.now(timezone.utc)
        )

        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        return nuevo

    @staticmethod
    async def cancelar(db: AsyncSession, temporizador_id: UUID, usuario_id: UUID) -> Temporizador:
        result = await db.execute(
            select(Temporizador).where(Temporizador.id == temporizador_id)
        )
        temporizador = result.scalar_one_or_none()

        if not temporizador:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Temporizador no encontrado")

        if temporizador.usuario_id != usuario_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para cancelar este temporizador")

        temporizador.estado = 'inactivo'
        await db.commit()
        await db.refresh(temporizador)
        return temporizador

    @staticmethod
    async def confirmar_alarma(db: AsyncSession, temporizador_id: UUID, usuario_id: UUID) -> Temporizador:
        result = await db.execute(
            select(Temporizador).where(Temporizador.id == temporizador_id)
        )
        temporizador = result.scalar_one_or_none()

        if not temporizador:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Temporizador no encontrado")

        if temporizador.usuario_id != usuario_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permiso para confirmar este temporizador")

        temporizador.estado = 'completado'
        temporizador.fecha_confirmacion = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(temporizador)
        return temporizador
