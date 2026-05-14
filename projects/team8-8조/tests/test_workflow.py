import unittest

from daily_news_agent.models import ArticleMatch, NewsArticle
from daily_news_agent.naver_news import NaverNewsError
from daily_news_agent.news_source import NAVER_KEY_MISSING_MESSAGE, NewsRouter
from daily_news_agent.workflow import DailyNewsWorkflow


class FakeNewsClient:
    def __init__(self, articles_by_keyword=None, error=None):
        self.articles_by_keyword = articles_by_keyword or {}
        self.error = error
        self.fetch_calls = []

    def fetch(self, keyword, limit=10):
        self.fetch_calls.append((keyword, limit))
        if self.error is not None:
            raise self.error
        return self.articles_by_keyword.get(keyword, [])[:limit]


class FakeNewsRouter:
    def __init__(self, articles_by_keyword=None, messages_by_keyword=None):
        self.articles_by_keyword = articles_by_keyword or {}
        self.messages_by_keyword = messages_by_keyword or {}

    def fetch(self, keyword, limit=10):
        return (
            self.articles_by_keyword.get(keyword, [])[:limit],
            list(self.messages_by_keyword.get(keyword, [])),
        )


class CountingAIClient:
    def __init__(self):
        self.embedded_texts = []
        self.queries = []

    def embed_documents(self, texts):
        self.embedded_texts.extend(texts)
        return [[1.0, 0.0] for _ in texts]

    def embed_query(self, text):
        self.queries.append(text)
        return [0.0, 1.0]

    def generate_briefing(self, interest, articles):
        return f"{interest}: {len(articles)}건"

    def generate_tags_batch(self, articles):
        return [[article.keyword] for article in articles]


class FakeVectorStore:
    def __init__(self, existing_ids=None, matches=None):
        self.existing_ids_value = set(existing_ids or [])
        self.upserted_articles = []
        self.query_keywords = []
        self.matches = matches or []

    def existing_ids(self, article_ids):
        return self.existing_ids_value.intersection(article_ids)

    def upsert_articles(self, articles, embeddings):
        self.upserted_articles.extend(articles)
        return len(articles)

    def query(self, query_embedding, top_k=8, keywords=None):
        self.query_keywords.append(keywords)
        return self.matches[:top_k]


def make_article(title, link, keyword):
    return NewsArticle(
        title=title,
        summary=f"{title} 요약",
        link=link,
        source="Example",
        published_at="2026-05-05",
        keyword=keyword,
    )


class NewsRouterTests(unittest.TestCase):
    def test_korean_keyword_uses_naver_when_available(self):
        article = make_article("반도체 뉴스", "https://example.com/n", "반도체")
        google = FakeNewsClient({"반도체": [make_article("Google 결과", "https://g/", "반도체")]})
        naver = FakeNewsClient({"반도체": [article]})
        router = NewsRouter(google_client=google, naver_client=naver)

        articles, messages = router.fetch("반도체", limit=5)

        self.assertEqual([a.link for a in articles], [article.link])
        self.assertEqual(messages, [])
        self.assertEqual(naver.fetch_calls, [("반도체", 5)])
        self.assertEqual(google.fetch_calls, [])

    def test_non_korean_keyword_uses_google(self):
        article = make_article("AI", "https://g/ai", "AI")
        google = FakeNewsClient({"AI": [article]})
        naver = FakeNewsClient({"AI": [make_article("Naver AI", "https://n/", "AI")]})
        router = NewsRouter(google_client=google, naver_client=naver)

        articles, messages = router.fetch("AI", limit=5)

        self.assertEqual([a.link for a in articles], [article.link])
        self.assertEqual(messages, [])
        self.assertEqual(google.fetch_calls, [("AI", 5)])
        self.assertEqual(naver.fetch_calls, [])

    def test_korean_keyword_falls_back_to_google_when_naver_missing(self):
        google_article = make_article("Google 한글", "https://g/k", "반도체")
        google = FakeNewsClient({"반도체": [google_article]})
        router = NewsRouter(google_client=google, naver_client=None)

        articles, messages = router.fetch("반도체", limit=5)

        self.assertEqual([a.link for a in articles], [google_article.link])
        self.assertEqual(messages, [NAVER_KEY_MISSING_MESSAGE])
        self.assertEqual(google.fetch_calls, [("반도체", 5)])

    def test_naver_missing_warning_emitted_only_once(self):
        google = FakeNewsClient({"반도체": [], "스타트업": []})
        router = NewsRouter(google_client=google, naver_client=None)

        _, first_messages = router.fetch("반도체", limit=5)
        _, second_messages = router.fetch("스타트업", limit=5)

        self.assertEqual(first_messages, [NAVER_KEY_MISSING_MESSAGE])
        self.assertEqual(second_messages, [])

    def test_naver_failure_falls_back_to_google_with_message(self):
        google_article = make_article("Google 우회", "https://g/back", "반도체")
        google = FakeNewsClient({"반도체": [google_article]})
        naver = FakeNewsClient(error=NaverNewsError("rate limit"))
        router = NewsRouter(google_client=google, naver_client=naver)

        articles, messages = router.fetch("반도체", limit=5)

        self.assertEqual([a.link for a in articles], [google_article.link])
        self.assertEqual(len(messages), 1)
        self.assertIn("Naver 호출 실패", messages[0])
        self.assertEqual(google.fetch_calls, [("반도체", 5)])


