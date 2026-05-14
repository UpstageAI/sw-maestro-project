from unittest.mock import AsyncMock

import pytest

from app.core.errors.error import (
    PersonaTextEmptyException,
    PersonaTextTooShortException,
)
from app.models.dtos.agent import CreateAgentDTO
from app.repositories.agent_repository import AgentRepository
from app.services.agent_service import AgentService

# Persona text 50자 이상이라 검증 통과.
VALID_PERSONA = "저는 28세 개발자입니다. 웹 개발을 하고 주말엔 등산을 좋아합니다. 신중하지만 친해지면 유머러스합니다."


def _build_service(db_session) -> AgentService:
    repo = AgentRepository(db_session)
    return AgentService(agent_repository=repo)


def _dto(persona: str = VALID_PERSONA) -> CreateAgentDTO:
    return CreateAgentDTO(name="민준", age=28, gender="M", persona_text=persona)


@pytest.mark.asyncio
async def test_create_clone_agent_extracts_job_and_tags(db_session, monkeypatch):
    fake = AsyncMock(return_value='{"job": "웹 개발자", "tags": ["#INTP", "#등산"]}')
    monkeypatch.setattr("app.services.agent_service.chat_completion", fake)

    service = _build_service(db_session)
    result = await service.create_clone_agent(_dto())

    assert result.name == "민준"
    assert result.age == 28
    assert result.gender == "M"
    assert result.job == "웹 개발자"
    assert result.tags == ["#INTP", "#등산"]
    assert result.agent_type == "clone"
    assert fake.await_count == 1


@pytest.mark.asyncio
async def test_create_clone_agent_system_prompt_preserves_persona(db_session, monkeypatch):
    """system_prompt 는 페르소나 원문 + 고정 규칙으로 구성된다."""
    monkeypatch.setattr(
        "app.services.agent_service.chat_completion",
        AsyncMock(return_value='{"job": "웹 개발자", "tags": ["#INTP"]}'),
    )

    service = _build_service(db_session)
    result = await service.create_clone_agent(_dto())

    assert VALID_PERSONA in result.system_prompt
    assert "절대로 당신이 AI라는 사실을 밝히거나 암시하지 마세요" in result.system_prompt


@pytest.mark.asyncio
async def test_create_clone_agent_falls_back_on_solar_failure(db_session, monkeypatch):
    """Solar 실패 시 job/tags 는 빈 값, system_prompt 는 영향 없다."""
    monkeypatch.setattr(
        "app.services.agent_service.chat_completion",
        AsyncMock(side_effect=RuntimeError("Solar down")),
    )

    service = _build_service(db_session)
    result = await service.create_clone_agent(_dto())

    assert result.id
    assert result.job == ""
    assert result.tags == []
    assert VALID_PERSONA in result.system_prompt
    assert "절대로 당신이 AI라는 사실을 밝히거나 암시하지 마세요" in result.system_prompt


@pytest.mark.asyncio
async def test_create_clone_agent_falls_back_on_invalid_json(db_session, monkeypatch):
    monkeypatch.setattr(
        "app.services.agent_service.chat_completion",
        AsyncMock(return_value="not even close to JSON"),
    )

    service = _build_service(db_session)
    result = await service.create_clone_agent(_dto())

    assert result.job == ""
    assert result.tags == []
    assert VALID_PERSONA in result.system_prompt


@pytest.mark.asyncio
async def test_create_clone_agent_defends_against_unexpected_shape(db_session, monkeypatch):
    # job 이 리스트, tags 가 문자열인 비정상 응답 — 방어적 파싱이 처리해야 함.
    monkeypatch.setattr(
        "app.services.agent_service.chat_completion",
        AsyncMock(return_value='{"job": ["wrong"], "tags": "also wrong"}'),
    )

    service = _build_service(db_session)
    result = await service.create_clone_agent(_dto())

    assert result.job == ""
    assert result.tags == []
    assert VALID_PERSONA in result.system_prompt


@pytest.mark.asyncio
async def test_create_clone_agent_empty_text_raises(db_session, monkeypatch):
    monkeypatch.setattr("app.services.agent_service.chat_completion", AsyncMock())
    service = _build_service(db_session)

    with pytest.raises(PersonaTextEmptyException):
        await service.create_clone_agent(_dto(persona="   "))


@pytest.mark.asyncio
async def test_create_clone_agent_too_short_raises(db_session, monkeypatch):
    monkeypatch.setattr("app.services.agent_service.chat_completion", AsyncMock())
    service = _build_service(db_session)

    with pytest.raises(PersonaTextTooShortException):
        await service.create_clone_agent(_dto(persona="짧은 텍스트"))


@pytest.mark.asyncio
async def test_create_clone_agent_too_long_raises(db_session, monkeypatch):
    monkeypatch.setattr("app.services.agent_service.chat_completion", AsyncMock())
    service = _build_service(db_session)

    from app.core.errors.error import PersonaTextTooLongException

    with pytest.raises(PersonaTextTooLongException):
        await service.create_clone_agent(_dto(persona="가" * 5001))
