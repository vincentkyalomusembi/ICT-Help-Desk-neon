from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlmodel import Session, select
from fastapi import HTTPException, status

from app.staff.model import Staff
from app.staff.schemas import StaffCreate, StaffUpdate, StaffResponse, PasswordChangeRequest
from app.core.security import hash_password


class StaffService:
    def __init__(self, session: Session):
        self.session = session

    
    def _get_or_404(self, staff_id: UUID) -> Staff:
        staff = self.session.get(Staff, staff_id)
        if not staff:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Staff with id '{staff_id}' not found.",
            )
        return staff

    def _assert_unique_field(
        self,
        field_name: str,
        value: str,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        col = getattr(Staff, field_name)
        stmt = select(Staff).where(col == value)
        if exclude_id:
            stmt = stmt.where(Staff.id != exclude_id)
        if self.session.exec(stmt).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A staff member with {field_name} '{value}' already exists.",
            )

    def create_staff(self, payload: StaffCreate) -> Staff:
        self._assert_unique_field("personal_number", payload.personal_number)
        self._assert_unique_field("email", payload.email)

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
            role=payload.role,
            password_hash=hash_password(payload.password),
            password_changed_at=now,
            created_at=now,
        )
        self.session.add(staff)
        self.session.commit()
        self.session.refresh(staff)
        return staff

    def get_staff_by_id(self, staff_id: UUID) -> Staff:
        return self._get_or_404(staff_id)

    def get_staff_by_email(self, email: str) -> Optional[Staff]:
        return self.session.exec(select(Staff).where(Staff.email == email)).first()

    def get_staff_by_personal_number(self, personal_number: str) -> Optional[Staff]:
        return self.session.exec(
            select(Staff).where(Staff.personal_number == personal_number)
        ).first()

    def list_staff(
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
        return list(self.session.exec(stmt).all())

    def update_staff(self, staff_id: UUID, payload: StaffUpdate) -> Staff:
        staff = self._get_or_404(staff_id)
        updates = payload.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(staff, field, value)
        self.session.add(staff)
        self.session.commit()
        self.session.refresh(staff)
        return staff

    def delete_staff(self, staff_id: UUID) -> None:
        staff = self._get_or_404(staff_id)
        self.session.delete(staff)
        self.session.commit()


    def change_password(self, staff_id: UUID, new_password: str) -> Staff:
        staff = self._get_or_404(staff_id)
        staff.password_hash = hash_password(new_password)
        staff.password_changed_at = datetime.now(timezone.utc)
        staff.failed_attempts = 0
        staff.locked_until = None
        self.session.add(staff)
        self.session.commit()
        self.session.refresh(staff)
        return staff

    def record_failed_attempt(
        self,
        staff: Staff,
        lock_after: int = 5,
        lock_minutes: int = 30,
    ) -> Staff:
        staff.failed_attempts += 1
        if staff.failed_attempts >= lock_after:
            staff.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=lock_minutes
            )
        self.session.add(staff)
        self.session.commit()
        self.session.refresh(staff)
        return staff

    def reset_failed_attempts(self, staff: Staff) -> Staff:
        staff.failed_attempts = 0
        staff.locked_until = None
        self.session.add(staff)
        self.session.commit()
        self.session.refresh(staff)
        return staff

    @staticmethod
    def is_account_locked(staff: Staff) -> bool:
        if staff.locked_until is None:
            return False
        return datetime.now(timezone.utc) < staff.locked_until
