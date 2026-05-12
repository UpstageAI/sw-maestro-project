"""Session endpoints.

Three flows:
  - POST /sessions/seed                  — generate the first interview question
                                           (one Solar call) + create a new
                                           session row (or append a seed turn
                                           to an existing one).
  - POST /sessions                       — submit answer, run LangGraph workflow
                                           up to the human_review interrupt and
                                           return the first awaiting_feedback
                                           snapshot. Persists the answer + the
                                           pre-allocated next turn id.
  - POST /sessions/{thread_id}/feedback  — inject UserFeedback into the existing
                                           thread, resume the graph, idempotent
                                           record_answer overwrite.

History endpoints:
  - GET    /sessions                     — list[SessionSummary]
  - GET    /sessions/{session_id}        — SessionDetail (404 if missing)
  - DELETE /sessions/{session_id}        — cascade delete
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any, AsyncIterator, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.schemas.session_history import (
    SessionDetail,
    SessionSummary,
    detail_from_row,
    summary_from_row,
)
from app.auth.deps import current_user
from app.graph.nodes import generate_seed_question
from app.graph.schema import (
    GraphState,
    SeedRequest,
    SeedResponse,
    SessionResult,
    SubmitRequest,
    UserFeedback,
)
from app.graph.workflow import get_graph
from app.log_format import stage
from app.services import session_store

log = logging.getLogger(__name__)

router = APIRouter()


# ---------- helpers ----------

def _score_to_int(score: float | None) -> int | None:
    if score is None:
        return None
    return max(0, min(100, round(score * 100)))


def _seed_title(req: SeedRequest, seed_q: str) -> str:
    if req.domains:
        return req.domains[0]
    if req.keywords:
        return req.keywords[0]
    return seed_q[:80]




# ---------- seed ----------

@router.post(
    "/sessions/seed",
    response_model=SeedResponse,
    response_model_by_alias=True,
)
async def create_seed(
    req: SeedRequest,
    user: dict = Depends(current_user),
) -> SeedResponse:
    stage(
        "🌱 [SEED] request",
        user=user["email"],
        domains=req.domains,
        keywords=req.keywords,
        materials=len(req.material_ids or []),
        existing_session=req.session_id,
    )
    if not req.domains and not req.keywords:
        raise HTTPException(
            status_code=400,
            detail="At least one of `domains` or `keywords` is required.",
        )
    try:
        seed = await generate_seed_question(req)
    except Exception as e:
        stage("✗ [SEED] generation failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"Seed generation failed: {e}") from e
    stage(
        "✓ [SEED] generated",
        domain=seed.domain_label,
        question=seed.question,
        citations=len(seed.citations),
    )

    citations_payload = [c.model_dump() for c in seed.citations]

    if req.session_id:
        # Append a seed turn to an existing session (e.g. user accepted the
        # last answer and wants a fresh question in the same chat).
        #
        # First drop any trailing unanswered turn — the previous /sessions
        # submit pre-allocates the BE's first follow-up candidate as a turn
        # so FE can submit against a known id, but when FE pivots here to a
        # new seed (uncertain/incorrect answer → domain switch) the candidate
        # is abandoned. Without this cleanup it would surface in the analysis
        # history as a question the user never saw.
        try:
            await asyncio.to_thread(
                session_store.delete_trailing_unanswered_turn,
                req.session_id,
            )
        except Exception as e:
            log.warning("orphan turn cleanup failed for %s: %s", req.session_id, e)

        try:
            turn_id = await asyncio.to_thread(
                session_store.append_turn,
                session_id=req.session_id,
                question=seed.question,
                domain_label=seed.domain_label,
                source="seed",
                citations=citations_payload,
            )
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Session not found or append failed: {e}",
            ) from e
        seed.session_id = req.session_id
        seed.turn_id = turn_id
        return seed

    try:
        sid, tid = await asyncio.to_thread(
            session_store.create_session,
            track=req.track,
            title=_seed_title(req, seed.question),
            domains=req.domains,
            keywords=req.keywords,
            material_ids=req.material_ids,
            seed_question=seed.question,
            seed_domain_label=seed.domain_label,
            seed_citations=citations_payload,
            user_id=user["id"],
        )
    except Exception as e:
        log.exception("create_session failed")
        raise HTTPException(status_code=500, detail=f"Session create failed: {e}") from e

    seed.session_id = sid
    seed.turn_id = tid
    return seed


# ---------- session result builder ----------

async def _build_session_result(
    thread_id: str,
    config: dict[str, Any],
    status: Literal["awaiting_feedback", "final"],
) -> SessionResult:
    """Read the latest checkpointed state for the thread and serialize it."""
    snapshot = await get_graph().aget_state(config)
    state = snapshot.values  # dict-like, mirrors GraphState

    analysis = state.get("analysis")
    follow_ups = state.get("follow_ups")
    if analysis is None or follow_ups is None:
        raise HTTPException(
            status_code=502,
            detail="Workflow returned incomplete state",
        )

    return SessionResult(
        question=state["question"],
        answer=state["answer"],
        notes=analysis.notes,
        follow_ups=follow_ups.follow_ups,
        answer_quality=analysis.answer_quality,
        explanation=analysis.explanation,
        question_intent=analysis.question_intent,
        retrieved_context=state.get("retrieved_context", []),
        evaluation=state.get("evaluation"),
        thread_id=thread_id,
        status=status,
    )


# ---------- submit answer ----------

@router.post(
    "/sessions",
    response_model=SessionResult,
    response_model_by_alias=True,
)
async def create_session(
    req: SubmitRequest,
    user: dict = Depends(current_user),
) -> SessionResult:
    thread_id = f"th_{uuid.uuid4().hex[:12]}"
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}

    initial: GraphState = {
        "question": req.question,
        "answer": req.answer,
        "domains": req.domains,
        "keywords": req.keywords,
        "material_ids": req.material_ids,
        "retrieved_context": [],
        "iteration_count": 0,
        "feedback_count": 0,
    }

    try:
        await get_graph().ainvoke(initial, config=config)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Workflow failed: {e}") from e

    result = await _build_session_result(thread_id, config, status="awaiting_feedback")

    # ---------- DB write side-effects ----------
    # Backwards-compat: if FE didn't send sessionId/turnId, allocate a fresh
    # session+turn now. Title falls back to the question text.
    sid = req.session_id or ""
    tid = req.turn_id or ""
    if not sid or not tid:
        try:
            sid, tid = await asyncio.to_thread(
                session_store.create_session,
                track="stack" if req.keywords else "cs",
                title=(req.domains[0] if req.domains
                       else (req.keywords[0] if req.keywords else req.question[:80])),
                domains=req.domains,
                keywords=req.keywords,
                material_ids=req.material_ids,
                seed_question=req.question,
                seed_domain_label=(req.domains[0] if req.domains else ""),
                seed_citations=[],
                user_id=user["id"],
            )
        except Exception as e:
            log.exception("graceful create_session failed")
            raise HTTPException(status_code=500, detail=f"Session create failed: {e}") from e

    # Idempotent overwrite of the turn that holds this question.
    try:
        await asyncio.to_thread(
            session_store.record_answer,
            session_id=sid,
            turn_id=tid,
            answer=req.answer,
            notes=[n.model_dump() for n in result.notes],
            follow_ups=[f.model_dump() for f in result.follow_ups],
            retrieved_context=[c.model_dump() for c in result.retrieved_context],
            citations=[],
            answer_quality=result.answer_quality,
            explanation=result.explanation,
            question_intent=result.question_intent,
            score=_score_to_int(
                result.evaluation.score if result.evaluation else None,
            ),
            thread_id=thread_id,
        )
    except Exception as e:
        log.exception("record_answer failed")
        raise HTTPException(status_code=500, detail=f"Persist failed: {e}") from e

    # Pre-allocate the next follow-up turn so the FE has a turn_id ready when
    # the user answers it. Only when there's at least one follow-up to answer.
    next_turn_id: str | None = None
    if result.follow_ups:
        next_q = result.follow_ups[0]
        try:
            next_turn_id = await asyncio.to_thread(
                session_store.append_turn,
                session_id=sid,
                question=next_q.text,
                domain_label=next_q.domain_label,
                level=next_q.level,
                source="follow_up",
                rationale=next_q.rationale,
                citations=[c.model_dump() for c in next_q.citations],
            )
        except Exception as e:
            log.warning("pre-allocate next turn failed: %s", e)

    result.session_id = sid
    result.next_turn_id = next_turn_id
    return result


# ---------- streaming submit ----------

# Stage labels for the SSE "stage" events. Mapped to user-facing copy in
# Korean so the FE can show progress text without a translation table.
_STAGE_LABELS: dict[str, str] = {
    "analyzer": "답변을 분석하고 있어요…",
    "term_extractor": "핵심 용어를 정리하는 중…",
    "knowledge_retriever": "참고 자료를 검색하는 중…",
    "question_generator": "다음 꼬리질문을 생성하는 중…",
    "evaluator": "질문 품질을 검토하는 중…",
}


def _sse(event: str, data: dict[str, Any]) -> bytes:
    """Serialize an SSE event. ensure_ascii=False so Korean stays UTF-8."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode(
        "utf-8"
    )


