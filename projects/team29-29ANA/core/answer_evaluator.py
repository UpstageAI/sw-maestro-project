"""답변 평가 모듈 — Report 입력용 EvaluationResult 생성기.

역할
- 질문/답변/JD/회사 정보/이력서 RAG 컨텍스트를 바탕으로 답변을 4개 축으로 평가한다.
- report_generator.py가 집계하기 쉬운 정규화된 점수와 약점 태그를 반환한다.
- weakness_tags는 꼬리질문 트리거이기도 하므로, 실제로 보완이 필요한 경우에만 반환한다.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

try:
    import chromadb
except ImportError:  # 로컬 테스트 환경에서 requirements 미설치 시에도 모듈 import 가능
    chromadb = None  # type: ignore[assignment]

try:
    from openai import APIError, OpenAI
except ImportError:  # 운영 환경에서는 requirements에 openai를 포함해야 함
    APIError = Exception  # type: ignore[assignment,misc]
    OpenAI = None  # type: ignore[assignment]

from models.types import EvaluationResult, Question, SessionContext

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# 환경설정
# ─────────────────────────────────────────────
LLM_MODEL = os.getenv("LLM_MODEL")
SOLAR_BASE_URL = os.getenv("SOLAR_BASE_URL")
SOLAR_API_KEY_ENV = "UPSTAGE_API_KEY"

_DEFAULT_CHROMA_PATH = Path(__file__).resolve().parent.parent / "chroma_db"
CHROMA_PATH = os.getenv("CHROMA_PATH", str(_DEFAULT_CHROMA_PATH))

RAG_TOP_K = 3
LLM_MAX_RETRIES = int(os.getenv("EVALUATOR_LLM_MAX_RETRIES", "2"))
LLM_TEMPERATURE = float(os.getenv("EVALUATOR_LLM_TEMPERATURE", "0.2"))
FALLBACK_ON_ERROR = os.getenv("EVALUATOR_FALLBACK_ON_ERROR", "1") != "0"

ANSWER_EXCERPT_MAX_CHARS = 2500
JD_EXCERPT_MAX_CHARS = 2500
RAG_QUERY_MAX_CHARS = 500
MAX_WEAKNESS_TAGS = 3

_llm_client: OpenAI | None = None
_chroma_client: Any | None = None

# report_generator의 weakness_summary가 지저분해지지 않도록 태그를 고정한다.
ALLOWED_WEAKNESS_TAGS: tuple[str, ...] = (
    "STAR 구조 부족",
    "상황/맥락 부족",
    "과제/역할 불명확",
    "행동 구체성 부족",
    "결과/성과 부족",
    "정량 지표 부족",
    "직무 관련성 부족",
    "회사/JD 연결 부족",
    "근거 부족",
    "답변 일관성 부족",
    "책임 범위 불명확",
    "기술 깊이 부족",
    "협업 설명 부족",
    "회고/학습 부족",
)

_SCORE_TO_DEFAULT_TAGS: dict[str, list[str]] = {
    "star_score": ["STAR 구조 부족", "상황/맥락 부족", "결과/성과 부족"],
    "specificity_score": ["행동 구체성 부족", "정량 지표 부족", "근거 부족"],
    "relevance_score": ["직무 관련성 부족", "회사/JD 연결 부족"],
    "consistency_score": ["답변 일관성 부족", "책임 범위 불명확"],
}

# 한국어 답변에서 자주 보이는 신호를 이용한 폴백용 휴리스틱.
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?\s*(?:%|퍼센트|명|건|개|개월|주|일|시간|분|초|ms|s|원|만원|억원|배|회|줄|명분)?")
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


# ─────────────────────────────────────────────
# 클라이언트 / RAG
# ─────────────────────────────────────────────
def _get_llm() -> Any:
    global _llm_client
    if OpenAI is None:
        raise RuntimeError("openai 패키지가 설치되어 있지 않습니다.")
    if _llm_client is None:
        api_key = os.getenv(SOLAR_API_KEY_ENV)
        if not api_key:
            raise RuntimeError(f"환경변수 {SOLAR_API_KEY_ENV} 가 설정되지 않았습니다.")
        _llm_client = OpenAI(api_key=api_key, base_url=SOLAR_BASE_URL)
    return _llm_client


def _get_chroma() -> Any:
    global _chroma_client
    if chromadb is None:
        raise RuntimeError("chromadb 패키지가 설치되어 있지 않습니다.")
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
    return _chroma_client


def _retrieve_resume_context(question: Question, answer: str, context: SessionContext) -> str:
    """질문/답변과 관련 있는 이력서·자소서 조각을 가져온다.

    Chroma가 없거나 컬렉션을 찾지 못해도 평가 자체는 진행되어야 하므로, 실패 시
    프롬프트에 명시 가능한 짧은 메시지만 반환한다.
    """
    query = f"{question.category} {question.text} {answer[:RAG_QUERY_MAX_CHARS]}".strip()
    if not query:
        return "(검색 쿼리 비어 있음)"

    try:
        collection = _get_chroma().get_collection(context.chroma_collection_name)
        result = collection.query(query_texts=[query], n_results=RAG_TOP_K)
        docs = (result.get("documents") or [[]])[0]
        return "\n\n---\n\n".join(docs) if docs else "(이력서 검색 결과 없음)"
    except Exception as e:  # noqa: BLE001 - RAG 실패가 세션 실패로 이어지지 않게 함
        logger.warning("이력서 RAG 검색 실패: %s", e)
        return "(이력서 컨텍스트 검색 실패)"


def _company_section(context: SessionContext) -> str:
    cp = context.company_profile
    if cp is None:
        return "(미수집)"
    return (
        f"기업명: {cp.name}\n"
        f"기술 스택: {', '.join(cp.tech_stack) if cp.tech_stack else '미상'}\n"
        f"문화: {cp.culture or '미상'}\n"
        f"최근 동향: {cp.recent_news or '미상'}"
    )


# ─────────────────────────────────────────────
# 프롬프트
# ─────────────────────────────────────────────
SYSTEM_PROMPT = f"""당신은 한국 IT/스타트업/대기업 면접을 10년 이상 진행한 시니어 면접관이자 커리어 코치입니다.
지원자의 모의 면접 답변을 리포트 생성에 바로 사용할 수 있도록 엄격하지만 공정하게 평가합니다.

