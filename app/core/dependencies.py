from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.auth.model import Session as DBSession
from app.staff.model import Staff, UserRole


def _extract_token(request: Request) -> str:
    token = request.cookies.get("session_id")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. No session cookie found.",
        )
    return token


async def _resolve_authenticated(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> tuple[Staff, DBSession]:
    """
    Single joined query resolving both the session and the staff member
    together. FastAPI caches this dependency's result per request, so
    routes depending on both CurrentStaff and CurrentSession only pay
    for one round-trip instead of two.
    """
    token = _extract_token(request)

    result = await db.execute(
        select(Staff, DBSession)
        .join(DBSession, DBSession.staff_id == Staff.id)
        .where(DBSession.token == token)
    )
    row = result.first()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
        )

    staff, db_session = row

    if not db_session.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been logged out.",
        )
    if datetime.now(timezone.utc) >= db_session.expires_at:
        db_session.is_active = False
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
        )

    return staff, db_session


async def get_current_session(
    resolved: tuple[Staff, DBSession] = Depends(_resolve_authenticated),
) -> DBSession:
    _, db_session = resolved
    return db_session


async def get_current_staff(
    resolved: tuple[Staff, DBSession] = Depends(_resolve_authenticated),
) -> Staff:
    staff, _ = resolved

    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff account no longer exists.",
        )

    return staff


async def get_current_active_staff(
    current: Staff = Depends(get_current_staff),
) -> Staff:
    if current.locked_until and datetime.now(timezone.utc) < current.locked_until:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {current.locked_until.isoformat()}.",
        )
    return current


async def get_current_staff_with_department(
    current: Staff = Depends(get_current_active_staff),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """Use on staff-profile endpoints that need current.department."""
    if "department" not in current.__dict__:
        result = await db.execute(
            select(Staff)
            .where(Staff.id == current.id)
            .options(selectinload(Staff.department))
        )
        current = result.scalar_one()
    return current


async def get_current_staff_with_ict_profile(
    current: Staff = Depends(get_current_active_staff),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """Use on ICT/ticket-assignment endpoints that need current.ict_profile."""
    if "ict_profile" not in current.__dict__:
        result = await db.execute(
            select(Staff)
            .where(Staff.id == current.id)
            .options(selectinload(Staff.ict_profile))
        )
        current = result.scalar_one()
    return current


async def require_admin(
    current: Staff = Depends(get_current_active_staff),
) -> Staff:
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current


async def require_ict(
    current: Staff = Depends(get_current_active_staff),
) -> Staff:
    if current.role not in {UserRole.ict_personnel, UserRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ICT personnel access required.",
        )
    return current

async def require_ict_with_profile(
    current: Staff = Depends(require_ict),
    db: AsyncSession = Depends(get_db),
) -> Staff:
    """Use on ICT-only endpoints that also need current.ict_profile."""
    if "ict_profile" not in current.__dict__:
        result = await db.execute(
            select(Staff)
            .where(Staff.id == current.id)
            .options(selectinload(Staff.ict_profile))
        )
        current = result.scalar_one()
    return current

# Type aliases
CurrentStaff = Annotated[Staff, Depends(get_current_active_staff)]
AdminStaff = Annotated[Staff, Depends(require_admin)]
IctStaff = Annotated[Staff, Depends(require_ict)]
IctStaffWithProfile = Annotated[Staff, Depends(require_ict_with_profile)]
CurrentSession = Annotated[DBSession, Depends(get_current_session)]
StaffWithDepartment = Annotated[Staff, Depends(get_current_staff_with_department)]
StaffWithIctProfile = Annotated[Staff, Depends(get_current_staff_with_ict_profile)]