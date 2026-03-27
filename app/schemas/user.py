from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime

class UserCreate(BaseModel):
    """Esquema para cuando el usuario se registra (recibe datos)"""
    email: EmailStr # EmailStr valida automáticamente que tenga un '@' y un dominio
    password: str

class UserResponse(BaseModel):
    """Esquema para cuando respondemos al usuario (envía datos)"""
    id: int
    email: EmailStr
    is_active: bool
    created_at: datetime

    # Por seguridad no incluimos 'password' ni 'hashed_password' aquí.
    # Esta configuración le dice a Pydantic que lea los datos desde el modelo de SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

# Esquemas para Autenticación

class Token(BaseModel):
    """Esquema para la respuesta al hacer Login (OpenAPI lo leerá para Dart)"""
    access_token: str
    token_type: str