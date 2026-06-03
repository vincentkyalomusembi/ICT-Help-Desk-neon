from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.ict_personnel.schemas import (
    IctPersonnelCreate,
    IctPersonnelResponse,
    IctPersonnelUpdate,
)
from app.ict_personnel.service import ict_personnel_service

router = APIRouter(prefix='/ict-personnel', tags=['ict_personnel'])


@router.post('/', response_model=IctPersonnelResponse, status_code=status.HTTP_201_CREATED)
async def create_ict_personnel(
    payload: IctPersonnelCreate,
    session: AsyncSession = Depends(get_db),
):
    return await ict_personnel_service.create(session, payload)


@router.get('/', response_model=List[IctPersonnelResponse])
async def list_ict_personnel(session: AsyncSession = Depends(get_db)):
    return await ict_personnel_service.list(session)


@router.get('/{personnel_id}', response_model=IctPersonnelResponse)
async def get_ict_personnel(
    personnel_id: int,
    session: AsyncSession = Depends(get_db),
):
    personnel = await ict_personnel_service.get(session, personnel_id)
    if personnel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='ICT personnel profile not found')
    return personnel


@router.patch('/{personnel_id}', response_model=IctPersonnelResponse)
async def update_ict_personnel(
    personnel_id: int,
    payload: IctPersonnelUpdate,
    session: AsyncSession = Depends(get_db),
):
    personnel = await ict_personnel_service.update(session, personnel_id, payload)
    if personnel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='ICT personnel profile not found')
    return personnel


@router.delete('/{personnel_id}', status_code=status.HTTP_204_NO_CONTENT)
async def delete_ict_personnel(
    personnel_id: int,
    session: AsyncSession = Depends(get_db),
):
    deleted = await ict_personnel_service.delete(session, personnel_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='ICT personnel profile not found')


@router.post('/{personnel_id}/sync-availability', response_model=IctPersonnelResponse)
async def sync_availability(
    personnel_id: int,
    session: AsyncSession = Depends(get_db),
):
    personnel = await ict_personnel_service.sync_availability(session, personnel_id)
    if personnel is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='ICT personnel profile not found')
    return personnel