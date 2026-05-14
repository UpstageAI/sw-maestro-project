"""f4_supervisor — 두 페르소나 의견과 교차 리뷰를 최종 리뷰 텍스트로 종합."""

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage

from schemas import (
    Opinion,
    OpinionQualityReport,
    QualityFlag,
    Review,
    ReviewQualityReport,
    ServicePlanInput,
    TargetUserPersonaCard,
)
from services.brief_evidence import introduces_unsupported_solution
from state import ProjectState

load_dotenv()

_llm = ChatUpstage(model="solar-pro3")

_WEAK_PASS_RATIO_LIMIT = 0.30
_F2_FAIL_PASS_RATIO_LIMIT = 0.30

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 서비스 기획 리뷰를 정리하는 중립적인 슈퍼바이저입니다. "
        "페르소나처럼 말하지 말고, 제품 기획자가 바로 읽을 수 있는 최종 리뷰를 작성하세요. "
        "기획안과 품질 기준을 통과한 1차 의견/교차 리뷰를 본문 판단의 주 근거로 사용하세요. "
        "페르소나의 생활 맥락은 왜 그런 반응이 나오는지 설명하는 보조 근거로 풍부하게 사용하세요. "
        "기획안에 명시되지 않은 추론은 본문 판단 근거로 사용하지 마세요. "
        "다만 입력 근거에서 자연스럽게 이어지는 경우 운영 방식, 정산 방식, 고객 문의 같은 추론은 "
        "반드시 '5. 추가 검증 가설' 섹션에만 최대 3개까지 쓰고, "
        "각 항목을 '[가설 | 기획안 미명시]'로 시작하세요. "
        "추가 검증 가설은 최종 판단의 직접 근거가 아니라 후속 확인 항목입니다. "
        "최종 판단 토큰 [통과], [보류], [재검토]는 작성하지 마세요. "
        "당신은 판단의 본문 근거만 작성합니다. "
        "반드시 아래 여섯 섹션을 같은 순서로 작성하세요:\n"
        "1. 종합 판단\n"
        "2. 긍정 신호\n"
        "3. 주요 우려\n"
        "4. 페르소나 간 차이\n"
        "5. 추가 검증 가설\n"
        "6. 다음 검증 질문",
    ),
    (
        "human",
        "## 서비스 기획안\n{brief}\n\n"
        "## 페르소나 A\n{persona_a}\n\n"
        "## 페르소나 B\n{persona_b}\n\n"
        "## 페르소나 A의 1차 의견\n{opinion_a}\n\n"
        "## 페르소나 B의 1차 의견\n{opinion_b}\n\n"
        "## 페르소나 A가 B 의견을 읽고 남긴 리뷰\n{review_a}\n\n"
        "## 페르소나 B가 A 의견을 읽고 남긴 리뷰\n{review_b}\n\n"
        "위 내용을 종합해 최종 리뷰를 작성하세요.",
    ),
])


def _format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 없음"


def _format_brief(brief: ServicePlanInput) -> str:
    features = _format_list(brief.key_features)
    return (
        f"제목: {brief.title or '-'}\n"
        f"설명: {brief.description or '-'}\n"
        f"타겟: {brief.target or '-'}\n"
        f"핵심 기능:\n{features}\n"
        f"우려사항: {brief.concerns or '-'}"
    )


def _format_persona(persona: TargetUserPersonaCard) -> str:
    return (
        f"ID: {persona.card_id}\n"
        f"이름: {persona.display_name}\n"
        f"연령대/성별/직업/지역: "
        f"{persona.age_group or '-'} / {persona.sex or '-'} / "
        f"{persona.occupation or '-'} / {persona.region or '-'}\n"
        f"요약: {persona.one_line_summary}\n"
        f"생활 맥락: {persona.life_context}\n"
        f"목표:\n{_format_list(persona.user_goals)}\n"
        f"불편함:\n{_format_list(persona.pain_points)}\n"
        f"긍정 트리거:\n{_format_list(persona.positive_triggers)}\n"
        f"부정 트리거:\n{_format_list(persona.negative_triggers)}\n"
        f"말투: {persona.speaking_style}"
    )


def _format_opinion(opinion: Opinion, quality: OpinionQualityReport | None = None) -> str:
    allowed_ids: set[str] | None = None
    quality_note = ""
    if quality:
        allowed_ids = set(quality.pass_point_ids) | set(quality.weak_point_ids)
        quality_note = "품질 기준을 통과한 포인트만 포함했습니다.\n"
    positive_points = [
        point for point in opinion.positive_points if allowed_ids is None or point.point_id in allowed_ids
    ]
    negative_points = [
        point for point in opinion.negative_points if allowed_ids is None or point.point_id in allowed_ids
    ]
    positive = "\n".join(
        f"- [{point.point_id}] {point.title}: {point.detail}"
        for point in positive_points
    )
    negative = "\n".join(
        f"- [{point.point_id}] {point.title}: {point.detail}"
        for point in negative_points
    )
    would_use = "사용할 것" if opinion.would_use else "사용 안 할 것"
    return (
        f"persona_id: {opinion.persona_id}\n"
        f"{quality_note}"
        f"긍정 포인트:\n{positive or '- 없음'}\n"
        f"부정 포인트:\n{negative or '- 없음'}\n"
        f"사용 의향: {would_use}\n"
        f"사용 의향 이유: {opinion.would_use_description or '-'}"
    )


