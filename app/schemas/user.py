from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from uuid import UUID  # <-- AÑADIDO

class UserCreate(BaseModel):
    """Esquema para cuando el usuario se registra (recibe datos)"""
    email: EmailStr = Field(..., description="Correo electrónico del usuario", examples=["emprendedor@kitchy.com"])
    password: str = Field(..., min_length=6, description="Contraseña en texto plano", examples=["ABdZn6A9a7riMDp$"])

class UserResponse(BaseModel):
    """Esquema para cuando respondemos al usuario (envía datos)"""
    id: UUID = Field(..., description="ID único del usuario en la base de datos")  # <-- CORREGIDO A UUID
    email: EmailStr
    is_active: bool = Field(default=True, description="Indica si la cuenta está habilitada")
    created_at: datetime = Field(..., description="Fecha y hora de registro")

    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    """Esquema para la respuesta al hacer Login"""
    access_token: str = Field(..., description="El token JWT firmado")
    token_type: str = Field(..., description="Tipo de token (usualmente 'bearer')")