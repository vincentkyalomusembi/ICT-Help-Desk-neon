from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel
from .model import TicketCategory, TicketStatus
from uuid import UUID


class TicketCreate(BaseModel):
    staff_id: UUID
    title: str
    description: str
    category: TicketCategory


class TicketUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[TicketCategory] = None
    status: Optional[TicketStatus] = None
    assigned_to_id: Optional[int] = None

class TicketRead(BaseModel):
    """Response schema for reading tickets."""
    id: int
    title: str
    description: str
    status: str
    category: str
    created_at: datetime
    updated_at: datetime

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