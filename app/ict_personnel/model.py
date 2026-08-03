from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import VARCHAR
from typing import Optional, List, TYPE_CHECKING
from uuid import UUID
import enum

if TYPE_CHECKING:
    from app.staff.model import Staff
    from app.tickets.model import Ticket
    from app.assets.model import AssetAllocation


class Specialization(str, enum.Enum):
    hardware = "hardware"
    networking = "networking"
    software_and_systems = "software_and_systems"
    security = "security"
    other = "other"

class Availability(str, enum.Enum):
    available = "available"
    busy = "busy"
    off_duty = "off_duty"
    on_leave = "on_leave"


class IctPersonnel(SQLModel, table=True):
    __tablename__ = "ict_personnel"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: UUID = Field(foreign_key="staff.id", unique=True)
    specialization: Optional[Specialization] = Field(
        default=None, nullable=True, index=True
    )
    availability: Availability = Field(
        default=Availability.available,
        sa_column_kwargs={"nullable": False},
        index=True,
    )
    phone_extension: Optional[str] = Field(default=None, max_length=10)
    is_active: bool = Field(default=False, index=True)

    staff: Optional["Staff"] = Relationship(
        back_populates="ict_profile",
        sa_relationship_kwargs={"lazy": "joined"},
    )
    assigned_tickets: List["Ticket"] = Relationship(back_populates="assigned_to")