from sqlmodel import Session, select
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from .model import Ticket, TicketStatus
from .schemas import TicketCreate, TicketUpdate

def create_ticket(session: Session, ticket_data: TicketCreate) -> Ticket:
    ticket = Ticket(
        staff_id=ticket_data.staff_id,
        title=ticket_data.title,
        description=ticket_data.description,
        category=ticket_data.category,
        status="OPEN",
        created_at=datetime.utcnow()
    )
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket

def get_ticket(session: Session, ticket_id: int) -> Ticket:
    return session.get(Ticket, ticket_id)

def list_tickets(session: Session):
    return session.exec(select(Ticket)).all()

def update_ticket(session: Session, ticket_id: int, ticket_data: TicketUpdate) -> Ticket:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        return None
    for field, value in ticket_data.dict(exclude_unset=True).items():
        setattr(ticket, field, value)
    if ticket.status == "RESOLVED":
        ticket.resolved_at = datetime.utcnow()
    session.add(ticket)
    session.commit()
    session.refresh(ticket)
    return ticket

def delete_ticket(session: Session, ticket_id: int) -> bool:
    ticket = session.get(Ticket, ticket_id)
    if not ticket:
        return False
    session.delete(ticket)
    session.commit()
    return True
