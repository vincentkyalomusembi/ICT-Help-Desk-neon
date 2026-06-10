from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_staff
from app.staff.model import Staff, UserRole
from app.staff.schemas import (
    StaffCreate, StaffCreateResponse, StaffResponse, StaffUpdate, PasswordChangeRequest,
    DirectorateCreate, DirectorateUpdate, DirectorateResponse,
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
)
from app.staff.service import StaffService


def require_admin(current: Staff = Depends(get_current_staff)) -> Staff:
    if current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required.",
        )
    return current


def verify_admin_or_self(staff_id: UUID, current: Staff) -> None:
    if current.role != UserRole.admin and current.id != staff_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own record.",
        )


# STAFF ROUTES

staff_router = APIRouter(prefix="/staff", tags=["Staff"])


@staff_router.post(
    "/",
    response_model=StaffCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new staff member (open)",
)
async def create_staff(
    payload: StaffCreate,
    session: AsyncSession = Depends(get_db),
):
    return await StaffService(session).create_staff(payload)


@staff_router.get(
    "/",
    response_model=list[StaffResponse],
    summary="List all staff (admin only)",
)
async def list_staff(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    directorate_id: Optional[int] = Query(None),
    department_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    return await StaffService(session).list_staff(
        skip=skip,
        limit=limit,
        directorate_id=directorate_id,
        department_id=department_id,
    )


@staff_router.get(
    "/me",
    response_model=StaffResponse,
    summary="Get the currently authenticated staff member",
)
async def get_me(current: Staff = Depends(get_current_staff)):
    return current


@staff_router.get(
    "/{staff_id}",
    response_model=StaffResponse,
    summary="Get a staff member by ID (admin only)",
)
async def get_staff(
    staff_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    return await StaffService(session).get_staff_by_id(staff_id)


@staff_router.patch(
    "/{staff_id}",
    response_model=StaffResponse,
    summary="Update a staff member (admin or self, role change is admin only)",
)
async def update_staff(
    staff_id: UUID,
    payload: StaffUpdate,
    session: AsyncSession = Depends(get_db),
    current: Staff = Depends(get_current_staff),
):
    verify_admin_or_self(staff_id, current)
    if payload.role is not None and current.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can change roles.",
        )
    return await StaffService(session).update_staff(staff_id, payload)


@staff_router.delete(
    "/{staff_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a staff member (admin only)",
)
async def delete_staff(
    staff_id: UUID,
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    await StaffService(session).delete_staff(staff_id)


@staff_router.post(
    "/{staff_id}/change-password",
    response_model=StaffResponse,
    summary="Change password (admin or self)",
)
async def change_password(
    staff_id: UUID,
    payload: PasswordChangeRequest,
    session: AsyncSession = Depends(get_db),
    current: Staff = Depends(get_current_staff),
):
    verify_admin_or_self(staff_id, current)
    return await StaffService(session).change_password(
        staff_id,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )


# DIRECTORATE ROUTES

directorate_router = APIRouter(prefix="/directorates", tags=["Directorates"])


@directorate_router.post(
    "/",
    response_model=DirectorateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a directorate (admin only)",
)
async def create_directorate(
    payload: DirectorateCreate,
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    return await StaffService(session).create_directorate(payload)


@directorate_router.get(
    "/",
    response_model=list[DirectorateResponse],
    summary="List all directorates (authenticated)",
)
async def list_directorates(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    return await StaffService(session).list_directorates(skip=skip, limit=limit)


@directorate_router.get(
    "/{directorate_id}",
    response_model=DirectorateResponse,
    summary="Get a directorate by ID (authenticated)",
)
async def get_directorate(
    directorate_id: int,
    session: AsyncSession = Depends(get_db),
):
    return await StaffService(session).get_directorate_by_id(directorate_id)


@directorate_router.get(
    "/{directorate_id}/departments",
    response_model=list[DepartmentResponse],
    summary="List departments under a directorate (authenticated)",
)
async def list_departments_by_directorate(
    directorate_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    return await StaffService(session).list_departments(
        skip=skip, limit=limit, directorate_id=directorate_id
    )


@directorate_router.patch(
    "/{directorate_id}",
    response_model=DirectorateResponse,
    summary="Update a directorate (admin only)",
)
async def update_directorate(
    directorate_id: int,
    payload: DirectorateUpdate,
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    return await StaffService(session).update_directorate(directorate_id, payload)


@directorate_router.delete(
    "/{directorate_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a directorate (admin only)",
)
async def delete_directorate(
    directorate_id: int,
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    await StaffService(session).delete_directorate(directorate_id)


# DEPARTMENT ROUTES

department_router = APIRouter(prefix="/departments", tags=["Departments"])


@department_router.post(
    "/",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a department (admin only)",
)
async def create_department(
    payload: DepartmentCreate,
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    return await StaffService(session).create_department(payload)


@department_router.get(
    "/",
    response_model=list[DepartmentResponse],
    summary="List all departments (authenticated)",
)
async def list_departments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    directorate_id: Optional[int] = Query(None, description="Filter by directorate"),
    session: AsyncSession = Depends(get_db),
):
    return await StaffService(session).list_departments(
        skip=skip, limit=limit, directorate_id=directorate_id
    )


@department_router.get(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Get a department by ID (authenticated)",
)
async def get_department(
    department_id: int,
    session: AsyncSession = Depends(get_db),
):
    return await StaffService(session).get_department_by_id(department_id)


@department_router.patch(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Update a department (admin only)",
)
async def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    return await StaffService(session).update_department(department_id, payload)


@department_router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a department (admin only)",
)
async def delete_department(
    department_id: int,
    session: AsyncSession = Depends(get_db),
    _: Staff = Depends(require_admin),
):
    await StaffService(session).delete_department(department_id)