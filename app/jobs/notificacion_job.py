"""
Trabajo en Segundo Plano para Notificaciones Programadas.

Este módulo define la tarea programada que se ejecuta de forma asíncrona y continua durante
el ciclo de vida de la aplicación para procesar y despachar notificaciones pendientes.
"""
import asyncio
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.notificacion_programada import NotificacionProgramada

logger = logging.getLogger(__name__)


async def procesar_notificaciones_loop():
    """
    Bucle Infinito para el Despacho y Procesamiento de Notificaciones.

    Se ejecuta de forma continua (cada 60 segundos) consultando la base de datos para identificar
    notificaciones pendientes que hayan alcanzado su hora programada de ejecución. 

    Abre y cierra una sesión de base de datos dedicada en cada ciclo para garantizar el aislamiento
    de transacciones y evitar fugas de conexión.

    ### Flujo de Trabajo:
    1. Obtiene la hora actual en formato UTC.
    2. Consulta registros de `NotificacionProgramada` donde `enviada` sea `False` y `fecha_programada` <= ahora.
    3. Marca cada notificación como enviada y registra la fecha de envío efectiva.
    4. Realiza el commit de la transacción e informa en el log.
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

