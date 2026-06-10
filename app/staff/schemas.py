from pydantic import BaseModel, EmailStr, field_validator, model_validator
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.staff.model import UserRole
from app.core.security import validate_password_strength


# Directorate

class DirectorateCreate(BaseModel):
    name: str
    description: Optional[str] = None


class DirectorateResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class DirectorateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


# Department

class DepartmentCreate(BaseModel):
    directorate_id: int
    name: str
    description: Optional[str] = None


class DepartmentBasic(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class DepartmentResponse(BaseModel):
    id: int
    directorate_id: int
    name: str
    description: Optional[str]

    class Config:
        from_attributes = True


class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    directorate_id: Optional[int] = None


# Staff

class StaffCreate(BaseModel):
    personal_number: str
    full_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    directorate_id: int
    department_id: int
    office_location: Optional[str] = None
    office_number: str
    role: UserRole = UserRole.staff
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "StaffCreate":
        if self.password != self.confirm_password:
            raise ValueError("password and confirm_password do not match.")
        return self


class StaffCreateResponse(BaseModel):
    message: str
    staff_id: UUID
    email: str


class StaffUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
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
    department: Optional[DepartmentBasic]
    office_location: Optional[str]
    office_number: str
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


# Password

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def new_passwords_match(self) -> "PasswordChangeRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("new_password and confirm_new_password do not match.")
        return self


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str
    confirm_new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def passwords_match(self) -> "PasswordResetConfirm":
        if self.new_password != self.confirm_new_password:
            raise ValueError("new_password and confirm_new_password do not match.")
        return self