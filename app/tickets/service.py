from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID

from app.tickets.model import Ticket, TicketStatus, TicketCategory
from app.tickets.schemas import TicketCreate, TicketUpdate
from app.ict_personnel.model import IctPersonnel, Availability, Specialization


# ── Triage Mapping ────────────────────────────────────────────

CATEGORY_TO_SPECIALIZATION = {
    TicketCategory.hardware: Specialization.hardware,
    TicketCategory.software: Specialization.software_and_systems,
    TicketCategory.network: Specialization.networking,
    TicketCategory.security_incidents: Specialization.security,
    TicketCategory.access_permissions: Specialization.software_and_systems,
    TicketCategory.other: None,
}


async def _auto_assign(db: AsyncSession, category: TicketCategory) -> Optional[int]:
    specialization = CATEGORY_TO_SPECIALIZATION.get(category)

    stmt = select(IctPersonnel).where(
        IctPersonnel.availability == Availability.available,
        IctPersonnel.is_active == True,
    )

    if specialization:
        stmt = stmt.where(IctPersonnel.specialization == specialization)

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    if not candidates:
        return None

    # Pick least loaded — fewest open tickets
    least_loaded = None
    min_tickets = float("inf")

    for candidate in candidates:
        count_result = await db.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_to_id == candidate.id,
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
            )
        )
        count = count_result.scalar()
        if count < min_tickets:
            min_tickets = count
            least_loaded = candidate

    return least_loaded.id if least_loaded else None


# ── Ticket Services ───────────────────────────────────────────

async def create_ticket(db: AsyncSession, data: TicketCreate, staff_id: UUID) -> Ticket:
    assigned_to_id = await _auto_assign(db, data.category)

    ticket = Ticket(
        staff_id=staff_id,
        assigned_to_id=assigned_to_id,
        title=data.title,
        description=data.description,
        category=data.category,
        status=TicketStatus.open,
        created_at=datetime.now(timezone.utc),
    )
    db.add(ticket)

    # Set assigned personnel to busy if assigned
    if assigned_to_id:
        result = await db.execute(
            select(IctPersonnel).where(IctPersonnel.id == assigned_to_id)
        )
        personnel = result.scalar_one_or_none()
        if personnel:
            personnel.availability = Availability.busy

    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_ticket(db: AsyncSession, ticket_id: int) -> Optional[Ticket]:
    result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
    return result.scalar_one_or_none()


async def list_tickets(db: AsyncSession) -> list[Ticket]:
    result = await db.execute(select(Ticket))
    return result.scalars().all()


async def update_ticket(db: AsyncSession, ticket_id: int, data: TicketUpdate) -> Optional[Ticket]:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return None

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(ticket, field, value)

    if ticket.status == TicketStatus.resolved:
        ticket.resolved_at = datetime.now(timezone.utc)

        # Free up the ICT personnel when ticket is resolved
        if ticket.assigned_to_id:
            result = await db.execute(
                select(IctPersonnel).where(IctPersonnel.id == ticket.assigned_to_id)
            )
            personnel = result.scalar_one_or_none()
            if personnel:
                open_tickets_result = await db.execute(
                    select(func.count(Ticket.id)).where(
                        Ticket.assigned_to_id == personnel.id,
                        Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress]),
                        Ticket.id != ticket_id
                    )
                )
                remaining = open_tickets_result.scalar()
                if remaining == 0:
                    personnel.availability = Availability.available

    await db.commit()
    await db.refresh(ticket)
    return ticket


async def delete_ticket(db: AsyncSession, ticket_id: int) -> bool:
    ticket = await get_ticket(db, ticket_id)
    if not ticket:
        return False
    await db.delete(ticket)
    await db.commit()
    return True