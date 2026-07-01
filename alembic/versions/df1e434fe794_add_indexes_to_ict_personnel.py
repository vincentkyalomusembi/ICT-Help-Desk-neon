"""add indexes to ict_personnel

Revision ID: df1e434fe794
Revises: 8ee814206a2f
Create Date: 2026-06-30 00:24:04.419813

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df1e434fe794'
down_revision: Union[str, Sequence[str], None] = '8ee814206a2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_ict_personnel_availability'), 'ict_personnel', ['availability'], unique=False)
    op.create_index(op.f('ix_ict_personnel_is_active'), 'ict_personnel', ['is_active'], unique=False)
    op.create_index(op.f('ix_ict_personnel_specialization'), 'ict_personnel', ['specialization'], unique=False)
    op.create_index(
        'ix_ict_personnel_triage_lookup',
        'ict_personnel',
        ['specialization', 'availability', 'is_active'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_ict_personnel_triage_lookup', table_name='ict_personnel')
    op.drop_index(op.f('ix_ict_personnel_specialization'), table_name='ict_personnel')
    op.drop_index(op.f('ix_ict_personnel_is_active'), table_name='ict_personnel')
    op.drop_index(op.f('ix_ict_personnel_availability'), table_name='ict_personnel')