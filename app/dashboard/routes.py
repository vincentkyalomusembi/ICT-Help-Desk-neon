from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import AdminStaff
from app.dashboard import service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/admin")
async def admin_dashboard(
    _: AdminStaff,
    db: AsyncSession = Depends(get_db),
):
    """
    Consolidated admin dashboard data — ticket summary, queued count,
    recent tickets, ICT personnel, asset breakdown, staff total, and
    active sessions in a single response, cached for 20 seconds.
    """
    return await service.get_admin_dashboard(db)