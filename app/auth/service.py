"""
app/sessions/service.py
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlmodel import Session, select

from app.auth.model import Session as DBSession
from app.auth.schemas import LoginRequest
from app.staff.model import Staff
from app.staff import service as staff_service
from app.core.security import verify_password, generate_session_token
from app.core.config import settings


#helpers 

def _get_client_ip(request: Request) -> Optional[str]:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else None


#login 

def login(db: Session, payload: LoginRequest, request: Request) -> DBSession:
    # 1. Find staff by email
    staff = staff_service.get_staff_by_email(db, payload.email)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    
    if staff_service.is_account_locked(staff):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {staff.locked_until.isoformat()}. "
                   "Please contact an administrator.",
        )

    if not verify_password(payload.password, staff.password_hash):
        staff_service.record_failed_attempt(db, staff)
        remaining = max(0, 5 - staff.failed_attempts)
        detail = (
            f"Invalid email or password. {remaining} attempt(s) remaining before lockout."
            if remaining > 0
            else "Account has been locked due to too many failed attempts."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    staff_service.reset_failed_attempts(db, staff)

    now = datetime.now(timezone.utc)
    session = DBSession(
        staff_id=staff.id,
        token=generate_session_token(),
        ip_address=_get_client_ip(request),
        login_at=now,
        expires_at=now + timedelta(hours=settings.SESSION_DURATION_HOURS),
        is_active=True,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


#logout 

def logout(db: Session, token: str) -> None:
    session = db.exec(
        select(DBSession).where(DBSession.token == token)
    ).first()

    if not session or not session.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session not found or already logged out.",
        )

    session.is_active = False
    db.add(session)
    db.commit()


def logout_all(db: Session, staff_id: UUID) -> int:
    """Invalidate every active session for a staff member. Returns count closed."""
    sessions = db.exec(
        select(DBSession).where(
            DBSession.staff_id == staff_id,
            DBSession.is_active == True,  
        )
    ).all()

    for s in sessions:
        s.is_active = False
        db.add(s)

    db.commit()
    return len(sessions)


#queries 
def list_active_sessions(db: Session, staff_id: UUID) -> list[DBSession]:
    now = datetime.now(timezone.utc)
    return list(
        db.exec(
            select(DBSession).where(
                DBSession.staff_id == staff_id,
                DBSession.is_active == True,  
                DBSession.expires_at > now,
            )
        ).all()
    )


def list_all_sessions(
    db: Session,
    *,
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
    return list(db.exec(stmt).all())