## 평가 축
1. star_score: STAR 구조 완성도. Situation/Task/Action/Result가 분명하고 본인 역할과 결과가 연결되는지 평가.
2. specificity_score: 구체성. 수치, 기간, 규모, 의사결정 근거, 사용 기술/도구, 실행 과정이 구체적인지 평가.
3. relevance_score: 질문·직무·JD·회사 맥락과의 관련성. 질문에 직접 답했고 지원 직무 역량을 보여주는지 평가.
4. consistency_score: 일관성. 답변 내부 논리, 이력서 발췌와의 부합, 과장/모순/책임 범위 불명확 여부를 평가.

## 점수 기준
- 5점: 매우 우수. 실제 면접에서도 강한 답변.
- 4점: 좋음. 작은 보완만 필요.
- 3점: 보통. 핵심은 있으나 구조/근거/구체성이 부족.
- 2점: 미흡. 질문 의도에 부분적으로만 답함.
- 1점: 매우 미흡. 질문 회피, 근거 부재, 심각한 모순.

## 약점 태그 규칙
- weakness_tags는 아래 목록에서만 고르세요.
- 실제 꼬리질문이 필요한 약점만 최대 {MAX_WEAKNESS_TAGS}개 반환하세요.
- 네 점수가 모두 4점 이상이고 뚜렷한 약점이 없으면 빈 배열 []을 반환하세요.
- 낮은 점수를 준 축과 태그가 서로 맞아야 합니다.

허용 태그: {', '.join(ALLOWED_WEAKNESS_TAGS)}

