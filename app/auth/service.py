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
