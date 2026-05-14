from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.models import AuditLogRecord, CandidateRecord, EvaluationResult, JobRecord, TokenMappingRecord


class SQLiteRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    jd_text TEXT NOT NULL,
                    criteria_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS candidates (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    resume_text TEXT NOT NULL,
                    masked_resume_text TEXT NOT NULL,
                    github_url TEXT,
                    portfolio_url TEXT,
                    source_filename TEXT,
                    extracted_urls_json TEXT NOT NULL DEFAULT '[]',
                    parsed_profile_json TEXT NOT NULL DEFAULT '{}',
                    github_status TEXT NOT NULL DEFAULT 'not_requested',
                    github_failure_reason TEXT,
                    github_profile_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS evaluations (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    jd_score INTEGER NOT NULL,
                    alignment_score INTEGER NOT NULL,
                    summary TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    job_id TEXT,
                    event_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS token_mappings (
                    id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    candidate_id TEXT NOT NULL,
                    token TEXT NOT NULL,
                    original TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            self._ensure_column(conn, "candidates", "source_filename", "TEXT")
            self._ensure_column(conn, "candidates", "extracted_urls_json", "TEXT NOT NULL DEFAULT '[]'")
            self._ensure_column(conn, "candidates", "parsed_profile_json", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "candidates", "github_status", "TEXT NOT NULL DEFAULT 'not_requested'")
            self._ensure_column(conn, "candidates", "github_failure_reason", "TEXT")
            self._ensure_column(conn, "candidates", "github_profile_json", "TEXT NOT NULL DEFAULT '{}'")
            self._ensure_column(conn, "audit_logs", "job_id", "TEXT")

    def _ensure_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, definition: str) -> None:
        columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")

    def upsert_job(self, job: JobRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO jobs (id, title, jd_text, criteria_json, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    jd_text = excluded.jd_text,
                    criteria_json = excluded.criteria_json,
                    status = excluded.status,
                    updated_at = excluded.updated_at
                """,
                (
                    job.id,
                    job.title,
                    job.jd_text,
                    json.dumps([item.model_dump() for item in job.criteria], ensure_ascii=False),
                    job.status,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                ),
            )

    def list_jobs(self) -> list[JobRecord]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [self._job_from_row(row) for row in rows]

    def get_job(self, job_id: str) -> JobRecord | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        return self._job_from_row(row) if row else None

    def insert_candidate(self, candidate: CandidateRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO candidates
                (
                    id,
                    job_id,
                    name,
                    resume_text,
                    masked_resume_text,
                    github_url,
                    portfolio_url,
                    source_filename,
                    extracted_urls_json,
                    parsed_profile_json,
                    github_status,
                    github_failure_reason,
                    github_profile_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    candidate.id,
                    candidate.job_id,
                    candidate.name,
                    candidate.resume_text,
                    candidate.masked_resume_text,
                    candidate.github_url,
                    candidate.portfolio_url,
                    candidate.source_filename,
                    json.dumps(candidate.extracted_urls, ensure_ascii=False),
                    json.dumps(candidate.parsed_profile.model_dump(), ensure_ascii=False),
                    candidate.github_status,
                    candidate.github_failure_reason,
                    json.dumps(candidate.github_profile.model_dump(mode="json"), ensure_ascii=False)
                    if candidate.github_profile
                    else "{}",
                    candidate.created_at.isoformat(),
                ),
            )

    def list_candidates(self, job_id: str) -> list[CandidateRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM candidates WHERE job_id = ? ORDER BY created_at DESC",
                (job_id,),
            ).fetchall()
        return [self._candidate_from_row(row) for row in rows]

    def insert_evaluation(self, result: EvaluationResult) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO evaluations
                (id, job_id, candidate_id, jd_score, alignment_score, summary, evidence_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    result.job_id,
                    result.candidate_id,
                    result.jd_score,
                    result.alignment_score,
                    result.summary,
                    json.dumps([item.model_dump() for item in result.evidence], ensure_ascii=False),
                    result.created_at.isoformat(),
                ),
            )

    def list_evaluations(self, job_id: str) -> list[EvaluationResult]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM evaluations WHERE job_id = ? ORDER BY jd_score DESC, alignment_score DESC",
                (job_id,),
            ).fetchall()
        return [self._evaluation_from_row(row) for row in rows]

    def insert_audit_log(self, record: AuditLogRecord) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (id, job_id, event_type, entity_id, payload_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.job_id,
                    record.event_type,
                    record.entity_id,
                    json.dumps(record.payload, ensure_ascii=False),
                    record.created_at.isoformat(),
                ),
            )

    def insert_token_mappings(self, records: list[TokenMappingRecord]) -> None:
        if not records:
            return
        with self.connect() as conn:
            conn.executemany(
                """
                INSERT INTO token_mappings (id, job_id, candidate_id, token, original, kind, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.id,
                        record.job_id,
                        record.candidate_id,
                        record.token,
                        record.original,
                        record.kind,
                        record.created_at.isoformat(),
                    )
                    for record in records
                ],
            )

    def list_token_mappings(self, candidate_id: str) -> list[TokenMappingRecord]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM token_mappings WHERE candidate_id = ? ORDER BY created_at ASC",
                (candidate_id,),
            ).fetchall()
        return [TokenMappingRecord(**dict(row)) for row in rows]

    def list_audit_logs(self, job_id: str | None = None, entity_id: str | None = None) -> list[AuditLogRecord]:
        query = "SELECT * FROM audit_logs"
        params: list[str] = []
        where_clauses: list[str] = []
        if job_id:
            where_clauses.append("job_id = ?")
            params.append(job_id)
        if entity_id:
            where_clauses.append("entity_id = ?")
            params.append(entity_id)
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " ORDER BY created_at DESC"
        with self.connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [
            AuditLogRecord(
                id=row["id"],
                job_id=row["job_id"],
                event_type=row["event_type"],
                entity_id=row["entity_id"],
                payload=json.loads(row["payload_json"]),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def _job_from_row(self, row: sqlite3.Row) -> JobRecord:
        payload = dict(row)
        payload["criteria"] = json.loads(payload.pop("criteria_json"))
        return JobRecord(**payload)

    def _candidate_from_row(self, row: sqlite3.Row) -> CandidateRecord:
        payload = dict(row)
        payload["extracted_urls"] = json.loads(payload.pop("extracted_urls_json", "[]"))
        payload["parsed_profile"] = json.loads(payload.pop("parsed_profile_json", "{}"))
        github_profile = json.loads(payload.pop("github_profile_json", "{}"))
        payload["github_profile"] = github_profile or None
        return CandidateRecord(**payload)

    def _evaluation_from_row(self, row: sqlite3.Row) -> EvaluationResult:
        payload = dict(row)
        payload["evidence"] = json.loads(payload.pop("evidence_json"))
        return EvaluationResult(**payload)
