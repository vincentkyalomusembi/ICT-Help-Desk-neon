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
    TicketCategory.other: None,  # any available tech is valid
}


# ── Auto Assignment ────────────────────────────────────────────

async def _auto_assign(
    db: AsyncSession,
    category: TicketCategory,
) -> Optional[IctPersonnel]:
    specialization = CATEGORY_TO_SPECIALIZATION.get(category)

    stmt = select(IctPersonnel).where(
        IctPersonnel.is_active == True,
        IctPersonnel.availability == Availability.available,
    )

    if specialization:
        stmt = stmt.where(IctPersonnel.specialization == specialization)

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    if not candidates:
        return None

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
            return candidate

        if oldest_closed is None or last_closed < oldest_closed:
            oldest_closed = last_closed
            best = candidate

    return best


# ── Dequeue ────────────────────────────────────────────────────

async def _dequeue_tickets(
    db: AsyncSession,
    personnel: IctPersonnel,
) -> None:
    """
    After a technician closes a ticket and becomes available, assign the
    oldest queued ticket matching their specialization. Fires automatically
    on every ticket close so the queue drains without admin intervention.
    """
    if not personnel.specialization:
        return

    # All categories this specialization can handle
    matching_categories = [
        category
        for category, spec in CATEGORY_TO_SPECIALIZATION.items()
        if spec == personnel.specialization
    ]

    # Any specialization can also handle 'other' category tickets
    matching_categories.append(TicketCategory.other)

    result = await db.execute(
        select(Ticket)
        .where(
            Ticket.assigned_to_id == None,  # noqa: E711
            Ticket.status == TicketStatus.open,
            Ticket.category.in_(matching_categories),
        )
        .order_by(Ticket.created_at.asc())
        .limit(1)
    )
    oldest_queued = result.scalars().first()

    if oldest_queued:
        oldest_queued.assigned_to_id = personnel.id
        personnel.availability = Availability.busy
        db.add(oldest_queued)
        db.add(personnel)
        await db.commit()


# ── Ticket Services ────────────────────────────────────────────

async def create_ticket(
    db: AsyncSession,
    data: TicketCreate,
    staff_id: UUID,
    user_session: UserSession,
) -> Ticket:
    personnel = await _auto_assign(db, data.category)

    ticket = Ticket(
        staff_id=staff_id,
        assigned_to_id=personnel.id if personnel else None,
        title=data.title,
        description=data.description,
        category=data.category,
        status=TicketStatus.open,
    )
    db.add(ticket)

    if personnel:
        personnel.availability = Availability.busy

    await db.commit()
    await db.refresh(ticket)

    await audit_service.create(db, AuditLogCreate(
        staff_id=staff_id,
        action=AuditAction.TICKET_CREATED,
        table_name="tickets",
        record_id=str(ticket.id),
    ), user_session)

    if personnel:
        await audit_service.create(db, AuditLogCreate(
            staff_id=staff_id,
            action=AuditAction.TICKET_ASSIGNED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

    if not personnel and data.category == TicketCategory.security_incidents:
        pass

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


async def list_queued_tickets(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> list[Ticket]:
    """Unassigned tickets waiting for a specialist to become available."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.assigned_to_id == None,  # noqa: E711
            Ticket.status == TicketStatus.open,
        )
        .order_by(Ticket.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def list_unresolved_tickets(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> list[Ticket]:
    """Tickets closed as unresolved — need admin follow-up or reassignment."""
    result = await db.execute(
        select(Ticket).where(
            Ticket.status == TicketStatus.closed,
            Ticket.comment != None,  # noqa: E711
        )
        .order_by(Ticket.closed_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def get_ticket_summary(db: AsyncSession) -> dict:
    """Count of tickets grouped by status."""
    result = await db.execute(
        select(Ticket.status, func.count(Ticket.id).label("count"))
        .group_by(Ticket.status)
    )
    return {row.status.value: row.count for row in result.all()}


async def get_tickets_by_personnel(db: AsyncSession) -> list[dict]:
    """Ticket count per technician broken down by status."""
    result = await db.execute(
        select(
            IctPersonnel.id,
            Ticket.status,
            func.count(Ticket.id).label("count"),
        )
        .join(Ticket, Ticket.assigned_to_id == IctPersonnel.id)
        .group_by(IctPersonnel.id, Ticket.status)
        .order_by(IctPersonnel.id)
    )
    summary: dict = {}
    for row in result.all():
        if row.id not in summary:
            summary[row.id] = {"personnel_id": row.id, "tickets": {}}
        summary[row.id]["tickets"][row.status.value] = row.count
    return list(summary.values())


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
                f"FIFO violation: ticket #{oldest_id} must be "
                f"addressed before #{ticket_id}."
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
            db.add(personnel)

        await db.commit()
        await db.refresh(ticket)

        await audit_service.create(db, AuditLogCreate(
            staff_id=user_session.staff_id,
            action=AuditAction.TICKET_CLOSED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

        # Dequeue: assign oldest waiting ticket to now-available technician
        if personnel:
            await _dequeue_tickets(db, personnel)

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


async def reassign_ticket(
    db: AsyncSession,
    ticket_id: int,
    user_session: UserSession,
) -> Ticket:
    """Admin: assign a queued or unresolved ticket to next available specialist."""
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        raise LookupError(f"Ticket #{ticket_id} not found.")

    personnel = await _auto_assign(db, ticket.category)
    if not personnel:
        raise ValueError(
            f"No available ICT specialist for category '{ticket.category}'. "
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

    if ticket.assigned_to_id:
        personnel_result = await db.execute(
            select(IctPersonnel).where(IctPersonnel.id == ticket.assigned_to_id)
        )
        personnel = personnel_result.scalar_one_or_none()
        if personnel and personnel.availability == Availability.busy:
            personnel.availability = Availability.available

    await db.delete(ticket)
    await db.commit()
    return True


async def get_stuck_tickets(
    db: AsyncSession,
    threshold_hours: int = 24,
    skip: int = 0,
    limit: int = 50,
) -> list[Ticket]:
    """Tickets open or in_progress beyond threshold — may need intervention."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=threshold_hours)
    result = await db.execute(
        select(Ticket).where(
            Ticket.status.in_([
                TicketStatus.open,
                TicketStatus.in_progress,
            ]),
            Ticket.created_at <= cutoff,
        )
        .order_by(Ticket.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()