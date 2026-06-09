from pydantic import BaseModel
from typing import Optional
from uuid import UUID

from app.ict_personnel.model import Specialization, Availability


class IctPersonnelCreate(BaseModel):
    staff_id: UUID
    specialization: Specialization
    phone_extension: Optional[str] = None


class IctPersonnelUpdate(BaseModel):
    specialization: Optional[Specialization] = None
    phone_extension: Optional[str] = None
    is_active: Optional[bool] = None
    # availability intentionally excluded — managed by ticket lifecycle only
    # except off_duty/on_leave which go through the dedicated endpoint below


class IctPersonnelDutyUpdate(BaseModel):
    """Admin-only: set a technician off duty or on leave."""
    availability: Availability

    def validate_duty_status(self) -> "IctPersonnelDutyUpdate":
        allowed = {Availability.off_duty, Availability.on_leave, Availability.available}
        if self.availability not in allowed:
            raise ValueError(
                "Only off_duty, on_leave, or available can be set via this endpoint. "
                "busy is managed automatically by the ticket system."
            )
        return self


class IctPersonnelResponse(BaseModel):
    id: int
    staff_id: UUID
    specialization: Specialization
    availability: Availability
    phone_extension: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True