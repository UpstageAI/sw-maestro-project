from pathlib import Path

import httpx

from newspick_ai.graph.collector import RssCollector


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "rss" / "example-feed.xml"


def test_collector_parses_one_rss_item_into_article_state():
    def fake_reader(feed_url: str) -> str:
        assert feed_url == "fixture://example"
        return FIXTURE_PATH.read_text(encoding="utf-8")

    articles = RssCollector(feed_reader=fake_reader).collect(
        feed_url="fixture://example"
    )

    assert articles[0]["url"] == "https://example.com/ai-news"
    assert articles[0]["title"] == "AI 뉴스"
    assert articles[0]["source"] == "Example Feed"
    assert articles[0]["publishedAt"] == "2026-05-12T00:00:00Z"
    assert articles[0]["category"] == "general"


def test_collector_uses_requested_category_label_over_rss_tags():
    feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Tagged Feed</title>
    <item>
      <title>AI 뉴스</title>
      <link>https://example.com/tagged-ai-news</link>
      <category>External Tag</category>
    </item>
  </channel>
</rss>
"""

    def fake_reader(feed_url: str) -> str:
        assert feed_url == "fixture://example"
        return feed

    articles = RssCollector(feed_reader=fake_reader).collect(
        feed_url="fixture://example",
        category="테크",
    )

    assert articles[0]["category"] == "테크"


def test_collector_uses_configured_source_name_over_rss_channel_title():
    feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>정치</title>
    <item>
      <title>정책 뉴스</title>
      <link>https://example.com/policy-news</link>
    </item>
  </channel>
</rss>
"""

    articles = RssCollector(feed_reader=lambda _feed_url: feed).collect(
        feed_url="fixture://policy",
        category="정책",
        source_name="뉴시스",
    )

    assert articles[0]["source"] == "뉴시스"
    assert articles[0]["category"] == "정책"


def test_collector_normalizes_category_channel_title_from_feed_url():
    feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>경제</title>
    <item>
      <title>경제 뉴스</title>
      <link>https://www.newsis.com/view/NISX20260513_0000000001</link>
    </item>
  </channel>
</rss>
"""

    articles = RssCollector(feed_reader=lambda _feed_url: feed).collect(
        feed_url="https://nwww.newsis.com/RSS/economy.xml",
        category="경제",
    )

    assert articles[0]["source"] == "뉴시스"


def test_collector_normalizes_verbose_hankyung_channel_title():
    feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>한국경제 | 뉴스 | 경제</title>
    <item>
      <title>경제 뉴스</title>
      <link>https://www.hankyung.com/article/202605130001</link>
    </item>
  </channel>
</rss>
"""

    articles = RssCollector(feed_reader=lambda _feed_url: feed).collect(
        feed_url="https://www.hankyung.com/feed/economy",
        category="경제",
    )

    assert articles[0]["source"] == "한국경제"


def test_collector_limits_articles_per_feed():
    feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Large Feed</title>
    <item><title>뉴스 1</title><link>https://example.com/1</link></item>
    <item><title>뉴스 2</title><link>https://example.com/2</link></item>
    <item><title>뉴스 3</title><link>https://example.com/3</link></item>
  </channel>
</rss>
"""

    articles = RssCollector(
        feed_reader=lambda _feed_url: feed,
        max_articles_per_feed=2,
    ).collect(feed_url="fixture://large")

    assert [article["title"] for article in articles] == ["뉴스 1", "뉴스 2"]


def test_collector_fetches_feed_with_user_agent(monkeypatch):
    seen_headers = {}

    def fake_get(url, *, headers, follow_redirects, timeout):
        seen_headers.update(headers)
        assert url == "https://example.com/feed"
        assert follow_redirects is True
        assert timeout == 10
        return httpx.Response(
            200,
            content=FIXTURE_PATH.read_bytes(),
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr("newspick_ai.graph.collector.httpx.get", fake_get)

    articles = RssCollector().collect(feed_url="https://example.com/feed")

    assert articles[0]["title"] == "AI 뉴스"
    assert "Mozilla/5.0" in seen_headers["User-Agent"]