async def _emit_text_chunks(
    text: str, *, chunk_size: int = 6, delay_s: float = 0.025
) -> AsyncIterator[str]:
    """Slice `text` into chunks of `chunk_size` chars and yield with a small
    delay so the FE can render a typing animation. The actual LLM has already
    finished by the time we call this; this is fake-streaming for UX, not a
    latency reduction. Real-streaming variant is future work."""
    if not text:
        return
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
        await asyncio.sleep(delay_s)


@router.post("/sessions/stream")
async def stream_session(
    req: SubmitRequest,
    user: dict = Depends(current_user),
) -> StreamingResponse:
    """SSE variant of POST /sessions.

    Wire format (Server-Sent Events, one event per `event:`/`data:` block,
    blocks separated by a blank line):

      - `started`            — first event, contains `thread_id`
      - `stage`               — emitted as each LangGraph node completes;
                                FE updates the loading status text
      - `meta`                — emitted right after the analyzer finishes;
                                gives the FE everything needed to populate the
                                analysis sidebar (notes, intent, quality, score)
      - `explanation_start`   — only when answer_quality is uncertain/incorrect
      - `explanation_delta`   — repeated, `{text: "..."}` chunks of the
                                teaching answer
      - `explanation_end`     — explanation streaming finished
      - `question_start`      — about to stream the next interview question
      - `question_delta`      — repeated, `{text: "..."}` chunks of the
                                follow-up question text
      - `question_end`        — final follow-up metadata (level, rationale, ...)
      - `done`                — full SessionResult-equivalent payload + DB ids
      - `error`               — fatal error; FE should fall back to /sessions

    Persistence and DB writes mirror /sessions exactly (same record_answer +
    pre-allocate next turn flow), so callers can swap one for the other.
    """
    thread_id = f"th_{uuid.uuid4().hex[:12]}"
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    stage(
        "📥 [SUBMIT] /sessions/stream",
        user=user["email"],
        thread=thread_id,
        question=req.question,
        answer=req.answer,
        materials=len(req.material_ids or []),
    )

    initial: GraphState = {
        "question": req.question,
        "answer": req.answer,
        "domains": req.domains,
        "keywords": req.keywords,
        "material_ids": req.material_ids,
        "retrieved_context": [],
        "iteration_count": 0,
        "feedback_count": 0,
    }

    async def event_stream() -> AsyncIterator[bytes]:
        emitted_stages: set[str] = set()
        try:
            stage("📤 [SSE] started", thread=thread_id)
            yield _sse("started", {"thread_id": thread_id})

            # Drive the graph one node at a time so we can surface progress.
            # graph.astream yields {node_name: state_update} dicts.
            try:
                async for event in get_graph().astream(initial, config=config):
                    for node_name in event.keys():
                        if node_name in _STAGE_LABELS and node_name not in emitted_stages:
                            emitted_stages.add(node_name)
                            yield _sse(
                                "stage",
                                {"step": node_name, "message": _STAGE_LABELS[node_name]},
                            )
            except Exception as e:
                log.exception("graph astream failed")
                yield _sse("error", {"message": f"분석 실패: {e}"})
                return

            # Pull the final accumulated state out of the checkpointer.
            try:
                result = await _build_session_result(
                    thread_id, config, status="awaiting_feedback"
                )
            except HTTPException as e:
                yield _sse("error", {"message": str(e.detail)})
                return

            # Persist (mirrors /sessions). Done before streaming the text so
            # the DB is consistent even if the client disconnects mid-stream.
            sid = req.session_id or ""
            tid = req.turn_id or ""
            if not sid or not tid:
                try:
                    sid, tid = await asyncio.to_thread(
                        session_store.create_session,
                        track="stack" if req.keywords else "cs",
                        title=(
                            req.domains[0]
                            if req.domains
                            else (req.keywords[0] if req.keywords else req.question[:80])
                        ),
                        domains=req.domains,
                        keywords=req.keywords,
                        material_ids=req.material_ids,
                        seed_question=req.question,
                        seed_domain_label=(req.domains[0] if req.domains else ""),
                        seed_citations=[],
                        user_id=user["id"],
                    )
                except Exception as e:
                    log.exception("graceful create_session failed")
                    yield _sse("error", {"message": f"세션 생성 실패: {e}"})
                    return

            score_int = _score_to_int(
                result.evaluation.score if result.evaluation else None
            )

            try:
                await asyncio.to_thread(
                    session_store.record_answer,
                    session_id=sid,
                    turn_id=tid,
                    answer=req.answer,
                    notes=[n.model_dump() for n in result.notes],
                    follow_ups=[f.model_dump() for f in result.follow_ups],
                    retrieved_context=[c.model_dump() for c in result.retrieved_context],
                    citations=[],
                    answer_quality=result.answer_quality,
                    explanation=result.explanation,
                    question_intent=result.question_intent,
                    score=score_int,
                    thread_id=thread_id,
                )
            except Exception as e:
                log.exception("record_answer failed")
                yield _sse("error", {"message": f"답변 저장 실패: {e}"})
                return

            # Meta event — FE populates the analysis sidebar immediately.
            yield _sse(
                "meta",
                {
                    "answer_quality": result.answer_quality,
                    "question_intent": result.question_intent,
                    "notes": [n.model_dump() for n in result.notes],
                    "retrieved_context": [c.model_dump() for c in result.retrieved_context],
                    "score": score_int,
                },
            )

            # Stream the teaching answer (only when the user said they didn't
            # know or got it wrong).
            if (
                result.answer_quality in ("uncertain", "incorrect")
                and result.explanation
            ):
                yield _sse("explanation_start", {})
                async for chunk in _emit_text_chunks(
                    result.explanation, chunk_size=6, delay_s=0.025
                ):
                    yield _sse("explanation_delta", {"text": chunk})
                yield _sse("explanation_end", {})

            # Pre-allocate the next turn's id (matches /sessions behavior so
            # the FE has a turn_id to submit against on the next answer).
            next_turn_id: str | None = None
            next_q = result.follow_ups[0] if result.follow_ups else None
            if next_q:
                try:
                    next_turn_id = await asyncio.to_thread(
                        session_store.append_turn,
                        session_id=sid,
                        question=next_q.text,
                        domain_label=next_q.domain_label,
                        level=next_q.level,
                        source="follow_up",
                        rationale=next_q.rationale,
                        citations=[c.model_dump() for c in next_q.citations],
                    )
                except Exception as e:
                    log.warning("pre-allocate next turn failed: %s", e)

                yield _sse("question_start", {})
                async for chunk in _emit_text_chunks(
                    next_q.text, chunk_size=6, delay_s=0.03
                ):
                    yield _sse("question_delta", {"text": chunk})
                yield _sse(
                    "question_end",
                    {
                        "level": next_q.level,
                        "rationale": next_q.rationale,
                        "domain_label": next_q.domain_label,
                        "citations": [c.model_dump() for c in next_q.citations],
                    },
                )

            stage(
                "📤 [SSE] done",
                thread=thread_id,
                session=sid,
                next_turn=next_turn_id,
                quality=result.answer_quality,
                score=score_int,
            )
            yield _sse(
                "done",
                {
                    "session_id": sid,
                    "turn_id": tid,
                    "next_turn_id": next_turn_id,
                    "thread_id": thread_id,
                    "answer_quality": result.answer_quality,
                    "explanation": result.explanation,
                    "question_intent": result.question_intent,
                    "score": score_int,
                    "notes": [n.model_dump() for n in result.notes],
                    "follow_ups": [f.model_dump() for f in result.follow_ups],
                    "retrieved_context": [c.model_dump() for c in result.retrieved_context],
                    "status": "awaiting_feedback",
                },
            )
        except asyncio.CancelledError:
            # Client disconnected; let the cancellation propagate so uvicorn
            # can clean up.
            raise
        except Exception as e:
            log.exception("stream_session unhandled error")
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # disable nginx buffering for SSE
        },
    )


