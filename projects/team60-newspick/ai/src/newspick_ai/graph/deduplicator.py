from typing import Protocol

from newspick_ai.graph.state import RefreshState


class ArticleRepository(Protocol):
    def existing_urls(self, urls: list[str]) -> set[str]:
        ...


class EmptyArticleRepository:
    def existing_urls(self, urls: list[str]) -> set[str]:
        return set()


class Deduplicator:
    def __init__(self, repository: ArticleRepository | None = None):
        self._repository = repository or EmptyArticleRepository()

    def run(self, state: RefreshState) -> RefreshState:
        articles = state["articles"]
        existing_urls = self._repository.existing_urls(
            [article["url"] for article in articles]
        )
        deduplicated = [
            article for article in articles if article["url"] not in existing_urls
        ]
        dropped_count = len(articles) - len(deduplicated)

        return {
            "articles": deduplicated,
            "events": [
                *state["events"],
                {
                    "stage": "dedupe",
                    "message": f"{dropped_count}건 중복 제거",
                    "articleIds": [article["id"] for article in deduplicated],
                    "count": dropped_count,
                },
            ],
        }
