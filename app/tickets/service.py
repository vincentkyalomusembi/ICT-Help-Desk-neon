from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from typing import Optional
from datetime import datetime, timezone, timedelta
from uuid import UUID

from app.tickets.model import Ticket, TicketStatus, TicketCategory
from app.tickets.schemas import TicketCreate, TicketUpdate, TicketConfirm
from app.ict_personnel.model import IctPersonnel, Availability, Specialization
from app.audit.service import audit_service
from app.audit.schemas import AuditLogCreate
from app.audit.model import AuditAction
from app.auth.model import Session as UserSession


# ── Triage Mapping ─────────────────────────────────────────────────────────────

CATEGORY_TO_SPECIALIZATION = {
    TicketCategory.hardware:           Specialization.hardware,
    TicketCategory.software:           Specialization.software_and_systems,
    TicketCategory.network:            Specialization.networking,
    TicketCategory.security_incidents: Specialization.security,
    TicketCategory.access_permissions: Specialization.software_and_systems,
    TicketCategory.other:              None,
}


# NEW: every function that returns a Ticket destined for TicketResponse
# serialization needs `staff` loaded, since TicketResponse.raised_by reads
# from it. A plain `await db.refresh(ticket)` after commit only guarantees
# column attributes are fresh — it does not reliably reload relationship
# attributes in async SQLAlchemy. Call this explicitly after every commit
# whose resulting ticket gets returned to a route.
async def _reload_staff(db: AsyncSession, ticket: Ticket) -> None:
    await db.refresh(ticket, attribute_names=["staff"])


# ── Auto Assignment ────────────────────────────────────────────────────────────

async def _auto_assign(
    db: AsyncSession,
    category: TicketCategory,
) -> Optional[IctPersonnel]:
    specialization = CATEGORY_TO_SPECIALIZATION.get(category)

    last_closed_subq = (
        select(
            Ticket.assigned_to_id.label("assigned_to_id"),
            func.max(Ticket.closed_at).label("last_closed"),
        )
        .group_by(Ticket.assigned_to_id)
        .subquery()
    )

    stmt = (
        select(IctPersonnel)
        .outerjoin(
            last_closed_subq,
            IctPersonnel.id == last_closed_subq.c.assigned_to_id,
        )
        .where(
            IctPersonnel.is_active == True,
            IctPersonnel.availability == Availability.available,
        )
        .order_by(
            last_closed_subq.c.last_closed.asc().nullsfirst(),
            IctPersonnel.id.asc(),
        )
        .limit(1)
    )

    if specialization:
        stmt = stmt.where(IctPersonnel.specialization == specialization)

    result = await db.execute(stmt)
    return result.scalars().first()


# ── Dequeue ────────────────────────────────────────────────────────────────────

async def _dequeue_tickets(
    db: AsyncSession,
    personnel: IctPersonnel,
) -> None:
    """
    After a technician becomes available, assign the oldest queued or
    reopened ticket matching their specialization.
    """
    if not personnel.specialization:
        return

    matching_categories = [
        category
        for category, spec in CATEGORY_TO_SPECIALIZATION.items()
        if spec == personnel.specialization
    ]
    matching_categories.append(TicketCategory.other)

    result = await db.execute(
        select(Ticket)
        .where(
            Ticket.assigned_to_id == None,  # noqa: E711
            Ticket.status.in_([TicketStatus.open, TicketStatus.reopened]),
            Ticket.category.in_(matching_categories),
        )
        .order_by(Ticket.created_at.asc())
        .limit(1)
    )
    oldest_queued = result.scalars().first()

    if oldest_queued:
        oldest_queued.assigned_to_id = personnel.id
        oldest_queued.status = TicketStatus.open
        personnel.availability = Availability.busy
        db.add(oldest_queued)
        db.add(personnel)
        await db.commit()


# ── Ticket Services ────────────────────────────────────────────────────────────

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
        db.add(personnel)

    # Flush (not commit) so ticket.id exists for the audit records below,
    # without paying for a separate round-trip yet.
    await db.flush()

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

    await db.commit()
    await db.refresh(ticket)
    await _reload_staff(db, ticket)  # NEW

    return ticket


