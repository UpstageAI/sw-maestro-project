"""AI 면접 코치 Orchestration API.

프론트엔드는 시간이 오래 걸리는 작업(문서 인덱싱, 질문 생성, 답변 평가,
리포트 생성)을 요청한 뒤 /api/jobs/{job_id}를 polling하여 로딩바와 현재 작업
메시지를 표시한다.
"""

from __future__ import annotations

import os
import shutil
import traceback
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import AnswerRequest, JobAcceptedResponse, JobResponse, ReportRequest
from api.serializers import (
    evaluation_to_dict,
    question_to_dict,
    report_to_dict,
    session_to_summary,
)
from api.store import store
from core.question_generator import generate_question
from core.report_generator import generate_report
from models.types import Question
from orchestrator import end_session, process_answer, start_session

APP_TITLE = "AI Interview Coach Orchestration API"
RUNTIME_DIR = Path(os.getenv("COACH_RUNTIME_DIR", Path(__file__).resolve().parent.parent / ".runtime"))
UPLOAD_DIR = RUNTIME_DIR / "uploads"

app = FastAPI(title=APP_TITLE, version="0.1.0")

# Next.js 로컬 개발 기본 포트 허용. 운영에서는 CORS_ALLOW_ORIGINS를 명시하세요.
_origins = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in _origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────
def _job_url(job_id: str) -> str:
    return f"/api/jobs/{job_id}"


def _ensure_pdf(file: UploadFile) -> None:
    filename = file.filename or ""
    content_type = file.content_type or ""
    if not filename.lower().endswith(".pdf") and content_type != "application/pdf":
        raise HTTPException(status_code=400, detail=f"PDF 파일만 업로드할 수 있습니다: {filename}")


async def _save_uploads(session_id: str, files: list[UploadFile]) -> list[str]:
    if not files:
        raise HTTPException(status_code=400, detail="최소 1개 이상의 PDF가 필요합니다.")

    target_dir = UPLOAD_DIR / session_id
    target_dir.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for idx, file in enumerate(files, start=1):
        _ensure_pdf(file)
        safe_name = Path(file.filename or f"document_{idx}.pdf").name
        path = target_dir / f"{idx:02d}_{safe_name}"
        with path.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                out.write(chunk)
        paths.append(str(path))
    return paths


def _assert_session_ready(session_id: str):
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    if session.state is None:
        raise HTTPException(status_code=409, detail="세션 초기화가 아직 완료되지 않았습니다.")
    return session


def _assert_not_busy(session_id: str) -> None:
    session = store.get_session(session_id)
    if session and session.busy_job_id:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "이미 진행 중인 작업이 있습니다.",
                "busy_job_id": session.busy_job_id,
                "status_url": _job_url(session.busy_job_id),
            },
        )


# ─────────────────────────────────────────────
# 백그라운드 작업
# ─────────────────────────────────────────────
def _run_start_session_job(
    job_id: str,
    session_id: str,
    pdf_paths: list[str],
    job_description: str,
    company_name: str,
    company_culture: str,
) -> None:
    try:
        store.update_job(
            job_id,
            status="running",
            step="indexing_documents",
            progress=10,
            message="PDF 문서를 파싱하고 ChromaDB에 인덱싱하는 중입니다.",
        )
        state = start_session(
            pdf_paths=pdf_paths,
            job_description=job_description,
            company_name=company_name,
            company_culture=company_culture,
        )

        store.update_job(
            job_id,
            step="generating_first_question",
            progress=80,
            message="지원 직무와 이력 컨텍스트를 바탕으로 첫 질문을 생성하는 중입니다.",
        )
        first_question = generate_question(state, is_followup=False)
        store.set_session_state(session_id, state=state, current_question=first_question)

        result = {
            "session": session_to_summary(session_id, state, first_question, None),
            "question": question_to_dict(first_question),
        }
        store.finish_job(job_id, result)
    except Exception as exc:  # noqa: BLE001 - API 작업 실패를 job 상태로 전달
        store.fail_job(job_id, f"{exc}\n{traceback.format_exc()}")


def _run_answer_job(job_id: str, session_id: str, question: Question, answer: str) -> None:
    try:
        session = store.get_session(session_id)
        if session is None or session.state is None:
            raise RuntimeError("세션 상태가 없습니다.")

        store.update_job(
            job_id,
            status="running",
            step="evaluating_answer",
            progress=20,
            message="답변을 STAR·구체성·직무 관련성·일관성 기준으로 평가하는 중입니다.",
        )
        action_result = process_answer(session.state, question, answer)

        action = action_result.get("action")
        payload: dict[str, object] = {"action": action}

        if action == "retry":
            payload["message"] = "답변이 너무 짧습니다. 50자 이상으로 더 구체적으로 답해주세요."
            payload["question"] = question_to_dict(question)
            store.finish_job(job_id, payload)
            return

        latest_eval = session.state.history[-1][1] if session.state.history else None
        if latest_eval is not None:
            payload["evaluation"] = evaluation_to_dict(latest_eval)

        if action in {"followup", "next_question", "can_report"}:
            next_question = action_result["question"]
            store.update_job(
                job_id,
                step="generating_next_question",
                progress=80,
                message="다음 질문을 준비하는 중입니다.",
            )
            store.set_session_state(session_id, state=session.state, current_question=next_question)
            payload["question"] = question_to_dict(next_question)
            payload["can_report"] = action == "can_report"

        elif action == "force_end":
            report = action_result["report"]
            store.set_session_state(session_id, state=session.state, last_report=report)
            payload["report"] = report_to_dict(report)

        payload["session"] = session_to_summary(
            session_id,
            session.state,
            store.get_session(session_id).current_question if store.get_session(session_id) else None,
            None,
        )
        store.finish_job(job_id, payload)
    except Exception as exc:  # noqa: BLE001
        store.fail_job(job_id, f"{exc}\n{traceback.format_exc()}")


