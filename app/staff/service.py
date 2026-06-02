from uuid import UUID
from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.staff.model import Staff
from app.staff.schemas import StaffCreate, StaffUpdate, PasswordChangeRequest
from app.core.security import hash_password, verify_password


#helpers 

def _get_or_404(db: Session, staff_id: UUID) -> Staff:
    staff = db.get(Staff, staff_id)
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Staff '{staff_id}' not found.",
        )
    return staff


def _assert_unique(
    db: Session,
    field: str,
    value: str,
    exclude_id: Optional[UUID] = None,
) -> None:
    col = getattr(Staff, field)
    stmt = select(Staff).where(col == value)
    if exclude_id:
        stmt = stmt.where(Staff.id != exclude_id)
    if db.exec(stmt).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A staff member with {field} '{value}' already exists.",
        )

def create_staff(db: Session, payload: StaffCreate) -> Staff:
    _assert_unique(db, "personal_number", payload.personal_number)
    _assert_unique(db, "email", payload.email)

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
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def get_staff_by_id(db: Session, staff_id: UUID) -> Staff:
    return _get_or_404(db, staff_id)


def get_staff_by_email(db: Session, email: str) -> Optional[Staff]:
    return db.exec(select(Staff).where(Staff.email == email)).first()


def get_staff_by_personal_number(db: Session, pn: str) -> Optional[Staff]:
    return db.exec(select(Staff).where(Staff.personal_number == pn)).first()


def list_staff(
    db: Session,
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
    return list(db.exec(stmt.offset(skip).limit(limit)).all())


def update_staff(db: Session, staff_id: UUID, payload: StaffUpdate) -> Staff:
    staff = _get_or_404(db, staff_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def delete_staff(db: Session, staff_id: UUID) -> None:
    staff = _get_or_404(db, staff_id)
    db.delete(staff)
    db.commit()


#password management 

def change_password(
    db: Session,
    staff_id: UUID,
    payload: PasswordChangeRequest,
) -> Staff:
    staff = _get_or_404(db, staff_id)

    if not verify_password(payload.current_password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if verify_password(payload.new_password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    staff.password_hash = hash_password(payload.new_password)
    staff.password_changed_at = datetime.now(timezone.utc)
    staff.failed_attempts = 0
    staff.locked_until = None
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


#lockout helpers (called from session/auth service)

def record_failed_attempt(
    db: Session,
    staff: Staff,
    lock_after: int = 5,
    lock_minutes: int = 30,
) -> Staff:
    staff.failed_attempts += 1
    if staff.failed_attempts >= lock_after:
        staff.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_minutes)
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def reset_failed_attempts(db: Session, staff: Staff) -> Staff:
    staff.failed_attempts = 0
    staff.locked_until = None
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


def is_account_locked(staff: Staff) -> bool:
    if not staff.locked_until:
        return False
    return datetime.now(timezone.utc) < staff.locked_until
