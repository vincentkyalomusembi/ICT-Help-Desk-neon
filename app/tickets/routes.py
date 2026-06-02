from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from typing import List, Optional
from uuid import UUID


from .model import TicketStatus
from app.core.database import get_db
from .service import create_ticket, get_ticket, list_tickets, update_ticket, delete_ticket
from .schemas import TicketCreate, TicketUpdate, TicketRead

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post("/", response_model=TicketRead)
async def create(ticket: TicketCreate, session: AsyncSession = Depends(get_db)):
    return await create_ticket(session, ticket)

@router.get("/{ticket_id}", response_model=TicketRead)
async def read(ticket_id: int, session: AsyncSession = Depends(get_db)):
    ticket = await get_ticket(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.get("/", response_model=list[TicketRead])
async def read_all(session: AsyncSession = Depends(get_db)):
    return await list_tickets(session)

@router.put("/{ticket_id}", response_model=TicketRead)
async def update(ticket_id: int, ticket: TicketUpdate, session: AsyncSession = Depends(get_db)):
    updated = await update_ticket(session, ticket_id, ticket)
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated

@router.delete("/{ticket_id}")
async def delete(ticket_id: int, session: AsyncSession = Depends(get_db)):
    success = await delete_ticket(session, ticket_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ok": True}
