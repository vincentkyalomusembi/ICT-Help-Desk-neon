from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlmodel import SQLModel
from app.auth.model import Session
from app.staff.model import Staff
from app.auth.schemas import LoginRequest
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.core.config import settings
import secrets
import uuid

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def generate_token() -> str:
    return secrets.token_hex(32)


async def login(db: AsyncSession, data: LoginRequest, ip_address: str = None) -> dict:
    result = await db.execute(select(Staff).where(Staff.email == data.email))
    staff = result.scalar_one_or_none()

    if not staff:
        return None

    # Check if account is locked
    if staff.locked_until and staff.locked_until > datetime.utcnow():
        return {"error": "Account is locked. Try again later."}

    # Verify password
    if not verify_password(data.password, staff.password_hash):
        staff.failed_attempts += 1
        if staff.failed_attempts >= 5:
            staff.locked_until = datetime.utcnow() + timedelta(minutes=30)
        await db.commit()
        return None

    # Reset failed attempts on successful login
    staff.failed_attempts = 0
    staff.locked_until = None
    await db.commit()

    # Create session
    token = generate_token()
    expires_at = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    session = Session(
        staff_id=staff.id,
        token=token,
        ip_address=ip_address,
        login_at=datetime.utcnow(),
        expires_at=expires_at,
        is_active=True
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return {
        "message": "Login successful",
        "staff_id": str(staff.id),
        "role": staff.role,
        "token": token,
        "expires_at": expires_at
    }


async def logout(db: AsyncSession, token: str) -> bool:
    result = await db.execute(select(Session).where(Session.token == token))
    session = result.scalar_one_or_none()
    if not session:
        return False
    session.is_active = False
    await db.commit()
    return True


async def get_session(db: AsyncSession, token: str) -> Session | None:
    result = await db.execute(
        select(Session).where(Session.token == token, Session.is_active == True)
    )
    session = result.scalar_one_or_none()
    if not session:
        return None
    if session.expires_at < datetime.utcnow():
        session.is_active = False
        await db.commit()
        return None
    return session