async def get_ticket(
    db: AsyncSession,
    ticket_id: int,
    viewer_personnel_id: Optional[int] = None,
    user_session: Optional[UserSession] = None,
) -> Optional[Ticket]:
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.staff))  # NEW
        .where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        return None

    if (
        viewer_personnel_id is not None
        and ticket.assigned_to_id == viewer_personnel_id
        and ticket.status == TicketStatus.open
    ):
        ticket.status = TicketStatus.in_progress
        db.add(ticket)

        if user_session:
            await audit_service.create(db, AuditLogCreate(
                staff_id=user_session.staff_id,
                action=AuditAction.TICKET_UPDATED,
                table_name="tickets",
                record_id=str(ticket.id),
            ), user_session)

        await db.commit()
        await db.refresh(ticket)
        await _reload_staff(db, ticket)  # NEW

    return ticket


async def list_tickets(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
    staff_id: Optional[UUID] = None,
    assigned_to_id: Optional[int] = None,
) -> list[Ticket]:
    stmt = (
        select(Ticket)
        .options(selectinload(Ticket.staff))  # NEW
        .order_by(Ticket.created_at.asc())
    )

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
        select(Ticket)
        .options(selectinload(Ticket.staff))  # NEW
        .where(
            Ticket.assigned_to_id == None,  # noqa: E711
            Ticket.status == TicketStatus.open,
        )
        .order_by(Ticket.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def list_team_unresolved(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 50,
) -> list[Ticket]:
    """
    Tickets marked unresolved by a technician — visible to all ICT personnel.
    Any available team member can pick these up via pickup_ticket().

    NOTE: list_unresolved_tickets was removed as a duplicate of this function
    (#4 in the perf report). Any route/import that referenced
    list_unresolved_tickets should now call list_team_unresolved instead.
    """
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.staff))  # NEW
        .where(Ticket.status == TicketStatus.unresolved)
        .order_by(Ticket.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def list_pending_confirmation(
    db: AsyncSession,
    staff_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[Ticket]:
    """
    Tickets resolved by ICT awaiting confirmation from the staff member
    who raised them.
    """
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.staff))  # NEW
        .where(
            Ticket.staff_id == staff_id,
            Ticket.status == TicketStatus.pending_confirmation,
        )
        .order_by(Ticket.created_at.asc())
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

    # Only the assigned technician can update
    if ticket.assigned_to_id != acting_personnel_id:
        raise PermissionError("You can only update tickets assigned to you.")

    # FIFO enforcement — must close oldest ticket first
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

    # Apply all field updates from payload
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    # Load technician for release
    personnel_result = await db.execute(
        select(IctPersonnel).where(IctPersonnel.id == acting_personnel_id)
    )
    personnel = personnel_result.scalar_one_or_none()

    if data.status == TicketStatus.resolved:
        # ICT resolved — move to pending_confirmation, release technician immediately.
        # The setattr loop above already wrote resolution_notes to the ticket.
        ticket.status = TicketStatus.pending_confirmation
        db.add(ticket)

        if personnel:
            personnel.availability = Availability.available
            db.add(personnel)

        await audit_service.create(db, AuditLogCreate(
            staff_id=user_session.staff_id,
            action=AuditAction.TICKET_UPDATED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

        await db.commit()
        await db.refresh(ticket)
        await _reload_staff(db, ticket)  # NEW

        # Technician is free — pull next from queue
        if personnel:
            await _dequeue_tickets(db, personnel)

    elif data.status == TicketStatus.unresolved:
        # ICT couldn't fix — push to team view, release technician immediately.
        # The setattr loop above already wrote resolution_notes to the ticket.
        ticket.status = TicketStatus.unresolved
        ticket.assigned_to_id = None  # unassigned so any team member can pick it up
        db.add(ticket)

        if personnel:
            personnel.availability = Availability.available
            db.add(personnel)

        await audit_service.create(db, AuditLogCreate(
            staff_id=user_session.staff_id,
            action=AuditAction.TICKET_UPDATED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

        await db.commit()
        await db.refresh(ticket)
        await _reload_staff(db, ticket)  # NEW

        # Technician is free — pull next from queue
        if personnel:
            await _dequeue_tickets(db, personnel)

    else:
        # Regular update (description, comment, etc.)
        db.add(ticket)

        await audit_service.create(db, AuditLogCreate(
            staff_id=user_session.staff_id,
            action=AuditAction.TICKET_UPDATED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

        await db.commit()
        await db.refresh(ticket)
        await _reload_staff(db, ticket)  # NEW

    return ticket


async def confirm_ticket(
    db: AsyncSession,
    ticket_id: int,
    data: TicketConfirm,
    staff_id: UUID,
    user_session: UserSession,
) -> Optional[Ticket]:
    """
    Staff confirms or rejects a resolved ticket.
    Technician is already released — this only affects ticket status.
    """
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.staff))  # NEW
        .where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        return None

    # Only the staff member who raised the ticket can confirm
    if ticket.staff_id != staff_id:
        raise PermissionError("You can only confirm tickets you raised.")

    # Only pending_confirmation tickets can be confirmed
    if ticket.status != TicketStatus.pending_confirmation:
        raise ValueError("This ticket is not awaiting confirmation.")

    if data.confirmed:
        # Staff happy — close the ticket
        ticket.status = TicketStatus.closed
        ticket.closed_at = datetime.now(timezone.utc)
        db.add(ticket)

        await audit_service.create(db, AuditLogCreate(
            staff_id=staff_id,
            action=AuditAction.TICKET_CLOSED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

        await db.commit()
        await db.refresh(ticket)
        await _reload_staff(db, ticket)  # NEW

    else:
        # Staff not happy — reopen and send back to triage queue
        ticket.status = TicketStatus.reopened
        ticket.rejection_reason = data.rejection_reason
        ticket.assigned_to_id = None    # back to triage
        ticket.resolution_notes = None  # cleared for next technician
        ticket.closed_at = None
        db.add(ticket)

        await audit_service.create(db, AuditLogCreate(
            staff_id=staff_id,
            action=AuditAction.TICKET_UPDATED,
            table_name="tickets",
            record_id=str(ticket.id),
        ), user_session)

        await db.commit()
        await db.refresh(ticket)
        await _reload_staff(db, ticket)  # NEW

    return ticket


async def pickup_ticket(
    db: AsyncSession,
    ticket_id: int,
    acting_personnel_id: int,
    user_session: UserSession,
) -> Optional[Ticket]:
    """
    Any available ICT team member picks up an unresolved ticket from the
    team view. No specialization restriction — already escalated.
    """
    result = await db.execute(
        select(Ticket)
        .options(selectinload(Ticket.staff))  # NEW
        .where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()

    if not ticket:
        return None

    if ticket.status != TicketStatus.unresolved:
        raise ValueError("Only unresolved tickets can be picked up from the team view.")

    personnel_result = await db.execute(
        select(IctPersonnel).where(IctPersonnel.id == acting_personnel_id)
    )
    personnel = personnel_result.scalar_one_or_none()

    if not personnel:
        raise ValueError("ICT personnel profile not found.")

    if personnel.availability != Availability.available:
        raise ValueError(
            "You currently have an active ticket. "
            "Complete it before picking up another."
        )

    ticket.assigned_to_id = acting_personnel_id
    ticket.status = TicketStatus.open
    ticket.resolution_notes = None  # fresh start for new technician
    personnel.availability = Availability.busy

    db.add(ticket)
    db.add(personnel)

    await audit_service.create(db, AuditLogCreate(
        staff_id=user_session.staff_id,
        action=AuditAction.TICKET_ASSIGNED,
        table_name="tickets",
        record_id=str(ticket.id),
    ), user_session)

    await db.commit()
    await db.refresh(ticket)
    await _reload_staff(db, ticket)  # NEW

    return ticket


async def reassign_ticket(
    db: AsyncSession,
    ticket_id: int,
    user_session: UserSession,
) -> Ticket:
    """Admin: assign a queued or reopened ticket to next available specialist."""
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
    ticket.resolution_notes = None  # FIX: clear resolution notes on reassign
    ticket.closed_at = None
    db.add(ticket)

    personnel.availability = Availability.busy
    db.add(personnel)

    await audit_service.create(db, AuditLogCreate(
        staff_id=user_session.staff_id,
        action=AuditAction.TICKET_ASSIGNED,
        table_name="tickets",
        record_id=str(ticket.id),
    ), user_session)

    await db.commit()
    await db.refresh(ticket)
    await _reload_staff(db, ticket)  # NEW

    return ticket


async def delete_ticket(db: AsyncSession, ticket_id: int) -> bool:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    ticket = result.scalar_one_or_none()
    if not ticket:
        return False

    assigned_to_id = ticket.assigned_to_id

    # Delete the ticket first
    await db.delete(ticket)

    personnel = None
    if assigned_to_id:
        personnel_result = await db.execute(
            select(IctPersonnel).where(IctPersonnel.id == assigned_to_id)
        )
        personnel = personnel_result.scalar_one_or_none()
        if personnel and personnel.availability == Availability.busy:
            personnel.availability = Availability.available
            db.add(personnel)

    # Commit deletion + availability change together so both persist
    await db.commit()

    # Now dequeue — technician is confirmed available before this runs
    if personnel:
        await _dequeue_tickets(db, personnel)

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
        select(Ticket)
        .options(selectinload(Ticket.staff))  # NEW
        .where(
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