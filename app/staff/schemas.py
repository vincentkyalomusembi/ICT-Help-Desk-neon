from pydantic import BaseModel, EmailStr, model_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.staff.model import UserRole


#Directorate 

class DirectorateCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DirectorateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


#Department 

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

class DirectorateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    directorate_id: Optional[int] = None
    
#Staff 

class StaffCreate(BaseModel):
    personal_number: str
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    directorate_id: int
    department_id: int
    job_title: str
    office_location: Optional[str] = None
    office_number: str
    role: UserRole = UserRole.staff
    password: str
    confirm_password: str

    @model_validator(mode="after")
    def passwords_match(self) -> "StaffCreate":
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match.")
        return self


class StaffUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    job_title: Optional[str] = None
    office_location: Optional[str] = None
    office_number: Optional[str] = None
    directorate_id: Optional[int] = None
    department_id: Optional[int] = None
    role: Optional[UserRole] = None


class StaffResponse(BaseModel):
    id: UUID
    personal_number: str
    full_name: str
    email: str
    phone_number: Optional[str]
    directorate_id: int
    department_id: int
    job_title: str
    office_location: Optional[str]
    office_number: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


#Password 

class PasswordChangeRequest(BaseModel):
    current_password: str          # must supply old password to change it
    new_password: str
    confirm_new_password: str

    @model_validator(mode="after")
    def new_passwords_match(self) -> "PasswordChangeRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("new_password and confirm_new_password do not match.")
        return self