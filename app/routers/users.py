from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserResponse

router = APIRouter()

# 1. Llamamos al guardia de seguridad
# Esto es lo que FastAPI lee para dibujar el botón Authorize en Swagger
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


# 2. Creamos la función que valida el Token (Criterio de Aceptación: Multi-tenancy)
async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Este es el Guardián. Revisa el token, lo abre y busca al usuario en la BD.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Abrimos el token con nuestra llave maestra
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    # Buscamos al usuario en la BD usando el ID del token
    query = select(User).where(User.id == int(user_id))
    result = await db.execute(query)
    user = result.scalars().first()

    if user is None:
        raise credentials_exception
    return user


# 3. Creamos nuestra primera RUTA PRIVADA
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Ruta protegida que devuelve los datos del usuario dueño del token.
    """
    return current_user