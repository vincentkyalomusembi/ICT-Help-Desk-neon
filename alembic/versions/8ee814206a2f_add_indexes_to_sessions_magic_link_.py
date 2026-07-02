"""add indexes to sessions magic_link_tokens password_reset_tokens

Revision ID: 8ee814206a2f
Revises: ef04bd679276
Create Date: 2026-06-29 23:53:27.100736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8ee814206a2f'
down_revision: Union[str, Sequence[str], None] = 'ef04bd679276'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(op.f('ix_magic_link_tokens_staff_id'), 'magic_link_tokens', ['staff_id'], unique=False)
    op.create_index(op.f('ix_password_reset_tokens_staff_id'), 'password_reset_tokens', ['staff_id'], unique=False)
    op.create_index(op.f('ix_sessions_expires_at'), 'sessions', ['expires_at'], unique=False)
    op.create_index(op.f('ix_sessions_is_active'), 'sessions', ['is_active'], unique=False)
    op.create_index(op.f('ix_sessions_login_at'), 'sessions', ['login_at'], unique=False)
    op.create_index(op.f('ix_sessions_staff_id'), 'sessions', ['staff_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_sessions_staff_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_login_at'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_is_active'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_expires_at'), table_name='sessions')
    op.drop_index(op.f('ix_password_reset_tokens_staff_id'), table_name='password_reset_tokens')
    op.drop_index(op.f('ix_magic_link_tokens_staff_id'), table_name='magic_link_tokens')