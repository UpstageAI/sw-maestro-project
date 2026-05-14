from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.rate_limit import limit_recommendation_endpoint
from app.modules.recommendation.schemas import RecommendationRequest, RecommendationResponse
from app.modules.recommendation.service import (
    RecommendationNotReadyError,
    UnknownCandidateMentorError,
    create_recommendation,
)

router = APIRouter(prefix="/api/recommendations", tags=["recommendation"])


@router.post("", response_model=RecommendationResponse)
async def create_recommendation_endpoint(
    request: RecommendationRequest,
    _: None = Depends(limit_recommendation_endpoint),
) -> RecommendationResponse:
    try:
        return await create_recommendation(request)
    except RecommendationNotReadyError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except UnknownCandidateMentorError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
