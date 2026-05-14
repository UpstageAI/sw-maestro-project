from __future__ import annotations

import dataclasses
from collections.abc import Callable

from daily_news_agent.ai_client import AIClient
from daily_news_agent.models import BriefingResult, CollectionResult, NewsArticle
from daily_news_agent.news_source import NewsRouter
from daily_news_agent.preprocessor import deduplicate_articles, normalize_keywords
from daily_news_agent.vector_store import ChromaArticleStore


class DailyNewsWorkflow:
    def __init__(
        self,
        news_router: NewsRouter,
        vector_store: ChromaArticleStore,
        ai_client: AIClient,
    ) -> None:
        self.news_router = news_router
        self.vector_store = vector_store
        self.ai_client = ai_client

    def run(
        self,
        interest: str,
        keyword_text: str,
        per_keyword_limit: int = 3,
        top_k: int = 5,
    ) -> BriefingResult:
        collection_result = self.collect_and_store(
            interest=interest,
            keyword_text=keyword_text,
            per_keyword_limit=per_keyword_limit,
        )
        return self.generate_briefing(
            interest=interest,
            keywords=collection_result.keywords,
            top_k=top_k,
            fallback_articles=collection_result.collected_articles,
            collected_count=collection_result.collected_count,
            stored_count=collection_result.stored_count,
            skipped_existing_count=collection_result.skipped_existing_count,
            errors=collection_result.errors,
        )

    def collect_and_store(
        self,
        interest: str,
        keyword_text: str,
        per_keyword_limit: int = 3,
        progress: Callable[[str], None] | None = None,
    ) -> CollectionResult:
        self._report(progress, "검색 키워드를 정리합니다.")
        keywords = normalize_keywords(keyword_text, limit=3) or normalize_keywords(interest, limit=3)
        if not keywords:
            raise ValueError("관심 분야 또는 검색 키워드를 입력해야 합니다.")

        collected_articles: list[NewsArticle] = []
        errors: list[str] = []
        for keyword in keywords:
            self._report(progress, f"`{keyword}` 뉴스를 수집합니다.")
            articles, messages = self.news_router.fetch(keyword, limit=per_keyword_limit)
            collected_articles.extend(articles)
            errors.extend(messages)

        self._report(progress, "수집된 기사를 정제하고 중복 링크를 제거합니다.")
        deduplicated_articles = deduplicate_articles(collected_articles)
        existing_ids = self.vector_store.existing_ids([article.id for article in deduplicated_articles])
        new_articles = [article for article in deduplicated_articles if article.id not in existing_ids]
        skipped_existing_count = len(deduplicated_articles) - len(new_articles)

        stored_count = 0
        if new_articles:
            self._report(progress, f"새 기사 {len(new_articles)}건의 태그를 생성합니다.")
            tags_list = self.ai_client.generate_tags_batch(new_articles)
            new_articles = [
                dataclasses.replace(article, tags=tags)
                for article, tags in zip(new_articles, tags_list)
            ]
            self._report(progress, f"새 기사 {len(new_articles)}건의 embedding을 생성합니다.")
            embeddings = self.ai_client.embed_documents(
                [article.document_text() for article in new_articles]
            )
            self._report(progress, "새 기사를 Chroma Vector DB에 저장합니다.")
            stored_count = self.vector_store.upsert_articles(new_articles, embeddings)
        elif deduplicated_articles:
            self._report(progress, "모든 기사가 이미 Vector DB에 저장되어 embedding 생성을 건너뜁니다.")

        return CollectionResult(
            interest=interest,
            keywords=keywords,
            collected_articles=deduplicated_articles,
            collected_count=len(deduplicated_articles),
            stored_count=stored_count,
            skipped_existing_count=skipped_existing_count,
            errors=errors,
        )

    def generate_briefing(
        self,
        interest: str,
        keywords: list[str],
        top_k: int = 5,
        fallback_articles: list[NewsArticle] | None = None,
        collected_count: int = 0,
        stored_count: int = 0,
        skipped_existing_count: int = 0,
        errors: list[str] | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> BriefingResult:
        fallback_articles = fallback_articles or []
        errors = errors or []
        self._report(progress, "관심 분야 query embedding을 생성합니다.")
        selected_articles = self._select_articles(
            interest=interest,
            keywords=keywords,
            fallback_articles=fallback_articles,
            top_k=top_k,
        )
        self._report(progress, f"선별 기사 {len(selected_articles)}건으로 브리핑을 생성합니다.")
        briefing = self.ai_client.generate_briefing(interest, selected_articles)
        briefing = _append_tags_section(briefing, selected_articles)

        return BriefingResult(
            interest=interest,
            keywords=keywords,
            collected_count=collected_count,
            stored_count=stored_count,
            skipped_existing_count=skipped_existing_count,
            selected_articles=selected_articles,
            briefing_markdown=briefing,
            errors=errors,
        )

    def _select_articles(
        self,
        interest: str,
        keywords: list[str],
        fallback_articles: list[NewsArticle],
        top_k: int,
    ) -> list[NewsArticle]:
        query_embedding = self.ai_client.embed_query(interest)
        matches = self.vector_store.query(query_embedding=query_embedding, top_k=top_k, keywords=keywords)
        if not matches:
            matches = self.vector_store.query(query_embedding=query_embedding, top_k=top_k)
        selected_articles = [match.article for match in matches if match.article.link]
        return selected_articles or fallback_articles[:top_k]

    def _report(self, progress: Callable[[str], None] | None, message: str) -> None:
        if progress:
            progress(message)


def _append_tags_section(briefing: str, articles: list[NewsArticle]) -> str:
    tag_lines = [
        f"- **{article.title}**: " + " ".join(f"`#{t}`" for t in article.tags)
        for article in articles
        if article.tags
    ]
    if not tag_lines:
        return briefing
    return briefing.rstrip() + "\n\n## 기사 태그\n" + "\n".join(tag_lines)
