import json
from langchain_core.prompts import ChatPromptTemplate

FILL_SYSTEM_PROMPT = """당신은 소설 장면의 누락된 시각 요소를 문맥에 맞게 추론해 채우는 전문가입니다.

입력으로 원문 텍스트와 현재 추출된 12개 장면 요소가 제공됩니다. 그 중 빈 문자열("")인 요소를 원문의 분위기와 맥락에 맞게 추론하여 채우세요.

규칙:
- 원문에 직접적인 단서가 없더라도, 장르·분위기·다른 요소들의 조합으로 합리적으로 추론하세요.
- 추론한 값은 구체적이고 시각적인 묘사여야 합니다. (예: "밤" → "깊은 밤, 달빛만이 비치는 어두운 밤")
- 각 요소값은 한국어로 작성하세요.
- 빈 값이 아닌 요소는 절대 수정하지 마세요. 그대로 유지하세요.
- 추론한 각 요소에 대해 fill_reason을 간단히 작성하세요."""

_prompt_template = ChatPromptTemplate.from_messages([
    ("system", FILL_SYSTEM_PROMPT),
    ("human", "원문:\n{novel_text}\n\n현재 장면 요소:\n{elements_json}\n\n빈 값인 요소를 채워주세요."),
])


def create_fill_messages(novel_text: str, elements_json: str) -> list[tuple[str, str]]:
    messages = _prompt_template.format_messages(novel_text=novel_text, elements_json=elements_json)
    return [(msg.type, msg.content) for msg in messages]
