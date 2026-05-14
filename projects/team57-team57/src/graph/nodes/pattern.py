"""pattern_aggregator node — LangGraph Tool use surface (LLM-driven bind_tools).

Solar 가 OpenAI 호환 tool calling 을 지원하므로 langchain-upstage `ChatUpstage.bind_tools(...)`
로 LLM 이 직접 SQL tool 호출 결정. trace 항목 3개로 분할:
  1) pattern.llm_decide  — LLM 첫 호출 (tool_calls 결정)
  2) pattern.sql_tool    — query_review_stats 실행 (LLM 의 args 로)
  3) pattern.llm_summarize — tool 결과 받아 자연어 정리
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from src.graph.tools.sql_query import query_review_stats
from src.llm.upstage_chat import get_chat_llm


_SYSTEM = (
    "You are a Korean review category aggregator. "
    "You have a tool: query_review_stats(place_id, group_by, days). "
    "ALWAYS call this tool first with group_by='category' and days=28 to get the negative TOP 3. "
    "After the tool returns, output ONLY plain Korean text (no markdown, no emojis):\n"
    "1. <카테고리> (<빈도>회)\n"
    "2. ...\n"
    "3. ...\n"
    'If the tool returns empty: "최근 4주간 분류된 부정 리뷰가 없습니다."'
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(s: str, n: int = 200) -> str:
    s = str(s or "")
    return s if len(s) <= n else s[:n] + "…"


def _make_log(node: str, kind: str, started_at: str, t0: float) -> dict:
    return {
        "node": node,
        "started_at": started_at,
        "duration_ms": int((time.perf_counter() - t0) * 1000),
        "kind": kind,
        "summary": "",
        "details": {},
    }


def pattern_agent_node(state: dict) -> dict:
    place_id = state["place_id"]
    model = os.getenv("MODEL_PATTERN", "solar-pro2")

    llm = get_chat_llm(model=model, temperature=0.0, tools=[query_review_stats])
    msgs: list = [
        SystemMessage(content=_SYSTEM),
        HumanMessage(
            content=f"매장 '{place_id}' 의 최근 4주 부정 카테고리 TOP 3 를 정리해주세요."
        ),
    ]

    logs: list[dict] = []

    # === Step 1: LLM 첫 호출 — tool_calls 결정 ===
    started1 = _now_iso()
    t0 = time.perf_counter()
    decide = llm.invoke(msgs)
    log1 = _make_log("pattern.llm_decide", "llm", started1, t0)
    tool_calls = getattr(decide, "tool_calls", []) or []
    log1["summary"] = (
        f"LLM 이 tool_calls {len(tool_calls)}건 결정"
        if tool_calls
        else "LLM 이 tool 호출 안 함 (직접 응답)"
    )
    log1["details"] = {
        "model": model,
        "duration_ms": log1["duration_ms"],
        "duration_api_ms": log1["duration_ms"],
        "input_tokens": getattr(getattr(decide, "usage_metadata", None), "input_tokens", 0)
        if hasattr(decide, "usage_metadata")
        else (decide.usage_metadata or {}).get("input_tokens", 0)
        if getattr(decide, "usage_metadata", None)
        else 0,
        "output_tokens": (decide.usage_metadata or {}).get("output_tokens", 0)
        if getattr(decide, "usage_metadata", None)
        else 0,
        "cache_read_tokens": 0,
        "cache_create_tokens": 0,
        "system_preview": _truncate(_SYSTEM),
        "prompt_preview": _truncate(msgs[1].content),
        "response_preview": _truncate(decide.content or json.dumps([tc.get("name") for tc in tool_calls], ensure_ascii=False)),
        "tool_calls": [
            {"name": tc.get("name"), "args": tc.get("args"), "id": tc.get("id")}
            for tc in tool_calls
        ],
    }
    logs.append(log1)
    msgs.append(decide)

    top3_data: list[dict] = []
    summary_text = ""

    if tool_calls:
        # === Step 2: 각 tool_call 실행 ===
        for tc in tool_calls:
            started2 = _now_iso()
            t0 = time.perf_counter()
            try:
                raw_result = query_review_stats.invoke(tc["args"])
            except Exception as e:  # noqa: BLE001
                raw_result = json.dumps({"error": str(e)}, ensure_ascii=False)

            try:
                parsed = json.loads(raw_result)
                if isinstance(parsed, list):
                    top3_data = parsed
            except json.JSONDecodeError:
                pass

            log_tool = _make_log("pattern.sql_tool", "sql_read", started2, t0)
            log_tool["summary"] = (
                f"query_review_stats({tc['args']}) → {len(top3_data) if isinstance(top3_data, list) else '?'} rows"
            )
            log_tool["details"] = {
                "tool": tc.get("name"),
                "args": tc.get("args"),
                "result": top3_data,
            }
            logs.append(log_tool)
            msgs.append(ToolMessage(content=raw_result, tool_call_id=tc["id"]))

        # === Step 3: LLM 두 번째 호출 — 결과 정리 ===
        started3 = _now_iso()
        t0 = time.perf_counter()
        final = llm.invoke(msgs)
        log3 = _make_log("pattern.llm_summarize", "llm", started3, t0)
        summary_text = (final.content or "").strip()
        log3["summary"] = f"TOP 3 자연어 정리 ({len(summary_text)}자)"
        log3["details"] = {
            "model": model,
            "duration_ms": log3["duration_ms"],
            "duration_api_ms": log3["duration_ms"],
            "input_tokens": (final.usage_metadata or {}).get("input_tokens", 0)
            if getattr(final, "usage_metadata", None)
            else 0,
            "output_tokens": (final.usage_metadata or {}).get("output_tokens", 0)
            if getattr(final, "usage_metadata", None)
            else 0,
            "cache_read_tokens": 0,
            "cache_create_tokens": 0,
            "system_preview": _truncate(_SYSTEM),
            "prompt_preview": "(이전 메시지 누적 + tool 결과)",
            "response_preview": _truncate(summary_text),
        }
        logs.append(log3)
    else:
        # tool 호출 없이 직접 응답 — fallback (정상 동작 아님)
        summary_text = (decide.content or "").strip() or "최근 4주간 분류된 부정 리뷰가 없습니다."

    return {"top3_data": top3_data, "top3_summary": summary_text, "node_log": logs}
