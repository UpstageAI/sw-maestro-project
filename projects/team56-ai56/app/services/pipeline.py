from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.core.models import (
    AuditLogRecord,
    CandidateCreate,
    CandidateRecord,
    Criterion,
    JobCreate,
    JobRecord,
    MaskingResult,
    TokenMappingRecord,
    utc_now,
)
from app.db.repository import SQLiteRepository
from app.services.evaluator import BaseEvaluator, MockEvaluator, UpstageEvaluator
from app.services.github_client import GitHubClient
from app.services.parser import ParsedResume, ResumeParser
from app.services.pii_guard import PIIGuard


class HireProofPipeline:
    def __init__(
        self,
        repository: SQLiteRepository | None = None,
        parser: ResumeParser | None = None,
        pii_guard: PIIGuard | None = None,
        github_client: GitHubClient | None = None,
        evaluator: BaseEvaluator | None = None,
    ) -> None:
        settings = get_settings()
        self.settings = settings
        self.repository = repository or SQLiteRepository(settings.sqlite_path)
        self.repository.init_schema()
        self.parser = parser or ResumeParser()
        self.pii_guard = pii_guard or PIIGuard()
        self.github_client = github_client or GitHubClient()
        self.mock_evaluator = MockEvaluator()
        self.evaluator = evaluator or (
            self.mock_evaluator
            if settings.evaluator_mode == "mock"
            else UpstageEvaluator(
                api_key=settings.upstage_api_key,
                model=settings.upstage_model,
                base_url=settings.upstage_base_url,
            )
        )
        if isinstance(self.evaluator, UpstageEvaluator):
            self.evaluator.set_audit_hook(self._handle_llm_audit_event)

    def preview_candidate_text(self, resume_text: str) -> dict:
        parsed = self.parser.parse_text(resume_text)
        masking = self.pii_guard.mask(parsed.raw_text)
        return self._build_preview(parsed, masking)

    def preview_candidate_file(self, filename: str, file_bytes: bytes) -> dict:
        saved_path = self._save_upload(filename, file_bytes)
        parsed = self.parser.parse_file(saved_path)
        masking = self.pii_guard.mask(parsed.raw_text)
        return self._build_preview(parsed, masking, source_filename=filename)

    def create_job(self, payload: JobCreate) -> JobRecord:
        criteria = self._suggest_criteria(payload.jd_text)
        job = JobRecord(title=payload.title, jd_text=payload.jd_text, criteria=criteria)
        self.repository.upsert_job(job)
        self.repository.insert_audit_log(
            AuditLogRecord(
                job_id=job.id,
                event_type="job_created",
                entity_id=job.id,
                payload={"title": job.title, "criteria_count": len(criteria)},
            )
        )
        return job

    def confirm_criteria(self, job_id: str, criteria: list[dict]) -> JobRecord:
        job = self.repository.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        job.criteria = [Criterion(**item) for item in criteria]
        job.status = "criteria_confirmed"
        job.updated_at = utc_now()
        self.repository.upsert_job(job)
        self.repository.insert_audit_log(
            AuditLogRecord(
                job_id=job.id,
                event_type="criteria_confirmed",
                entity_id=job.id,
                payload={"criteria": criteria},
            )
        )
        return job

    def add_candidate(self, job_id: str, payload: CandidateCreate) -> CandidateRecord:
        job = self.repository.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        parsed = self.parser.parse_text(payload.resume_text)
        return self._ingest_candidate(job, payload, parsed, self.pii_guard.mask(parsed.raw_text))

    def add_candidate_from_upload(
        self,
        job_id: str,
        candidate_name: str,
        filename: str,
        file_bytes: bytes,
        github_url: str | None = None,
        portfolio_url: str | None = None,
    ) -> CandidateRecord:
        job = self.repository.get_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
        saved_path = self._save_upload(filename, file_bytes, job_id=job_id)
        parsed = self.parser.parse_file(saved_path)
        payload = CandidateCreate(
            name=candidate_name,
            resume_text=parsed.raw_text,
            github_url=github_url,
            portfolio_url=portfolio_url,
            source_filename=filename,
        )
        return self._ingest_candidate(job, payload, parsed, self.pii_guard.mask(parsed.raw_text))

    def _ingest_candidate(
        self,
        job: JobRecord,
        payload: CandidateCreate,
        parsed: ParsedResume,
        masking: MaskingResult,
    ) -> CandidateRecord:
        if not masking.safe_for_llm:
            self.repository.insert_audit_log(
                AuditLogRecord(
                    job_id=job.id,
                    event_type="masking_blocked",
                    entity_id=job.id,
                    payload={"candidate_name": payload.name, "reasons": masking.failure_reasons},
                )
            )
            raise ValueError("PII gate blocked the candidate payload.")

        candidate = CandidateRecord(
            job_id=job.id,
            name=payload.name,
            resume_text=parsed.raw_text,
            masked_resume_text=masking.masked_text,
            github_url=payload.github_url or parsed.github_url,
            portfolio_url=payload.portfolio_url,
            source_filename=payload.source_filename,
            extracted_urls=parsed.extracted_urls,
            parsed_profile=parsed.profile,
        )
        github_result = self.github_client.fetch_profile(candidate.github_url)
        candidate.github_status = github_result.status
        candidate.github_failure_reason = github_result.failure_reason
        candidate.github_profile = github_result.profile
        self.repository.insert_candidate(candidate)
        self.repository.insert_token_mappings(
            [
                TokenMappingRecord(
                    job_id=job.id,
                    candidate_id=candidate.id,
                    token=token.token,
                    original=token.original,
                    kind=token.kind,
                )
                for token in masking.tokens
            ]
        )
        self.repository.insert_audit_log(
            AuditLogRecord(
                job_id=job.id,
                event_type="candidate_ingested",
                entity_id=candidate.id,
                payload={
                    "job_id": job.id,
                    "masked_token_count": len(masking.tokens),
                    "safe_for_llm": masking.safe_for_llm,
                    "source_filename": payload.source_filename,
                    "github_url": payload.github_url or parsed.github_url,
                    "extracted_url_count": len(parsed.extracted_urls),
                    "github_status": github_result.status,
                    "github_failure_reason": github_result.failure_reason,
                },
            )
        )
        if github_result.status != "skipped":
            self.repository.insert_audit_log(
                AuditLogRecord(
                    job_id=job.id,
                    event_type="github_fetch_completed" if github_result.status == "fetched" else "github_fetch_failed",
                    entity_id=candidate.id,
                    payload={
                        "github_url": candidate.github_url,
                        "github_status": github_result.status,
                        "github_failure_reason": github_result.failure_reason,
                        "recent_repo_count": len(github_result.profile.recent_repos) if github_result.profile else 0,
                    },
                )
            )

        evaluation = self._evaluate_candidate(job, candidate)
        self.repository.insert_evaluation(evaluation)
        self.repository.insert_audit_log(
            AuditLogRecord(
                job_id=job.id,
                event_type="candidate_evaluated",
                entity_id=candidate.id,
                payload={
                    "job_id": job.id,
                    "jd_score": evaluation.jd_score,
                    "alignment_score": evaluation.alignment_score,
                },
            )
        )
        return candidate

    def _build_preview(self, parsed: ParsedResume, masking: MaskingResult, source_filename: str | None = None) -> dict:
        return {
            "raw_text": parsed.raw_text,
            "masked_text": masking.masked_text,
            "safe_for_llm": masking.safe_for_llm,
            "failure_reasons": masking.failure_reasons,
            "tokens": [item.model_dump() for item in masking.tokens],
            "profile": parsed.profile.model_dump(),
            "extracted_urls": parsed.extracted_urls,
            "github_url": parsed.github_url,
            "source_filename": source_filename,
        }

    def _save_upload(self, filename: str, file_bytes: bytes, job_id: str | None = None) -> Path:
        target_dir = self.settings.uploads_dir / (job_id or "_preview")
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        target_path.write_bytes(file_bytes)
        return target_path

    def _suggest_criteria(self, jd_text: str) -> list[Criterion]:
        try:
            if isinstance(self.evaluator, UpstageEvaluator):
                self.evaluator.set_audit_context(
                    {
                        "job_title": jd_text[:80],
                        "entity_scope": "job_criteria",
                    }
                )
            return self.evaluator.suggest_criteria(jd_text)
        except Exception as exc:  # noqa: BLE001
            if not self.settings.fallback_to_mock_on_llm_error or self.evaluator is self.mock_evaluator:
                raise
            return self.mock_evaluator.suggest_criteria(jd_text)
        finally:
            if isinstance(self.evaluator, UpstageEvaluator):
                self.evaluator.clear_audit_context()

    def _evaluate_candidate(self, job: JobRecord, candidate: CandidateRecord):
        try:
            if isinstance(self.evaluator, UpstageEvaluator):
                self.evaluator.set_audit_context(
                    {
                        "job_id": job.id,
                        "candidate_id": candidate.id,
                        "entity_scope": "candidate_evaluation",
                    }
                )
            return self.evaluator.evaluate_candidate(job, candidate)
        except Exception as exc:  # noqa: BLE001
            self.repository.insert_audit_log(
                AuditLogRecord(
                    job_id=job.id,
                    event_type="llm_fallback_used",
                    entity_id=candidate.id,
                    payload={
                        "mode": self.settings.evaluator_mode,
                        "error": str(exc),
                    },
                )
            )
            if not self.settings.fallback_to_mock_on_llm_error or self.evaluator is self.mock_evaluator:
                raise
            return self.mock_evaluator.evaluate_candidate(job, candidate)
        finally:
            if isinstance(self.evaluator, UpstageEvaluator):
                self.evaluator.clear_audit_context()

    def _handle_llm_audit_event(self, event_type: str, payload: dict) -> None:
        self.repository.insert_audit_log(
            AuditLogRecord(
                job_id=payload.get("job_id"),
                event_type=event_type,
                entity_id=payload.get("candidate_id") or payload.get("job_id") or payload.get("job_title", "unknown"),
                payload=payload,
            )
        )
