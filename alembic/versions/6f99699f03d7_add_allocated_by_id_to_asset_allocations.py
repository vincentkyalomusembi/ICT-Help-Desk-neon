"""add allocated_by_id to asset_allocations

Revision ID: 6f99699f03d7
Revises: fdf16414b3ca
Create Date: 2026-06-24 16:38:49.594432

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '6f99699f03d7'
down_revision: Union[str, Sequence[str], None] = 'fdf16414b3ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('asset_allocations', sa.Column('allocated_by_id', sa.Uuid(), nullable=True))
    op.create_foreign_key(
        'fk_asset_allocations_allocated_by_id_staff',
        'asset_allocations', 'staff',
        ['allocated_by_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_asset_allocations_allocated_by_id_staff',
        'asset_allocations', type_='foreignkey',
    )
    op.drop_column('asset_allocations', 'allocated_by_id')