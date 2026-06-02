from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.assets.schemas import (
    AssetCreate, AssetUpdate, AssetResponse,
    AssetAllocationCreate, AssetAllocationUpdate, AssetAllocationResponse
)
from app.assets import service

router = APIRouter(prefix="/assets", tags=["Assets"])


# ── Asset Routes ──────────────────────────────────────────────

@router.post("/", response_model=AssetResponse)
async def create_asset(data: AssetCreate, db: AsyncSession = Depends(get_db)):
    return await service.create_asset(db, data)


@router.get("/", response_model=list[AssetResponse])
async def get_all_assets(db: AsyncSession = Depends(get_db)):
    return await service.get_all_assets(db)


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: int, db: AsyncSession = Depends(get_db)):
    asset = await service.get_asset_by_id(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(asset_id: int, data: AssetUpdate, db: AsyncSession = Depends(get_db)):
    asset = await service.update_asset(db, asset_id, data)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/{asset_id}")
async def delete_asset(asset_id: int, db: AsyncSession = Depends(get_db)):
    deleted = await service.delete_asset(db, asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"message": "Asset deleted successfully"}


# ── Asset Allocation Routes ───────────────────────────────────

@router.post("/allocate", response_model=AssetAllocationResponse)
async def allocate_asset(data: AssetAllocationCreate, db: AsyncSession = Depends(get_db)):
    return await service.allocate_asset(db, data)


@router.get("/allocations", response_model=list[AssetAllocationResponse])
async def get_all_allocations(db: AsyncSession = Depends(get_db)):
    return await service.get_all_allocations(db)


@router.get("/allocations/{allocation_id}", response_model=AssetAllocationResponse)
async def get_allocation(allocation_id: int, db: AsyncSession = Depends(get_db)):
    allocation = await service.get_allocation_by_id(db, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return allocation


@router.put("/allocations/{allocation_id}", response_model=AssetAllocationResponse)
async def update_allocation(allocation_id: int, data: AssetAllocationUpdate, db: AsyncSession = Depends(get_db)):
    allocation = await service.update_allocation(db, allocation_id, data)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    return allocation