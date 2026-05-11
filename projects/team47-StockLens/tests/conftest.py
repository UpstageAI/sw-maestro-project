from __future__ import annotations

import pytest

from models.schema import (
    AgentState,
    BenchmarkComparison,
    CauseHypothesis,
    CollectedData,
    NewsArticle,
    PriceRecord,
    PriceStats,
    ScoreComponents,
    SECFiling,
)


@pytest.fixture
def price_stats() -> PriceStats:
    return PriceStats(
        period_pct_change=3.5,
        max_single_day_gain=2.1,
        max_single_day_loss=-1.2,
        avg_volume=50_000_000,
        volume_spike_dates=["2024-01-15"],
        is_abnormal_move=False,
    )


@pytest.fixture
def collected_data(price_stats: PriceStats) -> CollectedData:
    return CollectedData(
        ticker="AAPL",
        company_name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        start_date="2024-01-01",
        end_date="2024-01-31",
        prices=[
            PriceRecord(date="2024-01-02", open=185.0, high=188.0, low=184.0, close=187.0, volume=60_000_000, pct_change=0.0),
            PriceRecord(date="2024-01-03", open=187.0, high=190.0, low=186.0, close=189.0, volume=55_000_000, pct_change=1.07),
        ],
        price_stats=price_stats,
        benchmarks=[
            BenchmarkComparison(ticker="^GSPC", label="S&P 500", pct_change_period=2.1),
            BenchmarkComparison(ticker="XLK", label="Technology ETF", pct_change_period=3.0),
        ],
        peer_tickers=["MSFT", "GOOGL"],
        news_articles=[
            NewsArticle(title="Apple hits new record", source="Reuters", published_at="2024-01-10T10:00:00Z", url="https://reuters.com/1"),
            NewsArticle(title="Apple hits new record", source="Bloomberg", published_at="2024-01-10T11:00:00Z", url="https://bloomberg.com/1"),
            NewsArticle(title="", source="Unknown", published_at="2024-01-11T00:00:00Z", url=""),
            NewsArticle(title="Apple Q1 earnings preview", source="CNBC", published_at="2024-01-12T09:00:00Z", url="https://cnbc.com/1"),
        ],
        sec_filings=[
            SECFiling(form_type="8-K", filed_at="2024-01-15", description="aapl-20240115.htm", url="https://sec.gov/1"),
            SECFiling(form_type="8-K", filed_at="2024-01-15", description="aapl-20240115.htm", url="https://sec.gov/1"),
        ],
    )


@pytest.fixture
def hypothesis() -> CauseHypothesis:
    return CauseHypothesis(
        id="hypothesis-1",
        title="Strong earnings beat",
        category="earnings",
        explanation="Apple exceeded Q1 estimates significantly.",
        evidence=["Revenue up 15% YoY"],
        counterpoints=["Guidance was in-line"],
        score_components=ScoreComponents(
            timing_alignment=0.9,
            source_credibility=0.8,
            stock_specificity=0.9,
            volume_confirmation=0.7,
            independent_source_confirmation=0.8,
        ),
        score=0.0,
        confidence="Low",
    )


@pytest.fixture
def agent_state(collected_data: CollectedData) -> AgentState:
    return {
        "ticker": "AAPL",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "collected_data": collected_data,
        "hypotheses": None,
        "report": None,
        "errors": [],
    }
