"""종합 리포트 생성 모듈 — 결정적 점수 집계 + Solar(Upstage) 코칭 코멘트"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from collections import Counter

from openai import APIError, OpenAI

from models.types import EvaluationResult, Question, Report

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 상수 / 환경설정
# ─────────────────────────────────────────────
LLM_MODEL = os.getenv("LLM_MODEL")
SOLAR_BASE_URL = os.getenv("SOLAR_BASE_URL")
SOLAR_API_KEY_ENV = "UPSTAGE_API_KEY"

LLM_MAX_RETRIES = 2
LLM_TEMPERATURE = 0.3   # 리포트는 질문 생성보다 일관성 우선

WEAKNESS_TOP_N = 5
ANSWER_EXCERPT_MAX_CHARS = 200
WEAKEST_ANSWERS_FOR_PROMPT = 2

SCORE_KEYS: tuple[str, ...] = (
    "star_score",
    "specificity_score",
    "relevance_score",
    "consistency_score",
)

_llm_client: OpenAI | None = None


# ─────────────────────────────────────────────
# 클라이언트 (lazy init)
# ─────────────────────────────────────────────
def _get_llm() -> OpenAI:
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv(SOLAR_API_KEY_ENV)
        if not api_key:
            raise RuntimeError(f"환경변수 {SOLAR_API_KEY_ENV} 가 설정되지 않았습니다.")
        _llm_client = OpenAI(api_key=api_key, base_url=SOLAR_BASE_URL)
    return _llm_client


# ─────────────────────────────────────────────
# 결정적 집계
# ─────────────────────────────────────────────
def _avg_4scores(r: EvaluationResult) -> float:
    return sum(getattr(r, k) for k in SCORE_KEYS) / len(SCORE_KEYS)


def _aggregate_overall_score(history: list[tuple[Question, EvaluationResult]]) -> float:
    if not history:
        return 0.0
    return round(sum(_avg_4scores(r) for _, r in history) / len(history), 2)


def _aggregate_category_scores(
    history: list[tuple[Question, EvaluationResult]],
) -> dict[str, float]:
    """카테고리별 평균 점수.

    꼬리질문은 부모 메인 질문과 동일한 category 를 가지므로 자연스럽게 같은
    버킷에 합산된다. 등장하지 않은 카테고리는 결과 dict 에서 제외해 0점 오해를 막는다.
    """
    bucket: dict[str, list[float]] = {}
    for q, r in history:
        bucket.setdefault(q.category, []).append(_avg_4scores(r))
    return {cat: round(sum(scores) / len(scores), 2) for cat, scores in bucket.items()}


def _aggregate_weakness_top(
    history: list[tuple[Question, EvaluationResult]],
    top_n: int = WEAKNESS_TOP_N,
) -> list[str]:
    """약점 태그를 빈도 내림차순으로 정렬해 상위 N개 반환."""
    counter: Counter[str] = Counter()
    for _, r in history:
        counter.update(r.weakness_tags)
    return [tag for tag, _ in counter.most_common(top_n)]


# ─────────────────────────────────────────────
# 결정적 폴백 (LLM 실패 시 사용)
# ─────────────────────────────────────────────
def _fallback_suggestions(weakness_top: list[str]) -> str:
    if not weakness_top:
        return (
            "전반적으로 균형 잡힌 답변이었습니다. "
            "STAR 구조와 구체적인 수치 인용을 한 단계 더 보강하면 답변이 한층 강해집니다."
        )
    tags = ", ".join(weakness_top)
    return (
        f"가장 자주 드러난 약점은 [{tags}] 입니다. "
        "STAR 구조(상황·과제·행동·결과)를 명시하고, 답변마다 정량 지표(수치·비율·기간)를 "
        "최소 1개 이상 인용해 보세요. 직무 관련성을 높이려면 회사·직무 키워드를 답변 도입부에 "
        "자연스럽게 배치하는 것도 효과적입니다."
    )


# ─────────────────────────────────────────────
# 코칭 시스템 프롬프트
# ─────────────────────────────────────────────
SYSTEM_PROMPT = """당신은 10년 이상 다양한 직무에서 면접·코칭을 진행해 온 시니어 면접 코치입니다.
지원자의 모의 면접 결과(점수·약점 태그·실제 답변 발췌)를 바탕으로, 친근하지만 직설적인 톤으로 개선 방향을 제시합니다.

## 좋은 코멘트의 특징
- 구체적인 약점부터 짚고, 그 다음 실행 가능한 개선 행동을 제시
- 추상적인 격려("화이팅!") 금지, 평가 데이터에 근거한 조언
- 한국어 존댓말, **5~8문장**

