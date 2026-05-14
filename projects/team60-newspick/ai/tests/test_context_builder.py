from newspick_ai.chat.context_builder import build_context


def test_context_builder_formats_articles_with_sources():
    articles = [
        {"id": "a1", "title": "AI 혁신", "source": "Tech", "publishedAt": "2026-05-12T09:00:00Z", "content": "AI 내용", "score": 0.9},
        {"id": "a2", "title": "반도체 시장", "source": "Economy", "publishedAt": "2026-05-12T10:00:00Z", "content": "반도체 내용", "score": 0.8},
    ]

    context = build_context(articles)

    assert "[1]" in context
    assert "[2]" in context
    assert "AI 혁신" in context
    assert "Tech" in context
    assert "반도체 시장" in context
    assert "Economy" in context
    assert len(context) <= 4000
