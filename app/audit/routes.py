from typing import List

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.audit.schemas import AuditLogResponse
from app.audit.service import audit_service
from app.core.dependencies import AdminStaff

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/", response_model=List[AuditLogResponse])
async def list_audit_logs(
    _: AdminStaff,
    skip: int = 0,
    limit: int = 500,
    session: AsyncSession = Depends(get_db),
):
    return await audit_service.list(session, skip, limit)


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit(
    log_id: int,
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    log = await audit_service.get(session, log_id)
    if log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log
