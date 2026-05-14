from __future__ import annotations

import json
import os

from openai import OpenAI

from models.schema import CauseHypothesis, ScoreComponents

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
You must not simply list news articles.
You must investigate possible causes, compare evidence, and produce a ranked explanation.
Do not provide buy, sell, or hold recommendations.
Do not provide financial advice.
Cite sources for every major claim.
Prefer primary sources and reputable financial news.
Clearly label uncertainty.
Separate company-specific, sector-wide, market-wide, macro, legal/regulatory, earnings, analyst, and technical drivers.
Compare the stock against the broader market, sector ETF, and peers.
Align event timestamps with price and volume movements when possible.
Rank explanations by timing alignment, source credibility, stock specificity, volume confirmation, and independent source confirmation.
Reject weak explanations.
Always include what the user should watch next.
The final report must be concise, structured, evidence-based, and understandable to non-professional investors."""

_HYPOTHESIS_TOOL: dict = {
    "type": "function",
    "function": {
        "name": "submit_hypotheses",
        "description": "Submit ranked hypotheses explaining a stock price movement",
        "parameters": {
            "type": "object",
            "properties": {
                "hypotheses": {
                    "type": "array",
                    "minItems": 3,
                    "maxItems": 5,
                    "items": {
                        "type": "object",
                        "required": [
                            "title", "category", "explanation",
                            "evidence", "counterpoints", "score_components",
                        ],
                        "properties": {
                            "title": {"type": "string"},
                            "category": {
                                "type": "string",
                                "enum": [
                                    "earnings", "analyst", "macro", "sector",
                                    "company_specific", "regulatory", "technical",
                                    "market_wide", "unknown",
                                ],
                            },
                            "explanation": {"type": "string"},
                            "evidence": {"type": "array", "items": {"type": "string"}},
                            "counterpoints": {"type": "array", "items": {"type": "string"}},
                            "supporting_article_indices": {
                                "type": "array",
                                "items": {"type": "integer"},
                            },
                            "score_components": {
                                "type": "object",
                                "required": [
                                    "timing_alignment", "source_credibility",
                                    "stock_specificity", "volume_confirmation",
                                    "independent_source_confirmation",
                                ],
                                "properties": {
                                    "timing_alignment": {"type": "number"},
                                    "source_credibility": {"type": "number"},
                                    "stock_specificity": {"type": "number"},
                                    "volume_confirmation": {"type": "number"},
                                    "independent_source_confirmation": {"type": "number"},
                                },
                            },
                        },
                    },
                },
            },
            "required": ["hypotheses"],
        },
    },
}


def build_hypothesis_prompt(
    ticker: str,
    period: str,
    price_change_pct: float,
    volume_change_pct: float,
    spy_change: float,
    sector_change: float,
    sector_name: str,
    peers: list[dict],
    news_items: list[dict],
    is_abnormal: bool,
    z_score: float,
) -> str:
    direction = "up" if price_change_pct >= 0 else "down"
    peer_lines = "\n".join(
        f"  {p['ticker']}: {'+' if p['change'] >= 0 else ''}{p['change']:.2f}%"
        for p in peers
    ) or "  No peer data available"
    news_lines = "\n".join(
        f"  [{i + 1}] \"{n['title']}\" — {n['source']} ({str(n['published_at'])[:10]})"
        for i, n in enumerate(news_items[:30])  # cap at 30 items for context window
    ) or "  No news/filings found for this period"

    return f"""Analyze why {ticker} moved {direction} {abs(price_change_pct):.2f}% over {period}.

PRICE DATA:
- {ticker} price change: {price_change_pct:.2f}%
- {ticker} volume change: {volume_change_pct:.2f}%
- Abnormal move: {is_abnormal} (z-score: {z_score:.2f})

MARKET CONTEXT:
- S&P 500 (^GSPC): {spy_change:.2f}%
- {sector_name} sector ETF: {sector_change:.2f}%
- Excess return vs S&P 500: {(price_change_pct - spy_change):.2f}%

PEER COMPARISON:
{peer_lines}

NEWS AND EVENTS (0-indexed):
{news_lines}

Generate 3–5 hypotheses explaining the move. For each hypothesis, provide:
- A clear title
- Category (earnings, analyst, macro, sector, company_specific, regulatory, technical, market_wide, unknown)
- Explanation (2–3 sentences)
- Evidence (list of facts supporting it)
- Counterpoints (what weakens this hypothesis)
- Supporting article indices from the NEWS AND EVENTS list above (0-indexed integers)
- Score components (each 0.0–1.0):
  * timing_alignment: how well the event timing matches the price move
  * source_credibility: quality and reliability of sources
  * stock_specificity: how specific this cause is to this stock vs. general market
  * volume_confirmation: does volume movement support this cause
  * independent_source_confirmation: confirmed by multiple independent sources

Return results as JSON matching the provided function schema."""


def call_hypothesis_llm(
    ticker: str,
    period: str,
    price_change_pct: float,
    volume_change_pct: float,
    spy_change: float,
    sector_change: float,
    sector_name: str,
    peers: list[dict],
    news_items: list[dict],
    is_abnormal: bool,
    z_score: float,
) -> list[CauseHypothesis]:
    prompt = build_hypothesis_prompt(
        ticker=ticker,
        period=period,
        price_change_pct=price_change_pct,
        volume_change_pct=volume_change_pct,
        spy_change=spy_change,
        sector_change=sector_change,
        sector_name=sector_name,
        peers=peers,
        news_items=news_items,
        is_abnormal=is_abnormal,
        z_score=z_score,
    )

    response = _get_client().chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        tools=[_HYPOTHESIS_TOOL],
        tool_choice={"type": "function", "function": {"name": "submit_hypotheses"}},
        temperature=0.3,
    )

    tool_calls = response.choices[0].message.tool_calls
    if not tool_calls:
        raise RuntimeError("LLM did not invoke the required tool — no tool_calls in response")
    tool_call = tool_calls[0]
    parsed = json.loads(tool_call.function.arguments)

    hypotheses: list[CauseHypothesis] = []
    for i, h in enumerate(parsed["hypotheses"]):
        sc = h.get("score_components", {})
        hypotheses.append(
            CauseHypothesis(
                id=f"hypothesis-{i + 1}",
                title=h["title"],
                category=h["category"],
                explanation=h["explanation"],
                evidence=h.get("evidence", []),
                counterpoints=h.get("counterpoints", []),
                supporting_article_indices=h.get("supporting_article_indices", []),
                score_components=ScoreComponents(
                    timing_alignment=float(sc.get("timing_alignment", 0.0)),
                    source_credibility=float(sc.get("source_credibility", 0.0)),
                    stock_specificity=float(sc.get("stock_specificity", 0.0)),
                    volume_confirmation=float(sc.get("volume_confirmation", 0.0)),
                    independent_source_confirmation=float(
                        sc.get("independent_source_confirmation", 0.0)
                    ),
                ),
                score=0.0,
                confidence="Low",
            )
        )

    return hypotheses
