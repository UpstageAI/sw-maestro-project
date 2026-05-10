import ast
import asyncio
import json
import logging
import re
import shutil
import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import os

from openai import AsyncOpenAI
from fastapi import BackgroundTasks, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from mcp_client import MCPClient, get_mcp_url

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=_LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("hwp-chatbot")

_LOG_BODY_MAX = 500  # 응답 본문 로깅 최대 길이 (truncate)


def _truncate(value: Any, limit: int = _LOG_BODY_MAX) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    if len(text) <= limit:
        return text
    return text[:limit] + f"...<+{len(text) - limit} chars>"


SESSION_BASE_STR = "/tmp/sessions"
SESSION_TIMEOUT = 3600  # 1 hour in seconds

_TOOL_CALL_TEXT_RE = re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL)
_TOOL_CALL_BLOCK_RE = re.compile(r"<tool_call>(.*?)</tool_call>", re.DOTALL)


def _first_line(text: str) -> str:
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped:
            return stripped
    return text.strip()


def _strip_text_tool_calls(text: str) -> tuple[str, bool]:
    """모델이 텍스트로 출력한 <tool_call>...</tool_call> 블록을 제거."""
    had = bool(_TOOL_CALL_TEXT_RE.search(text))
    cleaned = _TOOL_CALL_TEXT_RE.sub("", text).strip()
    return cleaned, had


