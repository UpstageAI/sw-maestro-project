from __future__ import annotations

from src.llm.provider import LLMProvider
from src.nodes.logging_utils import append_backend_log
from src.state import ReviewAgentState
from src.tools.safety_tools import filter_risky_reply_phrases


def run_reply_drafter_agent_node(state: ReviewAgentState, provider: LLMProvider) -> ReviewAgentState:
    drafted_replies: list[dict[str, object]] = []

    context = state.store_context
    used_feedback_count = len(context.get("recent_feedback_samples", []))
    for review in state.classified_reviews:
        if review.get("status") != "analyzed":
            drafted_replies.append(
                {
                    "review_index": review["review_index"],
                    "replies": [],
                    "safety_notes": ["skipped because analysis failed"],
                    "status": "draft_skipped",
                }
            )
            continue

        result = provider.draft_reply(
            review_text=str(review["masked_text"]),
            sentiment=str(review["sentiment"]),
            categories=list(review.get("categories", [])),
            store_name=str(context.get("name", "매장")),
            tone=str(context.get("reply_tone", "정중체")),
            menu_items=list(context.get("menu_items", [])),
            reply_samples=list(context.get("reply_samples", [])),
            recent_feedback_samples=list(context.get("recent_feedback_samples", [])),
        )

        safe_replies: list[str] = []
        safety_notes = list(result.safety_notes)
        for reply in result.replies:
            filtered_reply, notes = filter_risky_reply_phrases(reply)
            safe_replies.append(filtered_reply)
            safety_notes.extend(notes)

        drafted_replies.append(
            {
                "review_index": review["review_index"],
                "replies": safe_replies[:2],
                "safety_notes": safety_notes,
                "status": "drafted",
            }
        )

    state.drafted_replies = drafted_replies
    state.execution_log.append(f"ReplyDrafterAgentNode: drafted {len(drafted_replies)} reply bundles")
    append_backend_log(
        state,
        node_name="ReplyDrafterAgentNode",
        input_summary=(
            f"리뷰 {len(state.classified_reviews)}건, 톤 {context.get('reply_tone', '정중체')}, "
            f"최근 수정 답글 샘플 {used_feedback_count}개"
        ),
        output_summary=f"답글 초안 {len(drafted_replies)}건 생성",
        db_saved=False,
    )
    return state
