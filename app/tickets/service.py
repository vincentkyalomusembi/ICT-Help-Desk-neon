from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID

from app.tickets.model import Ticket, TicketStatus, TicketCategory
from app.tickets.schemas import TicketCreate, TicketUpdate
from app.ict_personnel.model import IctPersonnel, Availability, Specialization
from app.audit.service import audit_service
from app.audit.schemas import AuditLogCreate
from app.audit.model import AuditAction
from app.auth.model import Session as UserSession


# ── Triage Mapping ─────────────────────────────────────────────

CATEGORY_TO_SPECIALIZATION = {
    TicketCategory.hardware: Specialization.hardware,
    TicketCategory.software: Specialization.software_and_systems,
    TicketCategory.network: Specialization.networking,
    TicketCategory.security_incidents: Specialization.security,
    TicketCategory.access_permissions: Specialization.software_and_systems,
    TicketCategory.other: None,
}


# ── Auto Assignment ────────────────────────────────────────────

# CHANGE 2: Returns Optional[IctPersonnel] — None instead of raising when nobody available.
# Also falls back to any available tech if no specialist found.
async def _auto_assign(db: AsyncSession, category: TicketCategory) -> Optional[IctPersonnel]:
    specialization = CATEGORY_TO_SPECIALIZATION.get(category)

    stmt = select(IctPersonnel).where(
        IctPersonnel.is_active == True,
        IctPersonnel.availability == Availability.available,
    )
    if specialization:
        stmt = stmt.where(IctPersonnel.specialization == specialization)

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    # Fallback: if no specialist found, try any available tech
    if not candidates and specialization:
        fallback_stmt = select(IctPersonnel).where(
            IctPersonnel.is_active == True,
            IctPersonnel.availability == Availability.available,
        )
        fallback_result = await db.execute(fallback_stmt)
        candidates = fallback_result.scalars().all()

    # No one available at all — return None instead of raising
    if not candidates:
        return None

    # Among available, pick the one idle longest (fairness)
    best = None
    oldest_closed = None

    for candidate in candidates:
        last_result = await db.execute(
            select(func.max(Ticket.closed_at)).where(
                Ticket.assigned_to_id == candidate.id
            )
        )
        last_closed = last_result.scalar()

        if last_closed is None:
            # Never had a ticket — highest priority
            return candidate

        if oldest_closed is None or last_closed < oldest_closed:
            oldest_closed = last_closed
            best = candidate

    return best  # May be None if loop somehow yields nothing


# ── Ticket Services ────────────────────────────────────────────

