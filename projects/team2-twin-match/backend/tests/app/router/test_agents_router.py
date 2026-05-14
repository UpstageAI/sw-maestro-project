import pytest

from app.repositories.agent_repository import AgentRepository


@pytest.mark.asyncio
async def test_list_agents_empty(client_with_db):
    res = await client_with_db.get("/api/agents")
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_list_agents_returns_seeded_newest_first(client_with_db, db_session):
    repo = AgentRepository(db_session)
    first = await repo.create_clone(
        name="A", age=20, gender="F", job="디자이너",
        tags=["#a"], persona_text="A persona", system_prompt="A sys",
    )
    second = await repo.create_clone(
        name="B", age=21, gender="M", job="개발자",
        tags=["#b"], persona_text="B persona", system_prompt="B sys",
    )

    res = await client_with_db.get("/api/agents")
    assert res.status_code == 200

    body = res.json()
    assert [item["id"] for item in body] == [second.id, first.id]
    assert body[0]["tags"] == ["#b"]
    assert body[0]["agent_type"] == "clone"


@pytest.mark.asyncio
async def test_get_agent_returns_full_payload(client_with_db, db_session):
    repo = AgentRepository(db_session)
    created = await repo.create_clone(
        name="민준", age=28, gender="M", job="웹 개발자",
        tags=["#INTP", "#등산"],
        persona_text="저는 28세 개발자입니다. " * 3,
        system_prompt="(rendered system prompt)",
    )

    res = await client_with_db.get(f"/api/agents/{created.id}")
    assert res.status_code == 200

    body = res.json()
    assert body["id"] == created.id
    assert body["name"] == "민준"
    assert body["age"] == 28
    assert body["gender"] == "M"
    assert body["job"] == "웹 개발자"
    assert body["tags"] == ["#INTP", "#등산"]
    assert body["agent_type"] == "clone"


@pytest.mark.asyncio
async def test_get_agent_not_found_returns_spec_detail(client_with_db):
    res = await client_with_db.get(
        "/api/agents/00000000-0000-0000-0000-000000000000"
    )
    assert res.status_code == 404
    assert res.json() == {"detail": "Agent를 찾을 수 없습니다"}


@pytest.mark.asyncio
async def test_get_agent_invalid_uuid_returns_400(client_with_db):
    res = await client_with_db.get("/api/agents/not-a-uuid")
    assert res.status_code == 400
    assert res.json() == {"detail": "올바른 UUID 형식이 아닙니다"}
