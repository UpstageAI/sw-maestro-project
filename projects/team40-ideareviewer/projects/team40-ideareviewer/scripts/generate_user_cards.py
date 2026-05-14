"""RawNemotronPersona → TargetUserPersonaCard 변환 스크립트.

사용법:
    python scripts/generate_user_cards.py
"""

import argparse
import asyncio
import json
import os
import sys
from ast import literal_eval
from collections.abc import Awaitable, Callable
from functools import lru_cache
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
SELECTED_RAW_PATH = (
    Path(__file__).parent.parent / "data" / "personas" / "raw_personas.selected_100.json"
)
SELECTED_OUT_PATH = (
    Path(__file__).parent.parent / "data" / "personas" / "persona_cards.selected.json"
)

Converter = Callable[[RawNemotronPersona], Awaitable[TargetUserPersonaCard | None]]
Writer = Callable[[Path, list[TargetUserPersonaCard]], None]
DEFAULT_LLM_TIMEOUT_SECONDS = 90.0
DEFAULT_LLM_MAX_RETRIES = 5
DEFAULT_CONCURRENCY = 3
RATE_LIMIT_BACKOFF_SECONDS = 5.0
RATE_LIMIT_MAX_ATTEMPTS = 3


def configure_langsmith_tracing(enable: bool) -> None:
    value = "true" if enable else "false"
    os.environ["LANGSMITH_TRACING"] = value
    os.environ["LANGCHAIN_TRACING_V2"] = value


def configure_openai_client_platform(chat_model) -> None:
    """Avoid slow Windows WMI platform detection in the OpenAI SDK.

    Sets ``_platform`` to ``"Windows"`` and injects a lightweight
    ``platform_headers()`` method that skips arch / runtime detection
    (those WMI calls can take several seconds on Windows).
    """

    def _make_platform_headers(root_client):
        def platform_headers(self=root_client) -> dict:
            return {
                "X-Stainless-Lang": "python",
                "X-Stainless-Package-Version": self._version,
                "X-Stainless-OS": self._platform or "unknown",
                "X-Stainless-Arch": "unknown",
                "X-Stainless-Runtime": "CPython",
                "X-Stainless-Runtime-Version": "unknown",
            }

        return platform_headers

    for resource_name in ("client", "async_client"):
        resource = getattr(chat_model, resource_name, None)
        root_client = getattr(resource, "_client", None)
        if root_client is not None:
            root_client._platform = "Windows"
            if not callable(getattr(root_client, "platform_headers", None)):
                root_client.platform_headers = _make_platform_headers(root_client)


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

@lru_cache(maxsize=1)
def _get_structured_llm():
    """첫 호출 시점에만 LLM 클라이언트를 생성한다.

    Why: 모듈 import 시 즉시 생성하면 API 키 미설정/네트워크 상태에 import가
    좌우되고, `configure_langsmith_tracing`이 LLM 생성 이후에 호출되는 순서
    역전이 발생한다. 지연 초기화로 두 문제를 모두 회피한다.
    """
    chat_model = ChatUpstage(
        model="solar-pro3",
        timeout=DEFAULT_LLM_TIMEOUT_SECONDS,
        max_retries=DEFAULT_LLM_MAX_RETRIES,
    )
    configure_openai_client_platform(chat_model)
    return chat_model.with_structured_output(_LLMFields)


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
    chain = _PROMPT | _get_structured_llm()
    payload = {
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
    }
    for attempt in range(1, RATE_LIMIT_MAX_ATTEMPTS + 1):
        try:
            print(f"    API 요청 시작: {raw.uuid[:8]} (시도 {attempt})", flush=True)
            llm_fields: _LLMFields = await chain.ainvoke(payload)
            print(f"    API 응답 완료: {raw.uuid[:8]}", flush=True)
            break
        except Exception as e:
            if _is_rate_limit_error(e) and attempt < RATE_LIMIT_MAX_ATTEMPTS:
                wait = RATE_LIMIT_BACKOFF_SECONDS * attempt
                print(
                    f"  [rate limit] {raw.uuid[:8]} {wait:.0f}초 대기 후 재시도",
                    flush=True,
                )
                await asyncio.sleep(wait)
                continue
            print(f"  [오류] {raw.uuid[:8]}: {e}", flush=True)
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


def _is_rate_limit_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "429" in text or "too_many_requests" in text or "rate limit" in text


