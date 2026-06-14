from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentStaff, IctStaff, AdminStaff
from app.ict_personnel.schemas import (
    IctPersonnelCreate,
    IctPersonnelResponse,
    IctPersonnelUpdate,
    IctPersonnelDutyUpdate,
    IctPersonnelSetup,
)
from app.ict_personnel.service import ict_personnel_service

router = APIRouter(prefix="/ict-personnel", tags=["ICT Personnel"])


# NOTE: /me/setup must come before /{personnel_id} to avoid
# FastAPI matching "me" as an integer personnel_id

@router.post("/me/setup", response_model=IctPersonnelResponse)
async def setup_my_profile(
    payload: IctPersonnelSetup,
    current_staff: IctStaff,
    session: AsyncSession = Depends(get_db),
):
    """
    ICT personnel sets their specialization after first login.
    Profile becomes active and eligible for ticket assignments.
    """
    try:
        return await ict_personnel_service.setup_profile(
            session, current_staff.id, payload
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/", response_model=IctPersonnelResponse, status_code=status.HTTP_201_CREATED)
async def create_ict_personnel(
    payload: IctPersonnelCreate,
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    return await ict_personnel_service.create(session, payload)


@router.get("/", response_model=List[IctPersonnelResponse])
async def list_ict_personnel(
    _: CurrentStaff,
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    return await ict_personnel_service.list(session, skip, limit)


@router.get("/{personnel_id}", response_model=IctPersonnelResponse)
async def get_ict_personnel(
    personnel_id: int,
    _: CurrentStaff,
    session: AsyncSession = Depends(get_db),
):
    personnel = await ict_personnel_service.get(session, personnel_id)
    if personnel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ICT personnel profile not found."
        )
    return personnel


@router.patch("/{personnel_id}", response_model=IctPersonnelResponse)
async def update_ict_personnel(
    personnel_id: int,
    payload: IctPersonnelUpdate,
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    personnel = await ict_personnel_service.update(session, personnel_id, payload)
    if personnel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ICT personnel profile not found."
        )
    return personnel


@router.patch("/{personnel_id}/duty-status", response_model=IctPersonnelResponse)
async def set_duty_status(
    personnel_id: int,
    payload: IctPersonnelDutyUpdate,
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    """
    Admin sets a technician off duty, on leave, or returns them to available.
    Cannot override busy — ticket lifecycle controls that.
    """
    try:
        payload.validate_duty_status()
        personnel = await ict_personnel_service.set_duty_status(
            session, personnel_id, payload.availability
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    if personnel is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ICT personnel profile not found."
        )
    return personnel


@router.delete("/{personnel_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ict_personnel(
    personnel_id: int,
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    deleted = await ict_personnel_service.delete(session, personnel_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ICT personnel profile not found."
        )