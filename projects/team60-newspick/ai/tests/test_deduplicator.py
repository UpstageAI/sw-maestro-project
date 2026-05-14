from newspick_ai.graph.deduplicator import Deduplicator


class FakeArticleRepository:
    def existing_urls(self, urls: list[str]) -> set[str]:
        return {"https://example.com/dup"} & set(urls)


def test_deduplicator_removes_articles_with_existing_urls():
    state = {
        "articles": [
            {"id": "article_dup", "url": "https://example.com/dup"},
            {"id": "article_new", "url": "https://example.com/new"},
        ],
        "events": [],
    }

    output = Deduplicator(repository=FakeArticleRepository()).run(state)

    assert len(output["articles"]) == 1
    assert output["articles"][0]["id"] == "article_new"
    assert output["events"][0]["stage"] == "dedupe"
    assert output["events"][0]["message"] == "1건 중복 제거"