def _format_review(review: Review, quality: ReviewQualityReport | None = None) -> str:
    allowed_ids: set[str] | None = None
    quality_note = ""
    if quality:
        allowed_ids = set(quality.pass_feedback_ids) | set(quality.weak_feedback_ids)
        quality_note = "품질 기준을 통과한 리뷰 피드백만 포함했습니다.\n"
    point_feedbacks = [
        feedback
        for feedback in review.point_feedbacks
        if allowed_ids is None or feedback.target_point_id in allowed_ids
    ]
    feedbacks = "\n".join(
        f"- [{feedback.target_point_id}] {feedback.agreement}: {feedback.comment}"
        for feedback in point_feedbacks
    )
    revised = "사용할 것" if review.revised_would_use else "사용 안 할 것"
    return (
        f"reviewer_id: {review.reviewer_id}\n"
        f"target_id: {review.target_id}\n"
        f"{quality_note}"
        f"포인트별 피드백:\n{feedbacks or '- 없음'}\n"
        f"종합 소감: {review.overall_comment}\n"
        f"수정된 사용 의향: {revised}"
    )


def _build_supervisor_prompt_vars(state: ProjectState) -> dict[str, str]:
    return {
        "brief": _format_brief(state["brief"]),
        "persona_a": _format_persona(state["persona_a"]),
        "persona_b": _format_persona(state["persona_b"]),
        "opinion_a": _format_opinion(state["opinion_a"], state.get("opinion_quality_a")),
        "opinion_b": _format_opinion(state["opinion_b"], state.get("opinion_quality_b")),
        "review_a": _format_review(state["review_a"], state.get("review_quality_a")),
        "review_b": _format_review(state["review_b"], state.get("review_quality_b")),
    }


def _quality_flags(state: ProjectState) -> list[QualityFlag]:
    flags: list[QualityFlag] = []
    for key in ("opinion_quality_a", "opinion_quality_b", "review_quality_a", "review_quality_b"):
        report = state.get(key)
        if report:
            flags.extend(report.flags)
    return flags


def _quality_counts(state: ProjectState) -> tuple[int, int, int]:
    pass_count = weak_count = fail_count = 0
    for key in ("opinion_quality_a", "opinion_quality_b", "review_quality_a", "review_quality_b"):
        report = state.get(key)
        if not report:
            continue
        pass_count += len(getattr(report, "pass_point_ids", []) or getattr(report, "pass_feedback_ids", []))
        weak_count += len(getattr(report, "weak_point_ids", []) or getattr(report, "weak_feedback_ids", []))
        fail_count += len(getattr(report, "fail_point_ids", []) or getattr(report, "fail_feedback_ids", []))
    return pass_count, weak_count, fail_count


def _has_review_quality_fail(state: ProjectState) -> bool:
    for key in ("review_quality_a", "review_quality_b"):
        report = state.get(key)
        if not report:
            continue
        if getattr(report, "fail_feedback_ids", []):
            return True
        if any(flag.severity == "fail" for flag in report.flags):
            return True
    return False


def _both_reviews_would_use(state: ProjectState) -> bool:
    review_a = state.get("review_a")
    review_b = state.get("review_b")
    return bool(
        review_a
        and review_b
        and review_a.revised_would_use
        and review_b.revised_would_use
    )


def _can_pass_with_f2_failures(state: ProjectState, pass_count: int, weak_count: int, fail_count: int) -> bool:
    if not _both_reviews_would_use(state):
        return False
    if _has_review_quality_fail(state):
        return False
    total_count = pass_count + weak_count + fail_count
    if not total_count:
        return False
    return fail_count / total_count <= _F2_FAIL_PASS_RATIO_LIMIT


def _decision_from_quality(state: ProjectState) -> str:
    flags = _quality_flags(state)
    pass_count, weak_count, fail_count = _quality_counts(state)
    if fail_count or any(flag.severity == "fail" for flag in flags):
        if _can_pass_with_f2_failures(state, pass_count, weak_count, fail_count):
            return "[통과]"
        return "[재검토]"
    if weak_count:
        valid_count = pass_count + weak_count
        if valid_count and weak_count / valid_count <= _WEAK_PASS_RATIO_LIMIT:
            return "[통과]"
        return "[보류]"
    if any(flag.severity == "weak" for flag in flags):
        return "[보류]"
    return "[통과]"


def _strip_decision_tokens(text: str) -> str:
    for token in ("[통과]", "[보류]", "[재검토]"):
        text = text.replace(token, "")
    return "\n".join(line.rstrip() for line in text.splitlines() if line.strip()).strip()


