"""Intake node — NL parsing or dict pass-through."""

from __future__ import annotations

import re

from autocoin_ai.logger import get_logger
from autocoin_ai.constants import (
    DEFAULT_TRADER,
    HOLD_INPUT_AMBIGUOUS,
    LIFECYCLE_FAILED,
    LIFECYCLE_HOLD,
    PERSONA_MODERATE,
)
from autocoin_ai.models import AgentState, append_check, ensure_state_shape, set_trace
from autocoin_ai.prompts.intake_prompt import INTAKE_SCHEMA, INTAKE_SYSTEM_INSTRUCTION
from autocoin_ai.llm import gemini_generate
from autocoin_ai.validators import validate_request_context

_log = get_logger("intake")


def intake_node(state: AgentState) -> AgentState:
    next_state = ensure_state_shape(state)
    if next_state.get("lifecycle_status") == LIFECYCLE_FAILED:
        return next_state

    request_context = next_state.get("request_context", {})
    user_input = request_context.get("user_input")

    if not isinstance(user_input, dict):
        _fail(next_state, "INITIAL_REQUEST_CONTRACT_FAILED", ["request_context.user_input"])
        return next_state

    text = user_input.get("text") or user_input.get("raw_text")
    if text:
        _log.info("[intake] NL 텍스트 감지 → LLM 파싱 모드")
        return _llm_mode(next_state, user_input, str(text))
    _log.info("[intake] dict 입력 → 직접 파싱 모드")
    return _dict_mode(next_state, user_input)


def _llm_mode(state: AgentState, user_input: dict, text: str) -> AgentState:
    _log.info("[intake] LLM 파싱 시도: \"%s\"", text[:80])
    try:
        parsed = gemini_generate(text, INTAKE_SCHEMA, INTAKE_SYSTEM_INSTRUCTION)
    except Exception:
        _log.info("[intake] LLM 호출 실패 → 휴리스틱 폴백 시도")
        heuristic = _heuristic_parse(user_input, text)
        if heuristic is not None:
            _log.info("[intake] 휴리스틱 파싱 성공: %s %s %s USDT",
                      heuristic.get("symbol"), heuristic.get("side"), heuristic.get("size_usd"))
            _apply_parsed(state, heuristic, heuristic["trader_id"], text)
            set_trace(
                state,
                "intake",
                ["HEURISTIC_PARSE_FALLBACK"],
                ["request_context.user_input.text"],
                "PASS",
            )
            return state
        _log.info("[intake] 휴리스틱 폴백 실패 → HOLD (입력 모호)")
        _set_trader_defaults_for_hold(state, user_input, text)
        _hold_ambiguous(state, ["request_context.user_input.text"], "LLM parsing failed; more explicit symbol/side/amount is required.")
        return state

    required = INTAKE_SCHEMA["required"]
    if not all(k in parsed for k in required):
        _log.info("[intake] LLM 응답 스키마 불일치 → FAILED")
        _fail(state, "INTAKE_SCHEMA_INVALID", ["llm_response"])
        return state

    trader_id = parsed.get("trader_id") or user_input.get("trader_id") or DEFAULT_TRADER
    inferred_persona = str(parsed.get("inferred_persona") or PERSONA_MODERATE)
    state["trader_id"] = trader_id
    state["inferred_persona"] = inferred_persona
    override = parsed.get("persona_override_reason")
    state["persona_override_reason"] = override if override else None

    ambiguity = parsed.get("ambiguity_score", 0)
    _log.info("[intake] LLM 응답: symbol=%s, side=%s, ambiguity=%.2f",
              parsed.get("symbol", "?"), parsed.get("side", "?"), float(ambiguity))
    if ambiguity > 0.5:
        _log.info("[intake] 모호성 %.2f > 0.5 → 휴리스틱 폴백 시도", float(ambiguity))
        heuristic = _heuristic_parse(user_input, text)
        if heuristic is not None:
            _log.info("[intake] 휴리스틱 파싱 성공: %s %s %s USDT",
                      heuristic.get("symbol"), heuristic.get("side"), heuristic.get("size_usd"))
            _apply_parsed(state, heuristic, heuristic["trader_id"], text)
            set_trace(
                state,
                "intake",
                ["HEURISTIC_PARSE_FALLBACK"],
                ["request_context.user_input.text"],
                "PASS",
            )
            return state
        _log.info("[intake] 입력 모호 → HOLD")
        _hold_ambiguous(state, ["ambiguity_score"], "심볼, 방향, 금액 또는 진입 조건을 더 구체적으로 입력하세요.")
        return state

    _apply_parsed(state, parsed, trader_id, text)
    _log.info("[intake] 파싱 완료: %s %s %s USDT (trader=%s, persona=%s)",
              parsed.get("symbol"), parsed.get("side"), parsed.get("size_usd"), trader_id, inferred_persona)
    return state


