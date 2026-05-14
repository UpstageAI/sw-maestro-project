"""LangGraph state schema. ADR-0005 부록 정합.

상태 머신은 endpoint에서 instantiate된 입력 + 노드들이 기록하는 출력/안전 메타.
TypedDict default reducer는 overwrite — 노드는 변경할 필드만 dict로 return.
"""
from typing import Literal, Optional, TypedDict

from .contracts import Gender, MoodTag

SafetyViolation = Literal["honorific_missing", "diary_length", "caption_length"]


class DiaryState(TypedDict):
    # 메타
    session_id: str
    seq: int  # 1~4

    # 입력 (BFF forward)
    pet_id: str
    honorific: str
    species: str
    gender: Gender
    photo_signed_url: str
    keywords: str
    recent_diaries: list[str]

    # 재생성 (seq>=2)
    previous_diary_text: Optional[str]
    regen_feedback: Optional[str]

    # vision agent 산출 (analyze_image 노드가 채움, write_diary가 읽음)
    vision_description: Optional[str]

    # 출력 (write_diary 노드가 채움)
    diary_text: Optional[str]
    short_caption: Optional[str]
    mood_tag: Optional[MoodTag]

    # 안전 retry (state 내부, DB 영속 X)
    safety_retry_count: int  # 0부터 시작. call_llm마다 +1.
    safety_violation: Optional[SafetyViolation]
