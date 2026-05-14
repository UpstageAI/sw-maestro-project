from __future__ import annotations

import time

from ..llm import llm
from .extractor import extract

ROUTER_SYSTEM = (
    "사용자 질문이 주식·종목·시세·투자 리포트와 관련이 있는지 판단하세요. "
    "관련이 있으면 STOCK, 그렇지 않으면 OFFTOPIC. 다른 말 없이 한 단어만 출력하세요."
)

STOCK_SYSTEM = (
    "당신은 한국 주식 애널리스트입니다. 제공된 컨텍스트만 근거로 답변하세요. "
    "컨텍스트에 없는 사실은 '데이터 없음'이라고 답하세요. 매수/매도 추천 금지. 한국어로 답하세요."
)

OFFTOPIC_SYSTEM = (
    "당신은 친절한 어시스턴트입니다. 사용자의 질문이 주식과 무관하므로 "
    "일반 지식으로 짧게 답하세요. 한국어로 답하세요."
)

_STOCK_KEYWORDS = ("주식", "종목", "시세", "주가", "리포트", "거래량", "변동성", "고점", "저점")
_MAX_HISTORY_MESSAGES = 12


def _format_history(history: list[dict[str, str]] | None) -> str:
    if not history:
        return ""
    lines: list[str] = []
    for msg in history[-_MAX_HISTORY_MESSAGES:]:
        role = (msg.get("role") or "").strip().lower()
        content = (msg.get("content") or msg.get("text") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        label = "사용자" if role == "user" else "어시스턴트"
        lines.append(f"{label}: {content}")
    return "\n".join(lines)


def _classify(question: str, history: list[dict[str, str]] | None = None) -> str:
    if not llm.available:
        text = f"{_format_history(history)}\n{question}"
        return "STOCK" if any(k in text for k in _STOCK_KEYWORDS) else "OFFTOPIC"
    conversation = _format_history(history)
    user = (
        f"[이전 대화]\n{conversation}\n\n[현재 질문]\n{question}"
        if conversation
        else question
    )
    out = llm.generate(ROUTER_SYSTEM, user).strip().upper()
    return "STOCK" if "STOCK" in out else "OFFTOPIC"


def _trace_event(step: str, status: str, t0: float, **info) -> dict:
    return {
        "step": step,
        "status": status,
        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
        "info": info,
    }


def chat(question: str, symbol: str | None = None, history: list[dict[str, str]] | None = None) -> dict:
    trace: list[dict] = []
    history_turns = sum(
        1
        for m in (history or [])
        if isinstance(m, dict) and (m.get("role") in {"user", "assistant"})
    )

    t0 = time.perf_counter()
    route = _classify(question, history)
    trace.append(
        _trace_event(
            "router",
            "ok",
            t0,
            route=route,
            llm_used=llm.available,
            history_turns=history_turns,
            symbol=symbol or "",
        )
    )

    conversation = _format_history(history)

    if route == "STOCK" and symbol:
        t1 = time.perf_counter()
        ctx = extract(symbol, query=question, k=8)
        trace.append(
            _trace_event(
                "extractor",
                "ok" if ctx else "empty",
                t1,
                symbol=symbol,
                query=question,
                k=8,
                context_chars=len(ctx),
            )
        )
        if not ctx:
            answer = f"{symbol} 종목 데이터가 아직 수집되지 않았습니다. 먼저 리포트를 생성해 주세요."
            trace.append(
                _trace_event(
                    "answer", "skip", time.perf_counter(), reason="no_context"
                )
            )
            return {"route": "STOCK", "answer": answer, "trace": trace}
        user = (
            f"[컨텍스트]\n{ctx}\n\n[이전 대화]\n{conversation}\n\n[현재 질문]\n{question}"
            if conversation
            else f"[컨텍스트]\n{ctx}\n\n[질문]\n{question}"
        )
        t2 = time.perf_counter()
        ans = llm.generate(STOCK_SYSTEM, user)
        trace.append(
            _trace_event(
                "llm.generate",
                "ok",
                t2,
                system="STOCK",
                prompt_chars=len(user),
                answer_chars=len(ans),
                llm_ready=llm.available,
            )
        )
        return {"route": "STOCK", "answer": ans, "trace": trace}

    if route == "STOCK" and not symbol:
        ans = "주식 관련 질문이지만 종목이 지정되지 않았습니다. 먼저 종목 코드로 리포트를 생성해 주세요."
        trace.append(
            _trace_event("answer", "skip", time.perf_counter(), reason="no_symbol")
        )
        return {"route": "STOCK", "answer": ans, "trace": trace}

    user = (
        f"[이전 대화]\n{conversation}\n\n[현재 질문]\n{question}"
        if conversation
        else question
    )
    t3 = time.perf_counter()
    ans = llm.generate(OFFTOPIC_SYSTEM, user)
    trace.append(
        _trace_event(
            "llm.generate",
            "ok",
            t3,
            system="OFFTOPIC",
            prompt_chars=len(user),
            answer_chars=len(ans),
            llm_ready=llm.available,
        )
    )
    return {"route": "OFFTOPIC", "answer": ans, "trace": trace}
