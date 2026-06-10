from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_staff
from app.core.config import settings
from app.staff.model import Staff, UserRole
from app.auth.schemas import LoginRequest, LoginResponse, SessionResponse
from app.auth import service
from app.auth.magic import verify_magic_token, resend_magic_token
from app.auth.password_reset import request_password_reset, reset_password
from app.staff.schemas import PasswordResetRequest, PasswordResetConfirm

router = APIRouter(prefix="/auth", tags=["Auth"])


# Permission Helpers

def require_admin(current: Staff = Depends(get_current_staff)) -> Staff:
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current


# Routes

@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    summary="Login and receive a session cookie",
)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await service.login(db, payload, request)

    response.set_cookie(
        key="session_id",
        value=result["token"],
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.SESSION_EXPIRE_MINUTES * 60,
    )

    result.pop("token")
    return result


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout current session",
)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    token = request.cookies.get("session_id")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active session.",
        )
    await service.logout(db, token)
    response.delete_cookie("session_id")
    return {"message": "Logged out successfully."}


@router.post(
    "/logout/all",
    status_code=status.HTTP_200_OK,
    summary="Logout all your active sessions",
)
async def logout_all(
    response: Response,
    current: Staff = Depends(get_current_staff),
    db: AsyncSession = Depends(get_db),
):
    count = await service.logout_all(db, current.id)
    response.delete_cookie("session_id")
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


@router.get(
    "/verify",
    status_code=status.HTTP_200_OK,
    summary="Verify magic link token from email",
)
async def verify_email(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await verify_magic_token(db, token)
    return {"message": "Email verified successfully. You can now log in."}


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    summary="Resend magic link verification email",
)
async def resend_verification(
    email: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    await resend_magic_token(db, email)
    return {"message": "Verification email resent. Please check your inbox."}


@router.post(
    "/forgot-password",
    status_code=status.HTTP_200_OK,
    summary="Request a password reset link",
)
async def forgot_password(
    payload: PasswordResetRequest,
    session: AsyncSession = Depends(get_db),
):
    await request_password_reset(session, payload.email)
    return {"message": "Password reset link sent. Check your email."}


@router.post(
    "/reset-password",
    status_code=status.HTTP_200_OK,
    summary="Reset password using token from email",
)
async def confirm_reset_password(
    payload: PasswordResetConfirm,
    session: AsyncSession = Depends(get_db),
):
    await reset_password(session, payload.token, payload.new_password)
    return {"message": "Password reset successful. You can now log in."}