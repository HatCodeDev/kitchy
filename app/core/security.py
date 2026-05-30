"""
Utilidades de Seguridad y Criptografía.

Este módulo encapsula los mecanismos de hashing de contraseñas mediante
bcrypt (usando passlib) y la generación y firma de tokens JWT para el
sistema de autenticación y autorización de Kitchy API.
"""
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
    Compara una contraseña en texto plano con un hash almacenado.

    Utiliza el contexto de passlib con el algoritmo bcrypt para verificar
    si la contraseña proporcionada coincide con el hash almacenado, previniendo
    ataques de sincronización mediante una comparación en tiempo constante.

    Args:
        plain_password (str): Contraseña en texto plano provista por el usuario.
        hashed_password (str): Hash seguro recuperado de la base de datos.

    Returns:
        bool: True si la contraseña es correcta y coincide con el hash, False en caso contrario.
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Genera un hash seguro a partir de una contraseña en texto plano.

    Aplica el algoritmo bcrypt con un factor de trabajo configurado
    de forma automática para producir un hash unidireccional y seguro.

    Args:
        password (str): Contraseña en texto plano que se desea hashear.

    Returns:
        str: El hash resultante para ser guardado en el modelo de usuario.
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Genera un nuevo token de acceso firmado digitalmente (JWT) para un usuario.

    Toma un diccionario con los datos a codificar (comúnmente el identificador
    de usuario bajo el campo 'sub'), calcula su tiempo de expiración y firma
    el payload resultante usando la clave secreta y algoritmo configurados.

    Args:
        data (dict): Payload que contiene los datos del usuario a encriptar en el token.
        expires_delta (Optional[timedelta]): Tiempo de vida específico para el token.
            Si no se especifica, toma el valor predeterminado del archivo de configuración (7 días).

    Returns:
        str: Token JWT serializado en formato string listo para enviarse al cliente.
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