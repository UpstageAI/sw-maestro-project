"""데이터 조회·변경 Tool.

담당:
- D(박영준): calendar + workouts CRUD 8개
- E(신승민): health CRUD 4개

유저가 FE에서 보는 모든 데이터는 agent도 그대로 본다 — 그러므로 read+write 둘 다.
같은 파일을 둘이 만지므로 PR을 함수 단위로 잘게 쪼갤 것.
"""
import os
from datetime import date

from dotenv import load_dotenv
from supabase import Client, create_client

from schemas.models import CalendarEvent, HealthSnapshot, WorkoutRecord

load_dotenv()


def _client() -> Client:
    return create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])


# ---------- Calendar ----------
def get_calendar(start: date, end: date) -> list[CalendarEvent]:
    """[start, end] 범위 내 start_at을 가진 캘린더 이벤트 반환."""
    rows = (
        _client()
        .table("calendar_events")
        .select("*")
        .gte("start_at", f"{start}T00:00:00")
        .lte("start_at", f"{end}T23:59:59")
        .execute()
    )
    return [CalendarEvent.model_validate(row) for row in rows.data]


def create_calendar_event(event: CalendarEvent) -> CalendarEvent:
    """이벤트 1건 추가. id 채번 후 반환."""
    data = event.model_dump(mode="json", exclude={"id"})
    row = _client().table("calendar_events").insert(data).execute()
    return CalendarEvent.model_validate(row.data[0])


def update_calendar_event(event_id: str, patch: dict) -> CalendarEvent:
    """이벤트 부분 수정. 갱신된 이벤트 반환."""
    row = _client().table("calendar_events").update(patch).eq("id", event_id).execute()
    return CalendarEvent.model_validate(row.data[0])


def delete_calendar_event(event_id: str) -> None:
    """이벤트 1건 삭제."""
    _client().table("calendar_events").delete().eq("id", event_id).execute()


# ---------- Health ----------
_HEALTH_PATCH_FIELDS = frozenset({"sleep_hours", "activity_minutes", "resting_hr"})


def _ensure_supabase_env() -> None:
    """SUPABASE 환경변수 미설정 시 NotImplementedError로 위임.

    agent/tools.py의 health_tool은 NotImplementedError만 catch해서 빈 리스트로 fallback한다 —
    키 미설정 환경(스모크 테스트, 키 미보유 팀원 머신)에서도 호출이 깨지지 않도록 맞춘다.
    """
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        raise NotImplementedError("SUPABASE env not configured")


def get_health(start: date, end: date) -> list[HealthSnapshot]:
    """[start, end] 범위 health_snapshots 스냅샷 반환 (date 오름차순)."""
    _ensure_supabase_env()
    rows = (
        _client()
        .table("health_snapshots")
        .select("*")
        .gte("date", start.isoformat())
        .lte("date", end.isoformat())
        .order("date")
        .execute()
    )
    return [HealthSnapshot.model_validate(row) for row in rows.data]


def create_health_snapshot(snapshot: HealthSnapshot) -> HealthSnapshot:
    """스냅샷 1건 추가. id 채번 후 반환."""
    _ensure_supabase_env()
    data = snapshot.model_dump(mode="json", exclude={"id"})
    row = _client().table("health_snapshots").insert(data).execute()
    return HealthSnapshot.model_validate(row.data[0])


def update_health_snapshot(snapshot_date: date, patch: dict) -> HealthSnapshot:
    """해당 일자 스냅샷 부분 수정. 알려지지 않은 키는 무시, 없으면 ValueError."""
    _ensure_supabase_env()
    clean = {k: v for k, v in patch.items() if k in _HEALTH_PATCH_FIELDS}
    row = (
        _client()
        .table("health_snapshots")
        .update(clean)
        .eq("date", snapshot_date.isoformat())
        .execute()
    )
    if not row.data:
        raise ValueError(f"snapshot not found: {snapshot_date.isoformat()}")
    return HealthSnapshot.model_validate(row.data[0])


def delete_health_snapshot(snapshot_date: date) -> None:
    """해당 일자 스냅샷 삭제."""
    _ensure_supabase_env()
    _client().table("health_snapshots").delete().eq("date", snapshot_date.isoformat()).execute()


# ---------- Workouts ----------
def get_workouts(start: date, end: date) -> list[WorkoutRecord]:
    """[start, end] 범위 운동 기록 반환."""
    rows = (
        _client()
        .table("workout_records")
        .select("*")
        .gte("date", start.isoformat())
        .lte("date", end.isoformat())
        .execute()
    )
    return [WorkoutRecord.model_validate(row) for row in rows.data]


def create_workout(record: WorkoutRecord) -> WorkoutRecord:
    """운동 기록 1건 추가."""
    data = record.model_dump(mode="json", exclude={"id"})
    row = _client().table("workout_records").insert(data).execute()
    return WorkoutRecord.model_validate(row.data[0])


def update_workout(record_id: str, patch: dict) -> WorkoutRecord:
    """운동 기록 부분 수정."""
    row = _client().table("workout_records").update(patch).eq("id", record_id).execute()
    return WorkoutRecord.model_validate(row.data[0])


def delete_workout(record_id: str) -> None:
    """운동 기록 1건 삭제."""
    _client().table("workout_records").delete().eq("id", record_id).execute()
