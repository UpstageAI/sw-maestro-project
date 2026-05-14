import unittest

from daily_news_agent.models import NewsArticle
from daily_news_agent.summarizer import build_briefing_messages


class SummarizerTests(unittest.TestCase):
    def test_build_briefing_messages_contains_interest_and_article_links(self):
        articles = [
            NewsArticle(
                title="AI 정책 발표",
                summary="정부가 AI 정책을 발표했다.",
                link="https://example.com/ai",
                source="Example",
                published_at="2026-05-04",
                keyword="AI",
            )
        ]

        messages = build_briefing_messages("AI 산업 동향", articles)

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("뉴스 브리핑 에디터", messages[0]["content"])
        self.assertEqual(messages[1]["role"], "user")
        self.assertIn("AI 산업 동향", messages[1]["content"])
        self.assertIn("https://example.com/ai", messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
