import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from newspick_ai.env import MissingEnvironmentError
from newspick_ai.api.refresh_stream import create_refresh_stream_router


async def fake_refresh_runner(
    category_ids: list[str],
    run_id: str | None = None,
    reset: bool = False,
):
    yield "step", {"step": "collect", "current": 1, "total": 1}
    yield "done", {"articleIds": ["article_001"]}


@pytest.mark.asyncio
async def test_refresh_stream_emits_step_and_done_events():
    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(refresh_runner=fake_refresh_runner)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/refresh-stream")

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert "event: step" in response.text
    assert '"step":"collect"' in response.text
    assert "event: done" in response.text
    assert "article_001" in response.text


@pytest.mark.asyncio
async def test_refresh_stream_passes_selected_categories_and_run_id_to_runner():
    async def category_refresh_runner(
        category_ids: list[str],
        run_id: str | None = None,
        reset: bool = False,
    ):
        yield "done", {"categoryIds": category_ids, "runId": run_id}

    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(refresh_runner=category_refresh_runner)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/refresh-stream?categories=tech,economy&runId=run-123")

    assert response.status_code == 200
    assert '"categoryIds":["tech","economy"]' in response.text
    assert '"runId":"run-123"' in response.text


@pytest.mark.asyncio
async def test_refresh_stream_passes_reset_to_runner():
    async def reset_refresh_runner(
        category_ids: list[str],
        run_id: str | None = None,
        reset: bool = False,
    ):
        yield "done", {"reset": reset}

    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(refresh_runner=reset_refresh_runner)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/refresh-stream?reset=1")

    assert response.status_code == 200
    assert '"reset":true' in response.text


@pytest.mark.asyncio
async def test_refresh_stream_rejects_unknown_category():
    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(refresh_runner=fake_refresh_runner)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/refresh-stream?categories=unknown")

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_refresh_stream_converts_runner_errors_to_error_event():
    async def failing_refresh_runner(
        category_ids: list[str],
        run_id: str | None = None,
        reset: bool = False,
    ):
        raise RuntimeError("boom")
        yield "done", {}

    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(refresh_runner=failing_refresh_runner)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/refresh-stream")

    assert response.status_code == 200
    assert "event: error" in response.text
    assert '"code":"refresh_failed"' in response.text


@pytest.mark.asyncio
async def test_refresh_stream_converts_missing_environment_to_specific_error_event():
    async def failing_refresh_runner(
        category_ids: list[str],
        run_id: str | None = None,
        reset: bool = False,
    ):
        raise MissingEnvironmentError("AI 설정을 읽지 못해 재수집을 완료하지 못했어요.")
        yield "done", {}

    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(refresh_runner=failing_refresh_runner)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/refresh-stream?reset=1")

    assert response.status_code == 200
    assert "event: error" in response.text
    assert '"code":"missing_environment"' in response.text
    assert "AI 설정을 읽지 못해 재수집을 완료하지 못했어요." in response.text


@pytest.mark.asyncio
async def test_cancel_refresh_stream_is_idempotent():
    app = FastAPI()
    app.include_router(
        create_refresh_stream_router(refresh_runner=fake_refresh_runner)
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        first = await client.post("/refresh-stream/run-123/cancel")
        second = await client.post("/refresh-stream/run-123/cancel")

    assert first.status_code == 204
    assert second.status_code == 204
