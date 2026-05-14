from fastapi import APIRouter, Depends

from app.core.rate_limit import limit_llm_endpoint
from pydantic import BaseModel, Field

from app.modules.mentor_candidate.schemas import CandidateResult, TeamProfile
from app.modules.mentor_candidate.service import get_mentor_candidates


class MentorCandidateRequest(BaseModel):
    team_profile: TeamProfile
    top_k: int = Field(default=5, ge=1, le=20)
    prefilter_top_n: int | None = Field(default=None, ge=10, le=100)


router = APIRouter(prefix="/api/mentor-candidates", tags=["mentor-candidate"])


@router.post("", response_model=list[CandidateResult])
async def create_mentor_candidates(
    request: MentorCandidateRequest,
    _: None = Depends(limit_llm_endpoint),
) -> list[CandidateResult]:
    return await get_mentor_candidates(
        team_profile=request.team_profile,
        top_k=request.top_k,
        prefilter_top_n=request.prefilter_top_n,
    )
