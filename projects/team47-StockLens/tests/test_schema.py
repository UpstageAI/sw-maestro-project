from __future__ import annotations

import pytest
from pydantic import ValidationError

from models.schema import (
    AnalysisReport,
    CauseHypothesis,
    CollectedData,
    PriceRecord,
    PriceStats,
    ScoreComponents,
)


class TestPriceRecord:
    def test_valid_record(self):
        r = PriceRecord(date="2024-01-02", open=100.0, high=105.0, low=99.0, close=103.0, volume=1_000_000, pct_change=3.0)
        assert r.close == 103.0

    def test_requires_all_fields(self):
        with pytest.raises(ValidationError):
            PriceRecord(date="2024-01-02", open=100.0)


class TestPriceStats:
    def test_valid_stats(self):
        s = PriceStats(
            period_pct_change=2.5,
            max_single_day_gain=1.5,
            max_single_day_loss=-1.0,
            avg_volume=50_000_000,
            volume_spike_dates=["2024-01-10"],
            is_abnormal_move=False,
        )
        assert s.is_abnormal_move is False

    def test_volume_spike_dates_defaults_empty(self):
        s = PriceStats(
            period_pct_change=0.0,
            max_single_day_gain=0.0,
            max_single_day_loss=0.0,
            avg_volume=0.0,
            volume_spike_dates=[],
            is_abnormal_move=False,
        )
        assert s.volume_spike_dates == []


class TestScoreComponents:
    def test_valid_components(self):
        sc = ScoreComponents(
            timing_alignment=0.8,
            source_credibility=0.7,
            stock_specificity=0.9,
            volume_confirmation=0.6,
            independent_source_confirmation=0.75,
        )
        assert sc.timing_alignment == 0.8

    def test_requires_all_five_components(self):
        with pytest.raises(ValidationError):
            ScoreComponents(timing_alignment=0.8)


class TestCauseHypothesis:
    def test_valid_hypothesis(self, hypothesis):
        assert hypothesis.category == "earnings"
        assert hypothesis.confidence == "Low"

    def test_valid_categories(self):
        valid = ["earnings", "analyst", "macro", "sector", "company_specific", "regulatory", "technical", "market_wide", "unknown"]
        for cat in valid:
            h = CauseHypothesis(
                id="h", title="T", category=cat, explanation="E",
                evidence=[], counterpoints=[],
                score_components=ScoreComponents(timing_alignment=0, source_credibility=0, stock_specificity=0, volume_confirmation=0, independent_source_confirmation=0),
                score=0.0, confidence="Low",
            )
            assert h.category == cat


class TestAnalysisReport:
    def test_valid_report(self):
        r = AnalysisReport(
            one_line_conclusion="AAPL rose on strong earnings.",
            final_report_markdown="## Summary\nStrong quarter.",
            bull_case="Revenue growth continues.",
            bear_case="Margin pressure ahead.",
            watch_next=["Q2 guidance", "China demand"],
            timeline=[],
        )
        assert r.one_line_conclusion.startswith("AAPL")

    def test_watch_next_defaults_empty(self):
        r = AnalysisReport(
            one_line_conclusion="Test.",
            final_report_markdown="",
            bull_case="",
            bear_case="",
            watch_next=[],
            timeline=[],
        )
        assert r.watch_next == []