def _run_report_job(job_id: str, session_id: str, force: bool) -> None:
    try:
        session = store.get_session(session_id)
        if session is None or session.state is None:
            raise RuntimeError("세션 상태가 없습니다.")
        if not session.state.history:
            raise RuntimeError("평가된 답변이 없어 리포트를 생성할 수 없습니다.")

        store.update_job(
            job_id,
            status="running",
            step="generating_report",
            progress=30,
            message="누적 평가 점수와 약점 태그를 집계해 리포트를 생성하는 중입니다.",
        )

        if force:
            # 사용자가 중간에 그만두고 싶을 때 현재 history만으로 리포트를 생성한다.
            session.state.is_active = False
            report = generate_report(session.state.history)
        else:
            report = end_session(session.state)

        store.set_session_state(session_id, state=session.state, last_report=report)
        result = {
            "session": session_to_summary(session_id, session.state, session.current_question, None),
            "report": report_to_dict(report),
        }
        store.finish_job(job_id, result)
    except Exception as exc:  # noqa: BLE001
        store.fail_job(job_id, f"{exc}\n{traceback.format_exc()}")


# ─────────────────────────────────────────────
# API 엔드포인트
# ─────────────────────────────────────────────
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sessions", response_model=JobAcceptedResponse, status_code=202)
async def create_session(
    background_tasks: BackgroundTasks,
    files: Annotated[list[UploadFile], File(description="자소서/이력서 PDF 파일들")],
    job_description: Annotated[str, Form(description="채용공고 전문")],
    company_name: Annotated[str, Form(description="회사명. 비우면 Tavily 검색 생략")] = "",
    company_culture: Annotated[str, Form(description="사용자가 직접 보강한 회사 문화/인재상")] = "",
) -> JobAcceptedResponse:
    session = store.create_session_record()
    pdf_paths = await _save_uploads(session.session_id, files)

    job = store.create_job("start_session", session_id=session.session_id)
    background_tasks.add_task(
        _run_start_session_job,
        job.job_id,
        session.session_id,
        pdf_paths,
        job_description,
        company_name,
        company_culture,
    )
    return JobAcceptedResponse(
        job_id=job.job_id,
        session_id=session.session_id,
        status_url=_job_url(job.job_id),
        message="세션 생성 작업을 시작했습니다. status_url을 polling하세요.",
    )


@app.get("/api/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> dict:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return job.to_dict()


@app.get("/api/sessions/{session_id}")
def get_session(session_id: str) -> dict:
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    return session_to_summary(session_id, session.state, session.current_question, session.busy_job_id)


@app.get("/api/sessions/{session_id}/history")
def get_history(session_id: str) -> dict:
    session = _assert_session_ready(session_id)
    history = [
        {
            "question": question_to_dict(question),
            "evaluation": evaluation_to_dict(result),
        }
        for question, result in session.state.history
    ]
    return {"session_id": session_id, "count": len(history), "history": history}


@app.post("/api/sessions/{session_id}/answers", response_model=JobAcceptedResponse, status_code=202)
def submit_answer(session_id: str, request: AnswerRequest, background_tasks: BackgroundTasks) -> JobAcceptedResponse:
    session = _assert_session_ready(session_id)
    _assert_not_busy(session_id)
    if session.current_question is None:
        raise HTTPException(status_code=409, detail="현재 답변할 질문이 없습니다.")
    if request.question_id and request.question_id != session.current_question.id:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "현재 질문 id와 요청 question_id가 다릅니다.",
                "current_question": question_to_dict(session.current_question),
            },
        )

    job = store.create_job("process_answer", session_id=session_id)
    background_tasks.add_task(_run_answer_job, job.job_id, session_id, session.current_question, request.answer)
    return JobAcceptedResponse(
        job_id=job.job_id,
        session_id=session_id,
        status_url=_job_url(job.job_id),
        message="답변 평가 작업을 시작했습니다. status_url을 polling하세요.",
    )


@app.post("/api/sessions/{session_id}/report", response_model=JobAcceptedResponse, status_code=202)
def create_report(session_id: str, request: ReportRequest, background_tasks: BackgroundTasks) -> JobAcceptedResponse:
    session = _assert_session_ready(session_id)
    _assert_not_busy(session_id)

    if not request.force and session.state.bundle_count < session.state.min_bundles_for_report:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "아직 리포트 생성 최소 묶음 수를 만족하지 않았습니다. 중간 리포트가 필요하면 force=true로 요청하세요.",
                "bundle_count": session.state.bundle_count,
                "min_bundles_for_report": session.state.min_bundles_for_report,
            },
        )

    job = store.create_job("generate_report", session_id=session_id)
    background_tasks.add_task(_run_report_job, job.job_id, session_id, request.force)
    return JobAcceptedResponse(
        job_id=job.job_id,
        session_id=session_id,
        status_url=_job_url(job.job_id),
        message="리포트 생성 작업을 시작했습니다. status_url을 polling하세요.",
    )


@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    # 간단한 데모용 정리. 실제 서비스에서는 파일/Chroma collection 정리 정책을 별도 설계하세요.
    session = store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")
    upload_path = UPLOAD_DIR / session_id
    if upload_path.exists():
        shutil.rmtree(upload_path, ignore_errors=True)
    store.sessions.pop(session_id, None)
    return {"status": "deleted", "session_id": session_id}
