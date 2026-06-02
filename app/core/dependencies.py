from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from app.core.database import get_session          
from app.auth.model import Session as DBSession 
from app.staff.model import Staff, UserRole


def _extract_token(request: Request) -> str:
    """
    Pull the bearer token from the Authorization header.

    Raises 401 if the header is missing or malformed.
    """
    auth_header: str = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return auth_header[len("Bearer "):]


def _resolve_session(token: str, db: Session) -> DBSession:
    """
    Look up the session row, validate it is active and not expired.

    Raises 401 on any failure so callers never have to think about it.
    """
    db_session = db.exec(
        select(DBSession).where(DBSession.token == token)
    ).first()

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
        db.add(db_session)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return db_session


def get_current_session(
    request: Request,
    db: Session = Depends(get_session),
) -> DBSession:
    """Dependency → validated DBSession row."""
    token = _extract_token(request)
    return _resolve_session(token, db)


def get_current_staff(
    db_session: DBSession = Depends(get_current_session),
    db: Session = Depends(get_session),
) -> Staff:
    """Dependency → the Staff record that owns the current session."""
    staff = db.get(Staff, db_session.staff_id)
    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff account no longer exists.",
        )
    return staff


def get_current_active_staff(
    current: Staff = Depends(get_current_staff),
) -> Staff:
    """
    Dependency → Staff that is not locked.

    Use this on any endpoint where a locked account must be blocked
    even if their token is still technically valid.
    """
    from app.core.security import utc_now  

    if current.locked_until and utc_now() < current.locked_until:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is locked until {current.locked_until.isoformat()}.",
        )
    return current


def require_admin(
    current: Staff = Depends(get_current_active_staff),
) -> Staff:
    """Dependency → Staff with admin role."""
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current


def require_ict(
    current: Staff = Depends(get_current_active_staff),
) -> Staff:
    """Dependency → Staff with ict_personnel (or admin) role."""
    if current.role not in {UserRole.ict_personnel, UserRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ICT personnel access required.",
        )
    return current


CurrentStaff = Annotated[Staff, Depends(get_current_active_staff)]
AdminStaff   = Annotated[Staff, Depends(require_admin)]
IctStaff     = Annotated[Staff, Depends(require_ict)]