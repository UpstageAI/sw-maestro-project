"""Drafter 4종 — thanks / apology / apology_lowconf / neutral.

Conditional edge에 의해 라우팅되어 단일 호출됨.
prompt: system(매장 메타·톤) + few-shot(tone_samples) + hint(feedback) + user(리뷰+분류).
"""

from __future__ import annotations

import os
from typing import Literal

from src.graph.tools.safety_filter import filter_risky_phrases
from src.graph.trace import measure
from src.llm.upstage import complete_text_with_meta

# P0-2/P0-3 분기에서 사용하는 placeholder. 사장님이 직접 답글을 작성하도록 유도.
_NOOP_REPLY = "(자동 답글 생성 안 됨) 이 리뷰는 직접 답글을 작성해주세요."


_TONE_HINTS = {
    "정중체": "정중하고 격식 있는 존댓말",
    "친근체": "친근하고 따뜻한 존댓말 (이모티콘 가벼운 사용 OK)",
    "격식체": "공식적이고 격식 높은 존댓말",
}

_DRAFTER_INSTRUCTIONS = {
    "thanks": (
        "다음 긍정 리뷰에 진심 어린 감사 답글을 작성하세요.\n"
        "- 80~150자.\n"
        "- 리뷰에서 칭찬한 구체적 포인트를 한 번 언급.\n"
        "- 재방문을 자연스럽게 유도하는 한 마디."
    ),
    "apology": (
        "다음 부정 리뷰에 사과 답글을 작성하세요. 다음 3단 구조 강제:\n"
        "1) 사실 인정 (리뷰의 구체적 포인트 한 번 언급)\n"
        "2) 사과\n"
        "3) 개선 방향이나 대안 제시 (구체적이되, 가격/할인 약속·매장 정책 변경 표현 금지)\n"
        "- 100~180자."
    ),
    "apology_lowconf": (
        "다음 부정 가능성 리뷰에 *보수적인* 답글을 작성하세요.\n"
        "- 분류 신뢰도가 낮으므로 단정적 사과는 회피.\n"
        "- 불편함에 대한 공감 + 구체 사실관계 확인 요청 (예: '어떤 부분이 불편하셨는지 알려주시면…').\n"
        "- 가격/할인/정책 변경 약속 절대 금지.\n"
        "- 80~150자."
    ),
    "neutral": (
        "다음 중립 리뷰에 짧고 정중한 답글을 작성하세요.\n"
        "- 80~120자.\n"
        "- 방문에 대한 감사 + 다음 방문에 더 나은 경험을 약속하는 한 마디.\n"
        "- 과한 사과나 과한 칭찬 회피."
    ),
}


def _build_system(state: dict, drafter_kind: str) -> str:
    meta = state.get("place_metadata") or {}
    tone_pref = meta.get("tone_preference", "정중체")
    tone_hint = _TONE_HINTS.get(tone_pref, _TONE_HINTS["정중체"])

    menus = meta.get("menus") or []
    menu_str = (
        ", ".join(f"{m.get('name', '')}({m.get('price', '?')}원)" for m in menus[:8])
        or "(미입력)"
    )

    parts = [
        "You write a Korean reply to a customer review. NEVER explain, NEVER ask. "
        "Output ONLY the reply text in Korean — plain text only, NO markdown headers (#), "
        "NO bold (**), NO bullet points, NO quotes around the reply. Just the reply itself.",
        "",
        f"매장: {meta.get('display_name', '매장')} ({meta.get('category', '매장')})",
        f"답글 톤: {tone_hint}",
        f"가격대: {meta.get('price_range', '미입력')}",
        f"대표 메뉴: {menu_str}",
        "",
    ]

    samples = state.get("tone_samples") or []
    if samples:
        parts.append("[과거 사장 채택/수정 답글 — 톤 모방]")
        for i, s in enumerate(samples, 1):
            parts.append(f"샘플 {i}:")
            parts.append(f"  리뷰: {s.get('review_text', '')}")
            owner_final = s.get("owner_final") or s.get("ai_draft", "")
            parts.append(f"  답글: {owner_final}")
        parts.append("")

    hints = state.get("feedback_hints") or []
    if hints:
        parts.append("[사장 톤 hint]")
        for h in hints:
            parts.append(f"  - {h}")
        parts.append("")

    parts.append("[지시]")
    parts.append(_DRAFTER_INSTRUCTIONS[drafter_kind])
    parts.append("한국어 존댓말 고정. 답글 텍스트만, 평문으로.")
    return "\n".join(parts)