# ---------- feedback ----------

@router.post(
    "/sessions/{thread_id}/feedback",
    response_model=SessionResult,
    response_model_by_alias=True,
)
async def submit_feedback(
    thread_id: str,
    fb: UserFeedback,
    user: dict = Depends(current_user),
) -> SessionResult:
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    graph = get_graph()

    # Ownership check when FE sent a session_id with the feedback. Orphan
    # sessions (user_id=None) remain accessible during the migration window
    # (Workstream C will tighten this).
    if fb.session_id:
        existing = await asyncio.to_thread(session_store.get_session, fb.session_id)
        if existing is not None:
            _ensure_session_access(existing, user["id"])

    try:
        snapshot = await graph.aget_state(config)
    except Exception as e:  # pragma: no cover — checkpointer-specific
        raise HTTPException(
            status_code=404,
            detail=f"Thread {thread_id} not found",
        ) from e
    if not snapshot.values:
        raise HTTPException(
            status_code=404,
            detail=f"Thread {thread_id} has no state",
        )

    try:
        await graph.aupdate_state(config, {"feedback": fb})
        await graph.ainvoke(None, config=config)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Resume failed: {e}") from e

    new_snapshot = await graph.aget_state(config)
    next_nodes = new_snapshot.next  # () means END, ("human_review",) means paused

    if fb.action == "accept" or not next_nodes:
        result = await _build_session_result(thread_id, config, status="final")
    else:
        result = await _build_session_result(thread_id, config, status="awaiting_feedback")

    # Idempotent overwrite when the FE sent sessionId/turnId — same turn row,
    # updated follow-ups/explanation/score after the regenerate.
    if fb.session_id and fb.turn_id:
        try:
            await asyncio.to_thread(
                session_store.record_answer,
                session_id=fb.session_id,
                turn_id=fb.turn_id,
                answer=result.answer,
                notes=[n.model_dump() for n in result.notes],
                follow_ups=[f.model_dump() for f in result.follow_ups],
                retrieved_context=[c.model_dump() for c in result.retrieved_context],
                citations=[],
                answer_quality=result.answer_quality,
                explanation=result.explanation,
                question_intent=result.question_intent,
                score=_score_to_int(
                    result.evaluation.score if result.evaluation else None,
                ),
                thread_id=thread_id,
            )
            result.session_id = fb.session_id
        except Exception as e:
            log.warning("feedback record_answer failed: %s", e)

    return result


