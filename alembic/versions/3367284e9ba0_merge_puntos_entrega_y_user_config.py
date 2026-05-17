"""merge_puntos_entrega_y_user_config

Revision ID: 3367284e9ba0
Revises: ad1f2e5c89a7, f60acb49228d
Create Date: 2026-05-17 03:59:36.424556

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3367284e9ba0'
down_revision: Union[str, Sequence[str], None] = ('ad1f2e5c89a7', 'f60acb49228d')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
