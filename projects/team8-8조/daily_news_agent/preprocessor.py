from __future__ import annotations

import html
import re
from collections.abc import Iterable

from daily_news_agent.models import NewsArticle


TAG_PATTERN = re.compile(r"<[^>]+>")
WHITESPACE_PATTERN = re.compile(r"\s+")
HANGUL_PATTERN = re.compile(r"[가-힣ㄱ-ㆎ]")


def is_korean(text: str | None) -> bool:
    if not text:
        return False
    return bool(HANGUL_PATTERN.search(text))


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    without_tags = TAG_PATTERN.sub(" ", html.unescape(value))
    return WHITESPACE_PATTERN.sub(" ", without_tags).strip()


def normalize_keywords(raw_keywords: str, limit: int = 3) -> list[str]:
    normalized_input = raw_keywords.replace("\n", ",").replace(";", ",")
    keywords: list[str] = []
    seen: set[str] = set()

    for raw_keyword in normalized_input.split(","):
        keyword = clean_text(raw_keyword)
        if not keyword or keyword in seen:
            continue
        keywords.append(keyword)
        seen.add(keyword)
        if len(keywords) >= limit:
            break

    return keywords


def deduplicate_articles(articles: Iterable[NewsArticle]) -> list[NewsArticle]:
    deduplicated: list[NewsArticle] = []
    seen_links: set[str] = set()

    for article in articles:
        if not article.title or not article.link or article.link in seen_links:
            continue
        deduplicated.append(article)
        seen_links.add(article.link)

    return deduplicated

