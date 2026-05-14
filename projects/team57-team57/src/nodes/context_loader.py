from __future__ import annotations

from src.nodes.logging_utils import append_backend_log
from src.db.repository import ReviewAgentRepository
from src.state import ReviewAgentState
from src.tools.db_tools import load_recent_feedback_tool, load_store_context_tool


def run_context_loader_node(state: ReviewAgentState, repo: ReviewAgentRepository) -> ReviewAgentState:
    if state.store_id is None:
        state.errors.append("store_id is required")
        state.execution_log.append("ContextLoaderNode: missing store_id")
        append_backend_log(
            state,
            node_name="ContextLoaderNode",
            input_summary="store_id 없음",
            output_summary="매장 컨텍스트 로드 실패",
            db_saved=False,
            has_error=True,
        )
        return state

    context = load_store_context_tool(repo, state.store_id)
    context["recent_feedback_samples"] = load_recent_feedback_tool(repo, state.store_id, limit=5)
    state.store_context = context
    state.execution_log.append("ContextLoaderNode: loaded store context and feedback samples")
    append_backend_log(
        state,
        node_name="ContextLoaderNode",
        input_summary=f"store_id={state.store_id}",
        output_summary=(
            f"매장 '{context['name']}' 컨텍스트 로드, 메뉴 {len(context.get('menu_items', []))}개, "
            f"최근 수정 답글 {len(context.get('recent_feedback_samples', []))}개"
        ),
        db_saved=False,
    )
    return state
