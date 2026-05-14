from __future__ import annotations

from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import settings
from app.modules.combination_generator.schemas import CombinationResponse, CombCandidateResult
from app.modules.mentor_candidate.schemas import CandidateResult, Mentor, TeamProfile
from app.modules.report.schemas import RecommendationReport, ReportGenerationRequest
from app.modules.team_profile.schemas import ChatMessage, TeamProfilePromptRequest, TeamProfilePromptResponse

T = TypeVar("T", bound=BaseModel)


class MentorFitApiError(RuntimeError):
    pass


def _jsonable(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _error_detail(response: httpx.Response) -> str:
    try:
        data = response.json()
    except ValueError:
        return response.text or response.reason_phrase
    detail = data.get("detail") if isinstance(data, dict) else data
    if isinstance(detail, str):
        return detail
    return str(detail)


async def _request_json(method: str, path: str, *, json: dict[str, Any] | None = None) -> Any:
    url = f"{settings.api_base_url.rstrip('/')}{path}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(method, url, json=json)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        detail = _error_detail(exc.response)
        raise MentorFitApiError(f"FastAPI 요청 실패 ({exc.response.status_code}): {detail}") from exc
    except httpx.RequestError as exc:
        raise MentorFitApiError(f"FastAPI 서버에 연결할 수 없습니다: {exc}") from exc
    except ValueError as exc:
        raise MentorFitApiError("FastAPI 응답을 JSON으로 해석할 수 없습니다.") from exc


def _validate_model(model: type[T], data: Any) -> T:
    try:
        return model.model_validate(data)
    except ValidationError as exc:
        raise MentorFitApiError("FastAPI 응답 형식이 예상과 다릅니다.") from exc


async def create_team_profile_from_prompt(
    prompt: str,
    chat_messages: list[ChatMessage],
) -> TeamProfilePromptResponse:
    request = TeamProfilePromptRequest(prompt=prompt, chat_messages=chat_messages)
    data = await _request_json("POST", "/api/team-profile/prompt", json=request.model_dump(mode="json"))
    return _validate_model(TeamProfilePromptResponse, data)


async def create_mentor_candidates(
    team_profile: TeamProfile,
    top_k: int,
    prefilter_top_n: int | None,
) -> list[CandidateResult]:
    data = await _request_json(
        "POST",
        "/api/mentor-candidates",
        json={
            "team_profile": team_profile.model_dump(mode="json"),
            "top_k": top_k,
            "prefilter_top_n": prefilter_top_n,
        },
    )
    return [_validate_model(CandidateResult, item) for item in data]


async def create_combinations(
    team_profile: TeamProfile,
    candidates: list[CandidateResult],
) -> list[CombCandidateResult]:
    data = await _request_json(
        "POST",
        "/api/combinations",
        json={
            "team_profile": team_profile.model_dump(mode="json"),
            "candidates": _jsonable(candidates),
        },
    )
    return _validate_model(CombinationResponse, data).combinations


async def list_mentors() -> list[Mentor]:
    data = await _request_json("GET", "/api/mentors")
    return [_validate_model(Mentor, item) for item in data]


async def create_report(
    team_profile: TeamProfile,
    team_report: str,
    candidates: list[CandidateResult],
    combinations: list[CombCandidateResult],
    mentors: list[Mentor],
    current_matching_status: str | None,
) -> RecommendationReport:
    request = ReportGenerationRequest(
        team_profile=team_profile,
        team_report=team_report,
        candidates=candidates,
        combinations=combinations,
        mentors=mentors,
        current_matching_status=current_matching_status,
    )
    data = await _request_json("POST", "/api/report", json=request.model_dump(mode="json"))
    return _validate_model(RecommendationReport, data)
