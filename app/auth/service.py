from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.model import Session as DBSession
from app.auth.schemas import LoginRequest
from app.staff.model import Staff
from app.core.config import settings
from app.core.security import verify_password, generate_session_token
from app.audit.service import audit_service
from app.audit.schemas import AuditLogCreate
from app.audit.model import AuditAction


# Helpers

def _get_client_ip(request: Request) -> Optional[str]:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


# Login

async def login(db: AsyncSession, payload: LoginRequest, request: Request) -> dict:
    result = await db.execute(select(Staff).where(Staff.email == payload.email))
    staff = result.scalar_one_or_none()

    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if staff.locked_until and staff.locked_until > datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {staff.locked_until.isoformat()}. Please contact an administrator.",
        )

    if not staff.is_activated:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not activated. Please contact an administrator.",
        )

    if not verify_password(payload.password, staff.password_hash):
        staff.failed_attempts += 1
        if staff.failed_attempts >= 5:
            staff.locked_until = datetime.now(timezone.utc) + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
        await db.commit()
        remaining = max(0, 5 - staff.failed_attempts)
        detail = (
            f"Invalid email or password. {remaining} attempt(s) remaining before lockout."
            if remaining > 0
            else "Account has been locked due to too many failed attempts."
        )

        await audit_service.create_system(
            session=db,
            log_in=AuditLogCreate(
                staff_id=staff.id,
                action=AuditAction.LOGIN_FAILED,
                table_name="sessions",
                record_id=None,
                mac_address=None,
            ),
            ip_address=_get_client_ip(request),
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    staff.failed_attempts = 0
    staff.locked_until = None
    await db.commit()

    now = datetime.now(timezone.utc)
    session = DBSession(
        staff_id=staff.id,
        token=generate_session_token(),
        ip_address=_get_client_ip(request),
        login_at=now,
        expires_at=now + timedelta(minutes=settings.SESSION_EXPIRE_MINUTES),
        is_active=True,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    await audit_service.create(
        session=db,
        log_in=AuditLogCreate(
            staff_id=staff.id,
            action=AuditAction.LOGIN_SUCCESS,
            table_name="sessions",
            record_id=str(session.id),
            mac_address=None,
        ),
        user_session=session,
    )

    return {
        "message": "Login successful.",
        "staff_id": staff.id,
        "role": staff.role.value,
        "token": session.token,
        "expires_at": session.expires_at,
    }


# Logout

async def logout(db: AsyncSession, token: str) -> None:
    result = await db.execute(select(DBSession).where(DBSession.token == token))
    session = result.scalar_one_or_none()

    if not session or not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found or already logged out.",
        )

    session.is_active = False
    db.add(session)
    await db.commit()

    await audit_service.create(
        session=db,
        log_in=AuditLogCreate(
            staff_id=session.staff_id,
            action=AuditAction.LOGOUT,
            table_name="sessions",
            record_id=str(session.id),
            mac_address=None,
        ),
        user_session=session,
    )


async def logout_all(db: AsyncSession, staff_id: UUID) -> int:
    result = await db.execute(
        select(DBSession).where(
            DBSession.staff_id == staff_id,
            DBSession.is_active == True,
        )
    )
    sessions = result.scalars().all()

    for s in sessions:
        s.is_active = False
        db.add(s)

    await db.commit()

    for s in sessions:
        await audit_service.create(
            session=db,
            log_in=AuditLogCreate(
                staff_id=staff_id,
                action=AuditAction.LOGOUT,
                table_name="sessions",
                record_id=str(s.id),
                mac_address=None,
            ),
            user_session=s,
        )

    return len(sessions)


# Queries

async def list_active_sessions(db: AsyncSession, staff_id: UUID) -> list[DBSession]:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(DBSession).where(
            DBSession.staff_id == staff_id,
            DBSession.is_active == True,
            DBSession.expires_at > now,
        )
    )
    return result.scalars().all()


async def list_all_sessions(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    staff_id: Optional[UUID] = None,
    active_only: bool = False,
) -> list[DBSession]:
    stmt = select(DBSession)
    if staff_id:
        stmt = stmt.where(DBSession.staff_id == staff_id)
    if active_only:
        stmt = stmt.where(
            DBSession.is_active == True,
            DBSession.expires_at > datetime.now(timezone.utc),
        )
    stmt = stmt.order_by(DBSession.login_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()