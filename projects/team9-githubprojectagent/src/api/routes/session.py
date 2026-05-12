"""Session 기반 API. 모든 상태/진행은 세션 객체에. 프론트는 폴링."""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src import config
from src.services import orchestrator, pdf_publisher
from src.services.session_manager import State, manager
from src.templates import get as get_template
from src.templates import list_all

log = logging.getLogger(__name__)
router = APIRouter()


class CreateSessionRequest(BaseModel):
    repo_url: str
    pat: Optional[str] = None
    notion_token: Optional[str] = None
    notion_parent_page_id: Optional[str] = None
    user_attached_info: Optional[str] = None


class CreateSessionResponse(BaseModel):
    session_id: str


@router.post("/api/session", response_model=CreateSessionResponse)
def create(req: CreateSessionRequest) -> CreateSessionResponse:
    if not req.repo_url.strip():
        raise HTTPException(status_code=400, detail="repo_url 필수")
    s = manager().create(
        repo_url=req.repo_url.strip(),
        pat=req.pat or None,
        notion_token=req.notion_token or None,
        notion_parent_page_id=req.notion_parent_page_id or None,
        user_attached_info=req.user_attached_info or None,
    )
    orchestrator.start_session(s)
    return CreateSessionResponse(session_id=s.id)


@router.get("/api/session/{sid}")
def get_status(sid: str) -> dict:
    import time as _time
    s = manager().get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    now = _time.time()
    return {
        "id": s.id,
        "state": s.state,
        "state_age_sec": round(now - s.last_state_change, 1),
        "elapsed_sec": round(now - s.created_at, 1),
        "log": s.log[-50:],
        "questions": s.questions,
        "answers": s.answers,
        "draft": {
            "problem": s.draft.problem.model_dump() if s.draft.problem else None,
            "status": s.draft.status.model_dump() if s.draft.status else None,
            "cause": s.draft.cause.model_dump() if s.draft.cause else None,
            "result": s.draft.result.model_dump() if s.draft.result else None,
            "architecture": s.draft.architecture,
            "dataflow": s.draft.dataflow,
            "merged": s.draft.merged,
        },
        "verdict": s.verdict.model_dump() if s.verdict else None,
        "history": [v.model_dump() for v in s.history],
        "cost": s.cost_report,
        "error": s.error,
        "publish_result": s.publish_result,
        "repo_full_name": s.ctx.full_name if s.ctx else None,
        "repo_url": s.repo_url,
    }


@router.post("/api/session/{sid}/abort")
def abort_session(sid: str) -> dict:
    """사용자 abort. 다음 노드 진입 시 즉시 RuntimeError 발생 → 그래프 종료.
    이미 실행 중인 LLM 호출은 끝까지 실행 후 abort 됨 (Python thread limitation)."""
    s = manager().get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    s.request_abort("user requested abort")
    return {"ok": True, "state": s.state}


class AnswersRequest(BaseModel):
    answers: list[str]


@router.post("/api/session/{sid}/answers")
def submit_answers(sid: str, req: AnswersRequest) -> dict:
    s = manager().get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    if s.state != State.INTERVIEWING:
        raise HTTPException(status_code=400, detail=f"state={s.state}, INTERVIEWING 아님")
    if len(req.answers) != len(s.questions):
        raise HTTPException(
            status_code=400,
            detail=f"answers 개수 불일치: {len(req.answers)} vs {len(s.questions)}",
        )
    orchestrator.submit_answers(s, req.answers)
    return {"ok": True}


@router.get("/api/session/{sid}/templates")
def get_templates(sid: str) -> dict:
    s = manager().get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    if s.state not in (State.READY_FOR_TEMPLATE, State.PUBLISHING, State.DONE):
        raise HTTPException(status_code=400, detail=f"state={s.state}, 템플릿 단계 아님")
    out = []
    for t in list_all():
        preview = t.preview_md(s.draft, s.ctx) if t.preview_md else "(미리보기 없음)"
        out.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "preview_md": preview,
        })
    return {"templates": out}


class PublishRequest(BaseModel):
    template_id: str
    notion_token: Optional[str] = None
    notion_parent_page_id: Optional[str] = None


@router.post("/api/session/{sid}/publish")
def publish(sid: str, req: PublishRequest) -> dict:
    s = manager().get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    if s.state != State.READY_FOR_TEMPLATE:
        raise HTTPException(status_code=400, detail=f"state={s.state}, 발행 단계 아님")
    if req.notion_token:
        s.notion_token = req.notion_token
    if req.notion_parent_page_id:
        s.notion_parent_page_id = req.notion_parent_page_id
    orchestrator.publish_session(s, req.template_id)
    return {"ok": True}


# ------------------------------------------------------------
# PDF 발행 — Notion 대안. 템플릿의 preview_md → HTML → PDF
# ------------------------------------------------------------

class ExportPdfRequest(BaseModel):
    template_id: str


@router.post("/api/session/{sid}/export-pdf")
def export_pdf(sid: str, req: ExportPdfRequest) -> dict:
    s = manager().get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    if s.state not in (State.READY_FOR_TEMPLATE, State.PUBLISHING, State.DONE):
        raise HTTPException(status_code=400, detail=f"state={s.state}, 발행 단계 아님")
    try:
        template = get_template(req.template_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        path = pdf_publisher.render_pdf(s.draft, s.ctx, template)
    except Exception as e:
        log.exception("PDF 생성 실패")
        return {"success": False, "error": str(e), "filename": None, "download_url": None}

    return {
        "success": True,
        "error": None,
        "filename": path.name,
        "download_url": f"/api/session/{sid}/download/{path.name}",
        "absolute_path": str(path),
    }


@router.get("/api/session/{sid}/download/{filename}")
def download_artifact(sid: str, filename: str):
    s = manager().get(sid)
    if not s:
        raise HTTPException(status_code=404, detail="session not found")

    # path traversal 방어 — 파일명만 허용
    safe_name = Path(filename).name
    file_path = config.OUTPUT_DIR / safe_name
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="file not found")

    media_type = "application/pdf" if safe_name.lower().endswith(".pdf") else "text/markdown"
    return FileResponse(file_path, media_type=media_type, filename=safe_name)
