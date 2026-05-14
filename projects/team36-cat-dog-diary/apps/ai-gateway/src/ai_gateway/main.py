import hashlib
import json
import logging
import re
from collections.abc import AsyncIterator
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

from .contracts import (
    GatewayGenerateRequest,
    GatewayRegenerateRequest,
    HealthResponse,
)
from .graph import get_diary_graph
from .middleware import internal_secret_middleware, jwt_middleware
from .state import DiaryState

logger = logging.getLogger(__name__)

app = FastAPI(title="냥멍일기 AI Gateway")

# FastAPI middleware 등록 순서: 마지막 add가 가장 outer (request를 먼저 받음).
# 의도 흐름: request → internal_secret → jwt → endpoint.
# 따라서 jwt 먼저(inner), internal_secret 나중에(outer) 등록.
app.middleware("http")(jwt_middleware)
app.middleware("http")(internal_secret_middleware)


@app.get("/health")
def health() -> HealthResponse:
    return HealthResponse()


def _hash_user_id(user_id: str) -> str:
    """LangSmith trace 메타데이터용 — PII 회피, sub 노출 X (ADR-0012)."""
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]


def _initial_state(
    req: GatewayGenerateRequest | GatewayRegenerateRequest,
) -> DiaryState:
    is_regen = isinstance(req, GatewayRegenerateRequest)
    return {
        "session_id": req.session_id,
        "seq": req.seq,
        "pet_id": req.pet_id,
        "honorific": req.honorific,
        "species": req.species,
        "gender": req.gender,
        "photo_signed_url": req.photo_signed_url,
        "keywords": req.keywords,
        "recent_diaries": req.recent_diaries,
        "previous_diary_text": req.previous_diary_text if is_regen else None,
        "regen_feedback": req.feedback if is_regen else None,
        # regenerate에서 BFF가 forward — 있으면 graph가 analyze_image skip.
        "vision_description": req.vision_description if is_regen else None,
        "diary_text": None,
        "short_caption": None,
        "mood_tag": None,
        "safety_retry_count": 0,
        "safety_violation": None,
    }


# ----- SSE streaming -----

_TRACKED_NODES = {"analyze_image", "write_diary", "safety_check"}

# write_diary 누적 partial JSON에서 "diary_text" 값을 prefix로 추출.
# OpenAI structured outputs는 항상 valid JSON prefix를 stream하므로 정규식으로 충분.
_DIARY_TEXT_RE = re.compile(r'"diary_text"\s*:\s*"((?:[^"\\]|\\.)*)')

# system 프롬프트의 honorific placeholder를 LLM이 본문에 그대로 베끼는 경우 안전망.
# system.md 가드가 1차, 본 후처리가 2차. 빈 honorific은 처리 생략.
_HONORIFIC_PLACEHOLDERS = ("{{ honorific }}", "{{honorific}}", "{honorific}")


def _fix_honorific(text: str, honorific: str) -> str:
    if not honorific:
        return text
    for pat in _HONORIFIC_PLACEHOLDERS:
        text = text.replace(pat, honorific)
    return text


