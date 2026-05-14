from __future__ import annotations

from src.db.repository import ReviewAgentRepository
from src.nodes.logging_utils import append_backend_log
from src.state import ReviewAgentState
from src.tools.db_tools import load_negative_review_patterns_tool


def run_pattern_agent_node(state: ReviewAgentState, repo: ReviewAgentRepository) -> ReviewAgentState:
    if state.store_id is None:
        state.errors.append("store_id is required for pattern analysis")
        state.execution_log.append("PatternAgentNode: skipped because store_id missing")
        append_backend_log(
            state,
            node_name="PatternAgentNode",
            input_summary="store_id 없음",
            output_summary="패턴 분석 생략",
            db_saved=False,
            has_error=True,
        )
        return state

    pattern_data = load_negative_review_patterns_tool(repo, state.store_id)
    total_review_count = int(pattern_data["total_review_count"])

    if total_review_count < 10:
        state.pattern_summary = {
            "enabled": False,
            "message": "누적 데이터가 부족합니다",
            "total_review_count": total_review_count,
            "top_categories": [],
            "top_keywords": [],
        }
        state.execution_log.append("PatternAgentNode: insufficient data")
        append_backend_log(
            state,
            node_name="PatternAgentNode",
            input_summary=f"누적 리뷰 {total_review_count}건 조회",
            output_summary="누적 데이터가 부족합니다",
            db_saved=False,
        )
        return state

    category_counts = pattern_data["category_counts"]
    keyword_counts = pattern_data["keyword_counts"]

    top_categories = sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))[:3]
    top_keywords = sorted(keyword_counts.items(), key=lambda item: (-item[1], item[0]))[:5]

    state.pattern_summary = {
        "enabled": True,
        "message": "ok",
        "total_review_count": total_review_count,
        "negative_review_count": pattern_data["negative_review_count"],
        "top_categories": [
            {"name": name, "count": count}
            for name, count in top_categories
        ],
        "top_keywords": [
            {"name": name, "count": count}
            for name, count in top_keywords
        ],
    }
    state.execution_log.append("PatternAgentNode: computed complaint patterns")
    append_backend_log(
        state,
        node_name="PatternAgentNode",
        input_summary=f"누적 리뷰 {total_review_count}건, 부정 리뷰 {pattern_data['negative_review_count']}건 조회",
        output_summary=f"반복 불만 TOP 3 계산 완료",
        db_saved=False,
    )
    return state
