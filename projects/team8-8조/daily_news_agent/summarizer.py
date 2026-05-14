from __future__ import annotations

from daily_news_agent.models import NewsArticle


def format_articles_for_prompt(articles: list[NewsArticle]) -> str:
    lines: list[str] = []
    for index, article in enumerate(articles, start=1):
        lines.append(
            "\n".join(
                [
                    f"{index}. 제목: {article.title}",
                    f"   요약: {article.summary or '제공된 요약 없음'}",
                    f"   출처: {article.source}",
                    f"   발행일: {article.published_at or '알 수 없음'}",
                    f"   키워드: {article.keyword}",
                    f"   태그: {', '.join(article.tags) if article.tags else '없음'}",
                    f"   링크: {article.link}",
                ]
            )
        )
    return "\n\n".join(lines)


def build_briefing_messages(interest: str, articles: list[NewsArticle]) -> list[dict[str, str]]:
    article_text = format_articles_for_prompt(articles)
    system_prompt = (
        "당신은 뉴스 브리핑 에디터입니다. "
        "사용자의 관심 분야와 관련된 기사 목록만 바탕으로 한국어 일일 브리핑을 작성하세요. "
        "추측을 추가하지 말고, 기사에 없는 사실을 만들어내지 마세요. "
        "각 핵심 뉴스에는 원문 링크를 [원문 보기](url) 형식의 마크다운 링크로 포함하세요."
    )
    user_prompt = f"""관심 분야: {interest}

아래 기사 목록을 바탕으로 오늘의 뉴스 브리핑을 작성해 주세요.

출력 형식:
## 오늘의 핵심 요약
- 3문장 이내로 전체 흐름 요약

## 주요 뉴스
- 기사별로 제목, 핵심 내용, [원문 보기](링크) 형식으로 링크 포함

## 확인할 만한 흐름
- 여러 기사에서 공통적으로 보이는 흐름이나 쟁점 정리

기사 목록:
{article_text}
"""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

