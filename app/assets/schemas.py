from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from app.assets.model import DeviceType, AssetClassification, AssetCondition


class AssetCreate(BaseModel):
    asset_tag: str
    serial_number: str
    device_type: DeviceType
    brand: str
    model: str
    classification: AssetClassification
    condition: AssetCondition = AssetCondition.good
    purchase_date: Optional[date] = None
    warranty_expiry: Optional[date] = None


class AssetUpdate(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    classification: Optional[AssetClassification] = None
    condition: Optional[AssetCondition] = None
    warranty_expiry: Optional[date] = None


class AssetResponse(BaseModel):
    id: int
    asset_tag: str
    serial_number: str
    device_type: DeviceType
    brand: str
    model: str
    classification: AssetClassification
    condition: AssetCondition
    purchase_date: Optional[date]
    warranty_expiry: Optional[date]
    created_at: datetime

    class Config:
        from_attributes = True


class AssetAllocationCreate(BaseModel):
    asset_id: int
    staff_id: int
    allocated_by_id: int
    allocation_date: date
    notes: Optional[str] = None


class AssetAllocationUpdate(BaseModel):
    return_date: Optional[date] = None
    notes: Optional[str] = None


class AssetAllocationResponse(BaseModel):
    id: int
    asset_id: int
    staff_id: int
    allocated_by_id: int
    allocation_date: date
    return_date: Optional[date]
    notes: Optional[str]

    class Config:
        from_attributes = True