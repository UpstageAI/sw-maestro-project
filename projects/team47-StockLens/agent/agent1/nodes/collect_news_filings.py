from __future__ import annotations

from agent.agent1.tools.news import fetch_news
from agent.agent1.tools.sec import fetch_sec_filings
from models.schema import AgentState


def collect_news_filings_node(state: AgentState) -> dict:
    """뉴스·SEC 공시 수집 노드. 각 소스 실패해도 파이프라인 계속."""
    collected = state["collected_data"]
    warnings: list[str] = []
    articles, filings = [], []

    try:
        articles = fetch_news(
            company_name=collected.company_name or collected.ticker,
            ticker=collected.ticker,
            start_date=str(collected.start_date),
            end_date=str(collected.end_date),
        )
    except Exception as e:
        warnings.append(f"뉴스 수집 실패: {e}")

    try:
        filings = fetch_sec_filings(
            ticker=collected.ticker,
            start_date=str(collected.start_date),
            end_date=str(collected.end_date),
        )
    except Exception as e:
        warnings.append(f"SEC 공시 수집 실패: {e}")

    return {
        "collected_data": collected.model_copy(
            update={
                "news_articles": articles,
                "sec_filings": filings,
                "data_quality_warnings": collected.data_quality_warnings + warnings,
            }
        )
    }
