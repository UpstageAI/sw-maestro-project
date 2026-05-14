from __future__ import annotations

import operator
from datetime import date
from typing import Annotated, Optional

from pydantic import BaseModel
from typing_extensions import TypedDict


class PriceRecord(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    pct_change: float


class BenchmarkComparison(BaseModel):
    ticker: str
    label: str
    pct_change_period: float


class NewsArticle(BaseModel):
    title: str
    source: str
    published_at: str
    url: str
    summary: Optional[str] = None


class SECFiling(BaseModel):
    form_type: str
    filed_at: str
    description: str
    url: str


class PriceStats(BaseModel):
    period_pct_change: float
    max_single_day_gain: float
    max_single_day_loss: float
    avg_volume: float
    volume_spike_dates: list[str]
    is_abnormal_move: bool


class CollectedData(BaseModel):
    ticker: str
    start_date: date
    end_date: date
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None

    prices: list[PriceRecord] = []
    price_stats: Optional[PriceStats] = None

    benchmarks: list[BenchmarkComparison] = []
    peer_tickers: list[str] = []

    news_articles: list[NewsArticle] = []
    sec_filings: list[SECFiling] = []

    collected_at: str = ""
    data_quality_warnings: list[str] = []


# ── Agent 2 output models ──────────────────────────────────────────────────

class ScoreComponents(BaseModel):
    timing_alignment: float
    source_credibility: float
    stock_specificity: float
    volume_confirmation: float
    independent_source_confirmation: float


class CauseHypothesis(BaseModel):
    id: str
    title: str
    category: str  # earnings|analyst|macro|sector|company_specific|regulatory|technical|market_wide|unknown
    explanation: str
    score_components: ScoreComponents
    score: float = 0.0
    confidence: str = "Low"  # High|Medium|Low
    evidence: list[str] = []
    counterpoints: list[str] = []
    supporting_article_indices: list[int] = []


# ── Agent 3 output models ──────────────────────────────────────────────────

class TimelineEvent(BaseModel):
    datetime: str
    type: str  # price_move|news|earnings|filing|analyst
    description: str
    url: Optional[str] = None


class AnalysisReport(BaseModel):
    one_line_conclusion: str
    final_report_markdown: str
    bull_case: str
    bear_case: str
    watch_next: list[str]
    timeline: list[TimelineEvent] = []


# ── Shared LangGraph state ─────────────────────────────────────────────────

class AgentState(TypedDict):
    ticker: str
    start_date: str
    end_date: str
    collected_data: Optional[CollectedData]
    hypotheses: Optional[list[CauseHypothesis]]
    report: Optional[AnalysisReport]
    errors: Annotated[list[str], operator.add]
