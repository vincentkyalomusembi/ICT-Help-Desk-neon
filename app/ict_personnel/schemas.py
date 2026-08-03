from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime

from app.ict_personnel.model import Specialization, Availability


class DepartmentBasic(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class StaffBasic(BaseModel):
    id: UUID
    full_name: str
    email: str
    personal_number: str
    office_number: str
    office_location: Optional[str] = None
    department: Optional[DepartmentBasic] = None

    class Config:
        from_attributes = True


class IctPersonnelCreate(BaseModel):
    staff_id: UUID
    specialization: Specialization
    phone_extension: Optional[str] = None


class IctPersonnelUpdate(BaseModel):
    specialization: Optional[Specialization] = None
    phone_extension: Optional[str] = None
    is_active: Optional[bool] = None
    # availability excluded — managed by ticket lifecycle
    # off_duty/on_leave go through /duty-status endpoint


class IctPersonnelDutyUpdate(BaseModel):
    """Admin-only: set a technician off duty, on leave, or return to available."""
    availability: Availability

    def validate_duty_status(self) -> "IctPersonnelDutyUpdate":
        allowed = {Availability.off_duty, Availability.on_leave, Availability.available}
        if self.availability not in allowed:
            raise ValueError(
                "Only off_duty, on_leave, or available can be set via this endpoint. "
                "busy is managed automatically by the ticket system."
            )
        return self


class IctPersonnelSetup(BaseModel):
    """ICT personnel sets their own specialization after first login."""
    specialization: Specialization
    phone_extension: Optional[str] = None


class IctPersonnelResponse(BaseModel):
    id: int
    staff_id: UUID
    specialization: Optional[Specialization] = None
    availability: Availability
    phone_extension: Optional[str] = None
    is_active: bool
    staff: Optional[StaffBasic] = None  # joined — full staff details

    class Config:
        from_attributes = True


class IctPersonnelSelfUpdate(BaseModel):
    """Technician self-service update — no is_active, no availability."""
    specialization: Optional[Specialization] = None
    phone_extension: Optional[str] = None