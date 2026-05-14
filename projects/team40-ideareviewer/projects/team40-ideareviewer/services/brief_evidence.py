"""Deterministic text helpers for grounding artifacts in the service brief."""

from __future__ import annotations

import re

from schemas import ServicePlanInput

STOPWORDS = {
    "서비스",
    "기획",
    "사용자",
    "기능",
    "필요",
    "확인",
    "가능",
    "제공",
    "있는지",
    "합니다",
}

SOLUTION_CUES = {
    "자동화",
    "대시보드",
    "모니터링",
    "인증",
    "추천",
    "알고리즘",
    "챗봇",
    "보험",
    "정산",
    "등급",
    "실시간",
    "추적",
}

NUMERIC_PATTERN = re.compile(r"\d+(?:[.,]\d+)?\s*(?:%|퍼센트|원|만원|개|명|일|주|개월|년|시|분|회)?")


def text_terms(text: str) -> set[str]:
    return {
        _normalize_token(token)
        for token in re.findall(r"[가-힣A-Za-z0-9]+", text or "")
        if len(_normalize_token(token)) >= 2 and _normalize_token(token) not in STOPWORDS
    }


def numeric_terms(text: str) -> set[str]:
    return {
        re.sub(r"\s+", "", match.group(0))
        for match in NUMERIC_PATTERN.finditer(text or "")
    }


def brief_terms(brief: ServicePlanInput) -> set[str]:
    return text_terms(" ".join([
        brief.raw_text or "",
        brief.title or "",
        brief.description or "",
        brief.target or "",
        " ".join(brief.key_features),
        brief.concerns or "",
    ]))


def feature_terms(brief: ServicePlanInput) -> set[str]:
    return text_terms(" ".join([
        " ".join(brief.key_features),
        brief.description or "",
        brief.concerns or "",
    ]))


def has_brief_feature_overlap(text: str, brief: ServicePlanInput) -> bool:
    return bool(text_terms(text) & feature_terms(brief))


def introduces_unsupported_solution(text: str, brief: ServicePlanInput) -> bool:
    terms = text_terms(text)
    allowed = brief_terms(brief)
    introduced_solution_terms = (terms & SOLUTION_CUES) - allowed
    if introduced_solution_terms:
        return True
    cue_in_text = any(cue in (text or "") for cue in SOLUTION_CUES)
    introduced_terms = terms - allowed - STOPWORDS
    return cue_in_text and bool(introduced_terms)


def _normalize_token(token: str) -> str:
    value = token.strip()
    for suffix in (
        "으로",
        "에서",
        "에게",
        "하고",
        "한다",
        "하는",
        "하며",
        "으로",
        "과",
        "와",
        "을",
        "를",
        "은",
        "는",
        "이",
        "가",
    ):
        if len(value) > len(suffix) + 1 and value.endswith(suffix):
            return value[: -len(suffix)]
    return value
