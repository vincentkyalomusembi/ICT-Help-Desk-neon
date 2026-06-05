import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status

from app.auth.model import MagicLinkToken
from app.staff.model import Staff
from app.core.config import settings
from app.core.email import send_magic_link


async def create_magic_token(db: AsyncSession, staff_id) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.MAGIC_LINK_EXPIRE_MINUTES)

    record = MagicLinkToken(
        staff_id=staff_id,
        token=token,
        expires_at=expires_at,
        used=False,
    )
    db.add(record)
    await db.commit()
    return token


async def verify_magic_token(db: AsyncSession, token: str) -> None:
    result = await db.execute(
        select(MagicLinkToken).where(MagicLinkToken.token == token)
    )
    record = result.scalar_one_or_none()

    if not record or record.used or record.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification link.",
        )

    record.used = True

    # Activate the staff account
    staff_result = await db.execute(select(Staff).where(Staff.id == record.staff_id))
    staff = staff_result.scalar_one_or_none()
    if staff:
        staff.is_activated = True
        db.add(staff)

    db.add(record)
    await db.commit()


async def resend_magic_token(db: AsyncSession, email: str) -> None:
    result = await db.execute(select(Staff).where(Staff.email == email))
    staff = result.scalar_one_or_none()

    # Return silently even if email not found to avoid user enumeration
    if not staff or staff.is_activated:
        return

    token = await create_magic_token(db, staff.id)
    await send_magic_link(staff.email, staff.full_name, token)