"""
Controlador de Notificaciones y Alertas.

Este router expone los endpoints para consultar el listado de notificaciones
programadas y despachadas, brindando soporte al polling periódico del cliente móvil (Flutter).
"""
from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.notificacion_programada import NotificacionProgramada
from app.schemas.notificacion import NotificacionRead

router = APIRouter()


@router.get("/", response_model=List[NotificacionRead])
async def get_notificaciones(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    enviada: bool = Query(True)
):
    """
    Recupera el listado de notificaciones programadas o despachadas del usuario autenticado.

    ### Mecanismo de Polling optimizado:
    * Si se solicita con `enviada=True` (por defecto), el backend filtra de forma automática
      únicamente las alertas despachadas en los **últimos 5 minutos**. Esto reduce drásticamente
      el volumen de transferencia de red del polling periódico del cliente móvil (Flutter)
      evitando el renderizado repetido.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).
    """
    ahora = datetime.now(timezone.utc)
    hace_5_min = ahora - timedelta(minutes=5)
    
    query = select(NotificacionProgramada).where(
        NotificacionProgramada.usuario_id == current_user.id,
        NotificacionProgramada.enviada == enviada
    )
    
    # Si pedimos las enviadas, filtramos por los últimos 5 minutos para evitar repetidas en el cliente
    if enviada:
        query = query.where(NotificacionProgramada.fecha_envio >= hace_5_min)
        
    query = query.order_by(NotificacionProgramada.fecha_programada.desc())
    
    result = await db.execute(query)
    return result.scalars().all()
