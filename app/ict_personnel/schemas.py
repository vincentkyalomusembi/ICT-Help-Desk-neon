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


class IctPersonnelResponse(BaseModel):
    id: int
    staff_id: UUID
    specialization: Specialization
    availability: Availability
    phone_extension: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True