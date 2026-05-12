import unittest

from daily_news_agent.naver_news import (
    NaverNewsError,
    parse_naver_news_response,
)


SAMPLE_NAVER_JSON = """{
  "lastBuildDate": "Sat, 09 May 2026 09:00:00 +0900",
  "total": 2,
  "start": 1,
  "display": 2,
  "items": [
    {
      "title": "<b>반도체</b> 수출 호조",
      "originallink": "https://www.chosun.com/article/abc",
      "link": "https://n.news.naver.com/mnews/article/001/abc",
      "description": "<b>반도체</b> 수출이 늘었다",
      "pubDate": "Sat, 09 May 2026 08:00:00 +0900"
    },
    {
      "title": "원본 링크 없는 기사",
      "originallink": "",
      "link": "https://n.news.naver.com/mnews/article/002/def",
      "description": "Naver 링크만 존재",
      "pubDate": "Sat, 09 May 2026 07:00:00 +0900"
    }
  ]
}
"""


SAMPLE_NAVER_JSON_EMPTY_ITEMS = '{"items": []}'

SAMPLE_NAVER_JSON_MISSING_LINK = """{
  "items": [
    {
      "title": "링크 없는 기사",
      "originallink": "",
      "link": "",
      "description": "링크 없음",
      "pubDate": ""
    }
  ]
}
"""


class NaverNewsParserTests(unittest.TestCase):
    def test_parse_extracts_articles_with_html_stripped(self):
        articles = parse_naver_news_response(SAMPLE_NAVER_JSON, keyword="반도체")

        self.assertEqual(len(articles), 2)
        first = articles[0]
        self.assertEqual(first.title, "반도체 수출 호조")
        self.assertEqual(first.summary, "반도체 수출이 늘었다")
        self.assertEqual(first.link, "https://www.chosun.com/article/abc")
        self.assertEqual(first.source, "chosun.com")
        self.assertEqual(first.keyword, "반도체")
        self.assertEqual(first.published_at, "Sat, 09 May 2026 08:00:00 +0900")

    def test_parse_uses_naver_link_when_originallink_empty(self):
        articles = parse_naver_news_response(SAMPLE_NAVER_JSON, keyword="반도체")

        second = articles[1]
        self.assertEqual(second.link, "https://n.news.naver.com/mnews/article/002/def")
        self.assertEqual(second.source, "Naver News")

    def test_parse_respects_limit(self):
        articles = parse_naver_news_response(SAMPLE_NAVER_JSON, keyword="반도체", limit=1)

        self.assertEqual(len(articles), 1)

    def test_parse_returns_empty_list_for_empty_items(self):
        articles = parse_naver_news_response(SAMPLE_NAVER_JSON_EMPTY_ITEMS, keyword="반도체")

        self.assertEqual(articles, [])

    def test_parse_skips_items_without_link(self):
        articles = parse_naver_news_response(SAMPLE_NAVER_JSON_MISSING_LINK, keyword="반도체")

        self.assertEqual(articles, [])

    def test_parse_raises_naver_news_error_on_invalid_json(self):
        with self.assertRaises(NaverNewsError):
            parse_naver_news_response("not json", keyword="반도체")


if __name__ == "__main__":
    unittest.main()
