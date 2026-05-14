"""특허 명세서 생성 엔드포인트의 비즈니스 로직.

agent.generate_document()를 호출해 실제 LLM 응답을 만들고,
LLM/검색이 실패하면 examples/sample_response.json을 fallback으로 반환한다.
응답 shape는 docs/API_CONTRACT.md를 그대로 따른다.
"""

from __future__ import annotations

import copy
import json
import logging
from pathlib import Path
from typing import Any

try:
    from app.agent import generate_document
except ImportError:
    from backend.app.agent import generate_document


SAMPLE_RESPONSE_PATH = Path(__file__).resolve().parents[2] / "examples" / "sample_response.json"
FALLBACK_WARNING = "LLM 호출 또는 검색에 실패하여 데모용 샘플 결과로 표시합니다."

logger = logging.getLogger(__name__)


def _load_sample_response() -> dict[str, Any]:
    with SAMPLE_RESPONSE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def _build_fallback(idea: str, tone: str, use_search: bool) -> dict[str, Any]:
    response = copy.deepcopy(_load_sample_response())
    response["input"] = {"idea": idea, "tone": tone, "use_search": use_search}
    response["warnings"] = [*response.get("warnings", []), FALLBACK_WARNING]
    return response


def generate_patent_document(
    idea: str,
    tone: str = "serious",
    use_search: bool = True,
) -> dict[str, Any]:
    sample = _load_sample_response()
    try:
        document, sources = generate_document(idea)
    except Exception as exc:
        logger.warning("generate_document failed, using fallback: %s", exc)
        return _build_fallback(idea, tone, use_search)

    return {
        "id": sample.get("id", "demo-001"),
        "status": "completed",
        "input": {"idea": idea, "tone": tone, "use_search": use_search},
        "document": document,
        "sources": sources,
        "warnings": sample.get("warnings", []),
    }
