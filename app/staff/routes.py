from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlmodel import Session

from app.core.database import get_session
from app.core.dependencies import get_current_staff
from app.staff.model import Staff, UserRole
from app.staff.schemas import StaffCreate, StaffResponse, StaffUpdate, PasswordChangeRequest
from app.staff.service import StaffService  

router = APIRouter(prefix="/staff", tags=["Staff"])



def require_admin(current: Staff = Depends(get_current_staff)) -> Staff:
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current


def require_admin_or_self(
    staff_id: UUID,
    current: Staff = Depends(get_current_staff),
) -> Staff:
    if current.role != UserRole.admin and current.id != staff_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own record.",
        )
    return current



@router.post(
    "/",
    response_model=StaffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new staff member (admin only)",
)
def create_staff(
    payload: StaffCreate,
    session: Session = Depends(get_session),
    _: Staff = Depends(require_admin),
):
    service = StaffService(session)
    return service.create_staff(payload)


@router.get(
    "/",
    response_model=list[StaffResponse],
    summary="List all staff (admin only)",
)
def list_staff(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    directorate_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    session: Session = Depends(get_session),
    _: Staff = Depends(require_admin),
):
    service = StaffService(session)
    return service.list_staff(
        skip=skip,
        limit=limit,
        directorate_id=directorate_id,
        department_id=department_id,
    )


@router.get(
    "/me",
    response_model=StaffResponse,
    summary="Get the currently authenticated staff member",
)
def get_me(current: Staff = Depends(get_current_staff)):
    return current


@router.get(
    "/{staff_id}",
    response_model=StaffResponse,
    summary="Get a staff member by ID (admin or self)",
)
def get_staff(
    staff_id: UUID,
    session: Session = Depends(get_session),
    current: Staff = Depends(get_current_staff),
):
    require_admin_or_self(staff_id, current)
    service = StaffService(session)
    return service.get_staff_by_id(staff_id)


@router.patch(
    "/{staff_id}",
    response_model=StaffResponse,
    summary="Update a staff member (admin or self — role change is admin only)",
)
def update_staff(
    staff_id: UUID,
    payload: StaffUpdate,
    session: Session = Depends(get_session),
    current: Staff = Depends(get_current_staff),
):
    current = require_admin_or_self(staff_id, current)

    if payload.role is not None and current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change roles.",
        )

    service = StaffService(session)
    return service.update_staff(staff_id, payload)


@router.delete(
    "/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a staff member (admin only)",
)
def delete_staff(
    staff_id: UUID,
    session: Session = Depends(get_session),
    _: Staff = Depends(require_admin),
):
    service = StaffService(session)
    service.delete_staff(staff_id)




@router.post(
    "/{staff_id}/change-password",
    response_model=StaffResponse,
    summary="Change password (admin or self)",
)

def change_password(
    staff_id: UUID,
    payload: PasswordChangeRequest,
    session: Session = Depends(get_session),
    current: Staff = Depends(get_current_staff),
):
    require_admin_or_self(staff_id, current)
    service = StaffService(session)
    return service.change_password(staff_id, payload.new_password)
