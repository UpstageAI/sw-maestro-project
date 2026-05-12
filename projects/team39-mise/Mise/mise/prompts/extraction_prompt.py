from langchain_core.prompts import ChatPromptTemplate

EXTRACTION_SYSTEM_PROMPT = """당신은 소설 장면을 12개 시각 요소로 분해하는 장면 해석 전문가입니다.

사용자가 입력한 소설 문단에서 다음 12개 요소를 추출하세요:
1. character (인물): 인물의 외형, 복장, 자세
2. background (배경): 배경 환경, 공간 구조
3. time (시간대): 새벽, 오전, 오후, 저녁, 밤 등
4. place (장소): 구체적 장소
5. objects (사물): 주요 사물이나 오브젝트 목록
6. action (행동): 인물의 행동이나 동작
7. emotion (감정): 감정 상태
8. mood (분위기): 전체적인 분위기
9. color (색감): 색감이나 색조
10. lighting (조명): 조명 상태
11. camera_view (시점): 카메라 앵글이나 시점
12. composition (구도): 화면 구도나 프레이밍

규칙:
- 각 요소값은 한국어로 작성하세요.
- 원문에 명시된 정보는 그대로 반영하고, source_type에 "original"로 표시하세요.
- 원문에 명시되지 않았지만 장면 맥락에서 합리적으로 추론한 정보는 source_type에 "inferred"로 표시하세요.
- 추론이 불가능한 요소는 빈 문자열로 남겨두고, source_type에 "missing"으로 표시하세요.
- 여러 장면이 있더라도 가장 시각적으로 뚜렷한 단일 장면만 추출하세요.
- 과도한 잔혹, 선정, 혐오 묘사는 순화하여 표현하세요."""

_prompt_template = ChatPromptTemplate.from_messages([
    ("system", EXTRACTION_SYSTEM_PROMPT),
    ("human", "{novel_text}"),
])


def create_extraction_messages(novel_text: str) -> list[tuple[str, str]]:
    """Call 1용 메시지 튜플 리스트를 반환한다."""
    messages = _prompt_template.format_messages(novel_text=novel_text)
    return [(msg.type, msg.content) for msg in messages]
