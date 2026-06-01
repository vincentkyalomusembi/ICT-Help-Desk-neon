from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.tickets.model import TicketCategory, TicketStatus


class TicketCreate(BaseModel):
    title: str
    description: str
    category: TicketCategory


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TicketCategory] = None
    status: Optional[TicketStatus] = None
    assigned_to_id: Optional[int] = None


class TicketResponse(BaseModel):
    id: int
    staff_id: int
    assigned_to_id: Optional[int]
    title: str
    description: str
    category: TicketCategory
    status: TicketStatus
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True