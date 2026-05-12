"""직무 분류기 — JD 텍스트에서 JobFamily 를 추론.

전략: 키워드 매칭 우선 → 모호하면 LLM 폴백.
- 키워드만으로 명확하면 LLM 호출 없이 즉시 결정 (대부분의 JD).
- 동률·약한 점수만 LLM 에 위임.
- LLM 호출 자체가 실패해도 'general' 로 안전하게 떨어짐.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import get_args

from openai import OpenAI

from models.types import JobFamily

logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL")
SOLAR_BASE_URL = os.getenv("SOLAR_BASE_URL")
SOLAR_API_KEY_ENV = "UPSTAGE_API_KEY"

_VALID_FAMILIES: set[str] = set(get_args(JobFamily))

# ─────────────────────────────────────────────
# 키워드 사전 (lowercase 비교)
# ─────────────────────────────────────────────
JOB_KEYWORDS: dict[JobFamily, list[str]] = {
    "engineering": [
        "개발자", "엔지니어", "백엔드", "프론트엔드", "풀스택", "devops", "sre",
        "데이터 엔지니어", "ml", "머신러닝", "ai 엔지니어", "ios", "android",
        "안드로이드", "qa", "테스트", "임베디드", "보안 엔지니어", "플랫폼 엔지니어",
        "python", "java", "kotlin", "spring", "react", "vue", "node", "fastapi",
        "kubernetes", "docker",
    ],
    "design": [
        "디자이너", "ux", "ui", "bx", "그래픽 디자이너", "프로덕트 디자이너",
        "비주얼 디자이너", "모션 디자이너", "브랜드 디자이너", "리서처",
        "ux 리서처", "사용자 리서치",
    ],
    "product": [
        "pm", "po", "프로덕트 매니저", "프로덕트 오너", "기획자", "서비스 기획",
        "전략 기획", "사업 기획", "프로덕트 디렉터",
    ],
    "marketing": [
        "마케터", "마케팅", "퍼포먼스 마케팅", "그로스", "그로스 해커",
        "콘텐츠 마케팅", "브랜드 마케팅", "캠페인", "seo", "광고 운영",
        "crm", "ga4", "google ads",
    ],
    "sales_bd": [
        "영업", "세일즈", "bd", "사업개발", "비즈니스 디벨롭먼트", "account executive",
        "ae", "csm", "고객 성공", "어카운트 매니저", "파트너십",
    ],
    "operations": [
        "운영", "오퍼레이션", "cs", "고객 지원", "고객 응대", "물류", "scm",
        "백오피스", "ops", "서비스 운영",
    ],
    "hr_people": [
        "hr", "인사", "리쿠르터", "리크루터", "people", "조직문화", "hrbp",
        "l&d", "교육 담당", "인재 개발",
    ],
    "finance": [
        "재무", "회계", "fp&a", "세무", "재무회계", "결산", "감사", "treasury",
        "재경",
    ],
}


# ─────────────────────────────────────────────
# 키워드 매칭
# ─────────────────────────────────────────────
def _score_by_keywords(jd: str) -> dict[JobFamily, int]:
    """각 JobFamily 별로 JD 안에 매칭되는 키워드 개수를 반환."""
    text = jd.lower()
    scores: dict[JobFamily, int] = {}
    for family, kws in JOB_KEYWORDS.items():
        cnt = 0
        for kw in kws:
            # 한글 키워드는 단순 substring, 영문은 단어 경계
            if re.search(r"[a-z0-9]", kw):
                pattern = rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])"
                if re.search(pattern, text):
                    cnt += 1
            else:
                if kw in text:
                    cnt += 1
        scores[family] = cnt
    return scores


def _decide_from_scores(scores: dict[JobFamily, int]) -> JobFamily | None:
    """키워드 점수만으로 결정 가능하면 JobFamily, 아니면 None."""
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top, top_score = sorted_items[0]
    second_score = sorted_items[1][1] if len(sorted_items) > 1 else 0

    # 명확한 1등: 점수 ≥ 2 이고 2등과 차이 ≥ 2
    if top_score >= 2 and (top_score - second_score) >= 2:
        return top
    # 압도적 1등: 점수 ≥ 4
    if top_score >= 4:
        return top
    return None


# ─────────────────────────────────────────────
# LLM 폴백
# ─────────────────────────────────────────────
def _classify_via_llm(jd: str) -> JobFamily | None:
    """LLM 으로 직무 분류. 실패 시 None 반환 (호출자가 general 로 폴백)."""
    api_key = os.getenv(SOLAR_API_KEY_ENV)
    if not api_key:
        logger.warning("LLM 폴백 불가: %s 미설정", SOLAR_API_KEY_ENV)
        return None

    families = sorted(_VALID_FAMILIES)
    prompt = (
        "다음 채용공고의 직무 카테고리를 하나만 골라 JSON 으로 반환하세요.\n\n"
        f"카테고리 목록: {families}\n\n"
        "## 채용공고\n"
        f"{jd[:1500]}\n\n"
        '다음 JSON 한 줄만 출력: {"family": "engineering"}'
    )

    try:
        client = OpenAI(api_key=api_key, base_url=SOLAR_BASE_URL)
        resp = client.chat.completions.create(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": "당신은 채용 직무를 분류하는 정확한 분류기입니다."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or ""
        data = json.loads(raw)
        family = data.get("family", "").strip()
        if family in _VALID_FAMILIES:
            return family  # type: ignore[return-value]
        logger.warning("LLM 이 알 수 없는 family 반환: %r", family)
        return None
    except Exception as e:
        logger.warning("LLM 직무 분류 실패: %s", e)
        return None


# ─────────────────────────────────────────────
# 엔트리 포인트
# ─────────────────────────────────────────────
def infer_job_family(jd: str) -> JobFamily:
    """JD 텍스트에서 JobFamily 를 추론.

    Steps:
      1. 키워드 매칭으로 명확하면 즉시 반환
      2. 모호하면 LLM 폴백
      3. LLM 도 실패하면 'general' 반환
    """
    if not jd or not jd.strip():
        logger.info("빈 JD → general")
        return "general"

    # 1. 키워드 매칭
    scores = _score_by_keywords(jd)
    decided = _decide_from_scores(scores)
    if decided is not None:
        logger.info("키워드로 결정: %s (scores=%s)", decided, scores)
        return decided

    # 2. LLM 폴백
    logger.info("키워드로 모호 → LLM 폴백 (scores=%s)", scores)
    via_llm = _classify_via_llm(jd)
    if via_llm is not None:
        logger.info("LLM 으로 결정: %s", via_llm)
        return via_llm

    # 3. 최종 폴백 — 키워드 1등이 있으면 그거 사용, 아니면 general
    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    if sorted_items[0][1] > 0:
        fallback = sorted_items[0][0]
        logger.info("최종 폴백 — 키워드 1등 사용: %s", fallback)
        return fallback

    logger.info("최종 폴백 → general")
    return "general"