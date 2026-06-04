from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.audit.schemas import AuditLogCreate, AuditLogUpdate
from app.audit.model import AuditLog
from app.auth.model import Session as UserSession


class AuditService:
    async def create(
        self,
        session: AsyncSession,
        log_in: AuditLogCreate,
        user_session: UserSession,
    ) -> AuditLog:
        log = AuditLog(
            staff_id=log_in.staff_id,
            session_id=user_session.id,
            action=log_in.action,
            table_name=log_in.table_name,
            record_id=log_in.record_id,
            ip_address=user_session.ip_address,
            mac_address=log_in.mac_address,
            created_at=datetime.now(timezone.utc),
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log

    async def create_system(
        self,
        session: AsyncSession,
        log_in: AuditLogCreate,
        ip_address: Optional[str] = None,  # no session object available
    ) -> AuditLog:
        log = AuditLog(
            staff_id=log_in.staff_id,
            session_id=None,               #no session yet (e.g. LOGIN_FAILED)
            action=log_in.action,
            table_name=log_in.table_name,
            record_id=log_in.record_id,
            ip_address=ip_address,
            mac_address=log_in.mac_address,
            created_at=datetime.now(timezone.utc),
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log

    async def list(self, session: AsyncSession) -> List[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.id.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, session: AsyncSession, log_id: int) -> Optional[AuditLog]:
        stmt = select(AuditLog).where(AuditLog.id == log_id)
        result = await session.execute(stmt)
        return result.scalars().first()

    async def update(
        self,
        session: AsyncSession,
        log_id: int,
        payload: AuditLogUpdate,
    ) -> Optional[AuditLog]:
        log = await self.get(session, log_id)
        if log is None:
            return None

        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(log, field, value)

        session.add(log)
        await session.commit()
        await session.refresh(log)
        return log

    async def delete(self, session: AsyncSession, log_id: int) -> bool:
        log = await self.get(session, log_id)
        if log is None:
            return False

        await session.delete(log)
        await session.commit()
        return True


audit_service = AuditService()