from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.audit.model import AuditAction


class AuditLogCreate(BaseModel):
    staff_id: Optional[int] = None
    action: AuditAction
    table_name: str
    record_id: Optional[int] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    staff_id: Optional[int]
    action: AuditAction
    table_name: str
    record_id: Optional[int]
    ip_address: Optional[str]
    mac_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True