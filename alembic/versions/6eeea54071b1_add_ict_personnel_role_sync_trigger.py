"""add_ict_personnel_role_sync_trigger

Revision ID: 6eeea54071b1
Revises: f9d4c8e03260
Create Date: 2026-06-12 00:12:52.488780

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6eeea54071b1'
down_revision: Union[str, Sequence[str], None] = 'f9d4c8e03260'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION sync_ict_personnel_on_role_change()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Role changed TO ICT_PERSONNEL
            IF NEW.role = 'ICT_PERSONNEL' AND OLD.role != 'ICT_PERSONNEL' THEN
                INSERT INTO ict_personnel (staff_id, specialization, availability, is_active)
                VALUES (NEW.id, 'OTHER', 'AVAILABLE', true)
                ON CONFLICT (staff_id) DO UPDATE
                    SET is_active = true,
                        specialization = CASE
                            WHEN ict_personnel.specialization IS NOT NULL
                            THEN ict_personnel.specialization
                            ELSE 'OTHER'
                        END;

            -- Role changed FROM ICT_PERSONNEL
            ELSIF OLD.role = 'ICT_PERSONNEL' AND NEW.role != 'ICT_PERSONNEL' THEN
                UPDATE ict_personnel
                SET is_active = false
                WHERE staff_id = NEW.id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    op.execute("""
        CREATE TRIGGER staff_role_change_sync
        AFTER UPDATE ON staff
        FOR EACH ROW
        WHEN (OLD.role IS DISTINCT FROM NEW.role)
        EXECUTE FUNCTION sync_ict_personnel_on_role_change();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS staff_role_change_sync ON staff;")
    op.execute("DROP FUNCTION IF EXISTS sync_ict_personnel_on_role_change;")
