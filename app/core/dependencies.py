from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.auth.model import Session as DBSession
from app.staff.model import Staff, UserRole


def _extract_token(request: Request) -> str:
    """Extract bearer token from Authorization header."""
    auth_header: str = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_header[len("Bearer "):]


async def _resolve_session(token: str, db: AsyncSession) -> DBSession:
    """Look up and validate the session."""
    result = await db.execute(
        select(DBSession).where(DBSession.token == token)
    )
    db_session = result.scalar_one_or_none()

    if db_session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not db_session.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been logged out.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if datetime.now(timezone.utc) >= db_session.expires_at:
        db_session.is_active = False
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return db_session


async def get_current_session(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> DBSession:
    """Dependency that returns validated session."""
    token = _extract_token(request)
    return await _resolve_session(token, db)


async def get_current_staff(
    db_session: DBSession = Depends(get_current_session),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """Dependency that returns the current authenticated staff member."""
    result = await db.execute(
        select(Staff).where(Staff.id == db_session.staff_id)
    )
    staff = result.scalar_one_or_none()
    
    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff account no longer exists.",
        )
    return staff


async def get_current_active_staff(
    current: Staff = Depends(get_current_staff),
) -> Staff:
    """Dependency that ensures the staff account is not locked."""
    if current.locked_until and datetime.now(timezone.utc) < current.locked_until:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {current.locked_until.isoformat()}.",
        )
    return current


async def require_admin(
    current: Staff = Depends(get_current_active_staff),
) -> Staff:
    """Dependency that requires admin role."""
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current


async def require_ict(
    current: Staff = Depends(get_current_active_staff),
) -> Staff:
    """Dependency that requires ICT personnel or admin role."""
    if current.role not in {UserRole.ict_personnel, UserRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ICT personnel access required.",
        )
    return current


# Type aliases for easier use in route parameters
CurrentStaff = Annotated[Staff, Depends(get_current_active_staff)]
AdminStaff = Annotated[Staff, Depends(require_admin)]
IctStaff = Annotated[Staff, Depends(require_ict)]