from __future__ import annotations

from urllib.parse import quote_plus
from xml.etree import ElementTree

from daily_news_agent.models import NewsArticle
from daily_news_agent.naver_news import NaverNewsClient, NaverNewsError
from daily_news_agent.preprocessor import clean_text, is_korean


GOOGLE_NEWS_RSS_URL = "https://news.google.com/rss/search"


class NewsSourceError(RuntimeError):
    pass


def build_google_news_rss_url(keyword: str) -> str:
    query = quote_plus(f"{keyword} when:1d")
    return f"{GOOGLE_NEWS_RSS_URL}?q={query}&hl=ko&gl=KR&ceid=KR:ko"


def _find_text(item: ElementTree.Element, tag_name: str) -> str:
    child = item.find(tag_name)
    if child is None or child.text is None:
        return ""
    return clean_text(child.text)


def parse_google_news_rss(xml_text: str, keyword: str, limit: int | None = None) -> list[NewsArticle]:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise NewsSourceError("Google News RSS 응답을 XML로 파싱하지 못했습니다.") from exc

    articles: list[NewsArticle] = []
    for item in root.findall(".//item"):
        title = _find_text(item, "title")
        link = _find_text(item, "link")
        summary = _find_text(item, "description")
        published_at = _find_text(item, "pubDate")
        source = _find_text(item, "source") or "Google News"

        if not title or not link:
            continue

        articles.append(
            NewsArticle(
                title=title,
                summary=summary,
                link=link,
                source=source,
                published_at=published_at,
                keyword=keyword,
            )
        )

        if limit is not None and len(articles) >= limit:
            break

    return articles


class GoogleNewsRssClient:
    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch(self, keyword: str, limit: int = 10) -> list[NewsArticle]:
        try:
            import requests
        except ImportError as exc:
            raise NewsSourceError("requests 패키지가 설치되어 있지 않습니다.") from exc

        url = build_google_news_rss_url(keyword)
        headers = {"User-Agent": "daily-news-agent/0.1"}
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout_seconds)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NewsSourceError(f"Google News RSS 요청에 실패했습니다: {keyword}") from exc

        return parse_google_news_rss(response.text, keyword=keyword, limit=limit)


NAVER_KEY_MISSING_MESSAGE = (
    "Naver API 키가 설정되지 않아 한글 키워드도 Google News로 수집합니다. "
    ".env에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 추가하세요."
)


class NewsRouter:
    def __init__(
        self,
        google_client: GoogleNewsRssClient,
        naver_client: NaverNewsClient | None = None,
    ) -> None:
        self.google_client = google_client
        self.naver_client = naver_client
        self._naver_missing_warned = False

    def fetch(self, keyword: str, limit: int = 10) -> tuple[list[NewsArticle], list[str]]:
        messages: list[str] = []

        if is_korean(keyword):
            if self.naver_client is None:
                if not self._naver_missing_warned:
                    messages.append(NAVER_KEY_MISSING_MESSAGE)
                    self._naver_missing_warned = True
            else:
                try:
                    articles = self.naver_client.fetch(keyword, limit=limit)
                    return articles, messages
                except NaverNewsError as exc:
                    messages.append(f"Naver 호출 실패로 Google News로 우회합니다: {exc}")

        try:
            return self.google_client.fetch(keyword, limit=limit), messages
        except NewsSourceError as exc:
            messages.append(str(exc))
            return [], messages