class WorkflowTests(unittest.TestCase):
    def test_collect_and_store_skips_existing_articles_before_embedding(self):
        existing = make_article("기존 기사", "https://example.com/existing", "AI")
        fresh = make_article("새 기사", "https://example.com/fresh", "AI")
        ai_client = CountingAIClient()
        vector_store = FakeVectorStore(existing_ids={existing.id})
        workflow = DailyNewsWorkflow(
            news_router=FakeNewsRouter({"AI": [existing, fresh]}),
            vector_store=vector_store,
            ai_client=ai_client,
        )

        result = workflow.collect_and_store("AI 산업", "AI", per_keyword_limit=3)

        self.assertEqual(result.collected_count, 2)
        self.assertEqual(result.stored_count, 1)
        self.assertEqual(result.skipped_existing_count, 1)
        self.assertEqual([article.link for article in vector_store.upserted_articles], [fresh.link])
        self.assertEqual(len(ai_client.embedded_texts), 1)
        self.assertIn("새 기사", ai_client.embedded_texts[0])

    def test_collect_and_store_tags_new_articles(self):
        article = make_article("AI 정책 발표", "https://example.com/ai", "AI")
        ai_client = CountingAIClient()
        store = FakeVectorStore()
        workflow = DailyNewsWorkflow(
            news_router=FakeNewsRouter({"AI": [article]}),
            vector_store=store,
            ai_client=ai_client,
        )

        workflow.collect_and_store("AI 동향", "AI")

        self.assertEqual(len(store.upserted_articles), 1)
        self.assertEqual(store.upserted_articles[0].tags, ["AI"])

    def test_collect_and_store_propagates_router_messages_to_errors(self):
        article = make_article("기사", "https://example.com/a", "반도체")
        ai_client = CountingAIClient()
        store = FakeVectorStore()
        router = FakeNewsRouter(
            articles_by_keyword={"반도체": [article]},
            messages_by_keyword={"반도체": ["Naver 키 미설정"]},
        )
        workflow = DailyNewsWorkflow(
            news_router=router,
            vector_store=store,
            ai_client=ai_client,
        )

        result = workflow.collect_and_store("반도체 산업", "반도체")

        self.assertEqual(result.errors, ["Naver 키 미설정"])

    def test_generate_briefing_queries_with_keyword_metadata_filter_first(self):
        article = make_article("선별 기사", "https://example.com/selected", "AI")
        ai_client = CountingAIClient()
        vector_store = FakeVectorStore(matches=[ArticleMatch(article=article, score=0.8)])
        workflow = DailyNewsWorkflow(
            news_router=FakeNewsRouter({}),
            vector_store=vector_store,
            ai_client=ai_client,
        )

        result = workflow.generate_briefing("AI 산업", ["AI", "반도체"], top_k=3)

        self.assertEqual(vector_store.query_keywords[0], ["AI", "반도체"])
        self.assertEqual([selected.link for selected in result.selected_articles], [article.link])
        self.assertEqual(result.briefing_markdown, "AI 산업: 1건")


if __name__ == "__main__":
    unittest.main()