# ---------- history ----------

@router.get(
    "/sessions",
    response_model=list[SessionSummary],
    response_model_by_alias=True,
)
async def list_sessions(
    user: dict = Depends(current_user),
) -> list[SessionSummary]:
    rows = await asyncio.to_thread(session_store.list_sessions, 50, user["id"])
    return [summary_from_row(r) for r in rows]


def _ensure_session_access(row: dict, user_id: str) -> None:
    """Raise 403 if the session is owned by a different user. Orphan sessions
    (user_id=None) remain accessible during the migration window — Workstream C
    will tighten this once legacy rows are claimed."""
    owner = row.get("user_id")
    if owner is not None and owner != user_id:
        raise HTTPException(status_code=403, detail="forbidden")


@router.get(
    "/sessions/{session_id}",
    response_model=SessionDetail,
    response_model_by_alias=True,
)
async def get_session(
    session_id: str,
    user: dict = Depends(current_user),
) -> SessionDetail:
    row = await asyncio.to_thread(session_store.get_session, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="session not found")
    _ensure_session_access(row, user["id"])
    return detail_from_row(row)


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionSummary,
    response_model_by_alias=True,
)
async def rename_session(
    session_id: str,
    req: RenameRequest,
    user: dict = Depends(current_user),
) -> SessionSummary:
    existing = await asyncio.to_thread(session_store.get_session, session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="session not found")
    _ensure_session_access(existing, user["id"])

    ok = await asyncio.to_thread(
        session_store.update_session_title, session_id, req.title,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="session not found")
    detail = await asyncio.to_thread(session_store.get_session, session_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="session not found")
    return summary_from_row(detail)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    user: dict = Depends(current_user),
) -> None:
    existing = await asyncio.to_thread(session_store.get_session, session_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="session not found")
    _ensure_session_access(existing, user["id"])

    ok = await asyncio.to_thread(session_store.delete_session, session_id)
    if not ok:
        raise HTTPException(status_code=404, detail="session not found")
    return None