def _dict_mode(state: AgentState, user_input: dict) -> AgentState:
    request_context = state.get("request_context", {})
    missing = validate_request_context(request_context)
    if missing:
        _log.info("[intake] 필수 필드 누락 → FAILED: %s", missing)
        _fail(state, "INITIAL_REQUEST_CONTRACT_FAILED", ["request_context"])
        return state

    normalized = {
        "symbol": str(user_input["symbol"]).upper(),
        "side": str(user_input["side"]).upper(),
        "type": str(user_input["type"]).upper(),
    }
    if "quoteOrderQty" in user_input:
        normalized["quoteOrderQty"] = str(user_input["quoteOrderQty"])
    if "quantity" in user_input:
        normalized["quantity"] = str(user_input["quantity"])

    state["normalized_order_intent"] = normalized
    state["trader_id"] = str(user_input.get("trader_id") or DEFAULT_TRADER)
    state["inferred_persona"] = str(user_input.get("persona") or PERSONA_MODERATE)
    state["persona_override_reason"] = None

    append_check(state, "intake_parse_complete", "intake", "pass", ["normalized_order_intent"])
    set_trace(state, "intake", ["DICT_MODE_PASS"], ["request_context.user_input"], "PASS")
    _log.info("[intake] dict 파싱 완료: %s %s (trader=%s)",
              normalized.get("symbol"), normalized.get("side"), state.get("trader_id"))
    return state


def _apply_parsed(state: AgentState, parsed: dict, trader_id: str, text: str) -> None:
    state["normalized_order_intent"] = {
        "symbol": str(parsed.get("symbol", "")).upper(),
        "side": str(parsed.get("side", "")).upper(),
        "type": str(parsed.get("type", "MARKET")).upper(),
        "quoteOrderQty": str(parsed.get("size_usd", "0")),
    }
    state["trader_id"] = trader_id
    state["inferred_persona"] = str(parsed.get("inferred_persona") or PERSONA_MODERATE)
    override = parsed.get("persona_override_reason")
    state["persona_override_reason"] = override if override else None

    append_check(state, "intake_parse_complete", "intake", "pass", ["normalized_order_intent"])
    set_trace(state, "intake", ["NL_PARSED"], ["request_context.user_input.text"], "PASS")


def _heuristic_parse(user_input: dict, text: str) -> dict | None:
    normalized_text = text.upper()

    symbol = ""
    if "BTC" in normalized_text or "비트코인" in text:
        symbol = "BTCUSDT"
    elif "ETH" in normalized_text or "이더리움" in text:
        symbol = "ETHUSDT"

    side = ""
    if any(token in text for token in ("매수", "사줘", "사고", "구매")):
        side = "BUY"
    elif any(token in text for token in ("매도", "팔아", "팔고", "정리")):
        side = "SELL"

    amount = _extract_size_usd(text)
    if not symbol or not side or not amount:
        return None

    trader_id = _infer_trader_id(text, user_input)
    inferred_persona = _infer_persona(text)

    return {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "size_usd": amount,
        "trader_id": trader_id,
        "inferred_persona": inferred_persona,
        "persona_override_reason": "heuristic" if inferred_persona != PERSONA_MODERATE else "",
        "ambiguity_score": 0.1,
    }


def _extract_size_usd(text: str) -> str | None:
    usdt_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:USDT|USD|달러)", text, re.IGNORECASE)
    if usdt_match:
        return usdt_match.group(1)

    krw_match = re.search(r"(\d+(?:\.\d+)?)\s*만원", text)
    if krw_match:
        amount_krw = float(krw_match.group(1)) * 10000
        return str(round(amount_krw / 1350, 2))

    return None


def _infer_trader_id(text: str, user_input: dict) -> str:
    lowered = text.lower()
    if "워뇨띠" in text or "wonyotti" in lowered:
        return "wonyotti"
    if "bnf" in lowered:
        return "bnf"
    if "매억남" in text or "maeoaknam" in lowered:
        return "maeoaknam"
    if "리버모어" in text or "livermore" in lowered:
        return "livermore"
    return str(user_input.get("trader_id") or DEFAULT_TRADER)


def _infer_persona(text: str) -> str:
    lowered = text.lower()
    if "공격적" in text or "aggressive" in lowered or "빠르게" in text:
        return "AGGRESSIVE"
    if "보수적" in text or "conservative" in lowered or "천천히" in text:
        return "CONSERVATIVE"
    return PERSONA_MODERATE


def _fail(state: AgentState, reason: str, evidence: list) -> None:
    append_check(state, "intake_parse_complete", "intake", "fail", evidence)
    set_trace(state, "intake", [reason], evidence, LIFECYCLE_FAILED)
    state["lifecycle_status"] = LIFECYCLE_FAILED


def _hold_ambiguous(state: AgentState, evidence: list, notes: str) -> None:
    append_check(state, "intake_parse_complete", "intake", "fail", evidence)
    set_trace(state, "intake", ["INPUT_AMBIGUOUS"], evidence, LIFECYCLE_HOLD, notes)
    state["lifecycle_status"] = LIFECYCLE_HOLD
    state["hold_reason"] = HOLD_INPUT_AMBIGUOUS


def _set_trader_defaults_for_hold(state: AgentState, user_input: dict, text: str) -> None:
    state["trader_id"] = _infer_trader_id(text, user_input)
    state["inferred_persona"] = _infer_persona(text)
    state["persona_override_reason"] = None