# CHANGE 3: Handles None from _auto_assign — queues ticket unassigned.
async def create_ticket(
    db: AsyncSession,
    data: TicketCreate,
    staff_id: UUID,
    user_session: UserSession,
) -> Ticket:
    personnel = await _auto_assign(db, data.category)

    ticket = Ticket(
        staff_id=staff_id,
        # CHANGE 1: assigned_to_id is Optional[int]; None when no tech available
        assigned_to_id=personnel.id if personnel else None,
        title=data.title,
        description=data.description,
        category=data.category,
        status=TicketStatus.open,
    )
    db.add(ticket)

    if personnel:
        # Only mark busy when actually assigned
        personnel.availability = Availability.busy

    await db.commit()
    await db.refresh(ticket)

    # Audit: ticket created (always)
    await audit_service.create(db, AuditLogCreate(
        staff_id=staff_id,
        action=AuditAction.TICKET_CREATED,
        table_name="tickets",
        record_id=str(ticket.id),
    ), user_session)

    # Audit: assigned only when a tech was found
    if personnel:
        await audit_service.create(db, AuditLogCreate(
            staff_id=staff_id,
            action=AuditAction.TICKET_ASSIGNED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

    return ticket


async def get_ticket(
    db: AsyncSession,
    ticket_id: int,
    viewer_personnel_id: Optional[int] = None,
    user_session: Optional[UserSession] = None,
) -> Optional[Ticket]:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()

    if not ticket:
        return None

    # Auto in_progress: only when the assigned ICT views their own ticket
    if (
        viewer_personnel_id is not None
        and ticket.assigned_to_id == viewer_personnel_id
        and ticket.status == TicketStatus.open
    ):
        ticket.status = TicketStatus.in_progress
        await db.commit()
        await db.refresh(ticket)

        if user_session:
            await audit_service.create(db, AuditLogCreate(
                staff_id=user_session.staff_id,
                action=AuditAction.TICKET_UPDATED,
                table_name="tickets",
                record_id=str(ticket.id),
            ), user_session)

    return ticket


async def list_tickets(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    staff_id: Optional[UUID] = None,
    assigned_to_id: Optional[int] = None,
) -> list[Ticket]:
    stmt = select(Ticket).order_by(Ticket.created_at.asc())

    if staff_id:
        stmt = stmt.where(Ticket.staff_id == staff_id)
    if assigned_to_id:
        stmt = stmt.where(Ticket.assigned_to_id == assigned_to_id)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


# CHANGE 5: New helper — admin view of unassigned open tickets.
async def list_queued_tickets(db: AsyncSession) -> list[Ticket]:
    """Admin: tickets queued without assignment (no tech was available at creation)."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.assigned_to_id == None,  # noqa: E711 — SQLAlchemy requires == None
            Ticket.status == TicketStatus.open,
        ).order_by(Ticket.created_at.asc())
    )
    return result.scalars().all()


async def update_ticket(
    db: AsyncSession,
    ticket_id: int,
    data: TicketUpdate,
    acting_personnel_id: int,
    user_session: UserSession,
) -> Optional[Ticket]:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    if ticket.assigned_to_id != acting_personnel_id:
        raise PermissionError("You can only update tickets assigned to you.")

    if data.status in (TicketStatus.resolved, TicketStatus.unresolved):
        oldest_result = await db.execute(
            select(func.min(Ticket.id)).where(
                Ticket.assigned_to_id == ticket.assigned_to_id,
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
            )
        )
        oldest_id = oldest_result.scalar()
        if oldest_id and oldest_id != ticket_id:
            raise ValueError(
                f"FIFO violation: ticket #{oldest_id} must be addressed before #{ticket_id}."
            )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    if ticket.status in (TicketStatus.resolved, TicketStatus.unresolved):
        ticket.status = TicketStatus.closed
        ticket.closed_at = datetime.now(timezone.utc)

        result = await db.execute(
            select(IctPersonnel).where(IctPersonnel.id == ticket.assigned_to_id)
        )
        personnel = result.scalar_one_or_none()
        if personnel:
            personnel.availability = Availability.available

        await db.commit()
        await db.refresh(ticket)

        await audit_service.create(db, AuditLogCreate(
            staff_id=user_session.staff_id,
            action=AuditAction.TICKET_CLOSED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)
    else:
        await db.commit()
        await db.refresh(ticket)

        await audit_service.create(db, AuditLogCreate(
            staff_id=user_session.staff_id,
            action=AuditAction.TICKET_UPDATED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

    return ticket


# CHANGE 4: Raises clean ValueError (no tech) or LookupError (ticket not found)
# so the route handler can map them to distinct HTTP codes.
async def reassign_ticket(
    db: AsyncSession,
    ticket_id: int,
    user_session: UserSession,
) -> Ticket:
    """Admin-only: assign a queued or closed ticket to the next available technician."""
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        raise LookupError(f"Ticket #{ticket_id} not found.")

    personnel = await _auto_assign(db, ticket.category)
    if not personnel:
        raise ValueError(
            f"No available ICT personnel for category '{ticket.category}'. "
            "Ticket remains queued."
        )

    ticket.assigned_to_id = personnel.id
    ticket.status = TicketStatus.open
    ticket.comment = None
    ticket.closed_at = None

    personnel.availability = Availability.busy

    await db.commit()
    await db.refresh(ticket)

    await audit_service.create(db, AuditLogCreate(
        staff_id=user_session.staff_id,
        action=AuditAction.TICKET_ASSIGNED,
        table_name="tickets",
        record_id=str(ticket.id),
    ), user_session)

    return ticket


async def delete_ticket(db: AsyncSession, ticket_id: int) -> bool:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return False
    await db.delete(ticket)
    await db.commit()
    return True


async def get_stuck_tickets(
    db: AsyncSession,
    threshold_hours: int = 24,
) -> list[Ticket]:
    """Tickets open/in_progress/unresolved beyond the threshold."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=threshold_hours)
    result = await db.execute(
        select(Ticket).where(
            Ticket.status.in_([
                TicketStatus.open,
                TicketStatus.in_progress,
                TicketStatus.unresolved,
            ]),
            Ticket.created_at <= cutoff
        ).order_by(Ticket.created_at.asc())
    )
    return result.scalars().all()