from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.model import Session as AuthSession
from app.core.config import settings
from app.staff.model import Staff

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


class AuthService:
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def create_access_token(self, data: dict, expires_delta: timedelta) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + expires_delta
        to_encode.update({'exp': expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    async def get_staff_by_email(self, session: AsyncSession, email: str) -> Optional[Staff]:
        stmt = select(Staff).where(Staff.email == email)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def login(self, session: AsyncSession, email: str, password: str, ip_address: Optional[str] = None) -> dict:
        staff = await self.get_staff_by_email(session, email)
        if staff is None:
            raise ValueError('Invalid email or password')

        now = datetime.utcnow()
        if staff.locked_until and staff.locked_until > now:
            raise ValueError('Account is locked. Please try again later.')

        if not self.verify_password(password, staff.password_hash):
            staff.failed_attempts = (staff.failed_attempts or 0) + 1
            await session.commit()
            raise ValueError('Invalid email or password')

        if staff.failed_attempts:
            staff.failed_attempts = 0
            await session.commit()

        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = self.create_access_token(
            {
                'sub': str(staff.id),
                'role': str(staff.role),
            },
            expires_delta,
        )

        expires_at = now + expires_delta
        auth_session = AuthSession(
            staff_id=staff.id,
            token=access_token,
            ip_address=ip_address,
            login_at=now,
            expires_at=expires_at,
            is_active=True,
        )
        session.add(auth_session)
        await session.commit()
        await session.refresh(auth_session)

        return {
            'message': 'Login successful',
            'staff_id': staff.id,
            'role': str(staff.role),
            'token': access_token,
            'expires_at': expires_at,
            'session': auth_session,
        }

    async def logout(self, session: AsyncSession, token: str) -> bool:
        stmt = select(AuthSession).where(AuthSession.token == token, AuthSession.is_active == True)
        result = await session.execute(stmt)
        auth_session = result.scalars().first()
        if auth_session is None:
            return False

        auth_session.is_active = False
        await session.commit()
        return True

    async def list_sessions(self, session: AsyncSession) -> List[AuthSession]:
        stmt = select(AuthSession).order_by(AuthSession.id.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get_session(self, session: AsyncSession, session_id: int) -> Optional[AuthSession]:
        stmt = select(AuthSession).where(AuthSession.id == session_id)
        result = await session.execute(stmt)
        return result.scalars().first()


auth_service = AuthService()

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
