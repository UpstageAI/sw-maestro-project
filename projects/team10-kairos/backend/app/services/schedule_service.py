from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Schedule
from app.schemas import ScheduleCreate, ScheduleUpdate


class ScheduleNotFoundError(Exception):
    pass


class ScheduleValidationError(ValueError):
    pass


def create_schedule(db: Session, data: ScheduleCreate) -> Schedule:
    end_at = data.end_at or data.start_at + timedelta(hours=1)
    _validate_schedule(
        title=data.title,
        start_at=data.start_at,
        end_at=end_at,
        reminder_minutes=data.reminder_minutes,
    )
    schedule = Schedule(
        title=data.title,
        start_at=data.start_at,
        end_at=end_at,
        location=data.location,
        reminder_minutes=data.reminder_minutes,
        schedule_type=data.schedule_type,
        original_text=data.original_text,
        status="confirmed",
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


def list_schedules(db: Session) -> list[Schedule]:
    stmt = select(Schedule).order_by(Schedule.start_at.asc())
    return list(db.scalars(stmt).all())


def get_schedule(db: Session, schedule_id: int) -> Schedule:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise ScheduleNotFoundError
    return schedule


def update_schedule(db: Session, schedule_id: int, data: ScheduleUpdate) -> Schedule:
    schedule = get_schedule(db, schedule_id)
    update_data = data.model_dump(exclude_unset=True, exclude_none=True)

    next_title = update_data.get("title", schedule.title)
    next_start_at = update_data.get("start_at", schedule.start_at)
    next_end_at = update_data.get("end_at", schedule.end_at)
    next_reminder_minutes = update_data.get("reminder_minutes", schedule.reminder_minutes)

    if next_end_at is None and "start_at" in update_data:
        next_end_at = next_start_at + timedelta(hours=1)

    _validate_schedule(
        title=next_title,
        start_at=next_start_at,
        end_at=next_end_at,
        reminder_minutes=next_reminder_minutes,
    )

    for field, value in update_data.items():
        setattr(schedule, field, value)
    schedule.end_at = next_end_at

    db.commit()
    db.refresh(schedule)
    return schedule


def delete_schedule(db: Session, schedule_id: int, session_id: Optional[str] = None) -> Schedule:
    schedule = get_schedule(db, schedule_id)
    db.delete(schedule)
    db.commit()
    return schedule


def _validate_schedule(
    *,
    title: str,
    start_at: datetime,
    end_at: datetime | None,
    reminder_minutes: int,
) -> None:
    if not title.strip():
        raise ScheduleValidationError("일정 제목을 입력해주세요.")
    if end_at is not None and end_at <= start_at:
        raise ScheduleValidationError("종료 시간은 시작 시간보다 늦어야 합니다.")

    now = _now_for(start_at)
    if start_at < now:
        raise ScheduleValidationError("이미 지난 일정입니다. 시간을 다시 확인해주세요.")

    reminder_at = start_at - timedelta(minutes=reminder_minutes)
    if reminder_at < now:
        raise ScheduleValidationError("알림 시간이 이미 지났습니다. 더 짧은 알림 시간을 선택해주세요.")


def _now_for(value: datetime) -> datetime:
    if value.tzinfo is None:
        return datetime.now()
    return datetime.now(timezone.utc).astimezone(value.tzinfo)
