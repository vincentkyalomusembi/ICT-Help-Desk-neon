from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
import enum

if TYPE_CHECKING:
    from app.staff.model import Staff
    from app.ict_personnel.model import IctPersonnel


class TicketCategory(str, enum.Enum):
    hardware           = "hardware"
    software           = "software"
    network            = "network"
    access_permissions = "access_permissions"
    security_incidents = "security_incidents"
    other              = "other"


class TicketStatus(str, enum.Enum):
    open                 = "open"
    in_progress          = "in_progress"
    resolved             = "resolved"           # transient — immediately becomes pending_confirmation
    unresolved           = "unresolved"         # ICT couldn't fix — goes to team view
    pending_confirmation = "pending_confirmation"  # ICT resolved, awaiting staff confirm
    reopened             = "reopened"           # staff rejected — back in triage queue
    closed               = "closed"             # staff confirmed fixed


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: UUID = Field(foreign_key="staff.id", index=True)
    assigned_to_id: Optional[int] = Field(
        default=None,
        foreign_key="ict_personnel.id",
        nullable=True,
        index=True,
    )  # None means queued — no matching specialist available at creation time
    title: str
    description: str
    category: TicketCategory = Field(index=True, sa_column_kwargs={"nullable": False})
    status: TicketStatus = Field(default=TicketStatus.open, index=True, sa_column_kwargs={"nullable": False})
    comment: Optional[str] = Field(default=None, nullable=True)
    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), index=True)
    )
    closed_at: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True, index=True)
    )

    staff: Optional["Staff"] = Relationship(back_populates="tickets")
    assigned_to: Optional["IctPersonnel"] = Relationship(
        back_populates="assigned_tickets"
    )