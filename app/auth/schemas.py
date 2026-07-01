from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    staff_id: UUID
    role: str
    token: str
    expires_at: datetime


class StaffBasic(BaseModel):
    id: UUID
    full_name: str
    email: str

    class Config:
        from_attributes = True


class SessionResponse(BaseModel):
    id: int
    staff_id: UUID
    ip_address: Optional[str]
    login_at: datetime
    expires_at: datetime
    is_active: bool
    staff: Optional[StaffBasic] = None

    class Config:
        from_attributes = True


class LogoutRequest(BaseModel):
    token: str