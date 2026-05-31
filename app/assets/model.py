from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import TIMESTAMP
from typing import Optional, List, TYPE_CHECKING
from datetime import date, datetime
import enum

if TYPE_CHECKING:
    from app.staff.model import Staff
    #from app.ict_personnel.model import IctPersonnel


class DeviceType(str, enum.Enum):
    laptop = "LAPTOP"
    desktop = "DESKTOP"
    printer = "PRINTER"
    monitor = "MONITOR"
    other = "OTHER"


class AssetClassification(str, enum.Enum):
    confidential = "CONFIDENTIAL"
    internal = "INTERNAL"
    public = "PUBLIC"


class AssetCondition(str, enum.Enum):
    good = "GOOD"
    fair = "FAIR"
    poor = "POOR"
    decommissioned = "DECOMMISSIONED"


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    asset_tag: str = Field(max_length=50, unique=True, index=True)
    serial_number: str = Field(max_length=100, unique=True, index=True)
    device_type: DeviceType
    brand: str = Field(max_length=50)
    model: str = Field(max_length=100)
    classification: AssetClassification
    condition: AssetCondition = Field(default=AssetCondition.good)
    purchase_date: Optional[date] = Field(default=None)
    warranty_expiry: Optional[date] = Field(default=None)
    created_at: datetime = Field(
        sa_column=Column(TIMESTAMP(timezone=True), nullable=False)
    )

    allocations: List["AssetAllocation"] = Relationship(back_populates="asset")


class AssetAllocation(SQLModel, table=True):
    __tablename__ = "asset_allocations"

    id: Optional[int] = Field(default=None, primary_key=True)
    asset_id: int = Field(foreign_key="assets.id")
    staff_id: int = Field(foreign_key="staff.id")
    #allocated_by_id: int = Field(foreign_key="ict_personnel.id")
    allocation_date: date
    return_date: Optional[date] = Field(default=None)
    notes: Optional[str] = Field(default=None)

    asset: Optional["Asset"] = Relationship(back_populates="allocations")
    staff: Optional["Staff"] = Relationship(back_populates="asset_allocations")
    #allocated_by: Optional["IctPersonnel"] = Relationship(back_populates="allocations_processed")