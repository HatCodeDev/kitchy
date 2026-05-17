"""add_puntos_entrega

Revision ID: ad1f2e5c89a7
Revises: f42991c44300
Create Date: 2026-05-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad1f2e5c89a7'
down_revision: Union[str, Sequence[str], None] = 'f42991c44300'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Create puntos_entrega table and add FK to pedidos."""
    # Create puntos_entrega table
    op.create_table(
        'puntos_entrega',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('usuario_id', sa.UUID(), nullable=False),
        sa.Column('nombre', sa.String(length=150), nullable=False),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('direccion', sa.String(length=500), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('fecha_creacion', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('fecha_modificacion', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_puntos_entrega_usuario_id', 'puntos_entrega', ['usuario_id'], unique=False)

    # Add punto_entrega_id FK column to pedidos
    op.add_column(
        'pedidos',
        sa.Column('punto_entrega_id', sa.UUID(), nullable=True)
    )
    op.create_foreign_key(
        'fk_pedidos_punto_entrega_id',
        'pedidos',
        'puntos_entrega',
        ['punto_entrega_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    """Downgrade schema: Drop FK column from pedidos and remove puntos_entrega table."""
    # Drop FK from pedidos
    op.drop_constraint('fk_pedidos_punto_entrega_id', 'pedidos', type_='foreignkey')
    op.drop_column('pedidos', 'punto_entrega_id')

    # Drop puntos_entrega table
    op.drop_index('ix_puntos_entrega_usuario_id', table_name='puntos_entrega')
    op.drop_table('puntos_entrega')
