"""
Controlador de Usuarios.

Este router expone los endpoints para gestionar el perfil del usuario autenticado actual,
incluyendo la consulta de sus datos básicos y la actualización de su configuración por defecto.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.schemas.user import UserResponse
from app.schemas.user_config import UserConfigUpdate
from app.core.dependencies import get_current_user
from app.core.database import get_db

router = APIRouter()


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Obtiene el perfil del usuario autenticado actual.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).

    ### Información devuelta:
    * Correo electrónico e ID de cuenta.
    * Nivel de plan activo (ej. 'free').
    * Parámetros por defecto para costos de empaque y desgaste.
    """
    return current_user


@router.put("/config", response_model=UserResponse)
async def update_user_config(
    data: UserConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza la configuración global predeterminada del usuario logueado.

    Permite realizar una actualización parcial (PATCH-like) enviando únicamente
    los campos que se desean modificar. Los valores None en la petición son ignorados.

    ### Permisos:
    * **Usuario Autenticado** (requiere token Bearer JWT válido).

    ### Campos configurables:
    * **empaque_mxn_default**: Costo base por defecto para empaques (en pesos).
    * **desgaste_pct_default**: Porcentaje de desgaste predeterminado para herramientas y servicios.
    """
    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None:
            setattr(current_user, key, val)
    
    await db.commit()
    await db.refresh(current_user)
    return current_user