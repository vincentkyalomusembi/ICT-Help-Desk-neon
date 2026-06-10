from pydantic import BaseModel, model_validator
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID

from app.tickets.model import TicketCategory, TicketStatus


class TicketCreate(BaseModel):
    title: str
    description: str
    category: TicketCategory


class TicketUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[TicketStatus] = None
    comment: Optional[str] = None

    @model_validator(mode="after")
    def comment_required_for_unresolved(self) -> "TicketUpdate":
        if self.status == TicketStatus.unresolved and not self.comment:
            raise ValueError("A comment is required when marking a ticket as unresolved.")
        return self


class TicketResponse(BaseModel):
    id: int
    staff_id: UUID
    assigned_to_id: Optional[int] = None 
    title: str
    description: str
    category: TicketCategory
    status: TicketStatus
    comment: Optional[str] = None
    created_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketAdminResponse(TicketResponse):
    assigned_to_name: Optional[str] = None

    @property
    def age_hours(self) -> float:
        return (datetime.now(timezone.utc) - self.created_at).total_seconds() / 3600