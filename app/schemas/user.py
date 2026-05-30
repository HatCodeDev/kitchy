"""
Esquemas de validación Pydantic para Usuarios.

Este módulo define los esquemas de entrada (validación) y salida (serialización)
para los endpoints de autenticación, perfil y gestión de usuarios.
"""
from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime
from uuid import UUID
from typing import Optional
from decimal import Decimal

class UserCreate(BaseModel):
    """
    Esquema de entrada para el registro de un nuevo usuario en la plataforma.
    """
    email: EmailStr = Field(
        ..., 
        description="Correo electrónico principal del usuario. Debe tener un formato válido.", 
        examples=["emprendedor@kitchy.com"]
    )
    password: str = Field(
        ..., 
        min_length=6, 
        description="Contraseña en texto plano para la cuenta. Longitud mínima de 6 caracteres.", 
        examples=["ABdZn6A9a7riMDp$"]
    )


class UserResponse(BaseModel):
    """
    Esquema de salida para representar los datos de un usuario registrado.
    """
    id: UUID = Field(
        ..., 
        description="Identificador único universal (UUID) del usuario en la base de datos."
    )
    email: EmailStr = Field(
        ..., 
        description="Correo electrónico verificado del usuario."
    )
    is_active: bool = Field(
        default=True, 
        description="Indica si la cuenta de usuario se encuentra activa y autorizada para ingresar."
    )
    plan: str = Field(
        ..., 
        description="Nivel de suscripción actual del usuario en la plataforma.", 
        examples=["free", "premium"]
    )
    empaque_mxn_default: Optional[Decimal] = Field(
        default=Decimal("0.00"), 
        description="Costo de empaque unitario predeterminado (en MXN) para nuevos pedidos/recetas."
    )
    desgaste_pct_default: Optional[Decimal] = Field(
        default=Decimal("0.00"), 
        description="Porcentaje predeterminado asignado para cubrir costos de desgaste de herramientas, servicios o merma."
    )
    created_at: datetime = Field(
        ..., 
        description="Fecha y hora exactas en que el usuario se registró en Kitchy."
    )

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """
    Esquema de salida para el token de acceso JWT resultante de una autenticación exitosa.
    """
    access_token: str = Field(
        ..., 
        description="El JSON Web Token (JWT) firmado que debe ser incluido en la cabecera 'Authorization' de las peticiones protegidas."
    )
    token_type: str = Field(
        ..., 
        description="Tipo de token de autenticación. Siempre retorna 'bearer'."
    )