## 출력 형식
반드시 JSON 객체 하나만 출력하세요. 마크다운 코드펜스와 설명 문장은 금지합니다.
{{
  "star_score": 1,
  "specificity_score": 1,
  "relevance_score": 1,
  "consistency_score": 1,
  "weakness_tags": ["허용 태그 중 선택"],
  "feedback": {{
    "summary": "한 문장 총평",
    "strengths": ["잘한 점 1", "잘한 점 2"],
    "improvements": ["개선점 1", "개선점 2"],
    "followup_focus": "꼬리질문으로 확인하면 좋은 지점. 없으면 빈 문자열"
  }}
}}"""


def _build_user_prompt(question: Question, answer: str, context: SessionContext) -> str:
    resume_context = _retrieve_resume_context(question, answer, context)
    jd = context.job_description[:JD_EXCERPT_MAX_CHARS]
    ans = answer.strip()[:ANSWER_EXCERPT_MAX_CHARS]

    return f"""아래 면접 질문과 지원자 답변을 평가하세요.

## 질문 메타데이터
- 질문 ID: {question.id}
- 카테고리: {question.category}
- 난이도: {question.difficulty}/5
- 꼬리질문 여부: {question.is_followup}
- 부모 질문 ID: {question.parent_id or '(없음)'}

## 질문
{question.text}

## 지원자 답변
{ans}

## 직무 설명/JD
{jd}

## 지원 기업 정보
{_company_section(context)}

## 이력서/자소서 관련 발췌
{resume_context}

## 평가 지침
- 질문에 직접 답했는지 먼저 확인하세요.
- 이력서 발췌가 부족하더라도 답변 자체의 논리와 JD 관련성은 평가하세요.
- 답변에 없는 성과나 사실을 추측해서 칭찬하지 마세요.
- 단순히 표현이 매끄럽다는 이유로 높은 점수를 주지 마세요. 구조, 근거, 결과, 관련성이 있어야 합니다.
- feedback은 리포트에 그대로 들어갈 수 있게 한국어 존댓말로 작성하세요.

