from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.fixture
def mock_pipeline_result(collected_data):
    from models.schema import AnalysisReport
    report = AnalysisReport(
        one_line_conclusion="AAPL rose on earnings.",
        final_report_markdown="## Report\nDetails here.",
        bull_case="Growth continues.",
        bear_case="Margins at risk.",
        watch_next=["Q2 guidance"],
        timeline=[],
    )
    return {
        "ticker": "AAPL",
        "collected_data": collected_data,
        "hypotheses": [],
        "report": report,
        "errors": [],
    }


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestAnalyzeEndpoint:
    def test_valid_request_returns_200(self, mock_pipeline_result):
        with patch("api.main.pipeline") as mock_pipeline:
            mock_pipeline.invoke.return_value = mock_pipeline_result
            response = client.post("/analyze", json={
                "ticker": "AAPL",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            })
        assert response.status_code == 200
        data = response.json()
        assert data["ticker"] == "AAPL"
        assert "collected_data" in data
        assert data["errors"] == []
        assert data["disclaimer"] != ""

    def test_missing_field_returns_422(self):
        response = client.post("/analyze", json={"ticker": "AAPL"})
        assert response.status_code == 422

    def test_pipeline_error_returns_500(self):
        with patch("api.main.pipeline") as mock_pipeline:
            mock_pipeline.invoke.side_effect = RuntimeError("LLM timeout")
            response = client.post("/analyze", json={
                "ticker": "AAPL",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            })
        assert response.status_code == 500

    def test_ticker_is_uppercased(self, mock_pipeline_result):
        with patch("api.main.pipeline") as mock_pipeline:
            mock_pipeline.invoke.return_value = mock_pipeline_result
            response = client.post("/analyze", json={
                "ticker": "aapl",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            })
        assert response.status_code == 200
        assert response.json()["ticker"] == "AAPL"

    def test_pipeline_errors_field_propagated(self, mock_pipeline_result):
        mock_pipeline_result["errors"] = ["뉴스 수집 실패: timeout"]
        with patch("api.main.pipeline") as mock_pipeline:
            mock_pipeline.invoke.return_value = mock_pipeline_result
            response = client.post("/analyze", json={
                "ticker": "AAPL",
                "start_date": "2024-01-01",
                "end_date": "2024-01-31",
            })
        assert response.status_code == 200
        assert len(response.json()["errors"]) == 1
