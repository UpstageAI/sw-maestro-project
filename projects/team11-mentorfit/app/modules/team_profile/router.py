from fastapi import APIRouter, Depends

from app.core.rate_limit import limit_llm_endpoint
from app.modules.team_profile.schemas import (
    TeamProfilePromptRequest,
    TeamProfilePromptResponse,
    TeamProfileRequest,
    TeamProfileResponse,
)
from app.modules.team_profile.service import generate_team_profile, generate_team_profile_from_prompt

router = APIRouter(prefix="/api/team-profile", tags=["team-profile"])


@router.post("", response_model=TeamProfileResponse)
async def create_team_profile(
    request: TeamProfileRequest,
    _: None = Depends(limit_llm_endpoint),
) -> TeamProfileResponse:
    return await generate_team_profile(request)


@router.post("/prompt", response_model=TeamProfilePromptResponse)
async def create_team_profile_from_prompt(
    request: TeamProfilePromptRequest,
    _: None = Depends(limit_llm_endpoint),
) -> TeamProfilePromptResponse:
    return await generate_team_profile_from_prompt(request)
