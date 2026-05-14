import json
from langchain_core.prompts import ChatPromptTemplate

PROMPT_GENERATOR_SYSTEM_PROMPT = """당신은 장면 분석 데이터를 이미지 생성용 영문 프롬프트로 변환하는 전문가입니다.

입력으로 한국어 장면 요소가 제공됩니다. 이를 이미지 생성 AI가 이해할 수 있는 영문 프롬프트로 변환하세요.

positive_prompt 작성 규칙:
- 모든 설명은 영어로 작성하세요.
- 쉼표로 구분된 키워드 형태로 작성하세요.
- 순서: {{스타일}}, {{인물 묘사}}, {{행동}}, {{배경}}, {{주요 사물}}, {{분위기}}, {{조명}}, {{색감}}, {{구도}}, high quality, detailed
- 구체적이고 시각적인 표현을 사용하세요.

negative_prompt 작성 규칙:
- 반드시 다음 기본 항목을 포함하세요: excessive gore, explicit content, hate symbols, blurry, low quality, deformed, text, watermark, signature, out of frame
- 장면과 어울리지 않는 요소를 추가로 제외하세요.

missing_info:
- 입력 요소 중 빈 문자열이거나 추론이 불가능한 항목의 한국어 설명을 나열하세요.
- 모든 정보가 충분하면 빈 리스트를 반환하세요."""

_prompt_template = ChatPromptTemplate.from_messages([
    ("system", PROMPT_GENERATOR_SYSTEM_PROMPT),
    ("human", "장면 요소:\n{elements_json}\n\n이미지 스타일: {style}"),
])


def create_prompt_messages(elements: dict, style: str = "cinematic") -> list[tuple[str, str]]:
    """Call 2용 메시지 튜플 리스트를 반환한다."""
    elements_json = json.dumps(elements, ensure_ascii=False, indent=2)
    messages = _prompt_template.format_messages(elements_json=elements_json, style=style)
    return [(msg.type, msg.content) for msg in messages]
