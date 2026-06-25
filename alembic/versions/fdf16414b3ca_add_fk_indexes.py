"""add fk indexes

Revision ID: fdf16414b3ca
Revises: 32f4c79a8c73
Create Date: 2026-06-22 21:17:19.104309

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fdf16414b3ca'
down_revision: Union[str, Sequence[str], None] = '32f4c79a8c73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.get_context().autocommit_block():
        op.create_index(op.f('ix_departments_directorate_id'), 'departments', ['directorate_id'], unique=False, postgresql_concurrently=True)
        op.create_index(op.f('ix_staff_department_id'), 'staff', ['department_id'], unique=False, postgresql_concurrently=True)
        op.create_index(op.f('ix_staff_directorate_id'), 'staff', ['directorate_id'], unique=False, postgresql_concurrently=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.get_context().autocommit_block():
        op.drop_index(op.f('ix_staff_directorate_id'), table_name='staff', postgresql_concurrently=True)
        op.drop_index(op.f('ix_staff_department_id'), table_name='staff', postgresql_concurrently=True)
        op.drop_index(op.f('ix_departments_directorate_id'), table_name='departments', postgresql_concurrently=True)