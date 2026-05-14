from __future__ import annotations

from models.schema import AgentState, NewsArticle, SECFiling


def filter_noise_node(state: AgentState) -> dict:
    """뉴스·공시 노이즈 필터링·중복 제거 노드."""
    collected = state["collected_data"]

    seen_titles: set[str] = set()
    filtered_news: list[NewsArticle] = []
    for article in collected.news_articles:
        title = article.title.strip()
        if not title or not article.url:
            continue
        key = title.lower()
        if key in seen_titles:
            continue
        seen_titles.add(key)
        filtered_news.append(article)

    seen_urls: set[str] = set()
    filtered_filings: list[SECFiling] = []
    for filing in collected.sec_filings:
        if not filing.url or filing.url in seen_urls:
            continue
        seen_urls.add(filing.url)
        filtered_filings.append(filing)

    return {
        "collected_data": collected.model_copy(
            update={
                "news_articles": filtered_news,
                "sec_filings": filtered_filings,
            }
        )
    }
