"""lowercase enum values

Revision ID: ac347f18f0f3
Revises: eee8a026b3d1
Create Date: 2026-06-15 09:10:00.594141

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac347f18f0f3'
down_revision: Union[str, Sequence[str], None] = 'eee8a026b3d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Drop the trigger that depends on the role column
    op.execute("DROP TRIGGER IF EXISTS staff_role_change_sync ON staff")

    # Step 2: Convert column to TEXT to allow data update
    op.execute("ALTER TABLE staff ALTER COLUMN role TYPE TEXT USING role::TEXT")

    # Step 3: Update existing data to lowercase
    op.execute("UPDATE staff SET role = 'admin' WHERE role = 'ADMIN'")
    op.execute("UPDATE staff SET role = 'staff' WHERE role = 'STAFF'")
    op.execute("UPDATE staff SET role = 'ict_personnel' WHERE role = 'ICT_PERSONNEL'")

    # Step 4: Drop old enum and recreate with lowercase values only
    op.execute("DROP TYPE userrole")
    op.execute("CREATE TYPE userrole AS ENUM ('admin', 'staff', 'ict_personnel')")

    # Step 5: Convert column back to the new enum type
    op.execute("ALTER TABLE staff ALTER COLUMN role TYPE userrole USING role::userrole")

    # Step 6: Recreate the trigger
    op.execute("""
        CREATE TRIGGER staff_role_change_sync
        AFTER UPDATE ON public.staff
        FOR EACH ROW
        WHEN (OLD.role IS DISTINCT FROM NEW.role)
        EXECUTE FUNCTION sync_ict_personnel_on_role_change()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS staff_role_change_sync ON staff")
    op.execute("ALTER TABLE staff ALTER COLUMN role TYPE TEXT USING role::TEXT")
    op.execute("UPDATE staff SET role = 'ADMIN' WHERE role = 'admin'")
    op.execute("UPDATE staff SET role = 'STAFF' WHERE role = 'staff'")
    op.execute("UPDATE staff SET role = 'ICT_PERSONNEL' WHERE role = 'ict_personnel'")
    op.execute("DROP TYPE userrole")
    op.execute("CREATE TYPE userrole AS ENUM ('ADMIN', 'STAFF', 'ICT_PERSONNEL')")
    op.execute("ALTER TABLE staff ALTER COLUMN role TYPE userrole USING role::userrole")
    op.execute("""
        CREATE TRIGGER staff_role_change_sync
        AFTER UPDATE ON public.staff
        FOR EACH ROW
        WHEN (OLD.role IS DISTINCT FROM NEW.role)
        EXECUTE FUNCTION sync_ict_personnel_on_role_change()
    """)