def _build_user(state: dict) -> str:
    cats = state.get("categories") or []
    cat_str = ", ".join(c["category"] for c in cats) or "(없음)"

    risk_note = ""
    if state.get("risk_flag"):
        risk_note = (
            f"\n주의: 안전성 risk_flag 감지됨 ({state.get('risk_reason') or '욕설/위험 표현'}). "
            "구체적 약속·매장 정책 변경 표현은 절대 회피."
        )

    return (
        f"리뷰 원문 (PII 마스킹됨): {state['masked_text']}\n"
        f"감정: {state['sentiment']} (신뢰도 {state.get('confidence', 0):.2f})\n"
        f"카테고리(메타데이터): {cat_str}{risk_note}"
    )


def _draft(
    state: dict,
    kind: Literal["thanks", "apology", "apology_lowconf", "neutral"],
) -> dict:
    with measure(f"{kind}_drafter", "llm") as log:
        system = _build_system(state, kind)
        user = _build_user(state)
        text, meta = complete_text_with_meta(
            prompt=user,
            system=system,
            model=os.getenv("MODEL_DRAFTER", "solar-pro2"),
        )
        # P0-5: defense in depth — LLM 일탈 시 결정론적 후처리로 위험 표현 치환.
        filtered_text, safety_notes = filter_risky_phrases(text)

        few_shot_count = len(state.get("tone_samples") or [])
        hints_count = len(state.get("feedback_hints") or [])
        log["summary"] = (
            f"{kind} · few-shot {few_shot_count} · hint {hints_count} · "
            f"{len(filtered_text)}자 답글 생성"
            + (f" · 안전 필터 {len(safety_notes)}건" if safety_notes else "")
        )
        log["details"] = {
            **meta,
            "drafter_kind": kind,
            "few_shot_count": few_shot_count,
            "feedback_hints_count": hints_count,
            "reply_length": len(filtered_text),
            "safety_notes": safety_notes,
        }
    return {
        "reply_draft": filtered_text,
        "drafter_used": kind,
        "safety_notes": safety_notes,
        "node_log": [log],
    }


def thanks_drafter(state: dict) -> dict:
    return _draft(state, "thanks")


def apology_drafter(state: dict) -> dict:
    return _draft(state, "apology")


def apology_drafter_lowconf(state: dict) -> dict:
    return _draft(state, "apology_lowconf")


def neutral_drafter(state: dict) -> dict:
    return _draft(state, "neutral")


def noop_drafter(state: dict) -> dict:
    """P0-2/P0-3 분기: LLM 호출 없이 placeholder 답글 반환.

    lang_skip (비한국어) 또는 classification_failed (분류 실패) 일 때 라우터가 이 노드로 보낸다.
    사장님이 직접 답글을 작성하도록 안내하는 고정 텍스트를 reply_draft 로 채운다.
    """
    if state.get("classification_failed"):
        reason = f"classification_failed ({state.get('classification_error', '')[:60]})"
    elif state.get("lang_skip"):
        reason = f"lang_skip ({state.get('lang_skip_reason', 'non-Korean')})"
    else:
        reason = "unknown noop trigger"

    with measure("noop_drafter", "transform") as log:
        log["summary"] = f"noop 답글 — {reason}"
        log["details"] = {
            "reason": reason,
            "reply_length": len(_NOOP_REPLY),
        }
    return {
        "reply_draft": _NOOP_REPLY,
        "drafter_used": "noop",
        "safety_notes": [],
        "node_log": [log],
    }
