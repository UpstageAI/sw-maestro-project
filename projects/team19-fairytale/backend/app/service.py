"""AI 모듈 진입점.

FastAPI / 다른 호출자는 이 함수만 import 해서 사용하면 된다.
LangGraph 내부 구조(노드/상태)에 의존할 필요가 없다.

    from app.service import generate_story
    story = generate_story(req)   # req: StoryRequest

예외:
    LLMUnavailableError   → 업스트림 LLM 호출 자체 실패 (503으로 매핑 권장)
    StoryParsingError     → LLM 응답을 파싱해 결과를 만들 수 없음 (502)
    StoryGenerationError  → 그 외 생성 실패 (422)
"""
from __future__ import annotations

from app.exceptions import (
    LLMUnavailableError,
    StoryGenerationError,
    StoryParsingError,
)
from app.graph.builder import graph
from app.models.api import StoryRequest, Story


def generate_story(req: StoryRequest) -> Story:
    """일기 + 인물 관계 → 동화 1편 생성 (동기 호출)."""
    initial = {
        "diary_date": req.diary_date.isoformat(),
        "diary": req.diary,
        "people": [p.model_dump(mode="json") for p in req.people],
    }

    try:
        final = graph.invoke(initial)
    except (LLMUnavailableError, StoryGenerationError):
        # 노드에서 이미 도메인 예외로 감싸진 경우 그대로 전파.
        raise
    except Exception as e:
        # 예상치 못한 예외 (LangGraph 내부 등) → 도메인 예외로 변환.
        raise StoryGenerationError(
            f"예기치 못한 오류: {type(e).__name__}: {e}",
        ) from e

    s = final.get("story") or {}
    title, body = s.get("title", "").strip(), s.get("body", "").strip()
    if not body:
        raise StoryParsingError("LLM 응답에서 동화 본문을 추출하지 못했습니다.")

    return Story(title=title or "오늘의 동화", body=body)
