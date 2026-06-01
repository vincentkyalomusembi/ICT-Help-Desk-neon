"""Initial migration
Revision ID: 4588f534c2f2
Revises: 
Create Date: 2026-06-01 11:12:04.873049
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '4588f534c2f2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('directorates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table('departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('directorate_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['directorate_id'], ['directorates.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_table('staff',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('personal_number', sa.String(length=20), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=15), nullable=True),
        sa.Column('directorate_id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False),
        sa.Column('job_title', sa.String(length=100), nullable=False),
        sa.Column('office_location', sa.String(length=100), nullable=True),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('failed_attempts', sa.Integer(), nullable=False),
        sa.Column('locked_until', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('password_changed_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['directorate_id'], ['directorates.id']),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('personal_number'),
        sa.UniqueConstraint('email')
    )
    op.create_table('ict_personnel',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', UUID(as_uuid=True), nullable=False),
        sa.Column('specialization', sa.String(), nullable=False),
        sa.Column('availability', sa.String(), nullable=False),
        sa.Column('phone_extension', sa.String(length=10), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('staff_id')
    )
    op.create_table('tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', UUID(as_uuid=True), nullable=False),
        sa.Column('assigned_to_id', sa.Integer(), nullable=True),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id']),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['ict_personnel.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('assets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_tag', sa.String(length=50), nullable=False),
        sa.Column('serial_number', sa.String(length=100), nullable=False),
        sa.Column('device_type', sa.String(), nullable=False),
        sa.Column('brand', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('classification', sa.String(), nullable=False),
        sa.Column('condition', sa.String(), nullable=False),
        sa.Column('purchase_date', sa.Date(), nullable=True),
        sa.Column('warranty_expiry', sa.Date(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('asset_tag'),
        sa.UniqueConstraint('serial_number')
    )
    op.create_table('asset_allocations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('staff_id', UUID(as_uuid=True), nullable=False),
        sa.Column('allocation_date', sa.Date(), nullable=False),
        sa.Column('return_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['assets.id']),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('table_name', sa.String(length=50), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('mac_address', sa.String(length=17), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('staff_id', UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('login_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['staff_id'], ['staff.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )