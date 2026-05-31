from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import TIMESTAMP
from typing import Optional, TYPE_CHECKING
from datetime import datetime
import enum

if TYPE_CHECKING:
    from app.staff.model import Staff
    from app.ict_personnel.model import IctPersonnel


class TicketCategory(str, enum.Enum):
    hardware = "HARDWARE"
    software = "SOFTWARE"
    network = "NETWORK"
    access_permissions = "ACCESS_PERMISSIONS"
    security_incidents = "SECURITY_INCIDENTS"
    other = "OTHER"


class TicketStatus(str, enum.Enum):
    open = "OPEN"
    in_progress = "IN_PROGRESS"
    resolved = "RESOLVED"
    closed = "CLOSED"


class Ticket(SQLModel, table=True):
    __tablename__ = "tickets"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    assigned_to_id: Optional[int] = Field(default=None, foreign_key="ict_personnel.id")
    title: str = Field(max_length=150)
    description: str
    category: TicketCategory
    status: TicketStatus = Field(default=TicketStatus.open)
    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    resolved_at: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )

    staff: Optional["Staff"] = Relationship(back_populates="tickets")
    assigned_to: Optional["IctPersonnel"] = Relationship(back_populates="assigned_tickets")