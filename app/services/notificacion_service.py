from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notificacion_programada import NotificacionProgramada

class NotificacionService:
    @staticmethod
    async def programar_recordatorio(
        db: AsyncSession, 
        pedido_id: UUID, 
        fecha_entrega: datetime, 
        usuario_id: UUID
    ) -> NotificacionProgramada:
        """
        Programa una notificación para 2 horas antes de la entrega.
        Si el tiempo ya pasó, no se crea nada.
        """
        # Asegurar que la fecha_entrega tenga timezone UTC si no lo tiene
        if fecha_entrega.tzinfo is None:
            fecha_entrega = fecha_entrega.replace(tzinfo=timezone.utc)
            
        fecha_programada = fecha_entrega - timedelta(hours=2)
        ahora = datetime.now(timezone.utc)
        
        # Si la fecha programada ya pasó, no creamos notificación
        if fecha_programada <= ahora:
            return None
            
        nueva_notif = NotificacionProgramada(
            usuario_id=usuario_id,
            pedido_id=pedido_id,
            tipo='recordatorio_entrega',
            fecha_programada=fecha_programada,
            enviada=False
        )
        
        db.add(nueva_notif)
        await db.commit()
        await db.refresh(nueva_notif)
        return nueva_notif

    @staticmethod
    async def cancelar_recordatorio(db: AsyncSession, pedido_id: UUID, usuario_id: UUID):
        """
        Cancela (soft cancel) cualquier recordatorio pendiente para un pedido.
        """
        query = (
            update(NotificacionProgramada)
            .where(
                NotificacionProgramada.pedido_id == pedido_id,
                NotificacionProgramada.usuario_id == usuario_id,
                NotificacionProgramada.enviada == False,
                NotificacionProgramada.tipo == 'recordatorio_entrega'
            )
            .values(enviada=True, fecha_envio=datetime.now(timezone.utc))
        )
        await db.execute(query)
        await db.commit()
