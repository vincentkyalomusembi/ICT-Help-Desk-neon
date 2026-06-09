from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.dependencies import CurrentStaff, IctStaff, AdminStaff
from app.tickets.service import (
    create_ticket, get_ticket, list_tickets, list_queued_tickets,
    update_ticket, delete_ticket, get_stuck_tickets, reassign_ticket
)
from app.tickets.schemas import TicketCreate, TicketUpdate, TicketResponse, TicketAdminResponse

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create(
    ticket: TicketCreate,
    current_staff: CurrentStaff,
    session: AsyncSession = Depends(get_db),
):
    # _auto_assign now returns None instead of raising — no try/except needed.
    # Ticket is queued unassigned (assigned_to_id=None, status=open) and 201 is returned.
    return await create_ticket(session, ticket, current_staff.id, current_staff._session)


# NOTE: static routes must come before /{ticket_id}
@router.get("/admin/stuck", response_model=List[TicketAdminResponse])
async def stuck_tickets(
    _: AdminStaff,
    threshold_hours: int = 24,
    session: AsyncSession = Depends(get_db),
):
    return await get_stuck_tickets(session, threshold_hours)


# CHANGE 5: Admin endpoint to view queued (unassigned) tickets
@router.get("/admin/queued", response_model=List[TicketAdminResponse])
async def queued_tickets(
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    """List tickets awaiting assignment (no tech was available at creation time)."""
    return await list_queued_tickets(session)


@router.get("/", response_model=List[TicketResponse])
async def read_all(
    current_staff: CurrentStaff,
    skip: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_db),
):
    if current_staff.role == "ADMIN":
        return await list_tickets(session, skip, limit)
    elif current_staff.role == "ICT_PERSONNEL":
        return await list_tickets(session, skip, limit, assigned_to_id=current_staff.ict_profile.id)
    else:
        return await list_tickets(session, skip, limit, staff_id=current_staff.id)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def read(
    ticket_id: int,
    current_staff: CurrentStaff,
    session: AsyncSession = Depends(get_db),
):
    personnel_id = (
        current_staff.ict_profile.id
        if current_staff.role == "ICT_PERSONNEL" and current_staff.ict_profile
        else None
    )
    ticket = await get_ticket(session, ticket_id, personnel_id, current_staff._session)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update(
    ticket_id: int,
    ticket: TicketUpdate,
    current_staff: IctStaff,
    session: AsyncSession = Depends(get_db),
):
    try:
        updated = await update_ticket(
            session,
            ticket_id,
            ticket,
            current_staff.ict_profile.id,
            current_staff._session,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return updated


@router.post("/{ticket_id}/reassign", response_model=TicketResponse)
async def reassign(
    ticket_id: int,
    current_staff: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    try:
        return await reassign_ticket(session, ticket_id, current_staff._session)
    except LookupError as e:
        # Ticket not found
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        # No technician available — ticket stays queued
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    ticket_id: int,
    _: AdminStaff,
    session: AsyncSession = Depends(get_db),
):
    success = await delete_ticket(session, ticket_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")