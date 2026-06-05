import logging
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from fastapi import HTTPException, status

from app.staff.model import Staff, Directorate, Department
from app.staff.schemas import (
    StaffCreate, StaffUpdate,
    DirectorateCreate, DirectorateUpdate,
    DepartmentCreate, DepartmentUpdate,
)
from app.core.security import hash_password, verify_password
from app.auth.magic import create_magic_token
from app.core.email import send_magic_link

logger = logging.getLogger(__name__)


class StaffService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # Staff helpers

    async def _get_or_404(self, staff_id: UUID) -> Staff:
        staff = await self.session.get(Staff, staff_id)
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Staff with id '{staff_id}' not found.",
            )
        return staff

    async def _assert_unique_field(
        self,
        field_name: str,
        value: str,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        col = getattr(Staff, field_name)
        stmt = select(Staff).where(col == value)
        if exclude_id:
            stmt = stmt.where(Staff.id != exclude_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A staff member with {field_name} '{value}' already exists.",
            )

    # Directorate helpers

    async def _get_directorate_or_404(self, directorate_id: int) -> Directorate:
        obj = await self.session.get(Directorate, directorate_id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Directorate with id '{directorate_id}' not found.",
            )
        return obj

    async def _assert_directorate_name_unique(
        self, name: str, exclude_id: Optional[int] = None
    ) -> None:
        stmt = select(Directorate).where(Directorate.name == name)
        if exclude_id:
            stmt = stmt.where(Directorate.id != exclude_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Directorate with name '{name}' already exists.",
            )

    # Department helpers

    async def _get_department_or_404(self, department_id: int) -> Department:
        obj = await self.session.get(Department, department_id)
        if not obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department with id '{department_id}' not found.",
            )
        return obj

    async def _assert_department_name_unique(
        self, name: str, exclude_id: Optional[int] = None
    ) -> None:
        stmt = select(Department).where(Department.name == name)
        if exclude_id:
            stmt = stmt.where(Department.id != exclude_id)
        result = await self.session.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Department with name '{name}' already exists.",
            )

    # Staff CRUD

    async def create_staff(self, payload: StaffCreate) -> Staff:
        await self._assert_unique_field("personal_number", payload.personal_number)
        await self._assert_unique_field("email", payload.email)

        now = datetime.now(timezone.utc)
        staff = Staff(
            personal_number=payload.personal_number,
            full_name=payload.full_name,
            email=payload.email,
            phone_number=payload.phone_number,
            directorate_id=payload.directorate_id,
            department_id=payload.department_id,
            job_title=payload.job_title,
            office_location=payload.office_location,
            office_number=payload.office_number,
            role=payload.role,
            password_hash=hash_password(payload.password),
            password_changed_at=now,
            created_at=now,
        )
        self.session.add(staff)
        await self.session.commit()
        await self.session.refresh(staff)

        try:
            token = await create_magic_token(self.session, staff.id)
            await send_magic_link(staff.email, staff.full_name, token)
            logger.info(f"Magic link email sent to {staff.email}")
        except Exception as e:
            logger.error(
                f"Failed to send magic link to {staff.email}: {e}",
                exc_info=True,
            )

        return staff

    async def get_staff_by_id(self, staff_id: UUID) -> Staff:
        return await self._get_or_404(staff_id)

    async def get_staff_by_email(self, email: str) -> Optional[Staff]:
        result = await self.session.execute(select(Staff).where(Staff.email == email))
        return result.scalar_one_or_none()

    async def get_staff_by_personal_number(self, personal_number: str) -> Optional[Staff]:
        result = await self.session.execute(
            select(Staff).where(Staff.personal_number == personal_number)
        )
        return result.scalar_one_or_none()

    async def list_staff(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        directorate_id: Optional[int] = None,
        department_id: Optional[int] = None,
    ) -> list[Staff]:
        stmt = select(Staff)
        if directorate_id is not None:
            stmt = stmt.where(Staff.directorate_id == directorate_id)
        if department_id is not None:
            stmt = stmt.where(Staff.department_id == department_id)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_staff(self, staff_id: UUID, payload: StaffUpdate) -> Staff:
        staff = await self._get_or_404(staff_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(staff, field, value)
        self.session.add(staff)
        await self.session.commit()
        await self.session.refresh(staff)
        return staff

    async def delete_staff(self, staff_id: UUID) -> None:
        staff = await self._get_or_404(staff_id)
        await self.session.delete(staff)
        await self.session.commit()

    async def change_password(
        self, staff_id: UUID, current_password: str, new_password: str
    ) -> Staff:
        staff = await self._get_or_404(staff_id)
        if not verify_password(current_password, staff.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect.",
            )
        staff.password_hash = hash_password(new_password)
        staff.password_changed_at = datetime.now(timezone.utc)
        staff.failed_attempts = 0
        staff.locked_until = None
        self.session.add(staff)
        await self.session.commit()
        await self.session.refresh(staff)
        return staff

    async def record_failed_attempt(
        self,
        staff: Staff,
        lock_after: int = 5,
        lock_minutes: int = 30,
    ) -> Staff:
        staff.failed_attempts += 1
        if staff.failed_attempts >= lock_after:
            staff.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_minutes)
        self.session.add(staff)
        await self.session.commit()
        await self.session.refresh(staff)
        return staff

    async def reset_failed_attempts(self, staff: Staff) -> Staff:
        staff.failed_attempts = 0
        staff.locked_until = None
        self.session.add(staff)
        await self.session.commit()
        await self.session.refresh(staff)
        return staff

    @staticmethod
    def is_account_locked(staff: Staff) -> bool:
        if staff.locked_until is None:
            return False
        return datetime.now(timezone.utc) < staff.locked_until

    # Directorate CRUD

    async def create_directorate(self, payload: DirectorateCreate) -> Directorate:
        await self._assert_directorate_name_unique(payload.name)
        obj = Directorate(name=payload.name, description=payload.description)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_directorate_by_id(self, directorate_id: int) -> Directorate:
        return await self._get_directorate_or_404(directorate_id)

    async def list_directorates(
        self, *, skip: int = 0, limit: int = 50
    ) -> list[Directorate]:
        stmt = select(Directorate).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_directorate(
        self, directorate_id: int, payload: DirectorateUpdate
    ) -> Directorate:
        obj = await self._get_directorate_or_404(directorate_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] != obj.name:
            await self._assert_directorate_name_unique(data["name"], exclude_id=directorate_id)
        for field, value in data.items():
            setattr(obj, field, value)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete_directorate(self, directorate_id: int) -> None:
        obj = await self._get_directorate_or_404(directorate_id)
        await self.session.delete(obj)
        await self.session.commit()

    # Department CRUD

    async def create_department(self, payload: DepartmentCreate) -> Department:
        await self._get_directorate_or_404(payload.directorate_id)
        await self._assert_department_name_unique(payload.name)
        obj = Department(
            name=payload.name,
            description=payload.description,
            directorate_id=payload.directorate_id,
        )
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def get_department_by_id(self, department_id: int) -> Department:
        return await self._get_department_or_404(department_id)

    async def list_departments(
        self,
        *,
        skip: int = 0,
        limit: int = 50,
        directorate_id: Optional[int] = None,
    ) -> list[Department]:
        stmt = select(Department)
        if directorate_id is not None:
            stmt = stmt.where(Department.directorate_id == directorate_id)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_department(
        self, department_id: int, payload: DepartmentUpdate
    ) -> Department:
        obj = await self._get_department_or_404(department_id)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data and data["name"] != obj.name:
            await self._assert_department_name_unique(data["name"], exclude_id=department_id)
        if "directorate_id" in data:
            await self._get_directorate_or_404(data["directorate_id"])
        for field, value in data.items():
            setattr(obj, field, value)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete_department(self, department_id: int) -> None:
        obj = await self._get_department_or_404(department_id)
        await self.session.delete(obj)
        await self.session.commit()