from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    message: str
    staff_id: int
    role: str
    token: str
    expires_at: datetime


class SessionResponse(BaseModel):
    id: int
    staff_id: int
    token: str
    ip_address: Optional[str]
    login_at: datetime
    expires_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class LogoutRequest(BaseModel):
    token: str