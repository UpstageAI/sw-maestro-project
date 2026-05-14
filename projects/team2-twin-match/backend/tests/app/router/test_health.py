import pytest


@pytest.mark.asyncio
async def test_root(async_client):
    res = await async_client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "running"


@pytest.mark.asyncio
async def test_health(async_client):
    res = await async_client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "healthy"
    assert body["database"] == "connected"
