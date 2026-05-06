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
    Obtiene las notificaciones del usuario.
    Por defecto, retorna las enviadas en los últimos 5 minutos para el polling de Flutter.
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
