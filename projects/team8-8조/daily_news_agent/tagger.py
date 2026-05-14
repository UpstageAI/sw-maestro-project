from __future__ import annotations

from daily_news_agent.models import NewsArticle


def build_tagging_messages(article: NewsArticle) -> list[dict[str, str]]:
    system = (
        "당신은 뉴스 기사 태거입니다. "
        "기사 제목과 요약을 보고 핵심 주제를 나타내는 3~5개의 한국어 태그를 생성하세요. "
        "태그는 쉼표로 구분된 단어 또는 짧은 구로만 반환하세요. 다른 텍스트는 출력하지 마세요."
    )
    user = f"제목: {article.title}\n요약: {article.summary or '없음'}"
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_tags_response(response: str) -> list[str]:
    return [tag.strip() for tag in response.split(",") if tag.strip()][:5]
