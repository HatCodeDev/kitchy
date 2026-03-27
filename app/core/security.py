from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from passlib.context import CryptContext
from app.core.config import settings

# Configuración de Bcrypt para el Hashing de contraseñas
# Le decimos a passlib que use el esquema "bcrypt"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Compara una contraseña en texto plano con el hash de la base de datos.
    Devuelve True si coinciden, False si no.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Toma una contraseña en texto plano y devuelve el hash seguro.
    """
    return pwd_context.hash(password)


# 2. Configuración para los Tokens JWT
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Genera un nuevo gafete VIP (Token JWT) para el usuario.
    """
    # Hacemos una copia de los datos que queremos meter en el token (ej. el ID del usuario)
    to_encode = data.copy()

    # Calculamos cuándo va a caducar el token
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Si no nos dicen, le damos el tiempo por defecto que configuramos en el .env (7 días)
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    # Añadimos la fecha de caducidad ("exp") a los datos del token (estándar de JWT)
    to_encode.update({"exp": expire})

    # Firmamos el token usando nuestra SECRET_KEY secreta.
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return encoded_jwt