from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.tickets.service import create_ticket, get_ticket, list_tickets, update_ticket, delete_ticket
from app.tickets.schemas import TicketCreate, TicketUpdate, TicketResponse

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create(ticket: TicketCreate, session: AsyncSession = Depends(get_db)):
    return await create_ticket(session, ticket, ticket.staff_id)


@router.get("/", response_model=List[TicketResponse])
async def read_all(session: AsyncSession = Depends(get_db)):
    return await list_tickets(session)


@router.get("/{ticket_id}", response_model=TicketResponse)
async def read(ticket_id: int, session: AsyncSession = Depends(get_db)):
    ticket = await get_ticket(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update(ticket_id: int, ticket: TicketUpdate, session: AsyncSession = Depends(get_db)):
    updated = await update_ticket(session, ticket_id, ticket)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    return updated


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(ticket_id: int, session: AsyncSession = Depends(get_db)):
    success = await delete_ticket(session, ticket_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")