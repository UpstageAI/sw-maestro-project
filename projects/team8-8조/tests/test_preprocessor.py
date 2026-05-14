import unittest

from daily_news_agent.models import NewsArticle
from daily_news_agent.preprocessor import deduplicate_articles, is_korean, normalize_keywords


class PreprocessorTests(unittest.TestCase):
    def test_normalize_keywords_limits_to_unique_non_empty_values(self):
        keywords = normalize_keywords(" AI, 반도체, AI, , 스타트업, 경제 ", limit=3)

        self.assertEqual(keywords, ["AI", "반도체", "스타트업"])

    def test_deduplicate_articles_keeps_first_article_by_link(self):
        articles = [
            NewsArticle(
                title="첫 번째 기사",
                summary="첫 번째 요약",
                link="https://example.com/a",
                source="A",
                published_at="2026-05-04",
                keyword="AI",
            ),
            NewsArticle(
                title="중복 기사",
                summary="중복 요약",
                link="https://example.com/a",
                source="B",
                published_at="2026-05-04",
                keyword="AI",
            ),
            NewsArticle(
                title="다른 기사",
                summary="다른 요약",
                link="https://example.com/b",
                source="C",
                published_at="2026-05-04",
                keyword="반도체",
            ),
        ]

        deduped = deduplicate_articles(articles)

        self.assertEqual([article.title for article in deduped], ["첫 번째 기사", "다른 기사"])

    def test_is_korean_detects_hangul_characters(self):
        self.assertTrue(is_korean("반도체"))
        self.assertTrue(is_korean("AI 반도체"))
        self.assertTrue(is_korean("ㄱ"))

    def test_is_korean_returns_false_for_non_hangul(self):
        self.assertFalse(is_korean("AI"))
        self.assertFalse(is_korean("OpenAI 2026"))
        self.assertFalse(is_korean(""))
        self.assertFalse(is_korean(None))


if __name__ == "__main__":
    unittest.main()
