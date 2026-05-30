"""
Modelo de datos para la entidad Usuario.

Representa a los usuarios registrados en el sistema Kitchy,
sus credenciales, nivel de plan y configuraciones globales predeterminadas.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from decimal import Decimal
from app.core.database import Base


class User(Base):
    """
    Modelo ORM que representa la tabla 'users' en la base de datos.

    Atributos:
        id (UUID): Identificador único de usuario (Primary Key).
        email (str): Correo electrónico del usuario (único e indexado).
        hashed_password (str): Hash seguro de la contraseña.
        is_active (bool): Estado de activación de la cuenta. Por defecto True.
        plan (str): Nivel de suscripción ('free', 'premium', etc.). Por defecto 'free'.
        empaque_mxn_default (Decimal): Costo de empaque por defecto en MXN.
        desgaste_pct_default (Decimal): Porcentaje de desgaste de herramientas por defecto.
        created_at (datetime): Fecha y hora de registro de la cuenta.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email = Column(String, unique=True, index=True, nullable=False)

    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

    plan = Column(String(20), nullable=False, default='free')
    empaque_mxn_default = Column(Numeric(10, 2), nullable=True, default=Decimal('0.00'))
    desgaste_pct_default = Column(Numeric(5, 2), nullable=True, default=Decimal('0.00'))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __init__(self, **kwargs):
        """
        Inicializa una nueva instancia de User garantizando valores por defecto limpios.

        Args:
            **kwargs: Atributos clave-valor para poblar las columnas del modelo.
        """
        super().__init__(**kwargs)
        if self.plan is None:
            self.plan = 'free'
        if self.empaque_mxn_default is None:
            self.empaque_mxn_default = Decimal('0.00')
        if self.desgaste_pct_default is None:
            self.desgaste_pct_default = Decimal('0.00')
