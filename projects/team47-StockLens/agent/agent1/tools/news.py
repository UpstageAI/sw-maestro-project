from __future__ import annotations

import os

import requests

from models.schema import NewsArticle

MAX_ARTICLES = 50
NEWSAPI_BASE = "https://newsapi.org/v2/everything"


def fetch_news(
    company_name: str, ticker: str, start_date: str, end_date: str
) -> list[NewsArticle]:
    """NewsAPI로 관련 기사 수집. 실패 시 빈 리스트 반환."""
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        raise EnvironmentError("NEWSAPI_KEY 환경변수가 설정되지 않았습니다.")

    query = f'"{company_name}" OR "{ticker}" stock'
    params = {
        "q": query,
        "from": start_date,
        "to": end_date,
        "language": "en",
        "sortBy": "relevancy",
        "pageSize": MAX_ARTICLES,
        "apiKey": api_key,
    }

    resp = requests.get(NEWSAPI_BASE, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    if data.get("status") == "error":
        raise RuntimeError(f"NewsAPI error: {data.get('code')} — {data.get('message')}")

    articles: list[NewsArticle] = []
    for item in data.get("articles", []):
        articles.append(
            NewsArticle(
                title=item.get("title") or "",
                source=item.get("source", {}).get("name") or "",
                published_at=item.get("publishedAt") or "",
                url=item.get("url") or "",
                summary=item.get("description"),
            )
        )

    return articles
