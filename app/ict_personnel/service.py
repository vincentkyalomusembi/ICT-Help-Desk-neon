from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.ict_personnel.model import IctPersonnel, Availability
from app.ict_personnel.schemas import IctPersonnelCreate, IctPersonnelUpdate


class IctPersonnelService:

    async def create(
        self,
        session: AsyncSession,
        payload: IctPersonnelCreate
    ) -> IctPersonnel:
        personnel = IctPersonnel(
            staff_id=payload.staff_id,
            specialization=payload.specialization,
            availability=Availability.available,
            phone_extension=payload.phone_extension,
            is_active=True,
        )
        session.add(personnel)
        await session.commit()
        await session.refresh(personnel)
        return personnel

    async def list(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> List[IctPersonnel]:
        stmt = select(IctPersonnel).order_by(IctPersonnel.id.desc()).offset(skip).limit(limit)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get(
        self,
        session: AsyncSession,
        personnel_id: int
    ) -> Optional[IctPersonnel]:
        stmt = select(IctPersonnel).where(IctPersonnel.id == personnel_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def update(
        self,
        session: AsyncSession,
        personnel_id: int,
        payload: IctPersonnelUpdate,
    ) -> Optional[IctPersonnel]:
        personnel = await self.get(session, personnel_id)
        if personnel is None:
            return None

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(personnel, field, value)

        session.add(personnel)
        await session.commit()
        await session.refresh(personnel)
        return personnel

    async def set_duty_status(
        self,
        session: AsyncSession,
        personnel_id: int,
        availability: Availability,
    ) -> Optional[IctPersonnel]:
        """
        Admin-only availability control for off_duty / on_leave / returning available.
        Will not override busy — a technician with an active ticket stays busy
        until the ticket lifecycle releases them.
        """
        personnel = await self.get(session, personnel_id)
        if personnel is None:
            return None

        if personnel.availability == Availability.busy:
            raise ValueError(
                f"Cannot change availability: technician has an active ticket. "
                "They will be released automatically when the ticket is closed."
            )

        personnel.availability = availability
        session.add(personnel)
        await session.commit()
        await session.refresh(personnel)
        return personnel

    async def delete(
        self,
        session: AsyncSession,
        personnel_id: int
    ) -> bool:
        personnel = await self.get(session, personnel_id)
        if personnel is None:
            return False
        await session.delete(personnel)
        await session.commit()
        return True


ict_personnel_service = IctPersonnelService()