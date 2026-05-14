from fastapi import APIRouter
from pydantic import BaseModel

from newspick_ai.report.generator import DailyReportGenerator


class ReportRequest(BaseModel):
    article_ids: list[str] = []


def create_report_router(report_generator: DailyReportGenerator) -> APIRouter:
    router = APIRouter()

    @router.post("/report/generate")
    async def generate_report(body: ReportRequest = ReportRequest()):
        return await report_generator.generate(body.article_ids)

    return router
