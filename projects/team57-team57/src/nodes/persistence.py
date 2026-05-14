from __future__ import annotations

from src.db.repository import ReviewAgentRepository
from src.nodes.logging_utils import append_backend_log
from src.state import ReviewAgentState
from src.tools.db_tools import save_reviews_tool


def run_persistence_tool_node(state: ReviewAgentState, repo: ReviewAgentRepository) -> ReviewAgentState:
    if state.store_id is None:
        state.errors.append("store_id is required for persistence")
        state.execution_log.append("PersistenceToolNode: skipped because store_id missing")
        append_backend_log(
            state,
            node_name="PersistenceToolNode",
            input_summary="store_id 없음",
            output_summary="저장 생략",
            db_saved=False,
            has_error=True,
        )
        return state

    session_id, review_ids = save_reviews_tool(
        repo,
        store_id=state.store_id,
        raw_input_text=state.raw_input_text,
        classified_reviews=state.classified_reviews,
        drafted_replies=state.drafted_replies,
    )
    state.session_id = session_id
    state.saved_review_ids = review_ids
    state.execution_log.append(f"PersistenceToolNode: saved session {session_id} with {len(review_ids)} reviews")
    append_backend_log(
        state,
        node_name="PersistenceToolNode",
        input_summary=f"분석 결과 {len(state.classified_reviews)}건",
        output_summary=f"reviews 테이블에 {len(review_ids)}건 저장, session_id={session_id}",
        db_saved=True,
    )
    return state
