"""memory_save node — 분류 결과를 SQLite에 저장하고 답글 draft를 replies에 insert.

P0-2/P0-3: lang_skip 또는 classification_failed 인 경우 sentiment=NULL 로 기록하고
review_categories insert 는 건너뛴다. noop placeholder 답글은 정상적으로 replies 에 적재
(사장이 직접 답글을 작성한 흐름을 추적하기 위해).
"""

from __future__ import annotations

from src.graph.trace import measure
from src.store import sqlite as db


def memory_save_node(state: dict) -> dict:
    """SQLite write 2회: reviews 분류 결과 update + replies draft insert.

    Memory Store(tone_samples) write는 사장이 [복사]/[수정 저장] 했을 때만 → UI 호출.
    """
    skipped = bool(state.get("lang_skip") or state.get("classification_failed"))

    with measure("memory_save", "sql_write") as log:
        if skipped:
            # 분류 결과 없음 — sentiment NULL, categories insert skip
            db.update_classification(
                review_id=state["review_id"],
                masked_text=state["masked_text"],
                sentiment=None,
                confidence=state.get("confidence", 0.0),
                categories=[],
                risk_flag=state.get("risk_flag", False),
                risk_reason=state.get("risk_reason"),
            )
        else:
            db.update_classification(
                review_id=state["review_id"],
                masked_text=state["masked_text"],
                sentiment=state["sentiment"],
                confidence=state["confidence"],
                categories=state.get("categories") or [],
                risk_flag=state.get("risk_flag", False),
                risk_reason=state.get("risk_reason"),
            )

        reply_id = db.insert_reply(
            review_id=state["review_id"],
            draft_text=state["reply_draft"],
            drafter_used=state["drafter_used"],
        )

        if skipped:
            reason = (
                "classification_failed"
                if state.get("classification_failed")
                else "lang_skip"
            )
            log["summary"] = (
                f"분류 skip ({reason}) — neutral reply only · reply_id={reply_id}"
            )
        else:
            log["summary"] = f"reviews UPDATE + replies INSERT · reply_id={reply_id}"
        log["details"] = {
            "review_id": state["review_id"],
            "reply_id": reply_id,
            "drafter_used": state["drafter_used"],
            "categories_count": 0 if skipped else len(state.get("categories") or []),
            "skipped": skipped,
        }
    return {"reply_id": reply_id, "node_log": [log]}
