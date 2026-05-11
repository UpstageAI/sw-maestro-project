from __future__ import annotations

from datetime import datetime, timezone

from agent.agent1.tools.price import fetch_price_data
from models.schema import AgentState, CollectedData


def collect_price_node(state: AgentState) -> dict:
    """주가·거래량 조회 노드. 실패 시 errors 설정 후 조기 종료."""
    ticker = state["ticker"]
    start_date = state["start_date"]
    end_date = state["end_date"]

    try:
        prices, stats, company_name, sector, industry = fetch_price_data(ticker, start_date, end_date)
    except Exception as e:
        return {"errors": [f"주가 수집 실패: {e}"]}

    collected = CollectedData(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        company_name=company_name,
        sector=sector,
        industry=industry,
        prices=prices,
        price_stats=stats,
        collected_at=datetime.now(timezone.utc).isoformat(),
    )

    return {"collected_data": collected}
