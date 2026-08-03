import secrets
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth.model import PasswordResetToken
from app.staff.model import Staff
from app.core.config import settings
from app.core.security import hash_password
from app.core.email import send_password_reset


async def request_password_reset(db: AsyncSession, background_tasks: BackgroundTasks, email: str) -> None:
    result = await db.execute(select(Staff).where(Staff.email == email))
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No account found with that email.",
        )

    if not staff.is_activated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is not activated. Please verify your email first.",
        )

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.MAGIC_LINK_EXPIRE_MINUTES)

    record = PasswordResetToken(
        staff_id=staff.id,
        token=token,
        expires_at=expires_at,
        used=False,
    )
    db.add(record)
    await db.commit()

    background_tasks.add_task(send_password_reset, staff.email, staff.full_name, token)


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token == token)
    )
    record = result.scalar_one_or_none()

    if not record or record.used or record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset link.",
        )

    staff_result = await db.execute(select(Staff).where(Staff.id == record.staff_id))
    staff = staff_result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff account not found.",
        )

    staff.password_hash = hash_password(new_password)
    staff.password_changed_at = datetime.now(timezone.utc)
    staff.failed_attempts = 0
    staff.locked_until = None

    record.used = True

    db.add(staff)
    db.add(record)
    await db.commit()