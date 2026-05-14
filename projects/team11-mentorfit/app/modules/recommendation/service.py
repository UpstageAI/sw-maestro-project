from __future__ import annotations

from app.data.mentors import get_all_mentors
from app.modules.combination_generator.service import CombinationGeneratorService
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor
from app.modules.mentor_candidate.service import get_mentor_candidates
from app.modules.recommendation.schemas import RecommendationRequest, RecommendationResponse
from app.modules.report.schemas import ReportGenerationRequest
from app.modules.report.service import generate_report


class RecommendationNotReadyError(ValueError):
    """Raised when the collected team profile is not ready for recommendation."""


class UnknownCandidateMentorError(ValueError):
    """Raised when generated candidates reference mentors absent from the mentor dataset."""

    def __init__(self, missing_ids: list[int]):
        self.missing_ids = missing_ids
        super().__init__(f"멘토 데이터에 없는 후보 ID입니다: {missing_ids}")


def _missing_candidate_mentor_ids(candidates: list[CandidateResult], mentors: list[Mentor]) -> list[int]:
    mentor_ids = {mentor.mentor_id for mentor in mentors}
    candidate_ids = {candidate.mentor_id for candidate in candidates}
    return sorted(candidate_ids - mentor_ids)


async def create_recommendation(request: RecommendationRequest) -> RecommendationResponse:
    if not request.ready_for_recommendation or request.collection_status != "ready":
        raise RecommendationNotReadyError("추천 생성 준비가 완료되지 않았습니다.")

    if request.team_profile is None:
        raise RecommendationNotReadyError("추천 생성에 필요한 팀 프로필이 없습니다.")
    team_profile = request.team_profile

    mentors = get_all_mentors()
    candidates = await get_mentor_candidates(
        team_profile=team_profile,
        top_k=request.top_k,
        prefilter_top_n=request.prefilter_top_n,
    )

    missing_ids = _missing_candidate_mentor_ids(candidates, mentors)
    if missing_ids:
        raise UnknownCandidateMentorError(missing_ids)

    combinations = await CombinationGeneratorService(mentors=mentors).generate(
        team_profile=team_profile,
        candidates=candidates,
    )

    recommendation_report = await generate_report(
        ReportGenerationRequest(
            team_profile=team_profile,
            team_report=request.team_report,
            candidates=candidates,
            combinations=combinations,
            mentors=mentors,
            current_matching_status=request.current_matching_status,
        )
    )

    return RecommendationResponse(
        team_profile=team_profile,
        team_report=request.team_report,
        candidates=candidates,
        combinations=combinations,
        mentors=mentors,
        recommendation_report=recommendation_report,
    )
