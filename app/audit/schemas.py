from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from app.audit.model import AuditAction


class AuditLogCreate(BaseModel):
    staff_id: Optional[UUID] = None      
    action: AuditAction
    table_name: str
    record_id: Optional[int] = None
    mac_address: Optional[str] = None


class AuditLogUpdate(BaseModel):
    staff_id: Optional[UUID] = None
    action: Optional[AuditAction] = None
    table_name: Optional[str] = None
    record_id: Optional[int] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None


class AuditLogResponse(BaseModel):
    id: int
    staff_id: Optional[UUID]             
    session_id: Optional[int]            
    action: AuditAction
    table_name: str
    record_id: Optional[int]
    ip_address: Optional[str]
    mac_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True