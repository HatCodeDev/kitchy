"""
Servicio de Temporizadores de Producción.

Este módulo implementa la lógica para iniciar, pausar/cancelar y confirmar temporizadores
asociados a los pasos críticos de preparación de recetas en tiempo real.
"""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.temporizador import Temporizador


class TemporizadorService:
    """
    Servicio encargado de administrar el estado y la vida útil de los temporizadores activos.
    """

    @staticmethod
    async def iniciar(db: AsyncSession, paso_receta_id: UUID, duracion_segundos: int, usuario_id: UUID) -> Temporizador:
        """
        Inicia un nuevo temporizador activo para un paso de receta determinado.

        Para garantizar que un usuario no tenga múltiples temporizadores activos 'corriendo'
        de forma simultánea en la misma sesión, busca cualquier temporizador previo en estado
        'corriendo' para este usuario y lo desactiva automáticamente antes de inicializar el nuevo.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            paso_receta_id (UUID): ID del paso de receta al que se vincula el temporizador.
            duracion_segundos (int): Duración del temporizador en segundos.
            usuario_id (UUID): ID del usuario que inicia el temporizador.

        Returns:
            Temporizador: La instancia del nuevo temporizador corriendo persistido en DB.
        """
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
        """
        Cancela un temporizador en ejecución, cambiando su estado a 'inactivo'.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            temporizador_id (UUID): ID del temporizador a cancelar.
            usuario_id (UUID): ID del usuario propietario (seguridad multi-tenant).

        Returns:
            Temporizador: La instancia del temporizador actualizado.

        Raises:
            HTTPException: 404 si el temporizador no existe, o 403 si pertenece a otro usuario.
        """
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
        """
        Confirma la finalización exitosa de un temporizador de preparación.

        Cambia el estado del temporizador a 'completado' y estampa la hora exacta de confirmación en UTC.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            temporizador_id (UUID): ID del temporizador a confirmar.
            usuario_id (UUID): ID del usuario propietario (seguridad multi-tenant).

        Returns:
            Temporizador: La instancia del temporizador completada y persistida.

        Raises:
            HTTPException: 404 si el temporizador no existe, o 403 si pertenece a otro usuario.
        """
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
