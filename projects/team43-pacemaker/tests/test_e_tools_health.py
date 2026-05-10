"""E 슬라이스 — health CRUD 통합 테스트.

SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY가 모두 있어야 동작.
없으면 모듈 단위 skip — CI 및 키 미보유 팀원 머신 보호.

격리 날짜(2099-XX-XX)로 시드와 충돌 회피, autouse fixture로 cleanup.
"""
import os
from datetime import date

import pytest

pytestmark = pytest.mark.skipif(
    not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
    reason="SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY required for integration tests",
)

from schemas.models import HealthSnapshot
from tools.data_tools import (
    create_health_snapshot,
    delete_health_snapshot,
    get_health,
    update_health_snapshot,
)


ISOLATED_DATE = date(2099, 1, 1)
ISOLATED_DATE_MISSING = date(2099, 6, 15)


@pytest.fixture(autouse=True)
def _cleanup_isolated():
    delete_health_snapshot(ISOLATED_DATE)
    delete_health_snapshot(ISOLATED_DATE_MISSING)
    yield
    delete_health_snapshot(ISOLATED_DATE)
    delete_health_snapshot(ISOLATED_DATE_MISSING)


def test_get_health_empty_range_returns_empty_list():
    rows = get_health(date(2099, 12, 1), date(2099, 12, 31))
    assert rows == []


def test_get_health_seed_range_returns_recent_week():
    rows = get_health(date(2026, 4, 27), date(2026, 5, 6))
    assert len(rows) >= 7, "시드 데이터(4/27~5/6)가 7건 이상이어야 함"
    dates = [r.date for r in rows]
    assert dates == sorted(dates), "결과는 date 오름차순"


def test_lifecycle_create_get_update_delete():
    snapshot = HealthSnapshot(
        date=ISOLATED_DATE,
        sleep_hours=7.5,
        activity_minutes=40,
        resting_hr=62,
    )
    created = create_health_snapshot(snapshot)
    assert created.id is not None, "Supabase가 id를 채번해야 함"
    assert created.date == ISOLATED_DATE
    assert created.sleep_hours == 7.5

    fetched = get_health(ISOLATED_DATE, ISOLATED_DATE)
    assert len(fetched) == 1
    assert fetched[0].sleep_hours == 7.5

    updated = update_health_snapshot(
        ISOLATED_DATE, {"sleep_hours": 6.0, "resting_hr": 70}
    )
    assert updated.sleep_hours == 6.0
    assert updated.resting_hr == 70
    assert updated.activity_minutes == 40, "안 바꾼 필드는 유지"

    delete_health_snapshot(ISOLATED_DATE)
    after = get_health(ISOLATED_DATE, ISOLATED_DATE)
    assert after == []


def test_update_nonexistent_date_raises_value_error():
    with pytest.raises(ValueError):
        update_health_snapshot(ISOLATED_DATE_MISSING, {"sleep_hours": 6.0})


def test_update_ignores_unknown_keys():
    create_health_snapshot(
        HealthSnapshot(
            date=ISOLATED_DATE,
            sleep_hours=7.0,
            activity_minutes=30,
            resting_hr=60,
        )
    )
    updated = update_health_snapshot(
        ISOLATED_DATE,
        {"sleep_hours": 8.0, "unknown_field": "wat", "id": 999},
    )
    assert updated.sleep_hours == 8.0
