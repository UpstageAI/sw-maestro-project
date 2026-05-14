"""간단한 인메모리 Job/Session 저장소.

데모/로컬 개발용이다. 운영 배포에서는 Redis, DB, Celery/RQ 같은 외부 저장소와
작업 큐로 교체하는 것을 권장한다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Literal
from uuid import uuid4

from models.types import Question, Report, SessionState

JobStatus = Literal["queued", "running", "succeeded", "failed"]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    session_id: str | None = None
    status: JobStatus = "queued"
    step: str = "queued"
    progress: int = 0
    message: str = "작업 대기 중입니다."
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "session_id": self.session_id,
            "status": self.status,
            "step": self.step,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class SessionRecord:
    session_id: str
    state: SessionState | None = None
    current_question: Question | None = None
    last_report: Report | None = None
    busy_job_id: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)


class InMemoryStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self.jobs: dict[str, JobRecord] = {}
        self.sessions: dict[str, SessionRecord] = {}

    def create_session_record(self, session_id: str | None = None) -> SessionRecord:
        with self._lock:
            sid = session_id or uuid4().hex
            record = SessionRecord(session_id=sid)
            self.sessions[sid] = record
            return record

    def get_session(self, session_id: str) -> SessionRecord | None:
        with self._lock:
            return self.sessions.get(session_id)

    def create_job(self, job_type: str, session_id: str | None = None) -> JobRecord:
        with self._lock:
            job = JobRecord(job_id=uuid4().hex, job_type=job_type, session_id=session_id)
            self.jobs[job.job_id] = job
            if session_id and session_id in self.sessions:
                self.sessions[session_id].busy_job_id = job.job_id
                self.sessions[session_id].updated_at = utc_now_iso()
            return job

    def get_job(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self.jobs.get(job_id)

    def update_job(
        self,
        job_id: str,
        *,
        status: JobStatus | None = None,
        step: str | None = None,
        progress: int | None = None,
        message: str | None = None,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            job = self.jobs[job_id]
            if status is not None:
                job.status = status
            if step is not None:
                job.step = step
            if progress is not None:
                job.progress = max(0, min(100, progress))
            if message is not None:
                job.message = message
            if result is not None:
                job.result = result
            if error is not None:
                job.error = error
            job.updated_at = utc_now_iso()

    def finish_job(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self.jobs[job_id]
            job.status = "succeeded"
            job.step = "done"
            job.progress = 100
            job.message = "작업이 완료되었습니다."
            job.result = result
            job.updated_at = utc_now_iso()
            if job.session_id and job.session_id in self.sessions:
                session = self.sessions[job.session_id]
                if session.busy_job_id == job_id:
                    session.busy_job_id = None
                session.updated_at = utc_now_iso()

    def fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self.jobs[job_id]
            job.status = "failed"
            job.step = "failed"
            job.progress = 100
            job.message = "작업 중 오류가 발생했습니다."
            job.error = error
            job.updated_at = utc_now_iso()
            if job.session_id and job.session_id in self.sessions:
                session = self.sessions[job.session_id]
                if session.busy_job_id == job_id:
                    session.busy_job_id = None
                session.updated_at = utc_now_iso()

    def set_session_state(
        self,
        session_id: str,
        *,
        state: SessionState | None = None,
        current_question: Question | None = None,
        last_report: Report | None = None,
    ) -> None:
        with self._lock:
            session = self.sessions[session_id]
            if state is not None:
                session.state = state
            if current_question is not None:
                session.current_question = current_question
            if last_report is not None:
                session.last_report = last_report
            session.updated_at = utc_now_iso()


store = InMemoryStore()
