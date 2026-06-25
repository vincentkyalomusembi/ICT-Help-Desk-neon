from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID, uuid4
import enum

if TYPE_CHECKING:
    from app.ict_personnel.model import IctPersonnel
    from app.tickets.model import Ticket
    from app.assets.model import AssetAllocation
    from app.audit.model import AuditLog
    from app.auth.model import Session


class UserRole(str, enum.Enum):
    admin = "admin"
    staff = "staff"
    ict_personnel = "ict_personnel"


class Directorate(SQLModel, table=True):
    __tablename__ = "directorates"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True, index=True)
    description: Optional[str] = Field(default=None)

    departments: List["Department"] = Relationship(back_populates="directorate")
    staff: List["Staff"] = Relationship(back_populates="directorate")


class Department(SQLModel, table=True):
    __tablename__ = "departments"

    id: Optional[int] = Field(default=None, primary_key=True)
    directorate_id: int = Field(foreign_key="directorates.id", index=True)
    name: str = Field(max_length=100, unique=True, index=True)
    description: Optional[str] = Field(default=None)

    directorate: Optional["Directorate"] = Relationship(back_populates="departments")
    staff: List["Staff"] = Relationship(back_populates="department")


class Staff(SQLModel, table=True):
    __tablename__ = "staff"

    id: UUID = Field(
        sa_column=Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    )
    personal_number: str = Field(max_length=20, unique=True, index=True)
    full_name: str = Field(max_length=100)
    email: str = Field(max_length=100, unique=True, index=True)
    phone_number: Optional[str] = Field(default=None, max_length=15)
    directorate_id: int = Field(foreign_key="directorates.id", index=True)
    department_id: int = Field(foreign_key="departments.id", index=True)
    office_location: Optional[str] = Field(default=None, max_length=100)
    office_number: str = Field(max_length=20)
    role: UserRole = Field(default=UserRole.staff, sa_column_kwargs={"nullable": False})
    password_hash: str
    failed_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    password_changed_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    is_activated: bool = Field(default=False)
    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    # Timestamp when staff acknowledged the Information Security Policy.
    # Required by ICTA.3.002:2019 section 12.1 and the Help Desk ISP.
    # Null means not yet acknowledged — used to enforce policy gate on login.
    policy_acknowledged_at: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True, default=None)
    )

    directorate: Optional["Directorate"] = Relationship(back_populates="staff")
    department: Optional["Department"] = Relationship(back_populates="staff")
    ict_profile: Optional["IctPersonnel"] = Relationship(back_populates="staff")
    tickets: List["Ticket"] = Relationship(back_populates="staff")
    asset_allocations: List["AssetAllocation"] = Relationship(
        back_populates="staff",
        sa_relationship_kwargs={"foreign_keys": "[AssetAllocation.staff_id]"},
    )
    audit_logs: List["AuditLog"] = Relationship(back_populates="staff")
    sessions: List["Session"] = Relationship(back_populates="staff")