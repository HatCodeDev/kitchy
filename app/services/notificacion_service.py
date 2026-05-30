"""
Servicio de Gestión de Notificaciones.

Este módulo implementa la lógica para programar y cancelar notificaciones asíncronas
asociadas a pedidos de clientes (ej. recordatorios automáticos de entrega programados 2 horas antes).
"""
from datetime import datetime, timezone, timedelta
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notificacion_programada import NotificacionProgramada


class NotificacionService:
    """
    Servicio encargado del ciclo de vida de las alertas y notificaciones programadas en el sistema.
    """

    @staticmethod
    async def programar_recordatorio(
        db: AsyncSession, 
        pedido_id: UUID, 
        fecha_entrega: datetime, 
        usuario_id: UUID
    ) -> NotificacionProgramada:
        """
        Programa una notificación recordatorio para enviarse 2 horas antes de la entrega de un pedido.

        Si la fecha calculada de envío ya ha transcurrido al momento de la invocación,
        la función omite la creación y retorna None para prevenir disparos desfasados.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            pedido_id (UUID): ID del pedido a asociar al recordatorio.
            fecha_entrega (datetime): Fecha y hora pactada para entregar el pedido.
            usuario_id (UUID): ID del usuario que registra el recordatorio.

        Returns:
            Optional[NotificacionProgramada]: La instancia de la alerta creada o None si la fecha ya expiró.
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
        Cancela lógicamente los recordatorios pendientes asociados a un pedido específico.

        Marca todas las alertas programadas y no enviadas de este pedido como enviadas
        y les asigna el timestamp actual para desactivar su procesamiento por parte del Worker.

        Args:
            db (AsyncSession): Conexión activa de base de datos asíncrona.
            pedido_id (UUID): ID del pedido cuyos recordatorios se cancelarán.
            usuario_id (UUID): ID del usuario propietario de la orden.
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
