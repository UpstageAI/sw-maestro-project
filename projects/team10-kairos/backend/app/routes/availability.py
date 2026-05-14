from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from googleapiclient.errors import HttpError
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import AvailabilityResponse, BusySlot
from app.services import google_calendar

router = APIRouter()


@router.get("", response_model=AvailabilityResponse)
def get_availability(
    session_id: str = Query(..., description="Google 연동 세션 ID"),
    time_min: datetime = Query(..., description="조회 시작 (ISO 8601, 예: 2026-05-10T00:00:00+09:00)"),
    time_max: datetime = Query(..., description="조회 종료 (ISO 8601, 예: 2026-05-17T00:00:00+09:00)"),
    db: Session = Depends(get_db),
):
    """
    Google Calendar FreeBusy API로 막힌 시간대를 조회합니다.
    일정 공유 그리드에서 '불가' 슬롯 자동 처리에 사용합니다.
    이벤트 내용은 반환하지 않으며 시간 범위만 반환합니다.
    """
    if time_max <= time_min:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="time_max는 time_min보다 늦어야 합니다.",
        )

    creds = google_calendar.get_credentials(session_id, db)
    if not creds:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google Calendar 연동이 필요합니다. /auth/google로 먼저 인증해주세요.",
        )

    try:
        busy_raw = google_calendar.get_free_busy(
            session_id=session_id,
            db=db,
            time_min=_to_rfc3339(time_min),
            time_max=_to_rfc3339(time_max),
        )
    except HttpError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Google Calendar 조회 중 문제가 발생했습니다.",
        ) from exc

    busy_slots = [BusySlot(start=slot["start"], end=slot["end"]) for slot in busy_raw]

    return AvailabilityResponse(
        time_min=time_min,
        time_max=time_max,
        busy=busy_slots,
    )


def _to_rfc3339(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
