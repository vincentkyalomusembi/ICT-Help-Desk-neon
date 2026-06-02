from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update
from app.assets.model import Asset, AssetAllocation
from app.assets.schemas import (
    AssetCreate, AssetUpdate,
    AssetAllocationCreate, AssetAllocationUpdate
)
from datetime import datetime


# ── Asset Services ────────────────────────────────────────────

async def create_asset(db: AsyncSession, data: AssetCreate) -> Asset:
    asset = Asset(**data.model_dump(), created_at=datetime.utcnow())
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def get_all_assets(db: AsyncSession) -> list[Asset]:
    result = await db.execute(select(Asset))
    return result.scalars().all()


async def get_asset_by_id(db: AsyncSession, asset_id: int) -> Asset | None:
    result = await db.execute(select(Asset).where(Asset.id == asset_id))
    return result.scalar_one_or_none()


async def update_asset(db: AsyncSession, asset_id: int, data: AssetUpdate) -> Asset | None:
    asset = await get_asset_by_id(db, asset_id)
    if not asset:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(asset, key, value)
    await db.commit()
    await db.refresh(asset)
    return asset


async def delete_asset(db: AsyncSession, asset_id: int) -> bool:
    asset = await get_asset_by_id(db, asset_id)
    if not asset:
        return False
    await db.delete(asset)
    await db.commit()
    return True


# ── Asset Allocation Services ─────────────────────────────────

async def allocate_asset(db: AsyncSession, data: AssetAllocationCreate) -> AssetAllocation:
    allocation = AssetAllocation(**data.model_dump())
    db.add(allocation)
    await db.commit()
    await db.refresh(allocation)
    return allocation


async def get_all_allocations(db: AsyncSession) -> list[AssetAllocation]:
    result = await db.execute(select(AssetAllocation))
    return result.scalars().all()


async def get_allocation_by_id(db: AsyncSession, allocation_id: int) -> AssetAllocation | None:
    result = await db.execute(select(AssetAllocation).where(AssetAllocation.id == allocation_id))
    return result.scalar_one_or_none()


async def update_allocation(db: AsyncSession, allocation_id: int, data: AssetAllocationUpdate) -> AssetAllocation | None:
    allocation = await get_allocation_by_id(db, allocation_id)
    if not allocation:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(allocation, key, value)
    await db.commit()
    await db.refresh(allocation)
    return allocation