"""RawNemotronPersona → TargetUserPersonaCard 변환 스크립트.

사용법:
    python scripts/generate_user_cards.py
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from pydantic import BaseModel, Field

from schemas import DEFAULT_GUARDRAILS, RawNemotronPersona, TargetUserPersonaCard

load_dotenv()

RAW_PATH = Path(__file__).parent.parent / "data" / "personas" / "raw_personas.seed.json"
OUT_PATH = Path(__file__).parent.parent / "data" / "personas" / "persona_cards.seed.json"


class _LLMFields(BaseModel):
    """LLM이 생성할 텍스트 필드만. 나머지는 raw 데이터에서 직접 추출."""

    display_name: str = Field(description="페르소나의 한국 이름 (예: 민금자)")
    one_line_summary: str = Field(description="이 사람을 한 줄로 설명")
    life_context: str = Field(description="현재 삶의 맥락 2~3문장")
    user_goals: list[str] = Field(description="주요 목표 3개")
    pain_points: list[str] = Field(description="불편함/어려움 3개")
    positive_triggers: list[str] = Field(description="서비스에 긍정 반응하는 상황 3개")
    negative_triggers: list[str] = Field(description="서비스에 부정 반응하는 상황 3개")
    speaking_style: str = Field(description="말투 특징 한 줄")


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 사용자 프로파일링 전문가입니다. "
        "주어진 페르소나 원문을 분석해 각 필드를 한국어로 작성하세요. "
        "원문에 없는 정보를 추측하거나 만들어내지 마세요.",
    ),
    (
        "human",
        "나이: {age}세 / 성별: {sex} / 직업: {occupation} / 지역: {province}\n"
        "학력: {education_level} / 거주 형태: {housing_type}\n\n"
        "인물 설명: {persona}\n"
        "직업적 특성: {professional_persona}\n"
        "문화적 배경: {cultural_background}\n"
        "여가/취미: {hobbies_and_interests}\n"
        "가족 관계: {family_persona}\n"
        "목표: {career_goals_and_ambitions}",
    ),
])

_llm = ChatUpstage(model="solar-pro3").with_structured_output(_LLMFields)


def _age_group(age: int | None) -> str:
    if age is None:
        return "unknown"
    if age < 30:
        return "20s"
    elif age < 40:
        return "30s"
    elif age < 50:
        return "40s"
    elif age < 60:
        return "50s"
    elif age < 70:
        return "60s"
    return "70plus"


async def _convert(raw: RawNemotronPersona) -> TargetUserPersonaCard | None:
    chain = _PROMPT | _llm
    try:
        llm_fields: _LLMFields = await chain.ainvoke({
            "age": raw.age,
            "sex": raw.sex or "",
            "occupation": raw.occupation or "",
            "province": raw.province or "",
            "education_level": raw.education_level or "",
            "housing_type": raw.housing_type or "",
            "persona": raw.persona or "",
            "professional_persona": raw.professional_persona or "",
            "cultural_background": raw.cultural_background or "",
            "hobbies_and_interests": raw.hobbies_and_interests or "",
            "family_persona": raw.family_persona or "",
            "career_goals_and_ambitions": raw.career_goals_and_ambitions or "",
        })
    except Exception as e:
        print(f"  [오류] {raw.uuid[:8]}: {e}")
        return None

    age_grp = _age_group(raw.age)
    return TargetUserPersonaCard(
        card_id=f"persona_{raw.uuid[:12]}",
        source_uuid=raw.uuid,
        display_name=llm_fields.display_name,
        age_group=age_grp,
        sex=raw.sex,
        occupation=raw.occupation,
        region=raw.province,
        one_line_summary=llm_fields.one_line_summary,
        life_context=llm_fields.life_context,
        user_goals=llm_fields.user_goals,
        pain_points=llm_fields.pain_points,
        positive_triggers=llm_fields.positive_triggers,
        negative_triggers=llm_fields.negative_triggers,
        speaking_style=llm_fields.speaking_style,
        guardrails=DEFAULT_GUARDRAILS.copy(),
    )


async def generate_cards(raws: list[RawNemotronPersona], out_path: Path) -> list[TargetUserPersonaCard]:
    sem = asyncio.Semaphore(5)

    async def _with_sem(raw: RawNemotronPersona, idx: int) -> TargetUserPersonaCard | None:
        async with sem:
            print(f"  [{idx}/{len(raws)}] {raw.uuid[:8]}... 변환 중")
            card = await _convert(raw)
            if card:
                print(f"    → {card.card_id} ({card.display_name})")
            return card

    results = await asyncio.gather(*[_with_sem(r, i) for i, r in enumerate(raws, 1)])
    cards = [c for c in results if c is not None]
    out_path.write_text(
        json.dumps([c.model_dump() for c in cards], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"  저장 완료: {len(cards)}개 → {out_path.name}")
    return cards


async def main() -> None:
    raw_list = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    raws = [RawNemotronPersona(**r) for r in raw_list]
    print(f"{len(raws)}개 페르소나 변환 시작")
    await generate_cards(raws, OUT_PATH)
    print(f"\n완료: {len(raws)}개 → {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
