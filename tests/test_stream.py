from unittest.mock import patch

from fastapi.testclient import TestClient


def test_stream_status_disconnected(client: TestClient):
    with patch("app.services.stream_service.get_stream_status") as mock:
        from app.models.responses import StreamStatusResponse
        mock.return_value = StreamStatusResponse(connected=False, stream_name=None, last_event=None)
        resp = client.get("/api/v1/testnet/stream/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is False
    assert data["streamName"] is None
    assert data["lastEvent"] is None


def test_stream_status_connected(client: TestClient):
    with patch("app.services.stream_service.get_stream_status") as mock:
        from app.models.responses import StreamStatusResponse
        mock.return_value = StreamStatusResponse(
            connected=True,
            stream_name="btcusdt@ticker",
            last_event={"e": "24hrTicker", "s": "BTCUSDT", "c": "80000.00"},
        )
        resp = client.get("/api/v1/testnet/stream/status")

    assert resp.status_code == 200
    data = resp.json()
    assert data["connected"] is True
    assert data["streamName"] == "btcusdt@ticker"
    assert data["lastEvent"]["s"] == "BTCUSDT"


def test_stream_status_camel_case_keys(client: TestClient):
    with patch("app.services.stream_service.get_stream_status") as mock:
        from app.models.responses import StreamStatusResponse
        mock.return_value = StreamStatusResponse(connected=True, stream_name="btcusdt@ticker")
        resp = client.get("/api/v1/testnet/stream/status")

    data = resp.json()
    assert "streamName" in data
    assert "lastEvent" in data
    assert "stream_name" not in data
