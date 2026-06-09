from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
import enum

if TYPE_CHECKING:
    from app.staff.model import Staff
    from app.auth.model import Session


class AuditAction(str, enum.Enum):
    TICKET_CREATED = "TICKET_CREATED"
    TICKET_UPDATED = "TICKET_UPDATED"
    TICKET_ASSIGNED = "TICKET_ASSIGNED"
    TICKET_CLOSED = "TICKET_CLOSED"
    ASSET_ALLOCATED = "ASSET_ALLOCATED"
    ASSET_DEALLOCATED = "ASSET_DEALLOCATED"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"
    LOGIN_SUCCESS = "LOGIN_SUCCESS"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    PERMISSION_CHANGED = "PERMISSION_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"


class AuditLog(SQLModel, table=True):
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: Optional[UUID] = Field(default=None, foreign_key="staff.id")
    session_id: Optional[int] = Field(default=None, foreign_key="sessions.id")
    action: AuditAction
    table_name: str = Field(max_length=50, index=True)
    record_id: Optional[str] = Field(default=None, max_length=50)  # str to handle both int and UUID
    ip_address: Optional[str] = Field(default=None, max_length=45)
    mac_address: Optional[str] = Field(default=None, max_length=17)
    created_at: datetime = Field(
        sa_column=Column(
            TIMESTAMP(timezone=True),
            nullable=False,
            server_default=func.now()
        )
    )

    staff: Optional["Staff"] = Relationship(back_populates="audit_logs")
    session: Optional["Session"] = Relationship(back_populates="audit_logs")