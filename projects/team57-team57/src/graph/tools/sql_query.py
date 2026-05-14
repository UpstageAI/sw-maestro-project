"""SQL query tool — LLM이 호출할 수 있는 안전한 집계 함수.

LangGraph Tool use surface: PatternAgent가 이 tool을 bind_tools로 받아
arguments를 결정해 호출 → 결과를 보고 자연어로 요약.
"""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.tools import tool

from src.store import sqlite as db


@tool
def query_review_stats(
    place_id: str,
    group_by: Literal["category", "sentiment"] = "category",
    days: int = 28,
) -> str:
    """매장의 최근 N일 리뷰 통계를 집계합니다.

    Args:
        place_id: 매장 식별자 (예: "PLACE_001")
        group_by: 집계 기준. 'category'는 부정 리뷰의 카테고리별 빈도 TOP 3,
                  'sentiment'는 감정별 전체 빈도.
        days: 윈도우 일수 (기본 28일 = 4주).

    Returns:
        JSON 문자열. category: [{"category": "대기시간", "freq": 12}, ...].
                     sentiment: {"positive": 8, "negative": 18, "neutral": 2}.
    """
    if group_by == "category":
        rows = db.query_top3_negative_categories(place_id, days=days)
        return json.dumps(rows, ensure_ascii=False)

    # group_by == "sentiment"
    with db.connect() as conn:
        result = conn.execute(
            """SELECT sentiment, COUNT(*) AS freq
               FROM reviews
               WHERE place_id = ?
                 AND sentiment IS NOT NULL
                 AND created_at >= datetime('now', ?)
               GROUP BY sentiment""",
            (place_id, f"-{days} days"),
        ).fetchall()
    return json.dumps(
        {row["sentiment"]: row["freq"] for row in result}, ensure_ascii=False
    )
