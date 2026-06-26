from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.dependencies import CurrentStaff, IctStaff, AdminStaff, CurrentSession
from app.tickets.service import (
    create_ticket, get_ticket, list_tickets, list_queued_tickets,
    list_unresolved_tickets, get_ticket_summary, get_tickets_by_personnel,
    update_ticket, delete_ticket, get_stuck_tickets, reassign_ticket,
)
from app.tickets.schemas import TicketCreate, TicketUpdate, TicketResponse, TicketAdminResponse
from app.staff.model import UserRole

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create(
    ticket: TicketCreate,
    current_staff: CurrentStaff,
    current_session: CurrentSession,
    session: AsyncSession = Depends(get_db),
):
    return await create_ticket(session, ticket, current_staff.id, current_session)


# ── Admin routes — must come before /{ticket_id} ──────────────

@router.get("/admin/summary")
async def ticket_summary(
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    """Count of tickets grouped by status."""
    return await get_ticket_summary(session)


@router.get("/admin/by-personnel")
async def tickets_by_personnel(
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    """Ticket count per technician broken down by status."""
    return await get_tickets_by_personnel(session)


@router.get("/admin/stuck", response_model=List[TicketAdminResponse])
async def stuck_tickets(
    _: AdminStaff,
    threshold_hours: int = 24,
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    """Tickets open or in_progress beyond threshold hours."""
    return await get_stuck_tickets(session, threshold_hours, skip, limit)


@router.get("/admin/queued", response_model=List[TicketResponse])
async def queued_tickets(
    _: AdminStaff,
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    """Unassigned tickets waiting for a specialist."""
    return await list_queued_tickets(session, skip, limit)


@router.get("/admin/unresolved", response_model=List[TicketResponse])
async def unresolved_tickets(
    _: AdminStaff,
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    """Tickets closed as unresolved — need follow-up or reassignment."""
    return await list_unresolved_tickets(session, skip, limit)


# ── General routes ─────────────────────────────────────────────

@router.get("/", response_model=List[TicketResponse])
async def read_all(
    current_staff: CurrentStaff,
    skip: int = 0,
    limit: int = 50,
    mine_only: bool = False,
    session: AsyncSession = Depends(get_db),
):
    # mine_only=True always means "tickets I raised as staff",
    # regardless of role — this is how ICT personnel see their own
    # raised tickets separately from tickets assigned to them to work on.
    if mine_only:
        return await list_tickets(session, skip, limit, staff_id=current_staff.id)

    if current_staff.role == UserRole.admin:
        return await list_tickets(session, skip, limit)
    elif current_staff.role == UserRole.ict_personnel:
        return await list_tickets(
            session, skip, limit,
            assigned_to_id=current_staff.ict_profile.id,
        )
    else:
        return await list_tickets(session, skip, limit, staff_id=current_staff.id)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def read(
    ticket_id: int,
    current_staff: CurrentStaff,
    current_session: CurrentSession,
    session: AsyncSession = Depends(get_db),
):
    personnel_id = (
        current_staff.ict_profile.id
        if current_staff.role == UserRole.ict_personnel
        and current_staff.ict_profile
        else None
    )
    ticket = await get_ticket(session, ticket_id, personnel_id, current_session)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update(
    ticket_id: int,
    ticket: TicketUpdate,
    current_staff: IctStaff,
    current_session: CurrentSession,
    session: AsyncSession = Depends(get_db),
):
    try:
        updated = await update_ticket(
            session, ticket_id, ticket,
            current_staff.ict_profile.id,
            current_session,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )
    return updated


@router.post("/{ticket_id}/reassign", response_model=TicketResponse)
async def reassign(
    ticket_id: int,
    _: AdminStaff,
    current_session: CurrentSession,
    session: AsyncSession = Depends(get_db),
):
    try:
        return await reassign_ticket(session, ticket_id, current_session)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    ticket_id: int,
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    success = await delete_ticket(session, ticket_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found."
        )