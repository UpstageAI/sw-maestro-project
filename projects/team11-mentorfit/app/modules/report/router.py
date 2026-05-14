from fastapi import APIRouter, Depends

from app.core.rate_limit import limit_llm_endpoint
from app.modules.report.schemas import RecommendationReport, ReportGenerationRequest
from app.modules.report.service import generate_report

router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("", response_model=RecommendationReport)
async def create_report(
    request: ReportGenerationRequest,
    _: None = Depends(limit_llm_endpoint),
) -> RecommendationReport:
    return await generate_report(request)
