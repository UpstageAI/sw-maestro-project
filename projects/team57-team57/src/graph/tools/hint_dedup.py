"""톤 힌트 dedup/merge — 신규 힌트를 기존과 비교해 skip/merge/append 결정.

`merge_or_append_hint()` 가 진입점. Solar 에 JSON schema strict 로 결정 요청 후
실패 시 fallback 으로 그냥 append (현재 동작 보존).

Wave 5: dimension 인자 추가 — 같은 dimension 내 모순/중복 감지 sharpen.
"""

from __future__ import annotations

import os
from typing import Any

from src.store import memory

# JSON schema — Solar response_format=json_schema strict 용 (dedup 결정)
HINT_DEDUP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["skip", "merge", "append"]},
        "target_fid": {"type": ["string", "null"]},
        "merged_text": {"type": ["string", "null"]},
        "reason": {"type": "string"},
    },
    "required": ["action", "reason"],
}


# JSON schema — diff hint 구조화 추출 (AI 초안 vs 사장 최종)
DIFF_HINT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "dimension": {
            "type": "string",
            "enum": ["사과표현", "감사표현", "어투/톤", "길이", "이모티콘", "구체성", "기타"],
            "description": "사장 변경이 영향을 준 가장 두드러진 차원",
        },
        "before": {"type": "string", "description": "AI 초안의 변경된 표현 (1~15자)"},
        "after": {"type": "string", "description": "사장이 채택한 표현 (1~15자)"},
        "hint": {
            "type": "string",
            "description": "형식 우선: 'X 보다 Y 선호'. 단어 변경 없으면 'X 톤 선호'. 40자 이내.",
        },
    },
    "required": ["dimension", "hint"],
}


DIFF_HINT_SYSTEM = (
    "당신은 음식점 답글 톤 분석가입니다. AI 초안과 사장 최종본을 비교해 사장의 *구체적 선호*를 추출하세요.\n"
    "규칙:\n"
    "1. 사장이 바꾼 가장 두드러진 단어/표현을 찾아 before/after 필드에 추출.\n"
    "2. 가능하면 hint 를 'X 보다 Y 선호' 형식으로 작성. 단어 변경이 없고 톤만 다르면 'X 톤 선호'.\n"
    "3. dimension 은 변경이 가장 크게 일어난 차원 1개.\n"
    "4. 절대 일반론 (예: '정중하게 다듬음') 만 출력하지 말 것 — 반드시 구체적 표현을 포함.\n"
    "JSON 만 출력."
)


DEDUP_SYSTEM = (
    "당신은 음식점 답글 톤 힌트를 관리합니다. 기존 힌트 목록과 새 힌트를 보고 다음 중 하나를 결정하세요:\n\n"
    "1. skip — 새 힌트가 기존 중 하나와 사실상 같은 내용\n"
    "2. merge — 새 힌트가 기존 중 하나와 모순되거나 부분적으로 겹침 → 한 줄(40자 이내)로 통합. 새 힌트의 방향 우선.\n"
    "3. append — 새 힌트가 독립적인 새 정보\n\n"
    "특별 규칙 (중요):\n"
    "- 같은 dimension (예: '사과표현') 내에서 다른 선호 표현이면 반드시 MERGE.\n"
    "  예: 기존 '미안해요 선호' + 신규 '죄송합니다 선호' → merge "
    "(target_fid=기존 fid, merged_text='미안해요 보다 죄송합니다 선호')\n"
    "- 같은 dimension 에서 같은 선호이면 SKIP.\n"
    "  예: 기존 '정중체 선호' + 신규 '정중한 톤 선호' → skip\n"
    "- 서로 다른 dimension 이면 APPEND (모순 없음).\n\n"
    "JSON 만 출력. reason 은 8자 이내 한국어."
)


def _format_existing(existing: list[dict]) -> str:
    """`[fid] dimension: diff_hint` 줄 단위 포맷 (dimension 없으면 '기타')."""
    return "\n".join(
        f"[{e['fid']}] {e.get('dimension') or '기타'}: {e['diff_hint']}"
        for e in existing
    )


