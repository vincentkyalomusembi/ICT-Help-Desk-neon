from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.audit.schemas import AuditLogCreate, AuditLogResponse, AuditLogUpdate
from app.audit.service import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])

@router.post("/", response_model=AuditLogResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_log(
    payload: AuditLogCreate,
    session: AsyncSession = Depends(get_db),
):
    # create a new audit log entry
    return await audit_service.create(session, payload)

@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_logs(session: AsyncSession = Depends(get_db)):
    # Retrieve all audit records
    return await audit_service.list(session)

@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit(log_id: int, session: AsyncSession = Depends(get_db)):
    # Retrieve a specific audit record by ID
    log = await audit_service.get(session, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log

@router.patch("/{log_id}", response_model=AuditLogResponse)
async def update_audit(
    log_id: int,
    payload: AuditLogUpdate,
    session: AsyncSession = Depends(get_db),
):
    # Update an existing audit record
    updated = await audit_service.update(session, log_id, payload)
    if updated is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return updated

@router.delete("/{log_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_audit(log_id: int, session: AsyncSession = Depends(get_db)):
    # Delete an audit record
    deleted = await audit_service.delete(session, log_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Audit log not found")