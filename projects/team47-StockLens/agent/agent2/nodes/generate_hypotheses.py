from __future__ import annotations

from agent.agent2.tools.llm import call_hypothesis_llm
from models.schema import AgentState


def generate_hypotheses_node(state: AgentState) -> dict:
    """OpenAI GPT-4o를 사용해 주가 변동 원인 가설 3~5개를 생성하는 노드."""
    collected = state["collected_data"]

    stats = collected.price_stats
    period_pct = stats.period_pct_change if stats else 0.0
    is_abnormal = stats.is_abnormal_move if stats else False
    avg_vol = stats.avg_volume if stats else 0.0

    # Simple z-score proxy: period change normalised by typical daily volatility
    z_score = abs(period_pct / 1.5) if period_pct != 0 else 0.0

    # Volume change: last-day volume vs period average
    volume_change_pct = 0.0
    if collected.prices and avg_vol > 0:
        last_vol = collected.prices[-1].volume
        volume_change_pct = round((last_vol - avg_vol) / avg_vol * 100, 2)

    # Split benchmarks into SPY, sector ETF, and peers
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
            # Sector ETF
            sector_change = b.pct_change_period

    sector_name = collected.sector or "Market"
    period = f"{collected.start_date} to {collected.end_date}"

    # Combine news articles and SEC filings into a flat list for the prompt
    news_items: list[dict] = []
    for a in collected.news_articles:
        news_items.append({
            "title": a.title,
            "source": a.source,
            "published_at": a.published_at,
        })
    for f in collected.sec_filings:
        news_items.append({
            "title": f"{f.form_type}: {f.description}",
            "source": "SEC EDGAR",
            "published_at": f.filed_at,
        })

    try:
        hypotheses = call_hypothesis_llm(
            ticker=collected.ticker,
            period=period,
            price_change_pct=period_pct,
            volume_change_pct=volume_change_pct,
            spy_change=spy_change,
            sector_change=sector_change,
            sector_name=sector_name,
            peers=peers,
            news_items=news_items,
            is_abnormal=is_abnormal,
            z_score=z_score,
        )
    except Exception as e:
        return {"errors": [f"가설 생성 실패: {e}"]}

    return {"hypotheses": hypotheses}
