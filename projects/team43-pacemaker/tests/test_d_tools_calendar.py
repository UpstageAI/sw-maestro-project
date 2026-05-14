"""D 슬라이스 — calendar + workouts CRUD 통합 테스트.

SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY가 모두 있어야 동작.
없으면 모듈 단위 skip — CI 및 키 미보유 팀원 머신 보호.

격리 날짜(2099-XX-XX)로 시드와 충돌 회피, autouse fixture로 cleanup.
"""
import os
from datetime import date, datetime

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY required for integration tests",
)

from schemas.models import CalendarEvent, WorkoutRecord
from tools.data_tools import (
    create_calendar_event,
    create_workout,
    delete_calendar_event,
    delete_workout,
    get_calendar,
    get_workouts,
    update_calendar_event,
    update_workout,
)

# ---------- Calendar ----------
_CAL_DATE = date(2099, 1, 1)
_CAL_START = datetime(2099, 1, 1, 9, 0)
_CAL_END = datetime(2099, 1, 1, 10, 0)


@pytest.fixture(autouse=True)
def _cleanup_calendar():
    for ev in get_calendar(_CAL_DATE, _CAL_DATE):
        delete_calendar_event(str(ev.id))
    yield
    for ev in get_calendar(_CAL_DATE, _CAL_DATE):
        delete_calendar_event(str(ev.id))


def test_get_calendar_empty_range_returns_empty_list():
    rows = get_calendar(date(2099, 12, 1), date(2099, 12, 31))
    assert rows == []


def test_calendar_lifecycle_create_get_update_delete():
    event = CalendarEvent(start_at=_CAL_START, end_at=_CAL_END, title="격리 테스트 이벤트")
    created = create_calendar_event(event)
    assert created.id is not None, "Supabase가 id를 채번해야 함"
    assert created.title == "격리 테스트 이벤트"

    fetched = get_calendar(_CAL_DATE, _CAL_DATE)
    assert len(fetched) == 1
    assert fetched[0].title == "격리 테스트 이벤트"

    updated = update_calendar_event(str(created.id), {"title": "수정된 이벤트", "is_busy": False})
    assert updated.title == "수정된 이벤트"
    assert updated.is_busy is False

    delete_calendar_event(str(created.id))
    assert get_calendar(_CAL_DATE, _CAL_DATE) == []


# ---------- Workouts ----------
_WORKOUT_DATE = date(2099, 2, 1)


@pytest.fixture(autouse=True)
def _cleanup_workouts():
    for rec in get_workouts(_WORKOUT_DATE, _WORKOUT_DATE):
        delete_workout(str(rec.id))
    yield
    for rec in get_workouts(_WORKOUT_DATE, _WORKOUT_DATE):
        delete_workout(str(rec.id))


def test_get_workouts_empty_range_returns_empty_list():
    rows = get_workouts(date(2099, 12, 1), date(2099, 12, 31))
    assert rows == []


def test_workout_lifecycle_create_get_update_delete():
    record = WorkoutRecord(
        date=_WORKOUT_DATE,
        type="스쿼트",
        duration_min=30,
        muscles=["하체", "둔근"],
        intensity=3,
    )
    created = create_workout(record)
    assert created.id is not None, "Supabase가 id를 채번해야 함"
    assert created.type == "스쿼트"

    fetched = get_workouts(_WORKOUT_DATE, _WORKOUT_DATE)
    assert len(fetched) == 1
    assert fetched[0].type == "스쿼트"

    updated = update_workout(str(created.id), {"duration_min": 45, "intensity": 4})
    assert updated.duration_min == 45
    assert updated.intensity == 4
    assert updated.type == "스쿼트", "안 바꾼 필드는 유지"

    delete_workout(str(created.id))
    assert get_workouts(_WORKOUT_DATE, _WORKOUT_DATE) == []
