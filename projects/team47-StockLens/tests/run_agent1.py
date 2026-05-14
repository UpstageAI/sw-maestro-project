"""Agent 1 동작 확인용 스크립트. 실행: python -m tests.run_agent1"""
from __future__ import annotations

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv
load_dotenv()

from agent.agent1.graph import agent1_graph


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    start = sys.argv[2] if len(sys.argv) > 2 else "2024-01-01"
    end = sys.argv[3] if len(sys.argv) > 3 else "2024-01-31"

    print(f"\n[Agent 1 테스트] {ticker} | {start} ~ {end}\n")

    state = {
        "ticker": ticker,
        "start_date": start,
        "end_date": end,
        "collected_data": None,
        "hypotheses": None,
        "report": None,
        "errors": [],
    }

    result = agent1_graph.invoke(state)

    if result.get("errors"):
        print("오류:", result["errors"])
        return

    d = result["collected_data"]
    print(f"종목: {d.company_name} ({d.ticker})")
    print(f"섹터: {d.sector}")
    print(f"기간 수익률: {d.price_stats.period_pct_change}%")
    print(f"최대 일일 상승: {d.price_stats.max_single_day_gain}%")
    print(f"최대 일일 하락: {d.price_stats.max_single_day_loss}%")
    print(f"비정상 움직임: {d.price_stats.is_abnormal_move}")
    print(f"거래량 급증일: {d.price_stats.volume_spike_dates}")
    print(f"\n벤치마크 비교:")
    for b in d.benchmarks:
        print(f"  {b.label}: {b.pct_change_period:+.2f}%")
    print(f"\n뉴스 수집: {len(d.news_articles)}건")
    for a in d.news_articles[:3]:
        print(f"  [{a.source}] {a.title[:60]}")
    print(f"\nSEC 공시: {len(d.sec_filings)}건")
    for f in d.sec_filings[:3]:
        print(f"  [{f.form_type}] {f.filed_at} {f.description[:50]}")
    if d.data_quality_warnings:
        print(f"\n경고: {d.data_quality_warnings}")


if __name__ == "__main__":
    main()
