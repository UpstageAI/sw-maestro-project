from __future__ import annotations

import json
from datetime import datetime, timezone

from app.core.config import settings
from app.core.upstage import upstage_client
from app.modules.combination_generator.schemas import CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor
from app.modules.report.schemas import (
    RecommendationReport,
    ReportCombination,
    ReportGenerationRequest,
    ReportMentorSummary,
)

_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "recommendation_report",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "team_summary": {"type": "string"},
                "confidence_basis": {"type": "string"},
                "candidate_summary": {"type": "string"},
                "final_recommendation": {"type": "string"},
                "cautions": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "team_summary",
                "confidence_basis",
                "candidate_summary",
                "final_recommendation",
                "cautions",
            ],
            "additionalProperties": False,
        },
    },
}


def _mentor_map(mentors: list[Mentor]) -> dict[int, Mentor]:
    return {mentor.mentor_id: mentor for mentor in mentors}


def _candidate_map(candidates: list[CandidateResult]) -> dict[int, CandidateResult]:
    return {candidate.mentor_id: candidate for candidate in candidates}


def _require_mentor(mentor_by_id: dict[int, Mentor], mentor_id: int) -> Mentor:
    mentor = mentor_by_id.get(mentor_id)
    if mentor is None:
        raise ValueError(f"리포트 생성에 필요한 멘토 ID {mentor_id}를 mentors 입력에서 찾을 수 없습니다.")
    return mentor


def build_report_combinations(request: ReportGenerationRequest) -> list[ReportCombination]:
    mentor_by_id = _mentor_map(request.mentors)
    candidate_by_id = _candidate_map(request.candidates)
    report_combinations: list[ReportCombination] = []

    for combination in request.combinations:
        main_candidate = candidate_by_id.get(combination.mentor_id)
        main_mentor = _require_mentor(mentor_by_id, combination.mentor_id)
        main_reason = combination.reason or (main_candidate.reason if main_candidate else "추천 근거를 추가 확인해야 합니다.")
        main_weak_point = combination.weak_point or (main_candidate.weak_point if main_candidate else "보완점 정보를 추가 확인해야 합니다.")
        supplement_mentors = [
            ReportMentorSummary(
                mentor_id=supplement_id,
                name=_require_mentor(mentor_by_id, supplement_id).name,
                role="supplement",
                reason="메인 멘토의 약점을 보완하기 위한 보완 멘토 후보입니다.",
                weak_point="보완 멘토의 세부 적합도는 실제 일정과 팀 선호 조건에 따라 추가 확인이 필요합니다.",
            )
            for supplement_id in combination.candidate_ids
        ]
        report_combinations.append(
            ReportCombination(
                rank=combination.rank,
                main_mentor=ReportMentorSummary(
                    mentor_id=combination.mentor_id,
                    name=main_mentor.name,
                    role="main",
                    reason=main_reason,
                    weak_point=main_weak_point,
                ),
                supplement_mentors=supplement_mentors,
                strengths=combination.strengths[:3],
                weak_points=combination.weak_points[:3],
                recommendation_reason=main_reason,
            )
        )
    return report_combinations


def _mentor_line(mentor: Mentor) -> str:
    career = ", ".join(f"{company}({years}년)" for company, years in mentor.career)
    return (
        f"ID {mentor.mentor_id} / 이름 {mentor.name} / 기술 {', '.join(mentor.stacks)} / "
        f"도메인 {', '.join(mentor.domains)} / 목표 {mentor.target} / 경력 {career}"
    )


def _candidate_line(candidate: CandidateResult, mentor_by_id: dict[int, Mentor]) -> str:
    mentor = mentor_by_id.get(candidate.mentor_id)
    name = mentor.name if mentor else "알 수 없음"
    return f"{candidate.rank}. {name}(ID {candidate.mentor_id}) - 추천: {candidate.reason} / 보완점: {candidate.weak_point}"


def _combination_line(combination: CombCandidateResult, mentor_by_id: dict[int, Mentor]) -> str:
    main = mentor_by_id.get(combination.mentor_id)
    supplement_names = [mentor_by_id[id_].name for id_ in combination.candidate_ids if id_ in mentor_by_id]
    return (
        f"{combination.rank}. 메인 {main.name if main else combination.mentor_id} + 보완 {', '.join(supplement_names)} / "
        f"강점 {combination.strengths} / 약점 {combination.weak_points} / 근거 {combination.reason}"
    )


def _build_prompt(request: ReportGenerationRequest) -> list[dict]:
    mentor_by_id = _mentor_map(request.mentors)
    system_prompt = """당신은 SW마에스트로 멘토 추천 리포트를 작성하는 운영진입니다.
제공된 팀 리포트, 후보 추천 결과, 조합 결과, 실제 멘토 데이터만 근거로 최종 리포트 요약 문구를 작성하세요.
없는 기술, 경력, 투자 네트워크, 인증 성과는 절대 추론하지 마세요.
추천은 참고 자료이며 최종 판단은 사용자가 한다는 점을 주의사항에 포함하세요."""
    user_prompt = "\n\n".join(
        [
            f"[팀 프로필]\n{request.team_profile.model_dump_json()}",
            f"[팀 리포트]\n{request.team_report}",
            "[후보 멘토]\n" + "\n".join(_candidate_line(candidate, mentor_by_id) for candidate in request.candidates),
            "[추천 조합]\n" + "\n".join(_combination_line(combination, mentor_by_id) for combination in request.combinations),
            "[멘토 원본 데이터]\n" + "\n".join(_mentor_line(mentor) for mentor in request.mentors),
            f"[현재 매칭 현황]\n{request.current_matching_status or '제공되지 않음'}",
        ]
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]


def parse_report_response(raw: str, combinations: list[ReportCombination]) -> RecommendationReport:
    data = json.loads(raw)
    return RecommendationReport(
        team_summary=data["team_summary"],
        confidence_basis=data["confidence_basis"],
        candidate_summary=data["candidate_summary"],
        combinations=combinations,
        final_recommendation=data["final_recommendation"],
        cautions=data["cautions"],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _fallback_report(request: ReportGenerationRequest) -> RecommendationReport:
    combinations = build_report_combinations(request)
    cautions = ["AI 추천은 참고 자료이며 최종 멘토 선택과 연락은 사용자가 직접 판단해야 합니다."]
    if request.current_matching_status:
        cautions.append("현재 매칭 현황은 최신 상태가 아닐 수 있으므로 실제 가능 여부를 확인해야 합니다.")
    return RecommendationReport(
        team_summary=f"기술 스택은 {request.team_profile.skills}이며, 프로젝트 목표는 {request.team_profile.project_plan_tech_goals}입니다.",
        confidence_basis="입력된 팀 리포트, 후보 추천 근거, 조합 결과, 멘토 원본 데이터 범위 안에서 작성했습니다.",
        candidate_summary=f"총 {len(request.candidates)}명의 후보와 {len(combinations)}개의 멘토 조합을 검토했습니다.",
        combinations=combinations,
        final_recommendation="1순위 조합부터 실제 일정과 팀 선호 조건을 확인한 뒤 최종 멘토를 선택하는 것을 권장합니다.",
        cautions=cautions,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


async def generate_report(request: ReportGenerationRequest) -> RecommendationReport:
    combinations = build_report_combinations(request)
    if settings.mock_mode or not settings.upstage_api_key:
        return _fallback_report(request)

    raw = await upstage_client.get_chat_completion(
        messages=_build_prompt(request),
        model=settings.report_model,
        response_format=_RESPONSE_FORMAT,
    )
    try:
        return parse_report_response(raw, combinations)
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return _fallback_report(request)
