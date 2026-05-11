import asyncio
from collections import deque
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.models.requests import AutoSessionStartRequest
from app.models.responses import AutoOrderRunResponse, NormalizedOrderIntentResponse
from app.services import auto_session_service


def _run_response(run_id: str, lifecycle_status: str, trader_id: str | None = "wonyotti") -> AutoOrderRunResponse:
    return AutoOrderRunResponse(
        run_id=run_id,
        lifecycle_status=lifecycle_status,
        trader_id=trader_id,
        inferred_persona="MODERATE",
        normalized_order_intent=NormalizedOrderIntentResponse(
            symbol="BTCUSDT",
            side="BUY",
            type="MARKET",
            quote_order_qty="50",
        ),
        reason_codes=[],
    )


@pytest.mark.asyncio
async def test_start_auto_session_returns_active_status():
    await auto_session_service._reset_auto_session_state_for_tests()

    async def fake_run_auto_tick(raw_text: str, trader_id: str | None, current_settings):
        return _run_response("run_tick_001", "REPORT_READY")

    async def fake_wait_for_next_tick(interval_seconds: int) -> bool:
        await auto_session_service.stop_auto_session()
        return True

    with patch("app.services.auto_session_service._run_auto_tick", side_effect=fake_run_auto_tick), patch(
        "app.services.auto_session_service._wait_for_next_tick", side_effect=fake_wait_for_next_tick
    ):
        response = await auto_session_service.start_auto_session(
            AutoSessionStartRequest(raw_text="BTC를 50 USDT만큼 매수해줘"),
            settings,
        )
        assert response.session_status == "ACTIVE"
        assert response.selected_tick_interval_seconds == 300
        await asyncio.sleep(0)
    await auto_session_service._reset_auto_session_state_for_tests()


@pytest.mark.asyncio
async def test_overlap_protection_blocks_second_start():
    await auto_session_service._reset_auto_session_state_for_tests()
    release_tick = asyncio.Event()

    async def fake_run_auto_tick(raw_text: str, trader_id: str | None, current_settings):
        await release_tick.wait()
        return _run_response("run_tick_001", "REPORT_READY")

    with patch("app.services.auto_session_service._run_auto_tick", side_effect=fake_run_auto_tick):
        await auto_session_service.start_auto_session(
            AutoSessionStartRequest(raw_text="빠르게 BTC를 매수해줘"),
            settings,
        )

        with pytest.raises(ValueError, match="ACTIVE_AUTO_SESSION_EXISTS"):
            await auto_session_service.start_auto_session(
                AutoSessionStartRequest(raw_text="다시 시작"),
                settings,
            )

        release_tick.set()
        await auto_session_service.stop_auto_session()
        await asyncio.sleep(0)
    await auto_session_service._reset_auto_session_state_for_tests()


@pytest.mark.asyncio
async def test_stop_during_inflight_tick_transitions_to_stopped():
    await auto_session_service._reset_auto_session_state_for_tests()
    release_tick = asyncio.Event()

    async def fake_run_auto_tick(raw_text: str, trader_id: str | None, current_settings):
        await release_tick.wait()
        return _run_response("run_tick_001", "REPORT_READY")

    async def fake_wait_for_next_tick(interval_seconds: int) -> bool:
        return True

    with patch("app.services.auto_session_service._run_auto_tick", side_effect=fake_run_auto_tick), patch(
        "app.services.auto_session_service._wait_for_next_tick", side_effect=fake_wait_for_next_tick
    ):
        await auto_session_service.start_auto_session(
            AutoSessionStartRequest(raw_text="BTC를 계속 매수해줘"),
            settings,
        )

        stopping = await auto_session_service.stop_auto_session()
        assert stopping.session_status == "STOPPING"
        assert stopping.stop_requested is True

        release_tick.set()
        await asyncio.sleep(0)

        final = auto_session_service.get_auto_session_status()
        assert final.session_status == "STOPPED"
        assert final.stop_reason == "USER_STOPPED"
    await auto_session_service._reset_auto_session_state_for_tests()


