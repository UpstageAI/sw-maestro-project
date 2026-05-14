"""classifier node — Upstage Solar structured output (sentiment + categories + confidence + risk_flag).

Solar 의 response_format=json_schema 로 schema 강제 출력 (src.llm.upstage).
끝에 router 분기 *예측* trace 항목도 함께 append (route_by_sentiment 함수와 동일한 결정 로직).

P0-2: classify() 실패 시 1회 재시도, 그래도 실패하면 `classification_failed=True` 와 안전
기본값(neutral/conf=0.0)을 채워 다음 노드로 흘려보낸다 — graph.stream() 배치를 통째로
중단시키지 않는다.
P0-3: 상류 pii_mask 가 lang_skip=True 를 세팅했으면 LLM 호출 없이 short-circuit.
"""

from __future__ import annotations

import os

from src.graph.routes.sentiment import CONFIDENCE_THRESHOLD, route_by_sentiment
from src.graph.trace import measure
from src.llm.upstage import complete_json_with_meta

CATEGORY_LIST = ["맛", "서비스", "가격", "대기시간", "위생"]

# P0-2: API 5xx 등 일시 실패에 대해 최대 N회 재시도 후 안전 기본값으로 통과.
MAX_RETRIES = 1

CLASSIFIER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "sentiment": {
            "type": "string",
            "enum": ["positive", "negative", "neutral"],
            "description": "리뷰의 전반 감정",
        },
        "categories": {
            "type": "array",
            "description": "해당 카테고리. confidence 내림차순. 0~3개.",
            "items": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": CATEGORY_LIST},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["category", "confidence"],
            },
            "maxItems": 3,
        },
        "confidence": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "감정 분류에 대한 자신감",
        },
        "risk_flag": {
            "type": "boolean",
            "description": "욕설·심한 비방·법적 위험 표현이 있을 때만 true",
        },
        "risk_reason": {
            "type": ["string", "null"],
            "description": "risk_flag=true일 때 짧은 사유, 아니면 null",
        },
    },
    "required": ["sentiment", "categories", "confidence", "risk_flag"],
}


_SYSTEM_PROMPT = (
    "You are a Korean review classifier. NEVER explain, NEVER ask. "
    "Output ONLY valid JSON matching the provided json-schema. "
    "User input = a single Korean review. "
    f"Categories (one or more): {', '.join(CATEGORY_LIST)}. "
    "risk_flag=true only if profanity, defamation, or legal threats present."
)


# P0-2: 분류 실패/스킵 시 다운스트림(state contract)이 요구하는 모든 필드의 안전 기본값.
_SAFE_DEFAULTS: dict = {
    "sentiment": "neutral",
    "confidence": 0.0,
    "categories": [],
    "risk_flag": False,
    "risk_reason": None,
}


def classify(review_text: str) -> tuple[dict, dict]:
    """Standalone classification + meta — graph node와 eval script 공통."""
    return complete_json_with_meta(
        prompt=review_text,
        system=_SYSTEM_PROMPT,
        schema=CLASSIFIER_SCHEMA,
        model=os.getenv("MODEL_CLASSIFIER", "solar-pro2"),
    )


def _router_log_entry(started_at: str, predicted_route: str, summary: str, details: dict) -> dict:
    return {
        "node": "route_by_sentiment",
        "started_at": started_at,
        "duration_ms": 0,
        "kind": "router",
        "summary": summary,
        "details": {"next_node": predicted_route, **details},
    }


def classifier_node(state: dict) -> dict:
    """Trace 2개를 append: classifier(llm) + route_by_sentiment(router 예측).

    P0-3: state["lang_skip"] 이면 LLM 호출 없이 안전 기본값 + noop 분기 trace 만 남기고 반환.
    P0-2: classify() 가 예외를 raise 하면 MAX_RETRIES 만큼 재시도, 그래도 실패면
    classification_failed 플래그 + 안전 기본값으로 반환.
    """
    # ── P0-3: 상류 pii_mask 에서 비한국어 판정된 경우 short-circuit ─────────────
    if state.get("lang_skip"):
        with measure("classifier", "transform") as log:
            log["summary"] = "lang_skip → classifier 건너뜀"
            log["details"] = {
                "skipped": True,
                "reason": state.get("lang_skip_reason", "lang_skip"),
            }
        router_log = _router_log_entry(
            started_at=log["started_at"],
            predicted_route="noop_drafter",
            summary="→ noop_drafter (lang_skip)",
            details={"reason": "lang_skip"},
        )
        return {**_SAFE_DEFAULTS, "node_log": [log, router_log]}

    # ── P0-2: try/except + 1회 재시도 ──────────────────────────────────────────
    last_exc: Exception | None = None
    result: dict | None = None
    meta: dict | None = None
    attempts = 0
    with measure("classifier", "llm") as log:
        for attempt in range(MAX_RETRIES + 1):
            attempts = attempt + 1
            try:
                result, meta = classify(state["masked_text"])
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001 — 어떤 예외든 격리
                last_exc = exc
                result = None
                meta = None

        if last_exc is not None or result is None:
            # 모든 재시도 실패 — classification_failed 경로
            err_str = str(last_exc)[:200] if last_exc else "unknown error"
            log["kind"] = "llm"
            log["summary"] = f"classifier 실패 ({attempts}회 시도) — {err_str}"
            log["details"] = {
                "error": err_str,
                "retries": MAX_RETRIES,
                "attempts": attempts,
            }
        else:
            cats = [c["category"] for c in result.get("categories", [])]
            log["summary"] = (
                f"sentiment={result['sentiment']} · conf={result.get('confidence', 0):.2f} · "
                f"cats={cats} · risk={result.get('risk_flag', False)}"
            )
            log["details"] = {
                **(meta or {}),
                "schema_validated": True,
                "attempts": attempts,
                "output": {
                    "sentiment": result["sentiment"],
                    "confidence": result.get("confidence"),
                    "categories": result.get("categories"),
                    "risk_flag": result.get("risk_flag"),
                    "risk_reason": result.get("risk_reason"),
                },
            }

    # ── 실패 분기: classification_failed + 안전 기본값 ──────────────────────────
    if last_exc is not None or result is None:
        err_str = str(last_exc)[:200] if last_exc else "unknown error"
        router_log = _router_log_entry(
            started_at=log["started_at"],
            predicted_route="noop_drafter",
            summary=f"→ noop_drafter (classification_failed: {err_str[:60]})",
            details={"reason": "classification_failed"},
        )
        return {
            **_SAFE_DEFAULTS,
            "risk_reason": "classification failed",
            "classification_failed": True,
            "classification_error": err_str,
            "node_log": [log, router_log],
        }

    # ── 정상 분기: 기존 logic 유지 ─────────────────────────────────────────────
    predicted_state = {**state, **result}
    predicted_route = route_by_sentiment(predicted_state)
    reason_parts = [f"sentiment={result['sentiment']}"]
    if result["sentiment"] == "negative":
        reason_parts.append(
            f"conf={result.get('confidence', 0):.2f} "
            f"({'≥' if result.get('confidence', 0) >= CONFIDENCE_THRESHOLD else '<'} {CONFIDENCE_THRESHOLD})"
        )
    router_log = _router_log_entry(
        started_at=log["started_at"],
        predicted_route=predicted_route,
        summary=f"→ {predicted_route} ({' ∧ '.join(reason_parts)})",
        details={
            "threshold": CONFIDENCE_THRESHOLD,
            "decision_inputs": {
                "sentiment": result["sentiment"],
                "confidence": result.get("confidence"),
            },
        },
    )

    return {**result, "node_log": [log, router_log]}