JSON만 출력하세요."""


# ─────────────────────────────────────────────
# 파싱 / 정규화
# ─────────────────────────────────────────────
def _clamp_score(value: Any) -> int:
    try:
        score = int(round(float(value)))
    except (TypeError, ValueError):
        score = 3
    return max(1, min(5, score))


def _extract_json(raw: str) -> dict[str, Any]:
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

    if not isinstance(data, dict):
        raise ValueError(f"JSON 객체가 아님: {raw[:200]}")
    return data


def _normalize_feedback(raw_feedback: Any, scores: dict[str, int], weakness_tags: list[str]) -> str:
    if isinstance(raw_feedback, dict):
        feedback = raw_feedback
    elif isinstance(raw_feedback, str) and raw_feedback.strip():
        feedback = {"summary": raw_feedback.strip(), "strengths": [], "improvements": [], "followup_focus": ""}
    else:
        feedback = {
            "summary": "답변의 구조와 구체성을 기준으로 추가 보완이 필요합니다.",
            "strengths": [],
            "improvements": [],
            "followup_focus": "",
        }

    # 필수 키 보정. report_generator는 문자열을 그대로 프롬프트에 넣으므로 JSON 문자열로 고정한다.
    normalized = {
        "summary": str(feedback.get("summary") or "").strip(),
        "strengths": feedback.get("strengths") if isinstance(feedback.get("strengths"), list) else [],
        "improvements": feedback.get("improvements") if isinstance(feedback.get("improvements"), list) else [],
        "followup_focus": str(feedback.get("followup_focus") or "").strip(),
        "scores": scores,
        "weakness_tags": weakness_tags,
    }

    if not normalized["summary"]:
        normalized["summary"] = "답변을 평가했으며, 리포트 생성을 위한 점수와 약점 태그를 산출했습니다."

    return json.dumps(normalized, ensure_ascii=False)


def _normalize_tags(raw_tags: Any, scores: dict[str, int]) -> list[str]:
    tags: list[str] = []

    if isinstance(raw_tags, list):
        for tag in raw_tags:
            if not isinstance(tag, str):
                continue
            cleaned = tag.strip()
            if cleaned in ALLOWED_WEAKNESS_TAGS and cleaned not in tags:
                tags.append(cleaned)

    # 낮은 점수가 있는데 태그가 비어 있으면 리포트/꼬리질문용 기본 태그를 보강한다.
    low_score_keys = [key for key, score in scores.items() if score <= 3]
    for key in sorted(low_score_keys, key=lambda k: scores[k]):
        for tag in _SCORE_TO_DEFAULT_TAGS.get(key, []):
            if tag not in tags:
                tags.append(tag)
            if len(tags) >= MAX_WEAKNESS_TAGS:
                break
        if len(tags) >= MAX_WEAKNESS_TAGS:
            break

    # 점수가 충분히 높으면 꼬리질문이 불필요하다고 보고 태그를 제거한다.
    if min(scores.values()) >= 4:
        return []

    return tags[:MAX_WEAKNESS_TAGS]


def _normalize_result(data: dict[str, Any], question: Question, answer: str) -> EvaluationResult:
    scores = {
        "star_score": _clamp_score(data.get("star_score")),
        "specificity_score": _clamp_score(data.get("specificity_score")),
        "relevance_score": _clamp_score(data.get("relevance_score")),
        "consistency_score": _clamp_score(data.get("consistency_score")),
    }
    weakness_tags = _normalize_tags(data.get("weakness_tags"), scores)
    feedback = _normalize_feedback(data.get("feedback"), scores, weakness_tags)

    return EvaluationResult(
        question=question,
        user_answer=answer,
        star_score=scores["star_score"],
        specificity_score=scores["specificity_score"],
        relevance_score=scores["relevance_score"],
        consistency_score=scores["consistency_score"],
        weakness_tags=weakness_tags,
        feedback=feedback,
    )


# ─────────────────────────────────────────────
# LLM 호출
# ─────────────────────────────────────────────
def _is_permanent_api_error(err: APIError) -> bool:
    status = getattr(err, "status_code", None)
    if status is None or status == 429:
        return False
    return 400 <= status < 500


def _call_llm(user_prompt: str) -> dict[str, Any]:
    last_err: Exception | None = None

    for attempt in range(LLM_MAX_RETRIES + 1):
        try:
            response = _get_llm().chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=LLM_TEMPERATURE,
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or ""
            return _extract_json(raw)

        except (json.JSONDecodeError, ValueError) as e:
            last_err = e
            logger.warning(
                "평가 LLM 응답 파싱 실패 (시도 %d/%d): %s",
                attempt + 1,
                LLM_MAX_RETRIES + 1,
                e,
            )
        except APIError as e:
            last_err = e
            if _is_permanent_api_error(e):
                logger.error(
                    "평가 LLM 영구 API 에러로 중단 (status=%s): %s",
                    getattr(e, "status_code", "?"),
                    e,
                )
                break
            logger.warning(
                "평가 LLM API 오류 (시도 %d/%d): %s",
                attempt + 1,
                LLM_MAX_RETRIES + 1,
                e,
            )
            time.sleep(0.5 * (attempt + 1))

    assert last_err is not None
    raise RuntimeError(f"평가 LLM 호출 실패: {last_err}") from last_err


# ─────────────────────────────────────────────
# 결정적 폴백
# ─────────────────────────────────────────────
def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _score_star_heuristic(answer: str) -> int:
    has_situation = _contains_any(answer, ("당시", "상황", "문제", "프로젝트", "목표", "배경"))
    has_task = _contains_any(answer, ("역할", "담당", "과제", "목표", "책임", "해야"))
    has_action = _contains_any(answer, ("제가", "구현", "설계", "분석", "개선", "도입", "조율", "제안"))
    has_result = _contains_any(answer, ("결과", "성과", "달성", "감소", "증가", "개선", "배웠", "회고"))
    count = sum((has_situation, has_task, has_action, has_result))
    return [1, 2, 3, 4, 5][count]


def _score_specificity_heuristic(answer: str) -> int:
    length = len(answer.strip())
    number_count = len(_NUMBER_RE.findall(answer))
    concrete_markers = sum(
        1
        for marker in ("왜", "근거", "데이터", "지표", "사용자", "API", "DB", "테스트", "실험", "비교", "트레이드오프")
        if marker.lower() in answer.lower()
    )
    score = 1
    if length >= 120:
        score += 1
    if length >= 250:
        score += 1
    if number_count >= 1:
        score += 1
    if number_count >= 2 or concrete_markers >= 2:
        score += 1
    return max(1, min(5, score))


def _score_relevance_heuristic(question: Question, answer: str, context: SessionContext) -> int:
    base = 3
    q_terms = {t for t in re.split(r"\W+", question.text.lower()) if len(t) >= 2}
    jd_terms = {t for t in re.split(r"\W+", context.job_description.lower()) if len(t) >= 3}
    ans = answer.lower()

    q_overlap = sum(1 for t in q_terms if t in ans)
    jd_overlap = sum(1 for t in list(jd_terms)[:120] if t in ans)

    if q_overlap >= 2:
        base += 1
    if jd_overlap >= 3:
        base += 1
    if q_overlap == 0 and len(answer) < 180:
        base -= 1
    return max(1, min(5, base))


def _score_consistency_heuristic(answer: str) -> int:
    score = 4
    if _contains_any(answer, ("잘 모르", "기억이", "아마", "대충", "모르겠")):
        score -= 1
    if _contains_any(answer, ("하지만", "반면", "그런데")) and not _contains_any(answer, ("그래서", "결론", "따라서")):
        score -= 1
    if len(answer.strip()) < 120:
        score -= 1
    return max(1, min(5, score))


def _heuristic_evaluation(question: Question, answer: str, context: SessionContext) -> EvaluationResult:
    scores = {
        "star_score": _score_star_heuristic(answer),
        "specificity_score": _score_specificity_heuristic(answer),
        "relevance_score": _score_relevance_heuristic(question, answer, context),
        "consistency_score": _score_consistency_heuristic(answer),
    }
    weakness_tags = _normalize_tags([], scores)
    feedback = _normalize_feedback(
        {
            "summary": "LLM 평가 실패로 휴리스틱 기준에 따라 임시 평가를 생성했습니다.",
            "strengths": ["답변에 포함된 구조적 단서를 기준으로 기본 평가를 수행했습니다."],
            "improvements": ["실제 운영에서는 LLM 평가 결과로 더 정밀한 피드백을 생성하는 것을 권장합니다."],
            "followup_focus": ", ".join(weakness_tags),
        },
        scores,
        weakness_tags,
    )
    return EvaluationResult(
        question=question,
        user_answer=answer,
        star_score=scores["star_score"],
        specificity_score=scores["specificity_score"],
        relevance_score=scores["relevance_score"],
        consistency_score=scores["consistency_score"],
        weakness_tags=weakness_tags,
        feedback=feedback,
    )


# ─────────────────────────────────────────────
# 엔트리 포인트
# ─────────────────────────────────────────────
def evaluate_answer(question: Question, answer: str, context: SessionContext) -> EvaluationResult:
    """질문 + 답변 + 컨텍스트를 받아 EvaluationResult 반환.

    반환값은 orchestrator의 history에 저장되고, 이후 report_generator에서
    전체 점수·카테고리 점수·약점 요약·개선 제안 생성에 사용된다.
    """
    if not answer or not answer.strip():
        raise ValueError("평가할 답변이 비어 있습니다.")

    user_prompt = _build_user_prompt(question, answer, context)

    try:
        data = _call_llm(user_prompt)
        return _normalize_result(data, question, answer)
    except Exception as e:  # noqa: BLE001 - 운영 중 세션 중단 방지용 옵션
        if not FALLBACK_ON_ERROR:
            raise
        logger.warning("평가 LLM 실패 → 휴리스틱 폴백 사용: %s", e)
        return _heuristic_evaluation(question, answer, context)