async def generate_cards(
    raws: list[RawNemotronPersona],
    out_path: Path,
    *,
    converter: Converter = _convert,
    concurrency: int = DEFAULT_CONCURRENCY,
    converter_timeout_seconds: float | None = DEFAULT_LLM_TIMEOUT_SECONDS,
    writer: Writer | None = None,
) -> list[TargetUserPersonaCard]:
    sem = asyncio.Semaphore(concurrency)

    async def _with_sem(
        raw: RawNemotronPersona,
        result_idx: int,
    ) -> tuple[int, TargetUserPersonaCard | None]:
        async with sem:
            print(f"  [{result_idx + 1}/{len(raws)}] {raw.uuid[:8]}... 변환 중", flush=True)
            try:
                card = await _run_converter(
                    converter,
                    raw,
                    timeout_seconds=converter_timeout_seconds,
                )
            except TimeoutError:
                print(
                    f"  [타임아웃] {raw.uuid[:8]}: {converter_timeout_seconds}초 초과",
                    flush=True,
                )
                card = None
            if card is not None:
                print(f"    → {card.card_id} ({card.display_name})", flush=True)
            return result_idx, card

    write_cards = writer or _write_cards
    results: list[TargetUserPersonaCard | None] = [None] * len(raws)
    tasks = [
        asyncio.create_task(_with_sem(raw, idx))
        for idx, raw in enumerate(raws)
    ]
    for task in asyncio.as_completed(tasks):
        result_idx, card = await task
        results[result_idx] = card
        if card is not None:
            write_cards(out_path, _completed_cards(results))

    cards = _completed_cards(results)
    write_cards(out_path, cards)
    print(f"  저장 완료: {len(cards)}개 → {out_path.name}")
    return cards


async def _run_converter(
    converter: Converter,
    raw: RawNemotronPersona,
    *,
    timeout_seconds: float | None,
) -> TargetUserPersonaCard | None:
    if timeout_seconds is None or timeout_seconds <= 0:
        return await converter(raw)
    return await asyncio.wait_for(converter(raw), timeout=timeout_seconds)


def _completed_cards(
    results: list[TargetUserPersonaCard | None],
) -> list[TargetUserPersonaCard]:
    return [card for card in results if card is not None]


def _write_cards(path: Path, cards: list[TargetUserPersonaCard]) -> None:
    path.write_text(
        json.dumps([card.model_dump() for card in cards], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def generate_cards_from_paths(
    *,
    raw_path: Path,
    out_path: Path,
    converter: Converter = _convert,
    concurrency: int = DEFAULT_CONCURRENCY,
    limit: int | None = None,
    converter_timeout_seconds: float | None = DEFAULT_LLM_TIMEOUT_SECONDS,
) -> list[TargetUserPersonaCard]:
    raw_list = json.loads(raw_path.read_text(encoding="utf-8"))
    if limit is not None:
        raw_list = raw_list[:limit]
    raws = [RawNemotronPersona(**_normalize_raw_item(r)) for r in raw_list]
    print(f"{len(raws)}개 페르소나 변환 시작")
    cards = await generate_cards(
        raws,
        out_path,
        converter=converter,
        concurrency=concurrency,
        converter_timeout_seconds=converter_timeout_seconds,
    )
    print(f"\n완료: {len(cards)}개 → {out_path}")
    return cards


def _normalize_raw_item(item: dict) -> dict:
    normalized = dict(item)
    for field_name in ("skills_and_expertise_list", "hobbies_and_interests_list"):
        value = normalized.get(field_name)
        if isinstance(value, str):
            normalized[field_name] = _parse_string_list(value)
    return normalized


def _parse_string_list(value: str) -> list[str]:
    stripped = value.strip()
    if not stripped:
        return []
    try:
        parsed = literal_eval(stripped)
    except (SyntaxError, ValueError):
        return [stripped]
    if isinstance(parsed, list):
        return [str(item) for item in parsed]
    return [str(parsed)]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-path", type=Path, default=RAW_PATH)
    parser.add_argument("--out-path", type=Path, default=OUT_PATH)
    parser.add_argument("--selected", action="store_true")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--converter-timeout-seconds", type=float, default=DEFAULT_LLM_TIMEOUT_SECONDS)
    parser.add_argument("--trace", action="store_true")
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    configure_langsmith_tracing(args.trace)
    raw_path = SELECTED_RAW_PATH if args.selected else args.raw_path
    out_path = SELECTED_OUT_PATH if args.selected else args.out_path
    await generate_cards_from_paths(
        raw_path=raw_path,
        out_path=out_path,
        concurrency=args.concurrency,
        limit=args.limit,
        converter_timeout_seconds=args.converter_timeout_seconds,
    )


if __name__ == "__main__":
    asyncio.run(main())
