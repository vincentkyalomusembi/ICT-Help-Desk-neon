from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_staff
from app.staff.model import Staff, UserRole
from app.auth.schemas import LoginRequest, LoginResponse, LogoutRequest, SessionResponse
from app.auth import service

router = APIRouter(prefix="/auth", tags=["Auth"])


#Permission Helpers 

def require_admin(current: Staff = Depends(get_current_staff)) -> Staff:
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current


#Routes

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login and receive a session token",
)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await service.login(db, payload, request)


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout current session",
)
async def logout(
    payload: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    await service.logout(db, payload.token)
    return {"message": "Logged out successfully."}


@router.post(
    "/logout/all",
    status_code=status.HTTP_200_OK,
    summary="Logout all your active sessions",
)
async def logout_all(
    current: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    count = await service.logout_all(db, current.id)
    return {"message": f"{count} session(s) terminated."}


@router.get(
    "/sessions/me",
    response_model=list[SessionResponse],
    summary="List your active sessions",
)
async def my_sessions(
    current: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_active_sessions(db, current.id)


@router.get(
    "/sessions",
    response_model=list[SessionResponse],
    summary="List all sessions (admin only)",
)
async def all_sessions(
    _: Staff = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    staff_id: Optional[UUID] = Query(None),
    active_only: bool = Query(False),
):
    return await service.list_all_sessions(
        db,
        skip=skip,
        limit=limit,
        staff_id=staff_id,
        active_only=active_only,
    )


@router.delete(
    "/sessions/{staff_id}",
    status_code=status.HTTP_200_OK,
    summary="Force-logout all sessions for a staff member (admin only)",
)
async def force_logout(
    staff_id: UUID,
    _: Staff = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    count = await service.logout_all(db, staff_id)
    return {"message": f"{count} session(s) terminated for staff {staff_id}."}