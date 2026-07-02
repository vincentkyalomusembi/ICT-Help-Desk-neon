"""add indexes to asset_allocations fk columns

Revision ID: 4ed6c258079e
Revises: 69bdc81b9001
Create Date: 2026-06-29 23:15:18.516969

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ed6c258079e'
down_revision: Union[str, Sequence[str], None] = '69bdc81b9001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_asset_allocations_allocated_by_id'), 'asset_allocations', ['allocated_by_id'], unique=False)
    op.create_index(op.f('ix_asset_allocations_asset_id'), 'asset_allocations', ['asset_id'], unique=False)
    op.create_index(op.f('ix_asset_allocations_return_date'), 'asset_allocations', ['return_date'], unique=False)
    op.create_index(op.f('ix_asset_allocations_staff_id'), 'asset_allocations', ['staff_id'], unique=False)
    op.create_index(
        'ix_active_allocation_per_asset',
        'asset_allocations',
        ['asset_id'],
        unique=True,
        postgresql_where=sa.text('return_date IS NULL'),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_active_allocation_per_asset', table_name='asset_allocations')
    op.drop_index(op.f('ix_asset_allocations_staff_id'), table_name='asset_allocations')
    op.drop_index(op.f('ix_asset_allocations_return_date'), table_name='asset_allocations')
    op.drop_index(op.f('ix_asset_allocations_asset_id'), table_name='asset_allocations')
    op.drop_index(op.f('ix_asset_allocations_allocated_by_id'), table_name='asset_allocations')