import secrets
from datetime import datetime, timezone, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.model import MagicLinkToken
from app.core.config import settings


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