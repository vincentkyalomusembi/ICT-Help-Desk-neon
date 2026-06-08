from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from app.ict_personnel.model import IctPersonnel, Availability
from app.ict_personnel.schemas import IctPersonnelCreate, IctPersonnelUpdate
from app.tickets.model import Ticket, TicketStatus


class IctPersonnelService:

    async def create(self, session: AsyncSession, payload: IctPersonnelCreate) -> IctPersonnel:
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

    async def list(self, session: AsyncSession) -> List[IctPersonnel]:
        stmt = select(IctPersonnel).order_by(IctPersonnel.id.desc())
        result = await session.execute(stmt)
        return result.scalars().all()

    async def get(self, session: AsyncSession, personnel_id: int) -> Optional[IctPersonnel]:
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

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(personnel, field, value)

        session.add(personnel)
        await session.commit()
        await session.refresh(personnel)
        return personnel

    async def delete(self, session: AsyncSession, personnel_id: int) -> bool:
        personnel = await self.get(session, personnel_id)
        if personnel is None:
            return False
        await session.delete(personnel)
        await session.commit()
        return True

    async def get_open_ticket_count(self, session: AsyncSession, personnel_id: int) -> int:
        result = await session.execute(
            select(func.count(Ticket.id)).where(
                Ticket.assigned_to_id == personnel_id,
                Ticket.status.in_([TicketStatus.open, TicketStatus.in_progress])
            )
        )
        return result.scalar()

    async def sync_availability(self, session: AsyncSession, personnel_id: int) -> IctPersonnel:
        personnel = await self.get(session, personnel_id)
        if not personnel:
            return None
        count = await self.get_open_ticket_count(session, personnel_id)
        if count == 0 and personnel.availability == Availability.busy:
            personnel.availability = Availability.available
            session.add(personnel)
            await session.commit()
            await session.refresh(personnel)
        return personnel


ict_personnel_service = IctPersonnelService()