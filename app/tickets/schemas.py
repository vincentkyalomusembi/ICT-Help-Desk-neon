from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.tickets.model import TicketCategory, TicketStatus


class TicketCreate(BaseModel):
    staff_id: UUID
    title: str
    description: str
    category: TicketCategory


class TicketUpdate(BaseModel):
    description: Optional[str] = None
    category: Optional[TicketCategory] = None
    status: Optional[TicketStatus] = None


class TicketResponse(BaseModel):
    id: int
    staff_id: UUID
    assigned_to_id: Optional[int]
    title: str
    description: str
    category: TicketCategory
    status: TicketStatus
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True