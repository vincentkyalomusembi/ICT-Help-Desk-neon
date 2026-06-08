from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import TIMESTAMP
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from uuid import UUID

if TYPE_CHECKING:
    from app.staff.model import Staff
    from app.audit.model import AuditLog


class Session(SQLModel, table=True):
    __tablename__ = "sessions"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: UUID = Field(foreign_key="staff.id")
    token: str = Field(unique=True)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    login_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    expires_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    is_active: bool = Field(default=True)

    staff: Optional["Staff"] = Relationship(back_populates="sessions")
    audit_logs: list["AuditLog"] = Relationship(back_populates="session")


class MagicLinkToken(SQLModel, table=True):
    __tablename__ = "magic_link_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: UUID = Field(foreign_key="staff.id")
    token: str = Field(unique=True, index=True)
    expires_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    used: bool = Field(default=False)