import uuid
from sqlalchemy import Column, String, Boolean, DateTime, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from decimal import Decimal
from app.core.database import Base


class User(Base):
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
        super().__init__(**kwargs)
        if self.plan is None:
            self.plan = 'free'
        if self.empaque_mxn_default is None:
            self.empaque_mxn_default = Decimal('0.00')
        if self.desgaste_pct_default is None:
            self.desgaste_pct_default = Decimal('0.00')
