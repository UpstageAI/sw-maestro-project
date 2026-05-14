"""/data/* CRUD 라우터. D(박영준) + E(신승민) 합의로 구현."""
from datetime import date

from fastapi import APIRouter, HTTPException

from schemas.models import CalendarEvent, HealthSnapshot, WorkoutRecord

router = APIRouter()


# ---------- Calendar ----------
@router.get("/calendar", response_model=list[CalendarEvent])
def list_calendar(start: date, end: date) -> list[CalendarEvent]:
    raise HTTPException(status_code=501, detail="not implemented")


@router.post("/calendar", response_model=CalendarEvent, status_code=201)
def create_calendar(event: CalendarEvent) -> CalendarEvent:
    raise HTTPException(status_code=501, detail="not implemented")


@router.patch("/calendar/{event_id}", response_model=CalendarEvent)
def update_calendar(event_id: str, patch: dict) -> CalendarEvent:
    raise HTTPException(status_code=501, detail="not implemented")


@router.delete("/calendar/{event_id}", status_code=204)
def delete_calendar(event_id: str) -> None:
    raise HTTPException(status_code=501, detail="not implemented")


# ---------- Health ----------
@router.get("/health", response_model=list[HealthSnapshot])
def list_health(start: date, end: date) -> list[HealthSnapshot]:
    raise HTTPException(status_code=501, detail="not implemented")


@router.post("/health", response_model=HealthSnapshot, status_code=201)
def create_health(snapshot: HealthSnapshot) -> HealthSnapshot:
    raise HTTPException(status_code=501, detail="not implemented")


@router.patch("/health/{snapshot_date}", response_model=HealthSnapshot)
def update_health(snapshot_date: date, patch: dict) -> HealthSnapshot:
    raise HTTPException(status_code=501, detail="not implemented")


@router.delete("/health/{snapshot_date}", status_code=204)
def delete_health(snapshot_date: date) -> None:
    raise HTTPException(status_code=501, detail="not implemented")


# ---------- Workouts ----------
@router.get("/workouts", response_model=list[WorkoutRecord])
def list_workouts(start: date, end: date) -> list[WorkoutRecord]:
    raise HTTPException(status_code=501, detail="not implemented")


@router.post("/workouts", response_model=WorkoutRecord, status_code=201)
def create_workout(record: WorkoutRecord) -> WorkoutRecord:
    raise HTTPException(status_code=501, detail="not implemented")


@router.patch("/workouts/{record_id}", response_model=WorkoutRecord)
def update_workout(record_id: str, patch: dict) -> WorkoutRecord:
    raise HTTPException(status_code=501, detail="not implemented")


@router.delete("/workouts/{record_id}", status_code=204)
def delete_workout(record_id: str) -> None:
    raise HTTPException(status_code=501, detail="not implemented")
