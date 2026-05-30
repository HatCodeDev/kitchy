"""
Dependencias de seguridad e inyección para los controladores.

Este módulo expone las dependencias reutilizables de FastAPI, principalmente
el esquema de seguridad OAuth2 con flujo de contraseña (Password Bearer)
y funciones de extracción y validación del usuario autenticado actual.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
import jwt
import uuid  # <-- AÑADIDO: Importamos uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.config import settings
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
) -> User:
    """
    Extrae, valida y retorna el usuario autenticado a partir del token Bearer JWT.

    Esta dependencia intercepta la petición, decodifica el token firmado, extrae el
    ID del usuario y lo busca en la base de datos. Si el token ha expirado, está mal
    formado o el usuario no existe, arroja una excepción HTTP 401.

    Args:
        token (str): Token JWT decodificado proveniente del header Authorization.
        db (AsyncSession): Conexión activa de base de datos inyectada.

    Returns:
        User: Instancia del modelo SQLAlchemy del usuario autenticado.

    Raises:
        HTTPException: Si el token es inválido (401 Unauthorized).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token de acceso",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception

        # AÑADIDO: Convertimos el string a UUID validado
        user_id = uuid.UUID(user_id_str)

    except (jwt.PyJWTError, ValueError):  # ValueError captura si el UUID está mal formado
        raise credentials_exception

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalars().first()

    if user is None:
        raise credentials_exception
    return user