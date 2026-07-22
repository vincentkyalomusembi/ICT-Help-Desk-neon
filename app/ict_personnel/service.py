from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.ict_personnel.model import IctPersonnel, Availability
from app.ict_personnel.schemas import (
    IctPersonnelCreate, IctPersonnelUpdate, IctPersonnelSetup, IctPersonnelSelfUpdate
)
from app.staff.model import Staff


class IctPersonnelService:

    async def create(
        self,
        session: AsyncSession,
        payload: IctPersonnelCreate,
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
        return await self._load(session, personnel.id)

    async def _load(
        self,
        session: AsyncSession,
        personnel_id: int,
    ) -> Optional[IctPersonnel]:
        """Load a single personnel record with staff and department joined."""
        result = await session.execute(
            select(IctPersonnel)
            .options(
                selectinload(IctPersonnel.staff)
                .selectinload(Staff.department)
            )
            .where(IctPersonnel.id == personnel_id)
        )
        return result.scalars().first()

    async def list(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
    ) -> List[IctPersonnel]:
        stmt = (
            select(IctPersonnel)
            .options(
                selectinload(IctPersonnel.staff)
                .selectinload(Staff.department)
            )
            .order_by(IctPersonnel.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get(
        self,
        session: AsyncSession,
        personnel_id: int,
    ) -> Optional[IctPersonnel]:
        return await self._load(session, personnel_id)

    async def get_by_staff_id(
        self,
        session: AsyncSession,
        staff_id: UUID,
    ) -> Optional[IctPersonnel]:
        result = await session.execute(
            select(IctPersonnel)
            .options(
                selectinload(IctPersonnel.staff)
                .selectinload(Staff.department)
            )
            .where(IctPersonnel.staff_id == staff_id)
        )
        return result.scalars().first()

    async def setup_profile(
        self,
        session: AsyncSession,
        staff_id: UUID,
        payload: IctPersonnelSetup,
    ) -> IctPersonnel:
        """
        Called by ICT personnel after first login to set their specialization.
        Activates the profile so the triage system can assign tickets to them.
        """
        personnel = await self.get_by_staff_id(session, staff_id)

        if not personnel:
            raise ValueError(
                "No ICT personnel profile found. "
                "Your account role may not have been updated yet — contact admin."
            )

        if personnel.specialization is not None:
            raise ValueError(
                "Specialization already set. "
                "Use PATCH /ict-personnel/{id} to update it."
            )

        personnel.specialization = payload.specialization
        personnel.phone_extension = payload.phone_extension
        personnel.is_active = True

        session.add(personnel)
        await session.commit()
        await session.refresh(personnel)
        return await self._load(session, personnel.id)

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
        return await self._load(session, personnel.id)

    async def update_by_staff_id(
        self,
        session: AsyncSession,
        staff_id: UUID,
        payload: IctPersonnelSelfUpdate,
    ) -> Optional[IctPersonnel]:
        """
        Allows a technician to update their own profile using their staff_id.
        Delegates to update() once the personnel record is located.
        """
        personnel = await self.get_by_staff_id(session, staff_id)
        if personnel is None:
            return None
        return await self.update(session, personnel.id, payload)
    
    async def set_duty_status(
        self,
        session: AsyncSession,
        personnel_id: int,
        availability: Availability,
    ) -> Optional[IctPersonnel]:
        """
        Admin-only. Sets off_duty, on_leave, or returns to available.
        Cannot override busy — ticket lifecycle controls that.
        """
        personnel = await self.get(session, personnel_id)
        if personnel is None:
            return None

        if personnel.availability == Availability.busy:
            raise ValueError(
                "Cannot change availability: technician has an active ticket. "
                "They will be released automatically when the ticket is closed."
            )

        personnel.availability = availability
        session.add(personnel)
        await session.commit()
        await session.refresh(personnel)
        return await self._load(session, personnel.id)

    async def delete(
        self,
        session: AsyncSession,
        personnel_id: int,
    ) -> bool:
        personnel = await self.get(session, personnel_id)
        if personnel is None:
            return False
        await session.delete(personnel)
        await session.commit()
        return True


ict_personnel_service = IctPersonnelService()