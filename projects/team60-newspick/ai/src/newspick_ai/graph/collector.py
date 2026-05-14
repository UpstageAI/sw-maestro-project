import calendar
import hashlib
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx

from newspick_ai.graph.state import ArticleState, RefreshState

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 NewsPick/1.0"
    ),
    "Accept": (
        "application/rss+xml, application/xml;q=0.9, "
        "text/xml;q=0.8, */*;q=0.5"
    ),
}

MAX_ARTICLES_PER_FEED = 5

_SOURCE_BY_DOMAIN = {
    "hankyung.com": "한국경제",
    "mk.co.kr": "매일경제",
    "newsis.com": "뉴시스",
    "etnews.com": "전자신문",
}

_CATEGORY_CHANNEL_TITLES = {
    "IT·바이오",
    "경제",
    "사회",
    "이슈",
    "정책",
    "정치",
    "테크",
}


class RssCollector:
    def __init__(
        self,
        feed_reader: Callable[[str], str | bytes] | None = None,
        max_articles_per_feed: int = MAX_ARTICLES_PER_FEED,
    ):
        self._feed_reader = feed_reader
        self._max_articles_per_feed = max_articles_per_feed

    def collect(
        self,
        feed_url: str,
        category: str = "general",
        source_name: str | None = None,
    ) -> list[ArticleState]:
        parsed = self._parse(feed_url)
        source = self._source(feed_url, source_name or parsed.feed.get("title"))
        entries = parsed.entries[: self._max_articles_per_feed]
        logger.info("RSS 수집 [%s][%s] %d건", category, source, len(entries))
        if not parsed.entries:
            logger.warning(
                "RSS 항목 없음: category=%s url=%s status=%s bozo=%s error=%s",
                category,
                feed_url,
                parsed.get("status"),
                parsed.get("bozo"),
                getattr(parsed, "bozo_exception", None),
            )

        articles: list[ArticleState] = []
        for entry in entries:
            url = entry.get("link", "")
            articles.append(
                {
                    "id": self._article_id(url),
                    "url": url,
                    "title": entry.get("title", ""),
                    "source": source,
                    "category": self._category(entry, category),
                    "publishedAt": self._published_at(entry),
                    "description": entry.get("summary", ""),
                    "status": "collected",
                }
            )

        return articles

    def run(
        self,
        state: RefreshState,
        feed_url: str,
        category: str = "general",
        source_name: str | None = None,
    ) -> RefreshState:
        articles = self.collect(feed_url, category, source_name)
        return {
            "articles": [*state["articles"], *articles],
            "events": [
                *state["events"],
                {
                    "stage": "collect",
                    "message": f"{len(articles)}건 수집",
                    "articleIds": [article["id"] for article in articles],
                },
            ],
        }

    def _parse(self, feed_url: str):
        if self._feed_reader is None:
            response = httpx.get(
                feed_url,
                headers=_HEADERS,
                follow_redirects=True,
                timeout=10,
            )
            parsed = feedparser.parse(response.content)
            parsed["status"] = response.status_code
            if response.status_code >= 400 or parsed.get("bozo"):
                logger.warning(
                    "RSS 파싱 경고: url=%s status=%s final_url=%s bozo=%s error=%s",
                    feed_url,
                    response.status_code,
                    response.url,
                    parsed.get("bozo"),
                    getattr(parsed, "bozo_exception", None),
                )
            return parsed

        feed_body = self._feed_reader(feed_url)
        return feedparser.parse(feed_body)

    @staticmethod
    def _article_id(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _category(entry: Any, default: str = "general") -> str:
        return default

    @staticmethod
    def _source(feed_url: str, raw_source: str | None) -> str:
        domain_source = RssCollector._source_from_url(feed_url)
        source = (raw_source or "").strip()

        if source.startswith("한국경제 | 뉴스"):
            return "한국경제"
        if source in _CATEGORY_CHANNEL_TITLES and domain_source:
            return domain_source

        return source or domain_source or "Unknown"

    @staticmethod
    def _source_from_url(feed_url: str) -> str | None:
        host = urlparse(feed_url).netloc.lower()
        for domain, source in _SOURCE_BY_DOMAIN.items():
            if host == domain or host.endswith(f".{domain}"):
                return source

        return None

    @staticmethod
    def _published_at(entry: Any) -> str:
        published = entry.get("published_parsed")
        if published:
            timestamp = calendar.timegm(published)
            return datetime.fromtimestamp(timestamp, UTC).isoformat().replace(
                "+00:00", "Z"
            )

        return datetime.now(UTC).isoformat().replace("+00:00", "Z")
