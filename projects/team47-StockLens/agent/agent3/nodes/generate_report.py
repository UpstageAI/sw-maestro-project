from __future__ import annotations

from agent.agent3.tools.llm import call_report_llm
from models.schema import AgentState


def generate_report_node(state: AgentState) -> dict:
    """OpenAI GPT-4o를 사용해 구조화 분석 보고서를 생성하는 노드."""
    collected = state["collected_data"]
    hypotheses = state.get("hypotheses") or []

    stats = collected.price_stats
    period_pct = stats.period_pct_change if stats else 0.0
    is_abnormal = stats.is_abnormal_move if stats else False

    peer_set = {p.upper() for p in collected.peer_tickers}
    spy_change = 0.0
    sector_change = 0.0
    peers: list[dict] = []

    for b in collected.benchmarks:
        if b.ticker == "^GSPC":
            spy_change = b.pct_change_period
        elif b.ticker.upper() in peer_set:
            peers.append({"ticker": b.ticker, "change": b.pct_change_period})
        else:
            sector_change = b.pct_change_period

    sector_name = collected.sector or "Market"
    period = f"{collected.start_date} to {collected.end_date}"

    try:
        report = call_report_llm(
            ticker=collected.ticker,
            period=period,
            price_change_pct=period_pct,
            hypotheses=hypotheses,
            spy_change=spy_change,
            sector_change=sector_change,
            sector_name=sector_name,
            peers=peers,
            is_abnormal=is_abnormal,
        )
    except Exception as e:
        return {"errors": [f"보고서 생성 실패: {e}"]}

    return {"report": report}
