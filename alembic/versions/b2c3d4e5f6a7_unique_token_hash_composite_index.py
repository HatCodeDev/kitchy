"""unique token_hash and composite (user_id, used) index on password_reset_tokens

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-02 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enforce uniqueness on token_hash (REQ-9): swap the plain index for a unique one.
    op.drop_index('ix_password_reset_tokens_token_hash', table_name='password_reset_tokens')
    op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'], unique=True)
    # Composite index supporting the invalidation query (REQ-9 / REQ-3).
    op.create_index('ix_password_reset_tokens_user_id_used', 'password_reset_tokens', ['user_id', 'used'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_password_reset_tokens_user_id_used', table_name='password_reset_tokens')
    op.drop_index('ix_password_reset_tokens_token_hash', table_name='password_reset_tokens')
    op.create_index('ix_password_reset_tokens_token_hash', 'password_reset_tokens', ['token_hash'], unique=False)
