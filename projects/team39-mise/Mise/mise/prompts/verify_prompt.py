import json
from langchain_core.prompts import ChatPromptTemplate

VERIFY_SYSTEM_PROMPT = """당신은 소설 장면 분석의 일관성을 검증하는 전문가입니다.

입력으로 원문 텍스트와 보완이 완료된 12개 장면 요소가 제공됩니다. AI가 추론해 채운 값이 원문의 분위기, 장르, 시대적 배경과 충돌하지 않는지 검증하세요.

검증 항목:
1. 시대적 일관성: 원문이 중세 판타지인데 현대적 요소가 들어가지 않았는지
2. 분위기 일관성: 어두운 장면에 밝은 요소가 충돌하지 않는지
3. 논리적 일관성: 장소·시간·행동이 서로 모순되지 않는지
4. 시각적 적절성: 이미지 생성 시 시각적으로 표현 가능한 값인지

규칙:
- 모든 요소를 검토하되, 충돌이나 문제가 있는 요소만 수정하세요.
- 충돌이 없는 요소는 그대로 유지하세요.
- 수정한 이유를 수정 사항별로 서술하세요.
- 전체적으로 충돌이 없다면 elements를 그대로 반환하세요."""

_prompt_template = ChatPromptTemplate.from_messages([
    ("system", VERIFY_SYSTEM_PROMPT),
    ("human", "원문:\n{novel_text}\n\n검증할 장면 요소:\n{elements_json}\n\n일관성을 검증해주세요."),
])


def create_verify_messages(novel_text: str, elements_json: str) -> list[tuple[str, str]]:
    messages = _prompt_template.format_messages(novel_text=novel_text, elements_json=elements_json)
    return [(msg.type, msg.content) for msg in messages]
