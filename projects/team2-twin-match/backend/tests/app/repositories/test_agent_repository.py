from datetime import datetime, timezone

import pytest

from app.models.db.agent import Agent
from app.repositories.agent_repository import AgentRepository


@pytest.mark.asyncio
async def test_create_clone_round_trip(db_session):
    repo = AgentRepository(db_session)

    created = await repo.create_clone(
        name="민준",
        age=28,
        gender="M",
        job="웹 개발자",
        tags=["#INTP", "#등산"],
        persona_text="저는 28세 개발자입니다. " * 3,
        system_prompt="(rendered system prompt)",
    )

    assert created.id  # auto-generated UUID
    assert created.agent_type == "clone"
    assert created.name == "민준"
    assert created.tags == ["#INTP", "#등산"]
    assert created.created_at  # ISO 8601 string

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.tags == ["#INTP", "#등산"]
    assert fetched.persona_text == created.persona_text


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(db_session):
    repo = AgentRepository(db_session)
    assert await repo.get_by_id("nonexistent-id") is None


@pytest.mark.asyncio
async def test_list_clones_orders_newest_first_and_excludes(db_session):
    repo = AgentRepository(db_session)

    a = await repo.create_clone(
        name="A", age=20, gender="F", job="A직",
        tags=["#a"], persona_text="A persona", system_prompt="A",
    )
    b = await repo.create_clone(
        name="B", age=21, gender="M", job="B직",
        tags=["#b"], persona_text="B persona", system_prompt="B",
    )
    c = await repo.create_clone(
        name="C", age=22, gender="X", job="C직",
        tags=["#c"], persona_text="C persona", system_prompt="C",
    )

    listed = await repo.list_clones()
    # created_at 역순(최신순). c → b → a 순서.
    assert [dto.id for dto in listed] == [c.id, b.id, a.id]

    excluded = await repo.list_clones_excluding(b.id)
    assert [dto.id for dto in excluded] == [c.id, a.id]


@pytest.mark.asyncio
async def test_get_matchmaker_returns_seeded_singleton(db_session):
    repo = AgentRepository(db_session)

    # 시드 전: None
    assert await repo.get_matchmaker() is None

    # 시드: lifespan 이 하는 것과 동일한 방식
    db_session.add(
        Agent(
            id="matchmaker-test-id",
            agent_type="matchmaker",
            system_prompt="matchmaker prompt",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    await db_session.commit()

    matchmaker = await repo.get_matchmaker()
    assert matchmaker is not None
    assert matchmaker.id == "matchmaker-test-id"
    assert matchmaker.agent_type == "matchmaker"
    assert matchmaker.persona_text is None