@pytest.mark.asyncio
async def test_hold_stops_session():
    await auto_session_service._reset_auto_session_state_for_tests()
    async def fake_run_auto_tick(raw_text: str, trader_id: str | None, current_settings):
        return _run_response("run_tick_001", "HOLD")

    with patch("app.services.auto_session_service._run_auto_tick", side_effect=fake_run_auto_tick):
        await auto_session_service.start_auto_session(
            AutoSessionStartRequest(raw_text="적당히 알아서 사줘"),
            settings,
        )
        await asyncio.sleep(0)

        status = auto_session_service.get_auto_session_status()
        assert status.session_status == "STOPPED"
        assert status.stop_reason == "HOLD"
        assert status.tick_count == 1
    await auto_session_service._reset_auto_session_state_for_tests()


@pytest.mark.asyncio
async def test_each_tick_uses_new_run_id():
    await auto_session_service._reset_auto_session_state_for_tests()
    responses = deque(
        [
            _run_response("run_tick_001", "REPORT_READY"),
            _run_response("run_tick_002", "NO_ORDER"),
        ]
    )

    async def fake_run_auto_tick(raw_text: str, trader_id: str | None, current_settings):
        return responses.popleft()

    wait_calls = 0

    async def fake_wait_for_next_tick(interval_seconds: int) -> bool:
        nonlocal wait_calls
        wait_calls += 1
        return wait_calls > 1

    with patch("app.services.auto_session_service._run_auto_tick", side_effect=fake_run_auto_tick), patch(
        "app.services.auto_session_service._wait_for_next_tick", side_effect=fake_wait_for_next_tick
    ):
        await auto_session_service.start_auto_session(
            AutoSessionStartRequest(raw_text="BTC를 계속 추적해줘"),
            settings,
        )
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        status = auto_session_service.get_auto_session_status()
        assert status.tick_count == 2
        assert status.latest_run is not None
        assert status.latest_run.run_id == "run_tick_002"
    await auto_session_service._reset_auto_session_state_for_tests()


def test_auto_session_start_endpoint(client: TestClient):
    with patch("app.services.auto_session_service.start_auto_session", new_callable=AsyncMock) as mock_start:
        from app.models.responses import AutoTradingSessionResponse

        mock_start.return_value = AutoTradingSessionResponse(
            session_id="session_001",
            session_status="ACTIVE",
            stop_requested=False,
            selected_tick_interval_seconds=300,
            raw_text="BTC를 매수해줘",
            tick_count=0,
        )
        response = client.post("/api/v1/testnet/orders/auto/session/start", json={"rawText": "BTC를 매수해줘"})

    assert response.status_code == 200
    data = response.json()
    assert data["sessionStatus"] == "ACTIVE"
    assert data["selectedTickIntervalSeconds"] == 300


def test_auto_session_start_endpoint_rejects_overlap(client: TestClient):
    with patch("app.services.auto_session_service.start_auto_session", new_callable=AsyncMock) as mock_start:
        mock_start.side_effect = ValueError("ACTIVE_AUTO_SESSION_EXISTS")
        response = client.post("/api/v1/testnet/orders/auto/session/start", json={"rawText": "BTC를 매수해줘"})

    assert response.status_code == 409
    assert response.json()["error_code"] == "REQUEST_FAILED"


def test_auto_session_status_endpoint(client: TestClient):
    with patch("app.services.auto_session_service.get_auto_session_status") as mock_status:
        from app.models.responses import AutoTradingSessionResponse

        mock_status.return_value = AutoTradingSessionResponse(session_status="IDLE")
        response = client.get("/api/v1/testnet/orders/auto/session")

    assert response.status_code == 200
    assert response.json()["sessionStatus"] == "IDLE"


def test_auto_session_stop_endpoint(client: TestClient):
    with patch("app.services.auto_session_service.stop_auto_session", new_callable=AsyncMock) as mock_stop:
        from app.models.responses import AutoTradingSessionResponse

        mock_stop.return_value = AutoTradingSessionResponse(session_status="STOPPING", stop_requested=True)
        response = client.post("/api/v1/testnet/orders/auto/session/stop")

    assert response.status_code == 200
    assert response.json()["sessionStatus"] == "STOPPING"