## 출력 형식
응답은 반드시 다음 JSON 한 줄만 출력: {"suggestions": "코칭 코멘트 본문"}
마크다운 코드펜스, 인사말 등 다른 텍스트 일절 포함 금지."""


# ─────────────────────────────────────────────
# User 프롬프트 빌더
# ─────────────────────────────────────────────
def _weakest_answers_excerpt(
    history: list[tuple[Question, EvaluationResult]],
    n: int,
) -> str:
    if not history:
        return "(없음)"
    ranked = sorted(history, key=lambda x: _avg_4scores(x[1]))[:n]
    lines: list[str] = []
    for q, r in ranked:
        ans = r.user_answer.strip().replace("\n", " ")
        if len(ans) > ANSWER_EXCERPT_MAX_CHARS:
            ans = ans[:ANSWER_EXCERPT_MAX_CHARS] + "..."
        lines.append(
            f"- 질문([{q.category}]): {q.text}\n"
            f"  답변 발췌: {ans}\n"
            f"  평가 피드백: {r.feedback}"
        )
    return "\n".join(lines)


def _build_user_prompt(
    history: list[tuple[Question, EvaluationResult]],
    overall: float,
    category_scores: dict[str, float],
    weakness_top: list[str],
) -> str:
    cat_text = "\n".join(f"- {c}: {s}/5" for c, s in category_scores.items()) or "(없음)"
    weak_text = ", ".join(weakness_top) if weakness_top else "(없음)"
    weak_excerpt = _weakest_answers_excerpt(history, WEAKEST_ANSWERS_FOR_PROMPT)

    return f"""다음 모의 면접 결과를 바탕으로 종합 코칭 코멘트를 작성하세요.

## 전체 점수
{overall}/5 (응답 {len(history)}건 평균)

## 카테고리별 평균
{cat_text}

## 자주 드러난 약점 (빈도순)
{weak_text}

## 가장 약한 답변 발췌
{weak_excerpt}

## 작성 가이드
- 위 데이터에 근거한 약점 진단 → 개선 행동 순서로 작성
- 추상적 격려 금지, 구체적 행동(STAR 보강·수치 인용·도메인 키워드 등) 제시
- 한국어 존댓말, 5~8문장

다음 JSON만 출력:
{{"suggestions": "코칭 코멘트 본문"}}"""


# ─────────────────────────────────────────────
# LLM 호출 / JSON 파싱
# ─────────────────────────────────────────────
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


def _extract_suggestions_from_response(raw: str) -> str:
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        match = _JSON_OBJ_RE.search(cleaned)
        if not match:
            raise ValueError(f"JSON 객체를 찾을 수 없음: {raw[:200]}")
        data = json.loads(match.group(0))
    text = (data.get("suggestions") or "").strip()
    if not text:
        raise ValueError(f"빈 suggestions: {raw[:200]}")
    return text


def _is_permanent_api_error(err: APIError) -> bool:
    """4xx 클라이언트 에러는 재시도해도 의미 없음 (단, 429 rate limit 제외)."""
    status = getattr(err, "status_code", None)
    if status is None:
        return False
    if status == 429:
        return False
    return 400 <= status < 500


def _call_llm_for_suggestions(user_prompt: str) -> str:
    """LLM 호출 + JSON 파싱. 일시적 오류·파싱 실패 시 재시도."""
    last_err: Exception | None = None

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            resp = _get_llm().chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=LLM_TEMPERATURE,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content or ""
            return _extract_suggestions_from_response(raw)

        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            logger.warning(
                "LLM 응답 파싱 실패 (시도 %d/%d): %s",
                attempt + 1, LLM_MAX_RETRIES + 1, e,
            )
        except APIError as e:
            last_err = e
            if _is_permanent_api_error(e):
                logger.error(
                    "영구 API 에러로 즉시 중단 (status=%s): %s",
                    getattr(e, "status_code", "?"), e,
                )
                break
            logger.warning(
                "LLM API 오류 (시도 %d/%d): %s",
                attempt + 1, LLM_MAX_RETRIES + 1, e,
            )
            time.sleep(0.5 * (attempt + 1))

    assert last_err is not None
    raise RuntimeError(f"LLM 호출 실패: {last_err}") from last_err


def _safe_improvement_suggestions(
    history: list[tuple[Question, EvaluationResult]],
    overall: float,
    category_scores: dict[str, float],
    weakness_top: list[str],
) -> str:
    """LLM 코칭 코멘트 생성. 실패 시 결정적 폴백 텍스트로 안전하게 떨어진다.

    리포트 생성 자체가 실패하면 면접 세션 종료 흐름이 막히므로,
    LLM 단계는 반드시 폴백을 동반해야 한다.
    """
    try:
        prompt = _build_user_prompt(history, overall, category_scores, weakness_top)
        return _call_llm_for_suggestions(prompt)
    except Exception as e:
        logger.warning("LLM 코칭 코멘트 생성 실패 → 폴백 사용: %s", e)
        return _fallback_suggestions(weakness_top)


# ─────────────────────────────────────────────
# 엔트리 포인트
# ─────────────────────────────────────────────
def generate_report(history: list[tuple[Question, EvaluationResult]]) -> Report:
    """전체 Q&A 히스토리를 받아 종합 리포트 반환.

    - 점수/약점 집계는 결정적 로직.
    - improvement_suggestions 는 Solar(Upstage) LLM 코칭 코멘트, 실패 시 폴백.
    """
    if not history:
        logger.info("빈 history → 빈 리포트 반환")
        return Report(
            overall_score=0.0,
            category_scores={},
            weakness_summary=[],
            improvement_suggestions="평가할 답변이 없습니다.",
        )

    overall = _aggregate_overall_score(history)
    category_scores = _aggregate_category_scores(history)
    weakness_top = _aggregate_weakness_top(history)
    suggestions = _safe_improvement_suggestions(
        history, overall, category_scores, weakness_top,
    )

    return Report(
        overall_score=overall,
        category_scores=category_scores,
        weakness_summary=weakness_top,
        improvement_suggestions=suggestions,
    )
