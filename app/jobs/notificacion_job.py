import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.notificacion_programada import NotificacionProgramada

logger = logging.getLogger(__name__)

async def procesar_notificaciones_loop():
    """
    Loop infinito que procesa notificaciones programadas cada 60 segundos.
    """
    logger.info("Iniciando Job de Procesamiento de Notificaciones...")
    
    while True:
        try:
            # Abrimos una sesión nueva por cada ciclo para evitar problemas de conexión compartida
            async with AsyncSessionLocal() as db:
                ahora = datetime.now(timezone.utc)
                
                # Buscamos notificaciones pendientes que ya deben dispararse
                query = select(NotificacionProgramada).where(
                    NotificacionProgramada.enviada == False,
                    NotificacionProgramada.fecha_programada <= ahora
                )
                
                result = await db.execute(query)
                notificaciones_pendientes = result.scalars().all()
                
                if notificaciones_pendientes:
                    count = 0
                    for notif in notificaciones_pendientes:
                        notif.enviada = True
                        notif.fecha_envio = ahora
                        count += 1
                    
                    await db.commit()
                    logger.info(f"Job Notificaciones: Procesadas {count} notificaciones.")
                
        except Exception as e:
            logger.error(f"Error en el Job de Notificaciones: {str(e)}")
        
        # Esperar 60 segundos antes del siguiente ciclo
        await asyncio.sleep(60)
