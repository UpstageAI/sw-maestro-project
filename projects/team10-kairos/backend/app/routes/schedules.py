from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from googleapiclient.errors import HttpError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    AnalyzeScheduleRequest,
    AnalyzeScheduleResponse,
    ScheduleCreate,
    ScheduleRead,
    ScheduleUpdate,
)
from app.services import google_calendar
from app.services.schedule_graph import analyze_schedule
from app.services.schedule_service import (
    ScheduleNotFoundError,
    ScheduleValidationError,
    create_schedule,
    delete_schedule,
    list_schedules,
    update_schedule,
)

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeScheduleResponse)
def analyze_schedule_route(payload: AnalyzeScheduleRequest) -> AnalyzeScheduleResponse:
    try:
        return analyze_schedule(payload.text, payload.timezone, payload.analysis_context)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="일정 분석 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요.",
        ) from exc


@router.post("", response_model=ScheduleRead, status_code=status.HTTP_201_CREATED)
def create_schedule_route(payload: ScheduleCreate, db: Session = Depends(get_db)):
    try:
        schedule = create_schedule(db, payload)
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="일정을 저장하지 못했습니다.",
        ) from exc

    if payload.session_id:
        creds = google_calendar.get_credentials(payload.session_id, db)
        if creds:
            try:
                event_id = google_calendar.create_event(schedule, creds)
                schedule.google_event_id = event_id
                db.commit()
                db.refresh(schedule)
            except HttpError:
                pass  # Google Calendar 실패해도 로컬 저장은 유지

    return schedule


@router.get("", response_model=list[ScheduleRead])
def list_schedules_route(db: Session = Depends(get_db)):
    return list_schedules(db)


@router.patch("/{schedule_id}", response_model=ScheduleRead)
def update_schedule_route(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
):
    try:
        schedule = update_schedule(db, schedule_id, payload)
    except ScheduleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="일정을 찾을 수 없습니다.") from exc
    except ScheduleValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="일정을 수정하지 못했습니다.",
        ) from exc

    if payload.session_id and schedule.google_event_id:
        creds = google_calendar.get_credentials(payload.session_id, db)
        if creds:
            try:
                google_calendar.update_event(schedule, creds)
            except HttpError:
                pass

    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule_route(
    schedule_id: int,
    session_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    try:
        schedule = delete_schedule(db, schedule_id, session_id)
    except ScheduleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="일정을 찾을 수 없습니다.") from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="일정을 삭제하지 못했습니다.",
        ) from exc

    if session_id and schedule and schedule.google_event_id:
        creds = google_calendar.get_credentials(session_id, db)
        if creds:
            try:
                google_calendar.delete_event(schedule.google_event_id, creds)
            except HttpError:
                pass
