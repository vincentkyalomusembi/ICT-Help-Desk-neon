from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.audit.schemas import AuditLogCreate
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
        )
        session.add(log)
        await session.flush()  # joins parent transaction, no extra commit
        return log

    async def create_system(
        self,
        session: AsyncSession,
        log_in: AuditLogCreate,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Used for system-triggered actions with no user session (e.g. auto-close, auto-assign)."""
        log = AuditLog(
            staff_id=log_in.staff_id,
            session_id=None,
            action=log_in.action,
            table_name=log_in.table_name,
            record_id=log_in.record_id,
            ip_address=ip_address,
            mac_address=log_in.mac_address,
        )
        session.add(log)
        await session.flush()  # joins parent transaction, no extra commit
        return log

    async def list(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50
    ) -> List[AuditLog]:
        stmt = (
            select(AuditLog)
            .options(selectinload(AuditLog.staff))
            .order_by(AuditLog.id.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get(self, session: AsyncSession, log_id: int) -> Optional[AuditLog]:
        stmt = (
            select(AuditLog)
            .options(selectinload(AuditLog.staff))
            .where(AuditLog.id == log_id)
        )
        result = await session.execute(stmt)
        return result.scalars().first()


audit_service = AuditService()