import json
from typing import Any

from langchain_core.prompts import ChatPromptTemplate

from mise.prompts.prompt_generator import PROMPT_GENERATOR_SYSTEM_PROMPT

FOCUSED_PROMPT_GENERATOR_SYSTEM_PROMPT = PROMPT_GENERATOR_SYSTEM_PROMPT + """

추가 규칙 - 변경된 요소 강조:
사용자가 일부 요소만 수정해 재생성을 요청하는 경우 "변경된 요소" 목록이 별도로 제공됩니다.
이 항목들이 결과 이미지에 명확히 반영되도록 다음 규칙을 반드시 따르세요.

1. 위치 강조: positive_prompt에서 변경된 요소에 해당하는 키워드를 스타일 토큰 바로 뒤(맨 앞쪽)에 배치하세요.
2. 구체성 강화: 변경된 요소는 단일 키워드가 아니라 2~3개의 시각적 형용사를 결합한 구체적인 묘사로 작성하세요. (예: "young man" → "young man with sharp features, lean build, determined expression")
3. 재진술: 변경된 요소의 특징을 프롬프트 내 다른 적절한 섹션(분위기, 조명, 구도 중 1곳)에서 한 번 더 자연스럽게 재진술해 가중치를 보강하세요.
4. 경쟁 토큰 축소: 변경되지 않은 요소는 간결한 단일 키워드 형태로 표현해 변경된 요소가 시각적으로 도드라지도록 하세요.
5. 부정 프롬프트 강화: 변경된 요소와 시각적으로 충돌할 수 있는 통상적인 대안을 negative_prompt에 추가하세요. (예: character가 "청년"으로 바뀐 경우 "elderly, old man, child" 추가)
"""

_focused_prompt_template = ChatPromptTemplate.from_messages([
    ("system", FOCUSED_PROMPT_GENERATOR_SYSTEM_PROMPT),
    ("human", "장면 요소:\n{elements_json}\n\n변경된 요소 (강조 대상):\n{changed_json}\n\n이미지 스타일: {style}"),
])


def create_focused_prompt_messages(
    elements: dict[str, Any],
    changed_values: dict[str, Any],
    style: str = "cinematic",
) -> list[tuple[str, str]]:
    """변경된 요소(changed_values)를 강조하는 Call 2용 메시지 튜플 리스트를 반환한다."""
    elements_json = json.dumps(elements, ensure_ascii=False, indent=2)
    changed_json = json.dumps(changed_values, ensure_ascii=False, indent=2)
    messages = _focused_prompt_template.format_messages(
        elements_json=elements_json,
        changed_json=changed_json,
        style=style,
    )
    return [(msg.type, msg.content) for msg in messages]
