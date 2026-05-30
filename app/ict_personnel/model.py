from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List, TYPE_CHECKING
import enum

if TYPE_CHECKING:
    from app.staff.model import Staff
    from app.tickets.model import Ticket
    from app.assets.model import AssetAllocation


class Specialization(str, enum.Enum):
    hardware = "HARDWARE"
    networking = "NETWORKING"
    software_and_systems = "SOFTWARE_AND_SYSTEMS"
    security = "SECURITY"
    other = "OTHER"


class Availability(str, enum.Enum):
    available = "AVAILABLE"
    busy = "BUSY"
    off_duty = "OFF_DUTY"
    on_leave = "ON_LEAVE"


class IctPersonnel(SQLModel, table=True):
    __tablename__ = "ict_personnel"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id", unique=True)
    specialization: Specialization = Field(default=Specialization.hardware)
    availability: Availability = Field(default=Availability.available)
    phone_extension: Optional[str] = Field(default=None, max_length=10)
    is_active: bool = Field(default=True)

    staff: Optional["Staff"] = Relationship(back_populates="ict_profile")
    assigned_tickets: List["Ticket"] = Relationship(back_populates="assigned_to")
    allocations_processed: List["AssetAllocation"] = Relationship(back_populates="allocated_by")