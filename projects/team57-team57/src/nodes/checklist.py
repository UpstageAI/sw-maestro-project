from __future__ import annotations

from src.nodes.logging_utils import append_backend_log
from src.state import ReviewAgentState


CHECKLIST_RULES = {
    "대기시간": "피크타임 주문 대기 시간을 확인하세요.",
    "서비스": "직원 응대 문구와 고객 응대 흐름을 점검하세요.",
    "가격": "주요 메뉴 가격 인식과 구성 가치를 다시 확인하세요.",
    "위생": "테이블, 좌석, 주문대 청결 상태를 수시로 점검하세요.",
    "맛": "대표 메뉴의 레시피 일관성과 제공 품질을 확인하세요.",
}


def run_checklist_agent_node(state: ReviewAgentState) -> ReviewAgentState:
    pattern_summary = state.pattern_summary

    if not pattern_summary.get("enabled"):
        state.checklist = [
            "이번 주 부정 리뷰를 직접 3건 이상 다시 읽고 공통 표현을 확인하세요.",
            "피크타임 운영 동선을 한 번 점검하세요.",
            "대표 메뉴의 제공 품질을 매일 동일하게 유지하는지 확인하세요.",
        ]
        state.execution_log.append("ChecklistAgentNode: generated default checklist")
        append_backend_log(
            state,
            node_name="ChecklistAgentNode",
            input_summary="패턴 요약 비활성 상태",
            output_summary=f"기본 체크리스트 {len(state.checklist)}개 생성",
            db_saved=False,
        )
        return state

    checklist: list[str] = []
    for category_item in pattern_summary.get("top_categories", []):
        category_name = category_item["name"]
        checklist.append(CHECKLIST_RULES.get(category_name, f"{category_name} 관련 운영 항목을 점검하세요."))

    for keyword_item in pattern_summary.get("top_keywords", []):
        keyword = keyword_item["name"]
        if keyword == "줄":
            checklist.append("대기 줄 안내 방식과 피크타임 안내 문구를 점검하세요.")
        elif keyword == "누락":
            checklist.append("주문 누락 방지를 위한 확인 절차를 점검하세요.")

    deduped: list[str] = []
    seen: set[str] = set()
    for item in checklist:
        if item not in seen:
            seen.add(item)
            deduped.append(item)

    state.checklist = deduped[:5]
    state.execution_log.append(f"ChecklistAgentNode: generated {len(state.checklist)} checklist items")
    append_backend_log(
        state,
        node_name="ChecklistAgentNode",
        input_summary=f"TOP 카테고리 {len(pattern_summary.get('top_categories', []))}개",
        output_summary=f"체크리스트 {len(state.checklist)}개 생성",
        db_saved=False,
    )
    return state
