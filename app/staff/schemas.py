from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.staff.model import UserRole


class DirectorateCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DirectorateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    directorate_id: int
    name: str
    description: Optional[str] = None


class DepartmentResponse(BaseModel):
    id: int
    directorate_id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class StaffCreate(BaseModel):
    personal_number: str
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    directorate_id: int
    department_id: int
    job_title: str
    office_location: Optional[str] = None
    role: UserRole = UserRole.staff
    password: str


class StaffUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    office_location: Optional[str] = None
    directorate_id: Optional[int] = None
    department_id: Optional[int] = None
    role: Optional[UserRole] = None


class StaffResponse(BaseModel):
    id: int
    personal_number: str
    full_name: str
    email: str
    phone_number: Optional[str]
    directorate_id: int
    department_id: int
    job_title: str
    office_location: Optional[str]
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True