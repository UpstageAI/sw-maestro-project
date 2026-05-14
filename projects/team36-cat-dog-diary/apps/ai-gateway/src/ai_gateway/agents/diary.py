"""Diary agent — 텍스트 입력만으로 1인칭 일기 작성 + safety_check.

write_diary는 이미지를 직접 받지 않는다. analyze_image가 채운
state["vision_description"]를 user 프롬프트의 placeholder로 받아 작문한다.
사진 토큰은 vision agent에서만 1회 소비.

`safety_retry_count`는 이름 그대로 두지만 의미는 "write_diary 호출 횟수".
violation 시 retry edge는 write_diary로만 돌아가며 vision은 재호출하지 않는다.
"""
from functools import lru_cache
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END

from ..config import get_settings
from ..contracts import DiaryGenerationResult
from ..prompts_loader import build_system_message, build_user_message
from ..state import DiaryState

# write_diary 호출 max: 첫 호출 + retry 1회 = 2회.
SAFETY_MAX_CALLS = 2

# system 프롬프트의 honorific placeholder를 LLM이 본문에 그대로 베끼는 경우
# 안전망. system.md 가드가 1차, write_diary 출력 후처리가 2차.
_HONORIFIC_PLACEHOLDERS = ("{{ honorific }}", "{{honorific}}", "{honorific}")


def _fix_honorific(text: str, honorific: str) -> str:
    if not honorific:
        return text
    for pat in _HONORIFIC_PLACEHOLDERS:
        text = text.replace(pat, honorific)
    return text


@lru_cache(maxsize=1)
def _diary_llm() -> Any:
    """structured outputs로 DiaryGenerationResult 강제하는 ChatOpenAI singleton."""
    get_settings()  # OPENAI_API_KEY를 os.environ에 export 보장.
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,
    ).with_structured_output(DiaryGenerationResult)


def write_diary(state: DiaryState) -> dict:
    system_text = build_system_message(state)
    user_text = build_user_message(state)

    messages = [
        SystemMessage(content=system_text),
        HumanMessage(content=user_text),
    ]

    result = _diary_llm().invoke(messages)
    assert isinstance(result, DiaryGenerationResult)

    honorific = state["honorific"]
    return {
        "diary_text": _fix_honorific(result.diary_text, honorific),
        "short_caption": _fix_honorific(result.short_caption, honorific),
        "mood_tag": result.mood_tag,
        "safety_retry_count": state["safety_retry_count"] + 1,
    }


def safety_check(state: DiaryState) -> dict:
    """ADR-0005 부록 의사코드: honorific substring + 길이 sanity."""
    diary = state.get("diary_text") or ""
    caption = state.get("short_caption") or ""
    honorific = state["honorific"]

    if honorific not in diary:
        return {"safety_violation": "honorific_missing"}
    if not 50 <= len(diary) <= 1000:
        return {"safety_violation": "diary_length"}
    if not 1 <= len(caption) <= 100:
        return {"safety_violation": "caption_length"}
    return {"safety_violation": None}


def should_retry(state: DiaryState) -> str:
    """conditional edge — violation && safety_retry_count < SAFETY_MAX_CALLS → write_diary."""
    if state["safety_violation"] and state["safety_retry_count"] < SAFETY_MAX_CALLS:
        return "write_diary"
    return END
