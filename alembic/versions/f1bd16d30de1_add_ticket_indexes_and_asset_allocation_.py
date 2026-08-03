"""add ticket indexes and asset allocation constraint

Revision ID: f1bd16d30de1
Revises: 6fd3b31e4c28
Create Date: 2026-07-17 11:25:01.566157

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1bd16d30de1'
down_revision: Union[str, Sequence[str], None] = '6fd3b31e4c28'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TICKET_INDEXES = [
    ('ix_ticket_assigned_status', ['assigned_to_id', 'status']),
    ('ix_ticket_assigned_to_id', ['assigned_to_id']),
    ('ix_ticket_created_at', ['created_at']),
    ('ix_ticket_staff_id', ['staff_id']),
    ('ix_ticket_staff_status', ['staff_id', 'status']),
    ('ix_ticket_status', ['status']),
]


def upgrade() -> None:
    """Upgrade schema."""
    # CREATE INDEX CONCURRENTLY cannot run inside a transaction block.
    with op.get_context().autocommit_block():
        for name, columns in TICKET_INDEXES:
            op.create_index(
                name,
                'tickets',
                columns,
                unique=False,
                postgresql_concurrently=True,
            )

        # Partial unique index: only one active (return_date IS NULL)
        # allocation per asset at a time. Enforces this at the DB level
        # instead of relying on a check-then-insert race in service.py.
        op.create_index(
            'ix_asset_allocations_active_asset',
            'asset_allocations',
            ['asset_id'],
            unique=True,
            postgresql_where=sa.text('return_date IS NULL'),
            postgresql_concurrently=True,
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.get_context().autocommit_block():
        op.drop_index(
            'ix_asset_allocations_active_asset',
            table_name='asset_allocations',
            postgresql_concurrently=True,
        )

        for name, columns in reversed(TICKET_INDEXES):
            op.drop_index(
                name,
                table_name='tickets',
                postgresql_concurrently=True,
            )