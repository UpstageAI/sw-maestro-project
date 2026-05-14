from pathlib import Path

from newspick_ai.graph.content_extractor import (
    ContentExtractor,
    extract_article_text,
    extract_description_text,
)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "html" / "article_001.html"


async def test_content_extractor_extracts_title_and_body_from_html():
    def fake_reader(url: str) -> str:
        assert url == "https://example.com/a1"
        return FIXTURE_PATH.read_text(encoding="utf-8")

    state = {
        "articles": [
            {
                "id": "article_001",
                "url": "https://example.com/a1",
                "title": "AI가 바꾼 뉴스 소비",
                "status": "collected",
            }
        ],
        "events": [],
    }

    output = await ContentExtractor(http_reader=fake_reader).run(state)

    article = output["articles"][0]
    assert "본문 첫 문단" in article["content"]
    assert "본문 둘째 문단" in article["content"]
    assert len(article["content"]) >= 50
    assert output["events"][0]["stage"] == "extract"
    assert output["events"][0]["articleIds"] == ["article_001"]


async def test_content_extractor_uses_description_when_full_text_is_missing():
    def fake_reader(url: str) -> str:
        assert url == "https://example.com/a1"
        return "<html><body></body></html>"

    state = {
        "articles": [
            {
                "id": "article_001",
                "url": "https://example.com/a1",
                "title": "AI가 바꾼 뉴스 소비",
                "description": "<p>RSS 요약 첫 문장입니다.</p><p>RSS 요약 둘째 문장입니다.</p>",
                "status": "collected",
            }
        ],
        "events": [],
    }

    output = await ContentExtractor(http_reader=fake_reader).run(state)

    article = output["articles"][0]
    assert article["content"] == "RSS 요약 첫 문장입니다. RSS 요약 둘째 문장입니다."
    assert article["rawTextStatus"] == "description_only"
    assert article["status"] == "collected"
    assert output["events"][0]["articleIds"] == ["article_001"]


async def test_content_extractor_marks_failed_without_full_text_or_description():
    state = {
        "articles": [
            {
                "id": "article_001",
                "url": "https://example.com/a1",
                "title": "AI가 바꾼 뉴스 소비",
                "description": "",
                "status": "collected",
            }
        ],
        "events": [],
    }

    output = await ContentExtractor(http_reader=lambda _url: "").run(state)

    article = output["articles"][0]
    assert "content" not in article
    assert article["status"] == "extract_failed"
    assert output["events"][0]["articleIds"] == []


def test_extract_article_text_removes_script_and_article_chrome():
    html = """
    <html>
      <body>
        <article>
          <p>광고</p>
          <script>function track(){ window.dataLayer.push({event: "ad"}); }</script>
          <p>AI 에이전트가 이메일 작성과 파일 정리를 자동화하고 있다.</p>
          <p>기업들이 반복 업무를 줄이기 위해 관련 기능을 도입하고 있다.</p>
          <p>관련 뉴스 더보기</p>
        </article>
      </body>
    </html>
    """

    content = extract_article_text(html)

    assert "AI 에이전트" in content
    assert "반복 업무" in content
    assert "function" not in content
    assert "window" not in content
    assert "광고" not in content
    assert "관련 뉴스" not in content


def test_extract_description_text_removes_html_and_noise():
    content = extract_description_text(
        "<p>AI 에이전트가 반복 업무를 줄이고 있습니다.</p>"
        "<script>window.track()</script>"
        "<p>관련 뉴스 더보기</p>"
    )

    assert content == "AI 에이전트가 반복 업무를 줄이고 있습니다."


def test_extract_article_text_removes_related_news_tail():
    html = """
    <html>
      <body>
        <article>
          <p>조선업은 호황과 불황이 반복돼 고용 유지가 중요하다.</p>
          <p>정부는 생태계 유지와 협력 강화를 언급했다.</p>
          <p>◎공감언론 뉴시스 [email protected]</p>
          <p>"젊은 사람이 자리 좀 양보해라" 관련 기사 제목</p>
          <p>많이 본 뉴스</p>
        </article>
      </body>
    </html>
    """

    content = extract_article_text(html)

    assert "조선업은 호황과 불황" in content
    assert "정부는 생태계 유지" in content
    assert "공감언론" not in content
    assert "젊은 사람이" not in content
    assert "많이 본 뉴스" not in content
