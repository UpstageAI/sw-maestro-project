"""f0_parse — raw_input 자유 텍스트를 ServicePlanInput으로 구조화."""

import re

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage

from schemas import ServicePlanInput
from state import ProjectState

load_dotenv()

# with_structured_output(ServicePlanInput):
#   LLM 응답을 자유 텍스트가 아니라 ServicePlanInput Pydantic 모델로 바로 파싱해서 반환.
#   내부적으로 function calling / tool use를 사용해 JSON을 강제한다.
_llm = ChatUpstage(model="solar-pro3").with_structured_output(ServicePlanInput)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 IT 서비스 기획 분석가입니다. "
        "사용자가 입력한 자유 형식의 서비스 아이디어를 구조화된 기획안으로 파싱하세요. "
        "- raw_text는 원문 전체를 그대로 담으세요. "
        "- 입력에 명시되지 않은 정보는 None으로 두세요. "
        "- key_features는 3~5개로 정리하세요.",
    ),
    ("human", "{raw_input}"),
])


def _split_sentences(text: str) -> list[str]:
    return [
        part.strip(" \t\r\n.。")
        for part in re.split(r"(?<=[.!?。])\s+|\n+", text or "")
        if part.strip(" \t\r\n.。")
    ]


def _append_unique(items: list[str], value: str, limit: int) -> None:
    value = value.strip()
    if not value:
        return
    if any(value in item or item in value for item in items):
        return
    if len(items) < limit:
        items.append(value)


def _extract_target(raw_text: str) -> str | None:
    match = re.search(r"(.{2,40}?)(?:을|를)?\s*위한", raw_text)
    if match:
        return match.group(1).strip()
    match = re.search(r"(.{2,50}?와 .{2,50}?를)\s*직접\s*연결", raw_text)
    if match:
        return match.group(1).strip()
    return None


def _extract_key_features(raw_text: str) -> list[str]:
    features: list[str] = []
    for sentence in _split_sentences(raw_text):
        _append_unique(features, sentence, 5)
    return features


def _repair_brief(brief: ServicePlanInput, raw_text: str) -> ServicePlanInput:
    """Fill critical empty fields with conservative evidence from raw text."""
    raw = (raw_text or brief.raw_text or "").strip()
    updates: dict[str, object] = {"raw_text": raw}

    if not brief.description:
        sentences = _split_sentences(raw)
        if sentences:
            updates["description"] = sentences[0]

    if not brief.target:
        target = _extract_target(raw)
        if target:
            updates["target"] = target

    features = [feature.strip() for feature in brief.key_features if feature.strip()]
    for feature in _extract_key_features(raw):
        _append_unique(features, feature, 5)
    if features != brief.key_features:
        updates["key_features"] = features

    return brief.model_copy(update=updates)


def f0_parse(state: ProjectState) -> dict:
    # state["raw_input"]: 사용자가 graph.invoke({"raw_input": "..."})로 넘긴 자유 텍스트
    chain = _PROMPT | _llm
    brief: ServicePlanInput = chain.invoke({"raw_input": state["raw_input"]})
    brief = _repair_brief(brief, state["raw_input"])

    # LangGraph 노드는 반드시 dict를 반환해야 한다.
    # {"brief": brief} → LangGraph가 state["brief"] 필드를 이 값으로 덮어쓴다.
    return {"brief": brief}
