from __future__ import annotations

import json
from urllib.parse import urlparse

from daily_news_agent.models import NewsArticle
from daily_news_agent.preprocessor import clean_text


NAVER_NEWS_API_URL = "https://openapi.naver.com/v1/search/news.json"


class NaverNewsError(RuntimeError):
    pass


def _extract_source(originallink: str) -> str:
    if not originallink:
        return "Naver News"
    try:
        host = urlparse(originallink).hostname or ""
    except ValueError:
        return "Naver News"
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host or "Naver News"


def parse_naver_news_response(payload: str, keyword: str, limit: int | None = None) -> list[NewsArticle]:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise NaverNewsError("Naver News 응답을 JSON으로 파싱하지 못했습니다.") from exc

    raw_items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(raw_items, list):
        return []

    articles: list[NewsArticle] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue

        title = clean_text(item.get("title"))
        originallink = clean_text(item.get("originallink"))
        link = originallink or clean_text(item.get("link"))
        summary = clean_text(item.get("description"))
        published_at = clean_text(item.get("pubDate"))

        if not title or not link:
            continue

        articles.append(
            NewsArticle(
                title=title,
                summary=summary,
                link=link,
                source=_extract_source(originallink),
                published_at=published_at,
                keyword=keyword,
            )
        )

        if limit is not None and len(articles) >= limit:
            break

    return articles


class NaverNewsClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        timeout_seconds: int = 10,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout_seconds = timeout_seconds

    def fetch(self, keyword: str, limit: int = 10) -> list[NewsArticle]:
        try:
            import requests
        except ImportError as exc:
            raise NaverNewsError("requests 패키지가 설치되어 있지 않습니다.") from exc

        params = {
            "query": keyword,
            "display": max(1, min(int(limit), 100)),
            "sort": "date",
        }
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "User-Agent": "daily-news-agent/0.1",
        }
        try:
            response = requests.get(
                NAVER_NEWS_API_URL,
                params=params,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NaverNewsError(f"Naver News 요청에 실패했습니다: {keyword}") from exc

        return parse_naver_news_response(response.text, keyword=keyword, limit=limit)
