from __future__ import annotations

from agent.agent1.tools.benchmark import fetch_benchmark_data
from models.schema import AgentState


def collect_benchmark_node(state: AgentState) -> dict:
    """벤치마크·섹터ETF·Peer 비교 노드. 실패해도 파이프라인 계속."""
    collected = state["collected_data"]
    warnings: list[str] = []

    try:
        benchmarks, peer_tickers, fetch_warnings = fetch_benchmark_data(
            ticker=collected.ticker,
            sector=collected.sector or "",
            start_date=str(collected.start_date),
            end_date=str(collected.end_date),
            industry=collected.industry or "",
        )
        warnings.extend(fetch_warnings)
    except Exception as e:
        benchmarks, peer_tickers = [], []
        warnings.append(f"벤치마크 수집 실패: {e}")

    return {
        "collected_data": collected.model_copy(
            update={
                "benchmarks": benchmarks,
                "peer_tickers": peer_tickers,
                "data_quality_warnings": collected.data_quality_warnings + warnings,
            }
        )
    }