def merge_or_append_hint(
    place_id: str,
    new_hint: str,
    source_sample_ids: list[str],
    *,
    source: str = "auto_diff",
    dimension: str | None = None,
) -> dict:
    """Dedup/merge 정책으로 새 힌트를 처리.

    Args:
        dimension: 새 힌트의 차원 (사과표현/감사표현/...). 같은 dimension 내
            모순/중복 감지를 sharpen 하는 데 사용.

    Returns:
        {"action": "skip"|"merge"|"append",
         "result_fid": str | None,
         "merged_from": list[str],
         "reason": str}
    """
    new_hint = (new_hint or "").strip()
    if not new_hint:
        return {"action": "skip", "result_fid": None, "merged_from": [], "reason": "빈 힌트"}

    existing = memory.list_feedback_with_meta(place_id, limit=10)

    # 첫 힌트 — dedup 생략하고 바로 append
    if not existing:
        fid = memory.append_feedback(
            place_id,
            new_hint,
            source_sample_ids,
            source=source,
            dimension=dimension,
        )
        return {"action": "append", "result_fid": fid, "merged_from": [], "reason": "최초"}

    # Solar 에 결정 요청 — 기존 힌트는 [fid] dimension: text 포맷으로 전달
    try:
        from src.llm.upstage import complete_json_with_meta

        prompt = (
            f"기존 힌트들:\n{_format_existing(existing)}\n\n"
            f"새 힌트 ({dimension or '기타'}): {new_hint}"
        )
        decision, _meta = complete_json_with_meta(
            prompt,
            system=DEDUP_SYSTEM,
            schema=HINT_DEDUP_SCHEMA,
            model=os.getenv("MODEL_DIFF_HINT", "solar-pro2"),
        )
    except Exception:  # noqa: BLE001
        # LLM 실패 → fallback: 그냥 append (현재 동작 보존)
        fid = memory.append_feedback(
            place_id,
            new_hint,
            source_sample_ids,
            source=source,
            dimension=dimension,
        )
        return {
            "action": "append",
            "result_fid": fid,
            "merged_from": [],
            "reason": "LLM 실패 fallback",
        }

    action = decision.get("action") if isinstance(decision, dict) else None
    reason = (decision or {}).get("reason", "") or ""

    # skip — 아무것도 하지 않음
    if action == "skip":
        return {"action": "skip", "result_fid": None, "merged_from": [], "reason": reason}

    # merge — target_fid 삭제 후 merged_text 로 새 힌트 append (source="merged")
    if action == "merge":
        target_fid = (decision or {}).get("target_fid")
        merged_text = ((decision or {}).get("merged_text") or new_hint).strip() or new_hint
        # target_fid 가 실제 존재하는 fid 인지 확인 — 없으면 fallback 으로 append
        existing_fids = {e["fid"] for e in existing}
        if target_fid in existing_fids:
            memory.delete_feedback(place_id, target_fid)
            new_fid = memory.append_feedback(
                place_id,
                merged_text,
                source_sample_ids,
                source="merged",
                merged_from=[target_fid],
                dimension=dimension,
            )
            return {
                "action": "merge",
                "result_fid": new_fid,
                "merged_from": [target_fid],
                "reason": reason,
            }
        # target_fid 가 잘못된 경우 — append 로 fallback
        fid = memory.append_feedback(
            place_id,
            new_hint,
            source_sample_ids,
            source=source,
            dimension=dimension,
        )
        return {
            "action": "append",
            "result_fid": fid,
            "merged_from": [],
            "reason": reason or "target_fid 미존재 fallback",
        }

    # append (or schema violation fallback)
    fid = memory.append_feedback(
        place_id,
        new_hint,
        source_sample_ids,
        source=source,
        dimension=dimension,
    )
    return {
        "action": "append",
        "result_fid": fid,
        "merged_from": [],
        "reason": reason or "독립",
    }
