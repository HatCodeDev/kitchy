from fastapi import APIRouter, Depends
from app.models.user import User
from app.schemas.user import UserResponse
from app.core.dependencies import get_current_user # <-- Importamos desde el nuevo archivo

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Ruta protegida que devuelve los datos del usuario dueño del token.
    """
    return current_user