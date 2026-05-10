"""LLM 일정 분류 — LangGraph 기반 (분류 + 검증 + 재시도 + 폴백)

외부 인터페이스 (변경 금지 — pipeline.py 가 이렇게 호출):
    classify_event(title: str, description: str) -> str

반환: "면접" | "시험" | "약속" | "마감" | "기타" 중 하나.

내부 그래프:
    START → classify → validate → ┬─ valid          → END
                                  ├─ invalid·attempt<2 → classify (재시도)
                                  └─ invalid·attempt≥2 → fallback → END
"""

import json
import os
from typing import TypedDict

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_upstage import ChatUpstage
from langgraph.graph import END, StateGraph

load_dotenv()

CATEGORIES = ["면접", "시험", "약속", "마감", "기타"]
CATEGORY_SET = set(CATEGORIES)
MAX_ATTEMPTS = 2

_llm = ChatUpstage(model="solar-pro2", temperature=0)


class ClassifyState(TypedDict):
    title: str
    description: str
    category: str | None
    attempt: int
    is_valid: bool


SYSTEM_PROMPT = """당신은 한국어 일정 분류기입니다.
입력으로 일정 제목과 설명을 받아, 다음 5개 카테고리 중 정확히 하나로 분류하세요.

카테고리:
- 면접: 채용·인턴십·진학 등의 면접
- 시험: 학교 시험·자격증·평가
- 약속: 친구·가족·지인과의 모임·식사·미팅
- 마감: 과제·프로젝트·신청서 등 제출 데드라인
- 기타: 위 4개에 속하지 않는 모든 일정 (병원·여행·정기 점검 등)

반드시 다음 JSON 형식으로만 답하세요. 다른 텍스트 절대 포함 금지:
{"category": "면접"}"""

FEW_SHOT = [
    ("A기업 1차 기술면접", "서류 합격 후 화상 면접", "면접"),
    ("자료구조 중간고사", "1~5장 범위", "시험"),
    ("동아리 친구들과 저녁", "강남역 7시", "약속"),
    ("졸업 논문 1차 제출", "PDF 1부 제출", "마감"),
    ("정기 치과 검진", "오전 10시 예약", "기타"),
]


def _build_messages(title: str, description: str):
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    for ex_title, ex_desc, ex_cat in FEW_SHOT:
        messages.append(HumanMessage(content=f"제목: {ex_title}\n설명: {ex_desc}"))
        messages.append(AIMessage(content=json.dumps({"category": ex_cat}, ensure_ascii=False)))
    messages.append(HumanMessage(content=f"제목: {title}\n설명: {description or '(없음)'}"))
    return messages


def _extract_category(text: str) -> str | None:
    """LLM 응답 문자열에서 카테고리 추출. 실패 시 None."""
    if not text:
        return None
    # 1차: JSON 파싱
    try:
        data = json.loads(text.strip())
        cat = (data.get("category") or "").strip()
        if cat in CATEGORY_SET:
            return cat
    except (json.JSONDecodeError, AttributeError):
        pass
    # 2차: 응답 안에 카테고리 단어 직접 포함된 경우
    for c in CATEGORIES:
        if c in text:
            return c
    return None


def classify_node(state: ClassifyState) -> dict:
    """Solar API 호출 → 카테고리 추출 → state 갱신."""
    messages = _build_messages(state["title"], state["description"])
    response = _llm.invoke(messages)
    category = _extract_category(response.content)
    return {"category": category, "attempt": state["attempt"] + 1}


def validate_node(state: ClassifyState) -> dict:
    """카테고리가 5종 안에 있는지 검증."""
    return {"is_valid": state.get("category") in CATEGORY_SET}


def fallback_node(state: ClassifyState) -> dict:
    """재시도 한도 초과 시 안전한 기본값."""
    return {"category": "기타", "is_valid": True}


def route(state: ClassifyState) -> str:
    if state.get("is_valid"):
        return "end"
    if state["attempt"] < MAX_ATTEMPTS:
        return "retry"
    return "fallback"


_builder = StateGraph(ClassifyState)
_builder.add_node("classify", classify_node)
_builder.add_node("validate", validate_node)
_builder.add_node("fallback", fallback_node)
_builder.set_entry_point("classify")
_builder.add_edge("classify", "validate")
_builder.add_conditional_edges(
    "validate",
    route,
    {"retry": "classify", "fallback": "fallback", "end": END},
)
_builder.add_edge("fallback", END)
_graph = _builder.compile()


def classify_event(title: str, description: str) -> str:
    """제목+설명을 Solar API에 보내서 카테고리 반환.

    카테고리: "면접" | "시험" | "약속" | "마감" | "기타"
    """
    initial: ClassifyState = {
        "title": title,
        "description": description or "",
        "category": None,
        "attempt": 0,
        "is_valid": False,
    }
    try:
        result = _graph.invoke(initial)
        category = result.get("category")
        return category if category in CATEGORY_SET else "기타"
    except Exception as exc:
        # 네트워크·인증·LLM 응답 이상 시 안전 폴백
        print(f"[classifier] 예외 발생, 기타로 폴백: {exc}")
        return "기타"


if __name__ == "__main__":
    samples = [
        # 정상 5종 (각 카테고리 1개 기대)
        ("A기업 인성면접", "최종 단계 임원 면접"),
        ("운영체제 기말고사", "프로세스·메모리 단원"),
        ("동기들이랑 점심", "학식 12시"),
        ("팀 프로젝트 발표 자료 제출", "PDF 마감 23:59"),
        ("정기 안과 검진", "오후 3시 예약"),
        # 모호 케이스 — 분류기 판단 관찰용
        ("친구 결혼식 사회 보기", "오후 2시 예식장"),
        ("도서관 자리 잡기", "아침 8시 입장"),
        ("부산 출장", "1박 2일"),
    ]
    print("=== classifier.py 로컬 테스트 ===")
    for title, desc in samples:
        category = classify_event(title, desc)
        print(f"[{category}] {title} — {desc}")
    print("=== 끝 ===")