def _has_valid_artifacts(state: ProjectState) -> bool:
    reports = [
        state.get("opinion_quality_a"),
        state.get("opinion_quality_b"),
        state.get("review_quality_a"),
        state.get("review_quality_b"),
    ]
    if not any(reports):
        return True
    for report in reports:
        if not report:
            continue
        pass_ids = getattr(report, "pass_point_ids", []) or getattr(report, "pass_feedback_ids", [])
        weak_ids = getattr(report, "weak_point_ids", []) or getattr(report, "weak_feedback_ids", [])
        if pass_ids or weak_ids:
            return True
    return False


def _fallback_body_for_no_valid_artifacts(state: ProjectState) -> str:
    flag_codes = sorted({
        flag.code
        for flag in _quality_flags(state)
        if flag.severity in {"weak", "fail"}
    })
    reasons = ", ".join(flag_codes) if flag_codes else "validated artifact 없음"
    return (
        "1. 종합 판단\n"
        "품질 기준을 통과한 1차 의견 또는 교차 리뷰가 없어 최종 판단을 보류합니다.\n"
        "2. 긍정 신호\n"
        "- 현재 검증된 중간 산출물 안에서는 재사용할 수 있는 긍정 근거가 확인되지 않았습니다.\n"
        "3. 주요 우려\n"
        f"- 품질 실패/보류 사유: {reasons}\n"
        "- 실패한 1차 의견이나 리뷰 내용을 최종 근거로 사용하지 않았습니다.\n"
        "4. 페르소나 간 차이\n"
        "- 비교 가능한 검증 포인트가 부족해 차이를 판단하지 않았습니다.\n"
        "5. 추가 검증 가설\n"
        "- 품질 기준을 통과한 근거가 없어 추가 가설을 만들지 않았습니다.\n"
        "6. 다음 검증 질문\n"
        "- f2 의견이 기획서의 핵심 기능 또는 문제 문장과 직접 연결되도록 프롬프트와 품질 기준을 재점검하세요.\n"
        "- 통과 또는 보류 수준의 의견 포인트가 생성된 뒤 교차 리뷰를 다시 실행하세요."
    )


def _relocate_unsupported_hypothesis_lines(body: str, brief: ServicePlanInput) -> str:
    """Move ungrounded solution hypotheses out of grounded report sections."""
    lines = body.splitlines()
    kept: list[str] = []
    relocated: list[str] = []
    in_hypothesis_section = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("5. 추가 검증 가설"):
            in_hypothesis_section = True
            kept.append(line)
            continue
        if stripped[:2] in {"1.", "2.", "3.", "4.", "6."}:
            in_hypothesis_section = False
            kept.append(line)
            continue
        if stripped and not in_hypothesis_section and introduces_unsupported_solution(stripped, brief):
            relocated.append(stripped.lstrip("- "))
            continue
        kept.append(line)

    if not relocated:
        return _normalize_hypothesis_section(body)

    if not any(line.strip().startswith("5. 추가 검증 가설") for line in kept):
        kept.append("5. 추가 검증 가설")

    insert_at = next(
        index + 1
        for index, line in enumerate(kept)
        if line.strip().startswith("5. 추가 검증 가설")
    )
    kept = [
        line
        for index, line in enumerate(kept)
        if index < insert_at or line.strip() not in {"- 없음", "- 없음."}
    ]
    hypothesis_lines = [
        f"- [가설 | 기획안 미명시] {line}"
        for line in relocated
    ]
    return _normalize_hypothesis_section(
        "\n".join(kept[:insert_at] + hypothesis_lines + kept[insert_at:])
    )


def _normalize_hypothesis_section(body: str) -> str:
    lines = body.splitlines()
    normalized: list[str] = []
    in_hypothesis_section = False
    hypothesis_count = 0

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("5. 추가 검증 가설"):
            in_hypothesis_section = True
            hypothesis_count = 0
            normalized.append(line)
            continue
        if in_hypothesis_section and stripped[:2] in {"1.", "2.", "3.", "4.", "6."}:
            in_hypothesis_section = False
            normalized.append(line)
            continue
        if in_hypothesis_section and "[가설 | 기획안 미명시]" in stripped:
            if hypothesis_count >= 3:
                continue
            hypothesis_count += 1
            normalized.append("- " + stripped.lstrip("- "))
            continue
        normalized.append(line)

    return "\n".join(normalized).strip()


def supervisor_finalize(state: ProjectState) -> dict:
    """교차 리뷰까지 완료된 state를 읽어 최종 사용자용 리뷰 텍스트를 생성."""
    decision = _decision_from_quality(state)
    if not _has_valid_artifacts(state):
        return {
            "final_review_text": f"{decision}\n{_fallback_body_for_no_valid_artifacts(state)}".strip()
        }
    chain = _PROMPT | _llm | StrOutputParser()
    body = chain.invoke(_build_supervisor_prompt_vars(state))
    body = _strip_decision_tokens(body)
    body = _relocate_unsupported_hypothesis_lines(body, state["brief"])
    return {"final_review_text": f"{decision}\n{body}".strip()}
