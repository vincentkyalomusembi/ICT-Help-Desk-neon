import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.tickets.model import Ticket, TicketStatus
from app.tickets import service as tickets_service
from app.assets.model import Asset
from app.staff.model import Staff
from app.ict_personnel.service import ict_personnel_service
from app.auth import service as auth_service

# Simple in-process cache — good enough for a single Render instance.
# If you ever scale to multiple backend instances, swap this for Redis.
_CACHE: dict[str, Any] = {"data": None, "expires_at": 0.0}
_CACHE_TTL_SECONDS = 20


async def _build_admin_dashboard(db: AsyncSession) -> dict:
    # Ticket status counts
    ticket_summary = await tickets_service.get_ticket_summary(db)

    # Queued count — dedicated COUNT query, no row fetch
    queued_result = await db.execute(
        select(func.count(Ticket.id)).where(
            Ticket.assigned_to_id.is_(None),
            Ticket.status == TicketStatus.open,
        )
    )
    queued_count = queued_result.scalar_one()

    # 5 most recently created tickets
    recent_result = await db.execute(
        select(Ticket).order_by(Ticket.created_at.desc()).limit(5)
    )
    recent_tickets_raw = recent_result.scalars().all()
    recent_tickets = [
        {
            "id": t.id,
            "title": t.title,
            "category": t.category.value,
            "status": t.status.value,
            "staff_id": str(t.staff_id),
            "assigned_to_id": t.assigned_to_id,
            "comment": t.comment,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in recent_tickets_raw
    ]

    # ICT personnel — staff + department already eager-loaded by the service
    personnel_raw = await ict_personnel_service.list(db, skip=0, limit=100)
    personnel = [
        {
            "id": p.id,
            "staff_id": str(p.staff_id),
            "availability": p.availability.value,
            "specialization": p.specialization.value if p.specialization else None,
            "is_active": p.is_active,
            "full_name": p.staff.full_name if p.staff else None,
            "department": (
                p.staff.department.name if p.staff and p.staff.department else None
            ),
        }
        for p in personnel_raw
    ]

    # Assets — total + breakdown by device type, single grouped query
    asset_result = await db.execute(
        select(Asset.device_type, func.count(Asset.id)).group_by(Asset.device_type)
    )
    assets_by_type = {row[0].value: row[1] for row in asset_result.all()}
    assets_total = sum(assets_by_type.values())

    # Staff — total count via COUNT(*), not a full row fetch
    staff_count_result = await db.execute(select(func.count(Staff.id)))
    staff_total = staff_count_result.scalar_one()

    # Staff map — only for the staff_ids referenced by recent tickets
    # (personnel and sessions already carry their own staff relationship)
    staff_ids = {t["staff_id"] for t in recent_tickets}
    staff_map: dict[str, dict] = {}
    if staff_ids:
        staff_rows = await db.execute(
            select(Staff.id, Staff.full_name, Staff.email).where(
                Staff.id.in_(staff_ids)
            )
        )
        for row in staff_rows.all():
            staff_map[str(row.id)] = {
                "full_name": row.full_name,
                "email": row.email,
            }

    # Active sessions — staff already eager-loaded by auth_service
    sessions_raw = await auth_service.list_all_sessions(
        db, skip=0, limit=10, active_only=True
    )
    active_sessions = [
        {
            "id": s.id,
            "staff_id": str(s.staff_id),
            "ip_address": s.ip_address,
            "login_at": s.login_at.isoformat() if s.login_at else None,
            "is_active": s.is_active,
            "staff_name": s.staff.full_name if s.staff else None,
            "staff_email": s.staff.email if s.staff else None,
        }
        for s in sessions_raw
    ]

    return {
        "ticket_summary": ticket_summary,
        "queued_count": queued_count,
        "recent_tickets": recent_tickets,
        "personnel": personnel,
        "assets": {"total": assets_total, "by_type": assets_by_type},
        "staff_total": staff_total,
        "staff_map": staff_map,
        "active_sessions": active_sessions,
    }


async def get_admin_dashboard(db: AsyncSession, force_refresh: bool = False) -> dict:
    now = time.monotonic()
    if not force_refresh and _CACHE["data"] is not None and now < _CACHE["expires_at"]:
        return _CACHE["data"]

    data = await _build_admin_dashboard(db)
    _CACHE["data"] = data
    _CACHE["expires_at"] = now + _CACHE_TTL_SECONDS
    return data