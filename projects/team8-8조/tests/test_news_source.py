import unittest

from daily_news_agent.news_source import parse_google_news_rss


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Google News</title>
    <item>
      <title>AI 스타트업 투자 확대</title>
      <link>https://news.google.com/articles/abc</link>
      <description><![CDATA[<a href="https://example.com/a">AI 기업 투자 뉴스</a>]]></description>
      <pubDate>Mon, 04 May 2026 01:30:00 GMT</pubDate>
      <source url="https://example.com">Example News</source>
    </item>
    <item>
      <title>빈 링크 기사는 제외되어야 한다</title>
      <description>링크가 없는 기사</description>
    </item>
  </channel>
</rss>
"""


class GoogleNewsRssParserTests(unittest.TestCase):
    def test_parse_google_news_rss_extracts_clean_articles(self):
        articles = parse_google_news_rss(SAMPLE_RSS, keyword="AI")

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0].title, "AI 스타트업 투자 확대")
        self.assertEqual(articles[0].link, "https://news.google.com/articles/abc")
        self.assertEqual(articles[0].source, "Example News")
        self.assertEqual(articles[0].keyword, "AI")
        self.assertEqual(articles[0].summary, "AI 기업 투자 뉴스")
        self.assertEqual(articles[0].published_at, "Mon, 04 May 2026 01:30:00 GMT")


if __name__ == "__main__":
    unittest.main()
