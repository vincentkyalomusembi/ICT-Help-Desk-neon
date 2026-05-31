from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import TIMESTAMP
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
import enum

if TYPE_CHECKING:
    from app.ict_personnel.model import IctPersonnel
    from app.tickets.model import Ticket
    from app.assets.model import AssetAllocation
    from app.audit.model import AuditLog
    from app.auth.model import Session


class UserRole(str, enum.Enum):
    admin = "ADMIN"
    staff = "STAFF"
    ict_personnel = "ICT_PERSONNEL"


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
    directorate_id: int = Field(foreign_key="directorates.id")
    name: str = Field(max_length=100, unique=True, index=True)
    description: Optional[str] = Field(default=None)

    directorate: Optional["Directorate"] = Relationship(back_populates="departments")
    staff: List["Staff"] = Relationship(back_populates="department")


class Staff(SQLModel, table=True):
    __tablename__ = "staff"

    id: Optional[int] = Field(default=None, primary_key=True)
    personal_number: str = Field(max_length=20, unique=True, index=True)
    full_name: str = Field(max_length=100)
    #national_id: str = Field(max_length=20, unique=True)
    email: str = Field(max_length=100, unique=True, index=True)
    phone_number: Optional[str] = Field(default=None, max_length=15)
    directorate_id: int = Field(foreign_key="directorates.id")
    department_id: int = Field(foreign_key="departments.id")
    job_title: str = Field(max_length=100)
    office_location: Optional[str] = Field(default=None, max_length=100)
    role: UserRole = Field(default=UserRole.staff)
    password_hash: str
    failed_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=True)
    )
    password_changed_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )

    directorate: Optional["Directorate"] = Relationship(back_populates="staff")
    department: Optional["Department"] = Relationship(back_populates="staff")
    ict_profile: Optional["IctPersonnel"] = Relationship(back_populates="staff")
    tickets: List["Ticket"] = Relationship(back_populates="staff")
    asset_allocations: List["AssetAllocation"] = Relationship(back_populates="staff")
    audit_logs: List["AuditLog"] = Relationship(back_populates="staff")
    sessions: List["Session"] = Relationship(back_populates="staff")