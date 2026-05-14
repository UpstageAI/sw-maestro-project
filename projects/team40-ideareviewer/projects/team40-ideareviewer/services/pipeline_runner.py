"""UI-friendly helpers for running the persona review pipeline."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from schemas import RawNemotronPersona

load_dotenv()

ROOT_DIR = Path(__file__).parent.parent
RAW_PERSONAS_PATH = ROOT_DIR / "data" / "personas" / "raw_personas.seed.json"
PERSONA_CARDS_PATH = ROOT_DIR / "data" / "personas" / "persona_cards.seed.json"
SAMPLE_BRIEF_PATH = ROOT_DIR / "data" / "service_plans" / "sample_brief.seed.json"

NODE_LABELS = {
    "f0_parse": "기획 내용 분석",
    "select_personas": "가상 사용자 패널 선정",
    "generate_opinion": "1차 사용자 반응 생성",
    "collect_opinions": "1차 반응 취합",
    "generate_review": "페르소나 간 교차 검토",
    "collect_reviews": "교차 검토 취합",
    "supervisor_finalize": "최종 리포트 작성",
}


@dataclass(frozen=True)
class PipelineEvent:
    node_name: str
    label: str
    update_keys: list[str]
    update: dict[str, Any]


@dataclass(frozen=True)
class PersonaCardStatus:
    exists: bool
    count: int
    path: Path


@dataclass(frozen=True)
class LangSmithStatus:
    tracing_enabled: bool
    project: str
    endpoint: str
    has_api_key: bool


GraphStreamer = Callable[..., Iterable[dict[str, dict[str, Any] | None]]]


def compose_review_input(
    service_name: str,
    stage: str,
    focus_areas: list[str],
    description: str,
) -> str:
    """Combine product-style form fields into the raw graph input."""
    parts = []
    if service_name.strip():
        parts.append(f"서비스 이름: {service_name.strip()}")
    if stage.strip():
        parts.append(f"현재 단계: {stage.strip()}")
    if focus_areas:
        parts.append(f"중점 검토 항목: {', '.join(focus_areas)}")
    parts.append("기획 설명:")
    parts.append(description.strip())
    return "\n\n".join(parts).strip()


def load_sample_raw_input() -> str:
    if not SAMPLE_BRIEF_PATH.exists():
        return (
            "고령층이 병원 예약, 복약 알림, 보호자 공유를 쉽게 할 수 있는 "
            "모바일 서비스를 만들고 싶습니다. 특히 입력 과정이 어렵지 않은지, "
            "신뢰할 수 있는 서비스로 느껴질지 검토받고 싶습니다."
        )

    payload = json.loads(SAMPLE_BRIEF_PATH.read_text(encoding="utf-8"))
    return str(payload.get("raw_text") or "").strip()


def get_persona_card_status() -> PersonaCardStatus:
    if not PERSONA_CARDS_PATH.exists():
        return PersonaCardStatus(exists=False, count=0, path=PERSONA_CARDS_PATH)

    raw_cards = json.loads(PERSONA_CARDS_PATH.read_text(encoding="utf-8"))
    return PersonaCardStatus(exists=True, count=len(raw_cards), path=PERSONA_CARDS_PATH)


def get_langsmith_status() -> LangSmithStatus:
    tracing_value = os.getenv("LANGSMITH_TRACING", "").strip().lower()
    tracing_enabled = tracing_value in {"1", "true", "yes", "on"}
    return LangSmithStatus(
        tracing_enabled=tracing_enabled,
        project=os.getenv("LANGSMITH_PROJECT", "default"),
        endpoint=os.getenv("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"),
        has_api_key=bool(os.getenv("LANGSMITH_API_KEY")),
    )


def regenerate_persona_cards() -> None:
    from scripts.generate_user_cards import generate_cards

    raw_list = json.loads(RAW_PERSONAS_PATH.read_text(encoding="utf-8"))
    raws = [RawNemotronPersona(**item) for item in raw_list]
    asyncio.run(generate_cards(raws, PERSONA_CARDS_PATH))


def make_pipeline_event(node_name: str, update: dict[str, Any] | None) -> PipelineEvent:
    update = update or {}
    update_keys = [key for key, value in update.items() if value is not None]
    return PipelineEvent(
        node_name=node_name,
        label=NODE_LABELS.get(node_name, node_name),
        update_keys=update_keys,
        update=update,
    )


def _default_graph_streamer(
    payload: dict[str, Any],
    *,
    stream_mode: str,
) -> Iterable[dict[str, dict[str, Any] | None]]:
    from graph import graph

    return graph.stream(payload, stream_mode=stream_mode)


def stream_pipeline(
    raw_input: str,
    graph_streamer: GraphStreamer | None = None,
) -> Iterator[PipelineEvent]:
    if not raw_input.strip():
        raise ValueError("검토할 기획 내용을 입력해 주세요.")

    streamer = graph_streamer or _default_graph_streamer
    for chunk in streamer({"raw_input": raw_input}, stream_mode="updates"):
        for node_name, update in chunk.items():
            yield make_pipeline_event(node_name, update)
