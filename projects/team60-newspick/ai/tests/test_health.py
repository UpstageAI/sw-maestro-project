import pytest
from httpx import ASGITransport, AsyncClient

from newspick_ai.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok_payload():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=1.0,
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