def _ast_to_value(node: ast.AST) -> Any:
    """AST 노드 → Python 값. 따옴표 없는 식별자는 문자열로 보존(placeholder)."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = _ast_to_value(node.operand)
        return -operand if isinstance(operand, (int, float)) else operand
    if isinstance(node, ast.List):
        return [_ast_to_value(e) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return [_ast_to_value(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return {_ast_to_value(k): _ast_to_value(v) for k, v in zip(node.keys, node.values)}
    return None


def _parse_text_tool_calls(text: str) -> list[dict[str, Any]]:
    """<tool_call>...</tool_call> 블록을 파싱해 [{name, arguments}] 반환. 실패 시 []."""
    match = _TOOL_CALL_BLOCK_RE.search(text)
    if not match:
        return []

    inner = match.group(1).strip()
    # 외부 [ ] 그룹 평탄화: "[a()], [b()]" -> "a(), b()"
    inner = re.sub(r"\]\s*,\s*\[", ", ", inner)
    inner = inner.strip()
    if inner.startswith("["):
        inner = inner[1:]
    if inner.endswith("]"):
        inner = inner[:-1]

    try:
        tree = ast.parse(inner, mode="exec")
    except SyntaxError:
        return []

    calls: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            args = {kw.arg: _ast_to_value(kw.value) for kw in node.keywords if kw.arg}
            calls.append({"name": node.func.id, "arguments": args})
    return calls


def _extract_doc_id(result: Any) -> str | None:
    """MCP 응답에서 doc_id 추출. dict / str / 표준 content 형식 모두 대응."""
    if isinstance(result, dict):
        if "doc_id" in result:
            return str(result["doc_id"])
        content = result.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            text = first.get("text", "") if isinstance(first, dict) else ""
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict) and "doc_id" in parsed:
                    return str(parsed["doc_id"])
            except Exception:
                pass
            m = re.search(r"doc_id[\"':\s]+([A-Za-z0-9_-]+)", text)
            if m:
                return m.group(1)
    if isinstance(result, str):
        m = re.search(r"doc_id[\"':\s]+([A-Za-z0-9_-]+)", result)
        if m:
            return m.group(1)
    return None


_DOCID_PLACEHOLDERS = {"<doc_id>", "doc_id", "{doc_id}", "${doc_id}", ""}


def _normalize_tool_args(
    name: str,
    args: dict[str, Any],
    real_doc_id: str | None,
    hwpx_path: str,
) -> dict[str, Any]:
    """LLM이 잘못 패스한 doc_id를 real_doc_id로 치환하고, save_document의 output_path를 세션 경로로 강제."""
    out = dict(args)
    if "doc_id" in out and real_doc_id is not None:
        v = out["doc_id"]
        if not isinstance(v, str):
            out["doc_id"] = real_doc_id
        elif v in _DOCID_PLACEHOLDERS or v.isdigit():
            out["doc_id"] = real_doc_id
    if name == "save_document":
        out["output_path"] = hwpx_path
    return out


def _is_save_success(result: Any) -> bool:
    """MCP save_document 결과가 실제로 성공했는지 판정. 응답 안에 error 필드가 있으면 실패로 간주."""
    if result is None:
        return False
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            return "error" not in result.lower()
    if isinstance(result, dict):
        if "error" in result:
            return False
        content = result.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            text = first.get("text", "") if isinstance(first, dict) else ""
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    if "error" in parsed:
                        return False
                    return "message" in parsed or "Saved" in str(parsed)
            except Exception:
                return "error" not in text.lower()
        return True
    return False


async def _execute_text_tool_calls(
    calls: list[dict[str, Any]],
    hwpx_path: str,
) -> tuple[bool, list[str]]:
    """파싱된 도구 호출을 순차 실행. doc_id placeholder 자동 치환, save 경로 강제 지정."""
    if _mcp_client is None:
        return False, []

    real_doc_id: str | None = None
    called: list[str] = []
    save_called = False

    for call in calls:
        name = call["name"]
        raw_args = dict(call.get("arguments") or {})
        args = _normalize_tool_args(name, raw_args, real_doc_id, hwpx_path)

        if name == "save_document":
            save_called = True

        try:
            result = await _mcp_client.call_tool(name, args)
            called.append(name)
            if name == "create_document":
                extracted = _extract_doc_id(result)
                if extracted:
                    real_doc_id = extracted
        except Exception as exc:
            called.append(f"{name}(failed:{exc})")

    return save_called, called

_session_last_used: dict[str, float] = {}
_mcp_client: MCPClient | None = None
_solar_client: AsyncOpenAI | None = None


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

from pathlib import Path

SESSION_BASE = Path(SESSION_BASE_STR)


def get_session_dir(session_id: str) -> Path:
    return SESSION_BASE / session_id


def touch_session(session_id: str) -> Path:
    session_dir = get_session_dir(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    _session_last_used[session_id] = time.monotonic()
    return session_dir


def cleanup_expired_sessions() -> None:
    now = time.monotonic()
    expired = [
        sid
        for sid, last_used in list(_session_last_used.items())
        if now - last_used > SESSION_TIMEOUT
    ]
    for session_id in expired:
        session_dir = get_session_dir(session_id)
        if session_dir.exists():
            shutil.rmtree(session_dir, ignore_errors=True)
        _session_last_used.pop(session_id, None)


# ---------------------------------------------------------------------------
# Conversation history helpers
# ---------------------------------------------------------------------------

HISTORY_FILE = "history.json"
_MAX_HISTORY = 20  # 최대 20개 메시지 (= 10턴)


def load_history(session_dir: Path) -> list[dict[str, Any]]:
    history_path = session_dir / HISTORY_FILE
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def save_history(session_dir: Path, history: list[dict[str, Any]]) -> None:
    trimmed = history[-_MAX_HISTORY:]
    history_path = session_dir / HISTORY_FILE
    try:
        history_path.write_text(json.dumps(trimmed, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _mcp_client, _solar_client
    mcp_url = get_mcp_url()
    _mcp_client = MCPClient(mcp_url)
    await _mcp_client.connect()
    _solar_client = AsyncOpenAI(
        api_key=os.environ["SOLAR_API_KEY"],
        base_url="https://api.upstage.ai/v1",
    )
    yield
    await _mcp_client.close()
    _mcp_client = None
    await _solar_client.close()
    _solar_client = None


app = FastAPI(title="HWP Editor Chatbot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def session_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    session_id = request.headers.get("X-Session-ID")
    if session_id:
        touch_session(session_id)
    return await call_next(request)


@app.middleware("http")
async def logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """모든 요청/응답을 로깅. 본문은 truncate, /health 는 디버그 레벨로 강등."""
    req_id = uuid.uuid4().hex[:8]
    session_id = request.headers.get("X-Session-ID", "-")
    method = request.method
    path = request.url.path
    is_health = path == "/health"
    log_in = logger.debug if is_health else logger.info
    log_in("[%s] → %s %s session=%s", req_id, method, path, session_id)

    started = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as exc:
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.exception("[%s] ✗ %s %s failed in %.0fms: %s", req_id, method, path, elapsed_ms, exc)
        raise

    elapsed_ms = (time.monotonic() - started) * 1000
    log_out = logger.debug if is_health else logger.info

    # JSON 응답이면 본문 캡처(스트리밍은 건드리지 않음)
    body_preview = ""
    content_type = response.headers.get("content-type", "")
    if "application/json" in content_type and hasattr(response, "body_iterator"):
        chunks: list[bytes] = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        body_bytes = b"".join(chunks)
        body_preview = _truncate(body_bytes.decode("utf-8", errors="replace"))
        response = Response(
            content=body_bytes,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    log_out(
        "[%s] ← %s %s %d in %.0fms%s",
        req_id,
        method,
        path,
        response.status_code,
        elapsed_ms,
        f" body={body_preview}" if body_preview else "",
    )
    return response


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class MCPToolCallRequest(BaseModel):
    tool_name: str
    arguments: dict[str, Any] = {}


class ChatRequest(BaseModel):
    message: str
    session_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health(background_tasks: BackgroundTasks) -> dict[str, str]:
    background_tasks.add_task(cleanup_expired_sessions)
    return {"status": "ok"}


@app.get("/mcp/tools")
async def mcp_tools() -> dict[str, Any]:
    if _mcp_client is None:
        raise HTTPException(status_code=503, detail="MCP client not initialised")
    tools = await _mcp_client.list_tools()
    return {"tools": tools}


MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@app.post("/upload")
async def upload_hwpx(request: Request, file: UploadFile = File(...)) -> dict[str, Any]:
    session_id = request.headers.get("X-Session-ID", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")

    filename = file.filename or ""
    if not filename.lower().endswith(".hwpx"):
        raise HTTPException(status_code=400, detail="지원하지 않는 파일 형식입니다")

    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="파일 크기가 10MB를 초과합니다")

    session_dir = touch_session(session_id)
    dest = session_dir / "current.hwpx"
    dest.write_bytes(data)

    return {"filename": filename, "size": len(data), "session_id": session_id}


@app.get("/download")
async def download_hwpx(request: Request) -> FileResponse:
    session_id = request.headers.get("X-Session-ID", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")

    session_dir = get_session_dir(session_id)
    current_hwpx = session_dir / "current.hwpx"

    if not current_hwpx.exists():
        raise HTTPException(status_code=404, detail="편집된 파일이 없습니다")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    download_name = f"edited_{timestamp}.hwpx"

    return FileResponse(
        path=str(current_hwpx),
        media_type="application/octet-stream",
        filename=download_name,
    )


@app.delete("/clear-history")
async def clear_history(request: Request) -> dict[str, str]:
    session_id = request.headers.get("X-Session-ID", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")

    history_path = get_session_dir(session_id) / HISTORY_FILE
    if history_path.exists():
        history_path.unlink()

    return {"status": "cleared"}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict[str, str]:
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    session_dir = get_session_dir(session_id)
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)
    _session_last_used.pop(session_id, None)

    return {"status": "deleted"}


@app.get("/history")
async def get_history(request: Request) -> dict[str, Any]:
    session_id = request.headers.get("X-Session-ID", "")
    if not session_id:
        raise HTTPException(status_code=400, detail="X-Session-ID header required")
    history = load_history(get_session_dir(session_id))
    return {"history": history}


@app.post("/mcp/call")
async def mcp_call(body: MCPToolCallRequest) -> dict[str, Any]:
    if _mcp_client is None:
        raise HTTPException(status_code=503, detail="MCP client not initialised")
    result = await _mcp_client.call_tool(body.tool_name, body.arguments)
    return {"result": result}


_SOLAR_MODEL = "solar-pro"
_MAX_TOOL_ROUNDS = 10
_CHAT_TIMEOUT = 120

# 모델이 안정적으로 선택할 수 있도록 노출 툴을 핵심 10개로 제한.
# (MCP 서버는 126개 노출하지만 그중 새 문서 + 템플릿 작업에 꼭 필요한 것만)
_ALLOWED_TOOLS: frozenset[str] = frozenset({
    "create_document",
    "open_document",
    "save_document",
    "render_markdown",
    "get_document_structure",
    "get_table_map",
    "update_table_cell",
    "update_paragraph_text",
    "insert_table",
    "replace_text",
})


async def _run_tool_loop(
    messages: list[dict[str, Any]],
    solar_tools: list[dict[str, Any]],
    current_hwpx: Path,
) -> tuple[str, bool, bool, bool]:
    """Returns (response_text, file_ready, had_text_tool_calls, any_tool_call)."""
    if _solar_client is None:
        raise HTTPException(status_code=503, detail="Solar client not initialised")

    create_kwargs: dict[str, Any] = {
        "model": _SOLAR_MODEL,
        "max_tokens": 4096,
        "messages": list(messages),
    }
    if solar_tools:
        create_kwargs["tools"] = solar_tools

    response_text = ""
    had_text_tool_calls = False
    any_tool_call = False
    real_doc_id: str | None = None
    save_succeeded = False
    hwpx_path = str(current_hwpx)

    logger.info(
        "tool_loop start: msgs=%d tools=%d hwpx_exists=%s",
        len(create_kwargs["messages"]),
        len(solar_tools),
        current_hwpx.exists(),
    )

    for round_idx in range(_MAX_TOOL_ROUNDS):
        round_started = time.monotonic()
        response = await _solar_client.chat.completions.create(**create_kwargs)
        choice = response.choices[0]
        llm_ms = (time.monotonic() - round_started) * 1000
        logger.info(
            "round %d: finish=%s llm=%.0fms content=%s",
            round_idx,
            choice.finish_reason,
            llm_ms,
            _truncate(choice.message.content or "", 200),
        )

        if choice.finish_reason != "tool_calls":
            raw_content = choice.message.content or ""
            cleaned, had = _strip_text_tool_calls(raw_content)

            if had:
                calls = _parse_text_tool_calls(raw_content)
                if calls:
                    save_called, executed = await _execute_text_tool_calls(
                        calls, str(current_hwpx)
                    )
                    logger.info("text-toolcall executed=%s save=%s", executed, save_called)
                    if save_called:
                        had = False
                        any_tool_call = True

            had_text_tool_calls = had
            if any_tool_call:
                # 문서 작업 모드: 한 줄로 자르고 빈 응답이면 기본 메시지
                response_text = _first_line(cleaned) if cleaned else ""
                if not response_text and not had:
                    response_text = "작업이 완료되어 HWPX 파일에 저장되었습니다."
            else:
                # 대화 모드: 멀티라인 그대로 보존
                response_text = cleaned
            break

        any_tool_call = True

        tool_calls = choice.message.tool_calls or []
        serialised_tool_calls: list[dict[str, Any]] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in tool_calls
        ]

        current_messages: list[dict[str, Any]] = list(create_kwargs["messages"])
        current_messages.append(
            {
                "role": "assistant",
                "content": choice.message.content,
                "tool_calls": serialised_tool_calls,
            }
        )

        for tc in tool_calls:
            tool_name: str = tc.function.name
            try:
                raw_input: dict[str, Any] = json.loads(tc.function.arguments)
            except json.JSONDecodeError:
                raw_input = {}
            tool_input = _normalize_tool_args(tool_name, raw_input, real_doc_id, hwpx_path)
            logger.info(
                "  → tool_call %s args=%s",
                tool_name,
                _truncate(tool_input, 300),
            )

            # Dedup: 같은 tool-loop 내에서 두 번째 이상의 create_document는 MCP에 보내지 않고
            # 캐시된 doc_id를 synthetic 결과로 돌려준다 — 모델이 spam 호출해도 throwaway 문서 누적을 차단.
            if tool_name == "create_document" and real_doc_id is not None:
                synthetic = {
                    "doc_id": real_doc_id,
                    "format": "hwpx",
                    "message": "Document already exists (deduped)",
                }
                result_str = json.dumps(synthetic)
                logger.info("  ← tool_result %s deduped doc_id=%s", tool_name, real_doc_id)
                current_messages.append(
                    {"role": "tool", "tool_call_id": tc.id, "content": result_str}
                )
                continue

            tool_started = time.monotonic()
            raw_result: Any = None
            try:
                if _mcp_client is not None:
                    raw_result = await _mcp_client.call_tool(tool_name, tool_input)
                    result_str = (
                        raw_result if isinstance(raw_result, str) else json.dumps(raw_result)
                    )
                    logger.info(
                        "  ← tool_result %s in %.0fms result=%s",
                        tool_name,
                        (time.monotonic() - tool_started) * 1000,
                        _truncate(result_str, 300),
                    )
                else:
                    result_str = "MCP client not available"
                    logger.warning("  ← tool_result %s skipped (no MCP client)", tool_name)
            except Exception as exc:
                result_str = f"Error calling tool {tool_name}: {exc}"
                logger.exception(
                    "  ← tool_result %s failed in %.0fms: %s",
                    tool_name,
                    (time.monotonic() - tool_started) * 1000,
                    exc,
                )

            if tool_name == "create_document" and raw_result is not None:
                extracted = _extract_doc_id(raw_result)
                if extracted:
                    real_doc_id = extracted
            elif tool_name == "save_document" and _is_save_success(raw_result):
                save_succeeded = True

            current_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result_str,
                }
            )

        create_kwargs["messages"] = current_messages

        # save_document가 성공했으면 다음 LLM 호출 없이 즉시 종료 — round/LLM-호출 비용 절약.
        if save_succeeded:
            response_text = "작업이 완료되어 HWPX 파일에 저장되었습니다."
            break

    if not response_text:
        for msg in reversed(create_kwargs["messages"]):
            if msg.get("role") == "assistant" and msg.get("content"):
                cleaned, had = _strip_text_tool_calls(msg["content"])
                had_text_tool_calls = had_text_tool_calls or had
                candidate = _first_line(cleaned) if cleaned else ""
                if candidate:
                    response_text = candidate
                    break

    return response_text, current_hwpx.exists(), had_text_tool_calls, any_tool_call


@app.post("/chat")
async def chat(body: ChatRequest, request: Request) -> dict[str, Any]:
    session_id = request.headers.get("X-Session-ID") or body.session_id
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    if _solar_client is None:
        raise HTTPException(status_code=503, detail="Solar client not initialised")

    session_dir = touch_session(session_id)
    current_hwpx = session_dir / "current.hwpx"
    hwpx_path = str(current_hwpx)
    logger.info(
        "/chat session=%s file_exists=%s msg=%s",
        session_id,
        current_hwpx.exists(),
        _truncate(body.message, 200),
    )

    # Fetch tools from hwpx-mcp; degrade gracefully if unavailable
    mcp_tools: list[dict[str, Any]] = []
    if _mcp_client is not None:
        try:
            mcp_tools = await _mcp_client.list_tools()
            logger.debug("MCP list_tools returned %d tools", len(mcp_tools))
        except Exception as exc:
            logger.exception("MCP list_tools failed: %s", exc)
            mcp_tools = []

    # MCP uses camelCase inputSchema; Solar/OpenAI API expects function-calling format.
    # 핵심 10개만 노출 — 126개 전부 넘기면 모델이 툴 선택을 못 함.
    solar_tools: list[dict[str, Any]] = [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
            },
        }
        for t in mcp_tools
        if t["name"] in _ALLOWED_TOOLS
    ]

    available_tool_names = (
        ", ".join(t["function"]["name"] for t in solar_tools) if solar_tools else "없음"
    )
    file_exists = current_hwpx.exists()
    open_or_create = (
        f"1. open_document(file_path='{hwpx_path}') 호출하여 기존 파일 열기"
        if file_exists else
        f"1. create_document() 호출하여 새 빈 문서 생성 (반환된 doc_id를 기억하세요)"
    )
    open_or_create_brief = (
        f"open_document(file_path='{hwpx_path}') 로 기존 파일 열기"
        if file_exists else
        "create_document() 로 새 문서 생성 (반환된 doc_id 기억)"
    )
    system_prompt = (
        "당신은 한글(HWP) 문서 편집 AI 어시스턴트입니다.\n"
        "사용자 요청을 두 모드 중 하나로 처리합니다.\n\n"

        "## 모드 판단\n"
        "1. **문서 작업 모드** — 문서/양식/템플릿/보고서/기획서/레포트 생성·편집·저장 요청\n"
        "   예: '~ 만들어줘', '~ 양식', '~ 작성해줘', '표 추가', '글꼴 바꿔줘', '저장해줘'\n"
        "   짧은 긍정 응답('예', '네', 'ㄱㄱ', '바로', '응')도 직전 맥락이 작업 제안이면 작업 모드\n"
        "   → **즉시** MCP 도구를 호출해 파일 생성/저장. 추가 질문 금지.\n\n"
        "2. **대화 모드** — 인사/기능 안내/잡담 (예: '안녕', '뭐 할 수 있어?')\n"
        "   → 도구 호출 없이 자연스러운 텍스트 답변\n\n"

        "## 🚫 절대 금지 (가장 중요)\n"
        "- **확인 질문 금지**: '만들까요?', '시작할까요?', '예/아니오로 답해주세요' 같은 확인 절대 금지.\n"
        "  사용자가 '~ 만들어줘'라고 하면 정보 더 묻지 말고 합리적 기본값으로 즉시 만드세요.\n"
        "- **추가 정보 요청 금지**: 학교명/이름/학번/과목명 등 모르는 정보는 '[학교명]', '[이름]' 같은\n"
        "  플레이스홀더로 채우고 일단 양식부터 생성. 사용자가 나중에 채울 수 있음.\n"
        "- **거짓 에러 금지**: '오류가 발생했습니다', '시스템 점검 중', '기능이 중단된 상태' 등\n"
        "  거짓 에러 메시지를 절대 만들어내지 마세요. 도구를 실제로 호출해서 결과를 확인하세요.\n"
        "- **미리보기/제안만 금지**: 텍스트로 양식 미리보기를 보여주고 끝내지 마세요. **반드시 도구 호출**.\n"
        "- **다운로드 안내 금지**: 사용자는 채팅창 메시지 옆 'HWPX 다운로드' 버튼으로 파일을 받습니다.\n"
        "  파일 시스템 경로(`/tmp/...`), `export_to_text`/`export_to_html` 같은 변환 도구,\n"
        "  '파일 공유 URL 생성' 같은 가짜 대안을 절대 안내하지 마세요.\n"
        "  '다운로드 안 돼'라고 하면 → 도구를 다시 호출해서 파일을 새로 생성하세요.\n\n"

        "## 문서 작업 모드 규칙\n"
        f"- 세션 파일 경로: {hwpx_path}\n"
        "- 작업 순서:\n"
        f"  1) {open_or_create_brief}\n"
        "  2) render_markdown 으로 요청 주제의 실제 내용 작성 (Markdown → HWP 서식 자동 변환)\n"
        f"  3) save_document(doc_id, output_path='{hwpx_path}') 로 저장\n"
        "- 응답: 한 문장 완료 보고. 예: '레포트 양식이 HWPX 파일에 저장되었습니다.'\n"
        "- 콘텐츠 작성 시: 도구 사용법/메타 설명을 문서에 넣지 마세요.\n\n"

        "## 대화 모드 규칙\n"
        "- 친근하게 답하세요. 멀티라인/목록 OK.\n"
        "- 무엇을 할 수 있는지 안내하세요.\n"
        "- 도구 호출 금지.\n\n"

        "## 편집 도구 (작업 모드 전용)\n"
        "- 권장: render_markdown(doc_id, section_index, after_paragraph_index, markdown_text)\n"
        "- 표/스타일/이미지/검색교체/헤더푸터/페이지 설정 도구 사용 가능\n"
        "- 저장: save_document(doc_id, output_path)\n"
        f"- 사용 가능 도구: {available_tool_names}\n"
    )

    history = load_history(session_dir)

    messages_with_history: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        *history,
        {"role": "user", "content": body.message},
    ]

    try:
        response_text, file_ready, had_text_calls, any_tool_call = await asyncio.wait_for(
            _run_tool_loop(messages_with_history, solar_tools, current_hwpx),
            timeout=_CHAT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        return {
            "response": "요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
            "file_ready": current_hwpx.exists(),
        }

    # 거짓 성공 감지: 도구 호출 0회 + 파일 없음 + 완료 동사형 응답
    # 완료 동사 패턴: "저장했/저장되었/저장됐/생성했/만들어졌습니다" 등
    SUCCESS_PATTERN = re.compile(
        r"(저장|생성|완료|추가|삽입|수정|만들|작성)\S*?(했|되었|됐|어졌)습니다"
    )
    claimed_success_no_tools = (
        not any_tool_call
        and not file_ready
        and bool(response_text)
        and bool(SUCCESS_PATTERN.search(response_text))
    )
    needs_retry = had_text_calls or claimed_success_no_tools
    if needs_retry:
        logger.warning(
            "needs_retry: had_text_calls=%s claimed_success_no_tools=%s any_tool_call=%s file_ready=%s",
            had_text_calls,
            claimed_success_no_tools,
            any_tool_call,
            file_ready,
        )

    if needs_retry:
        reinforcement = (
            "이전 응답에서 도구를 호출하지 않고 거짓 성공 메시지를 출력했습니다. "
            "반드시 create_document/render_markdown/save_document 또는 적절한 MCP 도구를 "
            "실제로 호출해서 작업을 완수하세요. 도구 호출 없이 '저장했습니다'라고 답하지 마세요."
        )
        # history를 그대로 보존하고 끝에 system reinforcement 1개만 추가.
        # 이전 시도에서 만든 doc_id/render 결과가 살아있으므로 재시도가 더 빨리 수렴함.
        messages_with_reinforcement: list[dict[str, Any]] = list(messages_with_history) + [
            {"role": "system", "content": "## 재시도 강화\n" + reinforcement},
        ]
        try:
            response_text, file_ready, had_text_calls, any_tool_call = await asyncio.wait_for(
                _run_tool_loop(messages_with_reinforcement, solar_tools, current_hwpx),
                timeout=_CHAT_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return {
                "response": "요청 처리 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.",
                "file_ready": current_hwpx.exists(),
            }

    # 재시도 후에도 도구 미호출 + 파일 없음 + 완료 주장이면 솔직한 안내로 교체
    final_failed = (
        not any_tool_call
        and not file_ready
        and bool(response_text)
        and bool(SUCCESS_PATTERN.search(response_text))
    )
    if final_failed:
        logger.error(
            "final_failed: any_tool_call=%s file_ready=%s response=%s",
            any_tool_call,
            file_ready,
            _truncate(response_text, 200),
        )
        response_text = "파일 생성에 실패했습니다. 다시 한 번 요청해주세요."

    # 깨끗한 응답만 히스토리에 저장 — 오염된 응답 전파 차단
    clean_success = response_text and not had_text_calls and not final_failed
    if clean_success:
        updated_history = history + [
            {"role": "user", "content": body.message},
            {"role": "assistant", "content": response_text},
        ]
        save_history(session_dir, updated_history)

    return {"response": response_text, "file_ready": file_ready}