def _sse(event: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8")


def _extract_diary_text(buffer: str) -> str | None:
    m = _DIARY_TEXT_RE.search(buffer)
    if not m:
        return None
    raw = m.group(1)
    # 끝에 매달린 backslash는 escape 시작 → 잘라내고 디코드
    if raw.endswith("\\"):
        raw = raw[:-1]
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return None


async def _stream_graph(
    state: DiaryState, config: dict[str, Any]
) -> AsyncIterator[bytes]:
    honorific = state["honorific"]
    accumulated = ""        # write_diary LLM 출력 누적 (tool_call args)
    last_partial = ""       # 직전 emit된 diary_text (변동 시에만 재emit)
    write_starts = 0        # write_diary node start 횟수 (≥2 → retry)
    final_output: dict[str, Any] | None = None

    try:
        async for event in get_diary_graph().astream_events(
            state, config, version="v2"
        ):
            kind = event["event"]
            metadata = event.get("metadata") or {}
            node = metadata.get("langgraph_node")
            # 같은 노드 안의 sub-runnable(예: with_structured_output wrapping)도
            # 같은 langgraph_node metadata를 propagate해 on_chain_start가 다중 fire됨.
            # 노드 자체의 chain start만 잡으려면 event["name"] == node도 매치.
            is_node_chain = event.get("name") == node

            if (
                kind == "on_chain_start"
                and node in _TRACKED_NODES
                and is_node_chain
            ):
                if node == "write_diary":
                    write_starts += 1
                    if write_starts >= 2:
                        yield _sse({"type": "retry", "reason": "safety_violation"})
                        accumulated = ""
                        last_partial = ""
                yield _sse({"type": "node", "node": node, "phase": "start"})

            elif kind == "on_chain_end":
                output = event["data"].get("output")
                if node in _TRACKED_NODES and is_node_chain:
                    yield _sse({"type": "node", "node": node, "phase": "end"})
                    # analyze_image 산출물(vision_description)을 BFF에 emit —
                    # BFF가 가로채서 DB에 echo. 클라이언트엔 forward 안 됨.
                    if node == "analyze_image" and isinstance(output, dict):
                        vd = output.get("vision_description")
                        if vd:
                            yield _sse(
                                {
                                    "type": "vision_done",
                                    "vision_description": vd,
                                }
                            )
                # graph 또는 sub-chain output에서 final state 후보 갱신.
                # 마지막 매칭된 dict가 root graph의 output이 됨.
                if (
                    isinstance(output, dict)
                    and output.get("diary_text")
                    and output.get("short_caption")
                    and output.get("mood_tag")
                ):
                    final_output = output

            elif kind == "on_chat_model_stream" and node == "write_diary":
                chunk = event["data"]["chunk"]
                # structured output(function_calling)은 tool_call_chunks로 partial args 흘림.
                tool_chunks = getattr(chunk, "tool_call_chunks", None) or []
                for tc in tool_chunks:
                    args = (
                        tc.get("args")
                        if isinstance(tc, dict)
                        else getattr(tc, "args", None)
                    )
                    if args:
                        accumulated += args
                # 텍스트 모드 fallback (json_mode 등에서 content 사용 시).
                content = getattr(chunk, "content", "")
                if isinstance(content, str) and content:
                    accumulated += content

                partial = _extract_diary_text(accumulated)
                if partial:
                    partial = _fix_honorific(partial, honorific)
                    if partial != last_partial:
                        last_partial = partial
                        yield _sse(
                            {"type": "diary_partial", "diary_text": partial}
                        )

        if final_output:
            yield _sse(
                {
                    "type": "result",
                    "diary_text": _fix_honorific(
                        final_output["diary_text"], honorific
                    ),
                    "short_caption": _fix_honorific(
                        final_output["short_caption"], honorific
                    ),
                    "mood_tag": final_output["mood_tag"],
                }
            )
        else:
            yield _sse(
                {"type": "error", "message": "graph가 결과를 반환하지 않았습니다"}
            )

    except Exception as e:
        logger.exception("graph stream 실패")
        yield _sse({"type": "error", "message": str(e)})


def _stream_response(state: DiaryState, user_id: str) -> StreamingResponse:
    config: dict[str, Any] = {
        "metadata": {
            "session_id": state["session_id"],
            "seq": state["seq"],
            "owner_id_hash": _hash_user_id(user_id),
        },
        "tags": [f"seq:{state['seq']}"],
        "run_name": (
            "diary_generate" if state["seq"] == 1 else "diary_regenerate"
        ),
    }
    return StreamingResponse(
        _stream_graph(state, config),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",  # 프록시 버퍼링 차단 (즉시 flush)
        },
    )


@app.post("/diary/generate")
async def generate(
    req: GatewayGenerateRequest, request: Request
) -> StreamingResponse:
    user_id: str = request.state.user_id
    return _stream_response(_initial_state(req), user_id)


@app.post("/diary/regenerate")
async def regenerate(
    req: GatewayRegenerateRequest, request: Request
) -> StreamingResponse:
    user_id: str = request.state.user_id
    return _stream_response(_initial_state(req), user_id)
