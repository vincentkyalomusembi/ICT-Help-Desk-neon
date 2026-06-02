from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.audit.schemas import AuditLogCreate, AuditLogUpdate
from app.audit.model import AuditLog


class AuditService:
    # Create a new audit log entry
    async def create(self, session: AsyncSession, log_in: AuditLogCreate) -> AuditLog:
        log = AuditLog(
            staff_id=payload.staff_id,
            action=payload.action,
            table_name=payload.table_name,
            record_id=payload.record_id,
            ip_address=payload.ip_address,
            mac_address=payload.mac_address,
            created_at=datetime.utcnow(),
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