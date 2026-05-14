"""CostTracker 단위 테스트."""
import threading
import pytest
from src.tools.cost_tracker import CostTracker, tracker, fresh_tracker, PRICING


class TestCostTrackerRecord:
    def setup_method(self):
        self.ct = CostTracker()

    def test_record_stores_input_tokens(self):
        self.ct.record("solar-pro3:low", input_tokens=1000, output_tokens=0)
        report = self.ct.report()
        assert report["by_model"]["solar-pro3:low"]["in"] == 1000

    def test_record_stores_output_tokens(self):
        self.ct.record("solar-pro3:low", input_tokens=0, output_tokens=500)
        report = self.ct.report()
        assert report["by_model"]["solar-pro3:low"]["out"] == 500

    def test_record_accumulates_across_calls(self):
        self.ct.record("solar-pro3:high", 1000, 200)
        self.ct.record("solar-pro3:high", 500, 100)
        report = self.ct.report()
        assert report["by_model"]["solar-pro3:high"]["in"] == 1500
        assert report["by_model"]["solar-pro3:high"]["out"] == 300

    def test_record_multiple_models(self):
        self.ct.record("solar-pro3:low", 1000, 100)
        self.ct.record("solar-pro3:high", 2000, 300)
        report = self.ct.report()
        assert "solar-pro3:low" in report["by_model"]
        assert "solar-pro3:high" in report["by_model"]

    def test_record_thread_safe(self):
        errors = []

        def record_batch():
            try:
                for _ in range(100):
                    self.ct.record("solar-pro3:low", 10, 5)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_batch) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        report = self.ct.report()
        assert report["by_model"]["solar-pro3:low"]["in"] == 10 * 100 * 5


class TestCostTrackerReport:
    def setup_method(self):
        self.ct = CostTracker()

    def test_report_returns_dict(self):
        assert isinstance(self.ct.report(), dict)

    def test_report_has_by_model_key(self):
        assert "by_model" in self.ct.report()

    def test_report_has_total_usd_estimate(self):
        assert "total_usd_estimate" in self.ct.report()

    def test_empty_report_total_is_zero(self):
        assert self.ct.report()["total_usd_estimate"] == 0.0

    def test_report_calculates_usd_correctly(self):
        # solar-pro3:low: in=$0.5/1M, out=$1.5/1M
        self.ct.record("solar-pro3:low", input_tokens=1_000_000, output_tokens=1_000_000)
        report = self.ct.report()
        expected_usd = 0.5 + 1.5  # $2.0
        assert abs(report["total_usd_estimate"] - expected_usd) < 0.001

    def test_report_usd_rounded_to_5_decimals(self):
        self.ct.record("solar-pro3:low", 12345, 6789)
        report = self.ct.report()
        # round(value, 5) — 소수점 5자리
        total = report["total_usd_estimate"]
        assert total == round(total, 5)


class TestFreshTracker:
    def test_fresh_tracker_is_independent(self):
        global_t = tracker()
        global_t.record("solar-pro3:low", 1000, 100)
        with fresh_tracker() as ft:
            ft.record("solar-pro3:high", 500, 50)
            assert "solar-pro3:high" in ft.report()["by_model"]
            # 전역 트래커와 독립
            assert "solar-pro3:low" not in ft.report()["by_model"]

    def test_fresh_tracker_restores_global_after_exit(self):
        original = tracker()
        with fresh_tracker():
            pass
        assert tracker() is original


class TestRecordFromResponse:
    def test_record_from_response_with_usage_metadata(self):
        ct = CostTracker()
        mock_response = type("Resp", (), {"usage_metadata": {"input_tokens": 100, "output_tokens": 50}})()
        ct.record_from_response("solar-pro3:low", mock_response)
        report = ct.report()
        assert report["by_model"]["solar-pro3:low"]["in"] == 100
        assert report["by_model"]["solar-pro3:low"]["out"] == 50

    def test_record_from_response_without_usage_metadata(self):
        ct = CostTracker()
        mock_response = type("Resp", (), {"usage_metadata": None})()
        ct.record_from_response("solar-pro3:low", mock_response)
        report = ct.report()
        assert report["by_model"]["solar-pro3:low"]["in"] == 0
        assert report["by_model"]["solar-pro3:low"]["out"] == 0
