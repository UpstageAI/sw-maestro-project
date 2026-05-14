from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.models import CandidateCreate, Criterion, JobCreate
from app.services.pipeline import HireProofPipeline

router = APIRouter()
pipeline = HireProofPipeline()


class CriteriaConfirmRequest(BaseModel):
    criteria: list[Criterion]


class CandidatePreviewRequest(BaseModel):
    resume_text: str


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/jobs")
def create_job(payload: JobCreate) -> dict:
    job = pipeline.create_job(payload)
    return job.model_dump(mode="json")


@router.get("/jobs")
def list_jobs() -> list[dict]:
    return [job.model_dump(mode="json") for job in pipeline.repository.list_jobs()]


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict:
    job = pipeline.repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job": job.model_dump(mode="json"),
        "candidates": [candidate.model_dump(mode="json") for candidate in pipeline.repository.list_candidates(job_id)],
        "evaluations": [result.model_dump(mode="json") for result in pipeline.repository.list_evaluations(job_id)],
    }


@router.post("/jobs/{job_id}/criteria/confirm")
def confirm_criteria(job_id: str, payload: CriteriaConfirmRequest) -> dict:
    try:
        job = pipeline.confirm_criteria(job_id, [item.model_dump() for item in payload.criteria])
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return job.model_dump(mode="json")


@router.post("/jobs/{job_id}/candidates")
def add_candidate(job_id: str, payload: CandidateCreate) -> dict:
    try:
        candidate = pipeline.add_candidate(job_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return candidate.model_dump(mode="json")


@router.post("/jobs/{job_id}/candidates/preview")
def preview_candidate(job_id: str, payload: CandidatePreviewRequest) -> dict:
    job = pipeline.repository.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return pipeline.preview_candidate_text(payload.resume_text)


@router.get("/jobs/{job_id}/audit-logs")
def list_audit_logs(job_id: str) -> list[dict]:
    return [record.model_dump(mode="json") for record in pipeline.repository.list_audit_logs(job_id=job_id)]


@router.get("/candidates/{candidate_id}/token-mappings")
def list_token_mappings(candidate_id: str) -> list[dict]:
    return [record.model_dump(mode="json") for record in pipeline.repository.list_token_mappings(candidate_id)]
