"""Vision agent — 사진 → 한국어 시각 묘사 1단락.

분리 의도: 이미지 시각 정보 추출과 1인칭 작문 책임을 갈라 각 단계 프롬프트를
좁게 유지. write_diary는 이 산출(`vision_description`)만 받아 사진을 직접
보지 않는다.
"""
from functools import lru_cache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from ..config import get_settings
from ..prompts_loader import build_vision_system_message
from ..state import DiaryState


class VisionAnalysis(BaseModel):
    """vision agent의 structured output schema (BFF 노출 X)."""

    description: str = Field(min_length=100, max_length=600)


@lru_cache(maxsize=1)
def _vision_llm() -> Any:
    """structured outputs로 VisionAnalysis 강제하는 ChatOpenAI singleton.

    temperature 낮게 — 같은 사진에 대한 묘사 변동을 줄여 retry 시 일관성 유지.
    """
    get_settings()  # OPENAI_API_KEY를 os.environ에 export 보장.
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
    ).with_structured_output(VisionAnalysis)


def analyze_image(state: DiaryState) -> dict:
    system_text = build_vision_system_message(state)

    messages = [
        SystemMessage(content=system_text),
        HumanMessage(
            content=[
                {"type": "text", "text": "이 사진을 묘사해주세요."},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": state["photo_signed_url"],
                        "detail": "low",
                    },
                },
            ]
        ),
    ]

    result = _vision_llm().invoke(messages)
    assert isinstance(result, VisionAnalysis)

    return {"vision_description": result.description}
