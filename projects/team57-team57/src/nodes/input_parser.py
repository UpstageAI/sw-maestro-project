from __future__ import annotations

import re

from src.nodes.logging_utils import append_backend_log
from src.state import ReviewAgentState
from src.tools.safety_tools import contains_korean, mask_personal_information, normalize_whitespace


def run_input_parser_node(state: ReviewAgentState) -> ReviewAgentState:
    chunks = _split_reviews(state.raw_input_text)
    seen: set[str] = set()
    parsed_reviews: list[dict[str, str]] = []
    warnings = list(state.warnings)
    duplicate_count = 0
    non_korean_count = 0

    for chunk in chunks:
        normalized = normalize_whitespace(chunk)
        if not normalized:
            continue
        if normalized in seen:
            duplicate_count += 1
            continue
        seen.add(normalized)

        masked = mask_personal_information(normalized)
        if not contains_korean(masked):
            warnings.append(f"한국어 리뷰가 아니어서 제외됨: {normalized[:30]}")
            non_korean_count += 1
            continue

        parsed_reviews.append(
            {
                "original_text": normalized,
                "masked_text": masked,
            }
        )

    state.parsed_reviews = parsed_reviews
    state.warnings = warnings
    state.execution_log.append(f"InputParserNode: parsed {len(parsed_reviews)} reviews")
    append_backend_log(
        state,
        node_name="InputParserNode",
        input_summary=f"리뷰 {len(chunks)}건 입력",
        output_summary=f"리뷰 {len(parsed_reviews)}건 파싱, 중복 {duplicate_count}건 제거, 비한국어 {non_korean_count}건 제외",
        db_saved=False,
        has_warning=duplicate_count > 0 or non_korean_count > 0,
    )
    return state


def _split_reviews(raw_text: str) -> list[str]:
    if not raw_text.strip():
        return []

    lines = [line.strip() for line in raw_text.splitlines()]
    non_empty_lines = [line for line in lines if line]

    numbered = any(re.match(r"^\d+[.)]\s*", line) for line in non_empty_lines)
    if numbered:
        return [re.sub(r"^\d+[.)]\s*", "", line).strip() for line in non_empty_lines]

    if "\n\n" in raw_text:
        return [chunk.strip() for chunk in re.split(r"\n\s*\n", raw_text) if chunk.strip()]

    return non_empty_lines
