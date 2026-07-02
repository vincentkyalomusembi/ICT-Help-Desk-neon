from pydantic import BaseModel, model_validator, computed_field
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
    resolution_notes: Optional[str] = None  # what the technician did

    # FIX: removed the comment requirement for unresolved — resolution_notes
    # covers this. The old comment validator was causing 422s from the frontend
    # since the frontend only sends resolution_notes, not comment.
    @model_validator(mode="after")
    def validate_update(self) -> "TicketUpdate":
        if self.status in (
            TicketStatus.resolved,
            TicketStatus.unresolved,
        ) and not self.resolution_notes:
            raise ValueError(
                "resolution_notes is required — describe what you did to address this ticket."
            )
        return self


class TicketConfirm(BaseModel):
    """Staff confirms or rejects a resolved ticket."""
    confirmed: bool
    rejection_reason: Optional[str] = None

    @model_validator(mode="after")
    def validate_rejection(self) -> "TicketConfirm":
        if not self.confirmed and not self.rejection_reason:
            raise ValueError(
                "rejection_reason is required when rejecting a resolution."
            )
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
    resolution_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TicketAdminResponse(TicketResponse):
    @computed_field
    @property
    def age_hours(self) -> float:
        return (
            datetime.now(timezone.utc) - self.created_at
        ).total_seconds() / 3600