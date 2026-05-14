from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.rate_limit import limit_llm_endpoint
from app.data.mentors import get_all_mentors
from app.modules.combination_generator.schemas import CombinationResponse
from app.modules.combination_generator.service import CombinationGeneratorService
from app.modules.mentor_candidate.schemas import CandidateResult, TeamProfile


class CombinationRequest(BaseModel):
    team_profile: TeamProfile
    candidates: list[CandidateResult] = Field(..., min_length=1, max_length=20)


router = APIRouter(prefix="/api/combinations", tags=["combination-generator"])


@router.post("", response_model=CombinationResponse)
async def create_combinations(
    request: CombinationRequest,
    _: None = Depends(limit_llm_endpoint),
) -> CombinationResponse:
    mentors = get_all_mentors()
    mentor_ids = {mentor.mentor_id for mentor in mentors}
    missing_ids = sorted({candidate.mentor_id for candidate in request.candidates} - mentor_ids)
    if missing_ids:
        raise HTTPException(status_code=422, detail=f"멘토 데이터에 없는 후보 ID입니다: {missing_ids}")

    combinations = await CombinationGeneratorService(mentors=mentors).generate(request.team_profile, request.candidates)
    return CombinationResponse(combinations=combinations)
