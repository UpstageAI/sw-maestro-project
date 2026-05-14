"""공통 LLM 헬퍼 + tool calling 루프 + Solar rate limit 안전장치.

Solar Pro 3는 분당 호출 한도가 빡빡함 (free/starter 티어 ~30 RPM 추정).
파이프라인이 25콜+를 60~90초에 폭주시키면 429 발생.

방어 전략:
1. **모든 LLM 호출을 전역 lock으로 직렬화** + 호출 사이 최소 2초 간격
   → 분당 ~30콜 미만으로 자연 throttle. 병렬 섹션이라도 안 겹침.
2. **openai SDK 자동 retry 끔** (max_retries=0) — 너무 짧은 backoff(~15초)는 분당
   윈도우(60초) 못 기다림. 대신 우리가 직접 잡아서 60/120/180/240/300초 5회 재시도.
3. **429 발생 시 logger.warning** — 세션 로그에 표시 (멈춤 vs 대기 구분).
"""
import logging
import threading
import time
from typing import Sequence

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import BaseTool
from langchain_upstage import ChatUpstage

from src import config
from src.tools.cost_tracker import tracker

log = logging.getLogger(__name__)

TOOL_RESULT_MAX_CHARS = 8000
LLM_TIMEOUT = 120
LLM_MAX_RETRIES = 0  # openai SDK 자동 retry 끔 — 우리가 직접 처리

# 모든 LLM 호출 직렬화 + 최소 간격 (Solar 분당 한도 분산)
_LLM_LOCK = threading.Lock()
_LAST_CALL_TS = [0.0]
MIN_INTERVAL_SEC = 2.0

# 429 발생 시 재시도 대기 시각 (분당 윈도우 슬라이드 충분히 기다림)
RATE_LIMIT_WAITS_SEC = [60, 120, 180, 240, 300]


def llm(deep: bool = False) -> ChatUpstage:
    return ChatUpstage(
        api_key=config.UPSTAGE_API_KEY,
        model=config.MODEL_NAME,
        reasoning_effort=config.EFFORT_DEEP if deep else config.EFFORT_FAST,
        request_timeout=LLM_TIMEOUT,
        max_retries=LLM_MAX_RETRIES,
    )


def _throttle() -> None:
    """LLM 호출 직전. 전역 lock 보유 + 최소 간격 보장."""
    with _LLM_LOCK:
        elapsed = time.time() - _LAST_CALL_TS[0]
        if elapsed < MIN_INTERVAL_SEC:
            time.sleep(MIN_INTERVAL_SEC - elapsed)
        _LAST_CALL_TS[0] = time.time()


def _is_rate_limit(e: Exception) -> bool:
    err = str(e).lower()
    return (
        "429" in err
        or "too_many_requests" in err
        or "rate limit" in err
        or "ratelimiterror" in type(e).__name__.lower()
    )


def _safe_call(fn, *args, **kwargs):
    """LLM invoke 래퍼 — throttle + 429 자동 재시도."""
    last_err: Exception | None = None
    # 1번째: 즉시 시도, 그 이후 RATE_LIMIT_WAITS_SEC만큼 대기 후 재시도
    for attempt, wait_sec in enumerate([0] + RATE_LIMIT_WAITS_SEC):
        if wait_sec > 0:
            log.warning(
                "[429] Solar rate limit — %ds 대기 후 재시도 (%d/%d)",
                wait_sec, attempt, len(RATE_LIMIT_WAITS_SEC),
            )
            time.sleep(wait_sec)
        _throttle()
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_err = e
            if not _is_rate_limit(e):
                raise
    raise RuntimeError(
        f"Solar 429가 {len(RATE_LIMIT_WAITS_SEC)}회 재시도 후에도 계속됨. "
        f"Upstage 콘솔에서 한도 확인 필요. 마지막 에러: {last_err}"
    )


def _record(model_key: str, response) -> None:
    tracker().record_from_response(model_key, response)


def invoke(prompt: str, *, deep: bool = False) -> str:
    """단순 LLM 호출 (tool 없음)."""
    effort = config.EFFORT_DEEP if deep else config.EFFORT_FAST
    res = _safe_call(llm(deep).invoke, prompt)
    _record(f"{config.MODEL_NAME}:{effort}", res)
    return res.content if isinstance(res.content, str) else str(res.content)


def run_with_tools(
    *,
    system: str,
    user: str,
    tools: Sequence[BaseTool],
    deep: bool = False,
    max_iter: int = 5,
) -> str:
    """Tool calling 루프 — _safe_call로 모든 invoke 보호."""
    effort = config.EFFORT_DEEP if deep else config.EFFORT_FAST
    model_key = f"{config.MODEL_NAME}:{effort}"

    bound = llm(deep).bind_tools(list(tools))
    tool_map = {t.name: t for t in tools}

    messages: list[BaseMessage] = [
        SystemMessage(content=system),
        HumanMessage(content=user),
    ]

    last_text: str = ""
    for _ in range(max_iter):
        res: AIMessage = _safe_call(bound.invoke, messages)
        _record(model_key, res)
        last_text = res.content if isinstance(res.content, str) else str(res.content)

        tool_calls = getattr(res, "tool_calls", None) or []
        if not tool_calls:
            return last_text

        messages.append(res)
        for tc in tool_calls:
            name = tc.get("name", "")
            args = tc.get("args", {}) or {}
            tool = tool_map.get(name)
            if tool is None:
                content = f"[Error] 알 수 없는 도구: {name}"
            else:
                try:
                    content = tool.invoke(args)
                except Exception as e:
                    content = f"[Error] {name} 호출 실패: {e}"
            content_str = str(content)
            if len(content_str) > TOOL_RESULT_MAX_CHARS:
                content_str = content_str[:TOOL_RESULT_MAX_CHARS] + "\n...[truncated]"
            messages.append(ToolMessage(
                tool_call_id=tc.get("id", ""),
                content=content_str,
            ))

    if not last_text.strip():
        messages.append(HumanMessage(
            content="이제 도구 호출 없이, 지금까지 모은 정보로 최종 마크다운 섹션만 작성하세요."
        ))
        res = _safe_call(llm(deep).invoke, messages)
        _record(model_key, res)
        last_text = res.content if isinstance(res.content, str) else str(res.content)
    return last_text
