from __future__ import annotations

import json
import os

from openai import OpenAI

from models.schema import AnalysisReport, CauseHypothesis, TimelineEvent

_client: OpenAI | None = None


_UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
_MODEL = "solar-pro"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("UPSTAGE_API_KEY"),
            base_url=_UPSTAGE_BASE_URL,
        )
    return _client

SYSTEM_PROMPT = """You are a stock movement explanation agent.
Your job is to explain why a publicly traded stock moved up or down during a given time window.
Do not provide buy, sell, or hold recommendations.
Do not provide financial advice.
The final report must be concise, structured, evidence-based, and understandable to non-professional investors."""

_REPORT_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "submit_report",
        "description": "Submit the final structured analysis report",
        "parameters": {
            "type": "object",
            "required": [
                "one_line_conclusion", "final_report_markdown",
                "bull_case", "bear_case", "watch_next", "timeline",
            ],
            "properties": {
                "one_line_conclusion": {"type": "string"},
                "final_report_markdown": {"type": "string"},
                "bull_case": {"type": "string"},
                "bear_case": {"type": "string"},
                "watch_next": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 3,
                    "maxItems": 5,
                },
                "timeline": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "required": ["datetime", "type", "description"],
                        "properties": {
                            "datetime": {"type": "string"},
                            "type": {
                                "type": "string",
                                "enum": ["price_move", "news", "earnings", "filing", "analyst"],
                            },
                            "description": {"type": "string"},
                            "url": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


def build_report_prompt(
    ticker: str,
    period: str,
    price_change_pct: float,
    hypotheses: list[CauseHypothesis],
    spy_change: float,
    sector_change: float,
    sector_name: str,
    peers: list[dict],
    is_abnormal: bool,
) -> str:
    excess_return = price_change_pct - spy_change
    is_stock_specific = abs(excess_return) > 2.0

    top_hyps = sorted(hypotheses, key=lambda h: h.score, reverse=True)[:3]
    hyp_lines = "\n\n".join(
        f"{i + 1}. {h.title} ({h.confidence} confidence, score: {h.score:.2f})\n   {h.explanation}"
        for i, h in enumerate(top_hyps)
    )

    peer_lines = "\n".join(
        f"  {p['ticker']}: {'+' if p['change'] >= 0 else ''}{p['change']:.2f}%"
        for p in peers
    ) or "  No peer data available"

    return f"""Generate a complete investor-friendly analysis report for {ticker} ({period}).

STOCK: {ticker}
PERIOD: {period}
PRICE CHANGE: {price_change_pct:.2f}%
ABNORMAL MOVE: {is_abnormal}
STOCK-SPECIFIC MOVE: {is_stock_specific}

MARKET CONTEXT:
- S&P 500: {spy_change:.2f}%
- {sector_name} sector ETF: {sector_change:.2f}%
- Excess return vs S&P 500: {excess_return:.2f}%

PEER COMPARISON:
{peer_lines}

TOP HYPOTHESES:
{hyp_lines}

Write the full report in Markdown with these exact sections:
## One-Line Conclusion
## Price Movement Summary
## Is This Move Abnormal?
## Top Likely Causes
## Timeline of Events
## Market, Sector & Peer Comparison
## Bull Case
## Bear Case
## What to Watch Next

Also provide:
- one_line_conclusion: a single sentence summarising the primary cause
- bull_case: a short paragraph on the optimistic scenario
- bear_case: a short paragraph on the pessimistic scenario
- watch_next: 3–5 things to monitor going forward
- timeline: key events with datetime, type, and description

Format as JSON matching the report schema."""


def call_report_llm(
    ticker: str,
    period: str,
    price_change_pct: float,
    hypotheses: list[CauseHypothesis],
    spy_change: float,
    sector_change: float,
    sector_name: str,
    peers: list[dict],
    is_abnormal: bool,
) -> AnalysisReport:
    prompt = build_report_prompt(
        ticker=ticker,
        period=period,
        price_change_pct=price_change_pct,
        hypotheses=hypotheses,
        spy_change=spy_change,
        sector_change=sector_change,
        sector_name=sector_name,
        peers=peers,
        is_abnormal=is_abnormal,
    )

    response = _get_client().chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        tools=[_REPORT_TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_report"}},
        temperature=0.2,
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise RuntimeError("LLM did not invoke the required tool — no tool_calls in response")
    tool_call = tool_calls[0]
    data = json.loads(tool_call.function.arguments)

    timeline = [
        TimelineEvent(
            datetime=e["datetime"],
            type=e["type"],
            description=e["description"],
            url=e.get("url"),
        )
        for e in data.get("timeline", [])
    ]

    return AnalysisReport(
        one_line_conclusion=data["one_line_conclusion"],
        final_report_markdown=data["final_report_markdown"],
        bull_case=data["bull_case"],
        bear_case=data["bear_case"],
        watch_next=data["watch_next"],
        timeline=timeline,
    )
