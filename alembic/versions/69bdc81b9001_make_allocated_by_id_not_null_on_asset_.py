"""make allocated_by_id not null on asset_allocations

Revision ID: 69bdc81b9001
Revises: 0e44c1f96b2a
Create Date: 2026-06-25 23:00:33.035496

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69bdc81b9001'
down_revision: Union[str, Sequence[str], None] = '0e44c1f96b2a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('asset_allocations', 'allocated_by_id', nullable=False)


def downgrade() -> None:
    op.alter_column('asset_allocations', 'allocated_by_id', nullable=True)