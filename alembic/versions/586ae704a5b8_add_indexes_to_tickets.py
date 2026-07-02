"""add indexes to tickets

Revision ID: 586ae704a5b8
Revises: 1879266e1365
Create Date: 2026-06-30 09:50:36.136794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '586ae704a5b8'
down_revision: Union[str, Sequence[str], None] = '1879266e1365'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_tickets_assigned_to_id'), 'tickets', ['assigned_to_id'], unique=False)
    op.create_index(op.f('ix_tickets_category'), 'tickets', ['category'], unique=False)
    op.create_index(op.f('ix_tickets_closed_at'), 'tickets', ['closed_at'], unique=False)
    op.create_index(op.f('ix_tickets_created_at'), 'tickets', ['created_at'], unique=False)
    op.create_index(op.f('ix_tickets_staff_id'), 'tickets', ['staff_id'], unique=False)
    op.create_index(op.f('ix_tickets_status'), 'tickets', ['status'], unique=False)
    op.create_index(
        'ix_tickets_assigned_to_status',
        'tickets',
        ['assigned_to_id', 'status'],
        unique=False,
    )
    op.create_index(
        'ix_tickets_status_created_at',
        'tickets',
        ['status', 'created_at'],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_tickets_status_created_at', table_name='tickets')
    op.drop_index('ix_tickets_assigned_to_status', table_name='tickets')
    op.drop_index(op.f('ix_tickets_status'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_staff_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_created_at'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_closed_at'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_category'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_assigned_to_id'), table_name='tickets')