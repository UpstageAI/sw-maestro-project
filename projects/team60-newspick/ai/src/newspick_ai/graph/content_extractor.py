import asyncio
import logging
import re
from collections.abc import Callable
from html.parser import HTMLParser

import httpx

from newspick_ai.graph.state import RefreshState

logger = logging.getLogger(__name__)


_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsPick/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
_SCRIPT_TAGS = {"script", "style", "noscript"}
_SCRIPT_TEXT_PATTERN = re.compile(
    r"\b(?:function|document\.|window\.|googletag|dable|gtag|dataLayer|const|let|var)\b",
    re.IGNORECASE,
)
_SHORT_NOISE_PATTERN = re.compile(
    r"(광고|ADVERTISEMENT|구독|기사제보|저작권|무단전재|재배포|관련기사|관련 뉴스|"
    r"많이 본 뉴스|실시간|댓글|공유|프린트|글자크기|닫기|로그인)",
    re.IGNORECASE,
)
_TRAILING_BOILERPLATE_PATTERN = re.compile(
    r"(◎공감언론|저작권자|무단전재|관련기사|관련 뉴스|많이 본 뉴스|이 시각 관심정보|"
    r"Copyright|\bADVERTISEMENT\b).*",
    re.IGNORECASE | re.DOTALL,
)


class ContentExtractor:
    def __init__(self, http_reader: Callable[[str], str] | None = None, concurrency: int = 20):
        self._http_reader = http_reader
        self._concurrency = concurrency

    async def run(self, state: RefreshState) -> RefreshState:
        sem = asyncio.Semaphore(self._concurrency)

        async def fetch_one(article):
            async with sem:
                try:
                    html = await self._fetch(article["url"])
                    content = extract_article_text(html)
                    next_article = dict(article)
                    if content:
                        next_article["content"] = content
                        next_article["rawTextStatus"] = "full_text"
                        return next_article, article["id"]
                    description = extract_description_text(article.get("description", ""))
                    if description:
                        next_article["content"] = description
                        next_article["rawTextStatus"] = "description_only"
                        return next_article, article["id"]
                    next_article["status"] = "extract_failed"
                    return next_article, None
                except Exception as e:
                    logger.warning("본문 추출 실패 [%s]: %s", article["url"], e)
                    next_article = dict(article)
                    next_article["status"] = "extract_failed"
                    return next_article, None

        results = await asyncio.gather(*[fetch_one(a) for a in state["articles"]])
        articles = [r[0] for r in results]
        extracted_ids = [r[1] for r in results if r[1] is not None]

        return {
            "articles": articles,
            "events": [
                *state["events"],
                {
                    "stage": "extract",
                    "message": f"{len(extracted_ids)}건 본문 추출",
                    "articleIds": extracted_ids,
                },
            ],
        }

    async def _fetch(self, url: str) -> str:
        if self._http_reader is not None:
            return self._http_reader(url)
        async with httpx.AsyncClient(timeout=10, headers=_HEADERS, follow_redirects=True) as client:
            response = await client.get(url)
            return response.text


def extract_article_text(html: str) -> str:
    trafilatura_text = _extract_with_trafilatura(html)
    if trafilatura_text:
        return _clean_article_text(trafilatura_text)

    parser = ArticleTextParser()
    parser.feed(html)
    return _clean_article_text(parser.content())


def extract_description_text(description: str) -> str:
    parser = PlainTextParser()
    parser.feed(description)
    return _clean_article_text(parser.content())


def _extract_with_trafilatura(html: str) -> str:
    try:
        import trafilatura
    except ImportError:
        return ""

    extracted = trafilatura.extract(html)
    return (extracted or "").strip()


class ArticleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._in_article = False
        self._article_depth = 0
        self._skip_depth = 0
        self._paragraph_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag in _SCRIPT_TAGS:
            self._skip_depth += 1
            return

        if tag == "article":
            self._in_article = True
            self._article_depth = 1
            return

        if self._in_article:
            self._article_depth += 1

    def handle_endtag(self, tag: str):
        if self._skip_depth:
            if tag in _SCRIPT_TAGS:
                self._skip_depth -= 1
            return

        if not self._in_article:
            return

        self._article_depth -= 1
        if tag == "article" or self._article_depth <= 0:
            self._in_article = False
            self._article_depth = 0

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        if self._in_article and data.strip():
            self._paragraph_parts.append(data.strip())

    def content(self) -> str:
        return "\n".join(self._paragraph_parts).strip()


class PlainTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        if tag in _SCRIPT_TAGS:
            self._skip_depth += 1

    def handle_endtag(self, tag: str):
        if self._skip_depth and tag in _SCRIPT_TAGS:
            self._skip_depth -= 1

    def handle_data(self, data: str):
        if self._skip_depth:
            return
        if data.strip():
            self._parts.append(data.strip())

    def content(self) -> str:
        return "\n".join(self._parts).strip()


def _clean_article_text(text: str) -> str:
    text = _TRAILING_BOILERPLATE_PATTERN.sub("", text)
    segments = []
    for segment in re.split(r"[\r\n]+", text):
        normalized = re.sub(r"\s+", " ", segment).strip()
        if not normalized or _is_noise_segment(normalized):
            continue
        segments.append(normalized)

    return re.sub(r"\s+", " ", " ".join(segments)).strip()


def _is_noise_segment(segment: str) -> bool:
    if _SCRIPT_TEXT_PATTERN.search(segment):
        return True
    if len(segment) <= 100 and _SHORT_NOISE_PATTERN.search(segment):
        return True
    if segment.count("{") + segment.count("}") >= 2:
        return True
    return False
