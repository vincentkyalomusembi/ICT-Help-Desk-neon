from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from typing import List, Optional
from uuid import UUID


from .model import TicketStatus
from app.core.database import get_session
from .service import create_ticket, get_ticket, list_tickets, update_ticket, delete_ticket
from .schemas import TicketCreate, TicketUpdate, TicketRead

router = APIRouter(prefix="/tickets", tags=["Tickets"])

@router.post("/", response_model=TicketRead)
def create(ticket: TicketCreate, session: Session = Depends(get_session)):
    return create_ticket(session, ticket)

@router.get("/{ticket_id}", response_model=TicketRead)
def read(ticket_id: int, session: Session = Depends(get_session)):
    ticket = get_ticket(session, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.get("/", response_model=list[TicketRead])
def read_all(session: Session = Depends(get_session)):
    return list_tickets(session)

@router.put("/{ticket_id}", response_model=TicketRead)
def update(ticket_id: int, ticket: TicketUpdate, session: Session = Depends(get_session)):
    updated = update_ticket(session, ticket_id, ticket)
    if not updated:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return updated

@router.delete("/{ticket_id}")
def delete(ticket_id: int, session: Session = Depends(get_session)):
    success = delete_ticket(session, ticket_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ok": True}
