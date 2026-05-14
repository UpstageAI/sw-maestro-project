"""LLM 호출로 특허 명세서 7섹션을 생성한다.

패턴: ChromaDB 검색 1회로 RAG 컨텍스트 확보 + ChatOpenAI(Solar) 단일 호출로 JSON 생성.
LangChain Agent 루프는 사용하지 않는다. 7섹션 JSON 강제 출력의 안정성을 위해 단순 패턴 채택.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from langchain_openai import ChatOpenAI

try:
    from app.tools import ChromaPatentTool
except ImportError:
    from backend.app.tools import ChromaPatentTool


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"

REQUIRED_SECTIONS = {
    "title",
    "technical_field",
    "background",
    "problem",
    "configuration",
    "claims",
    "summary",
}
EXPECTED_CLAIMS_COUNT = 4


def _load_prompt(filename: str) -> str:
    """prompts/*.md에서 ```text 블록 안 본문만 추출. 블록 없으면 파일 전체."""
    text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
    match = re.search(r"```text\n(.*?)\n```", text, re.DOTALL)
    return match.group(1) if match else text


def _safe_search_context(idea: str, match_count: int = 3) -> tuple[str, list[dict[str, Any]]]:
    """ChromaDB 검색. 실패해도 LLM 호출은 계속할 수 있도록 빈 컨텍스트로 graceful 처리.

    Returns:
        (LLM에 넣을 컨텍스트 문자열, sources 매핑용 결과 리스트)
    """
    try:
        chroma = ChromaPatentTool.from_env()
        raw_json = chroma.search_for_context(idea, match_count=match_count)
        parsed = json.loads(raw_json)
        results = parsed.get("results", []) or []
        return raw_json, results
    except Exception:
        return '{"query": "", "count": 0, "results": []}', []


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.getenv("OPENAI_DESC_MODEL", "solar-mini-250422"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        api_key=os.getenv("OPENAI_API_KEY"),
        temperature=0.7,
    )


def _parse_json_response(content: str) -> dict[str, Any]:
    """LLM이 markdown 코드블록(```json ... ```)으로 감싸도 받아낸다."""
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*\n", "", stripped)
        stripped = re.sub(r"\n```\s*$", "", stripped)
    return json.loads(stripped)


def _validate_document(document: dict[str, Any]) -> None:
    missing = REQUIRED_SECTIONS - set(document.keys())
    if missing:
        raise ValueError(f"LLM 응답에 누락된 섹션: {missing}")
    claims = document.get("claims")
    if not isinstance(claims, list) or len(claims) != EXPECTED_CLAIMS_COUNT:
        raise ValueError(
            f"claims는 길이 {EXPECTED_CLAIMS_COUNT}의 문자열 배열이어야 함, 실제: {claims!r}"
        )


def _to_sources(search_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    """ChromaDB 결과 → API 컨트랙트의 sources 형식으로 변환.

    KIPRIS 특허는 공개 URL이 없어 빈 문자열로 둔다. 프론트는 비어 있어도 처리 가능.
    """
    sources: list[dict[str, str]] = []
    for item in search_results:
        title = item.get("title") or item.get("inventionTitle") or ""
        snippet = item.get("description") or ""
        sources.append({"title": title, "url": "", "snippet": snippet[:200]})
    return sources


def generate_document(idea: str) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """아이디어 → (7섹션 dict, sources 리스트).

    예외는 호출자가 처리(generator.py에서 fallback 발동).
    """
    system_prompt = _load_prompt("system_prompt.md")
    search_context, search_results = _safe_search_context(idea)

    user_message = (
        f"발명 아이디어:\n{idea}\n\n"
        f"관련 특허 검색 결과(참고용, 사실로 인용하지 말 것):\n{search_context}\n\n"
        "위 시스템 메시지의 형식 규칙을 그대로 지켜 JSON 객체만 출력해."
    )

    llm = _build_llm()
    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
    )

    document = _parse_json_response(response.content)
    _validate_document(document)

    sources = _to_sources(search_results)
    return document, sources
