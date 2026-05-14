from __future__ import annotations

from src.llm.provider import LLMProvider
from src.nodes.logging_utils import append_backend_log
from src.state import ReviewAgentState


def run_classifier_agent_node(state: ReviewAgentState, provider: LLMProvider) -> ReviewAgentState:
    classified_reviews: list[dict[str, object]] = []
    failed_count = 0

    menu_items = state.store_context.get("menu_items", [])
    for index, review in enumerate(state.parsed_reviews):
        try:
            result = provider.classify_review(
                review_text=review["masked_text"],
                menu_items=menu_items,
            )
        except Exception:
            try:
                result = provider.classify_review(
                    review_text=review["masked_text"],
                    menu_items=menu_items,
                )
            except Exception as exc:
                state.warnings.append(f"분석 실패: review_index={index}, error={exc}")
                failed_count += 1
                classified_reviews.append(
                    {
                        "review_index": index,
                        "original_text": review["original_text"],
                        "masked_text": review["masked_text"],
                        "sentiment": None,
                        "confidence": None,
                        "categories": [],
                        "menu_tags": [],
                        "status": "analysis_failed",
                    }
                )
                continue

        classified_reviews.append(
            {
                "review_index": index,
                "original_text": review["original_text"],
                "masked_text": review["masked_text"],
                "sentiment": result.sentiment,
                "confidence": result.confidence,
                "categories": result.categories,
                "menu_tags": result.menu_tags,
                "rationale": result.rationale,
                "status": "analyzed",
            }
        )

    state.classified_reviews = classified_reviews
    state.execution_log.append(f"ClassifierAgentNode: analyzed {len(classified_reviews)} reviews")
    append_backend_log(
        state,
        node_name="ClassifierAgentNode",
        input_summary=f"리뷰 {len(state.parsed_reviews)}건, 메뉴 후보 {len(menu_items)}개",
        output_summary=f"{len(classified_reviews)}건 분석 완료, {failed_count}건 실패",
        db_saved=False,
        has_warning=failed_count > 0,
    )
    return state
