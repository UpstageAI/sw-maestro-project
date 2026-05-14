from __future__ import annotations

import json
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.models import GoogleCredential, Schedule


def get_credentials(session_id: str, db: Session) -> Optional[Credentials]:
    """DB에서 토큰을 불러오고, 만료됐으면 자동으로 갱신 후 저장."""
    row = db.query(GoogleCredential).filter_by(session_id=session_id).first()
    if not row:
        return None

    creds = Credentials(
        token=row.token,
        refresh_token=row.refresh_token,
        token_uri=row.token_uri,
        client_id=row.client_id,
        client_secret=row.client_secret,
        scopes=json.loads(row.scopes),
    )
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        row.token = creds.token
        db.commit()

    return creds


def create_event(schedule: Schedule, creds: Credentials) -> str:
    """Google Calendar에 이벤트를 생성하고 event_id를 반환."""
    service = build("calendar", "v3", credentials=creds)
    event = service.events().insert(
        calendarId="primary",
        body=_build_event_body(schedule),
    ).execute()
    return event["id"]


def update_event(schedule: Schedule, creds: Credentials) -> None:
    """Google Calendar 이벤트를 최신 일정 정보로 업데이트."""
    if not schedule.google_event_id:
        return
    service = build("calendar", "v3", credentials=creds)
    service.events().update(
        calendarId="primary",
        eventId=schedule.google_event_id,
        body=_build_event_body(schedule),
    ).execute()


def delete_event(google_event_id: str, creds: Credentials) -> None:
    """Google Calendar에서 이벤트를 삭제."""
    service = build("calendar", "v3", credentials=creds)
    service.events().delete(
        calendarId="primary",
        eventId=google_event_id,
    ).execute()


def get_free_busy(
    session_id: str,
    db: Session,
    time_min: str,
    time_max: str,
) -> list[dict]:
    """지정 기간의 바쁜 시간대 목록을 반환. [{start, end}, ...]"""
    creds = get_credentials(session_id, db)
    if not creds:
        return []

    service = build("calendar", "v3", credentials=creds)
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "items": [{"id": "primary"}],
    }
    result = service.freebusy().query(body=body).execute()
    busy_slots = result.get("calendars", {}).get("primary", {}).get("busy", [])
    return busy_slots


def _build_event_body(schedule: Schedule) -> dict:
    body: dict = {
        "summary": schedule.title,
        "start": {"dateTime": schedule.start_at.isoformat(), "timeZone": "Asia/Seoul"},
        "end": {"dateTime": schedule.end_at.isoformat(), "timeZone": "Asia/Seoul"},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": schedule.reminder_minutes}],
        },
    }
    if schedule.location:
        body["location"] = schedule.location
    return body
