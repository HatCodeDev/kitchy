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
    Ruta protegida que devuelve los datos del usuario dueño del token.
    """
    return current_user

@router.put("/config", response_model=UserResponse)
async def update_user_config(
    data: UserConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Actualiza la configuración global del usuario logueado.
    Realiza una actualización parcial de los campos que no sean None.
    """
    update_data = data.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None:
            setattr(current_user, key, val)
    
    await db.commit()
    await db.refresh(current_user)
    return current_user