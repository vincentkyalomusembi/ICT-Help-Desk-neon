"""add index to staff role

Revision ID: 1879266e1365
Revises: df1e434fe794
Create Date: 2026-06-30 00:30:41.100597

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1879266e1365'
down_revision: Union[str, Sequence[str], None] = 'df1e434fe794'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_staff_role'), 'staff', ['role'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_staff_role'), table_name='staff')