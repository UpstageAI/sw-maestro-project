MAX_CONTEXT_LENGTH = 4000
MAX_CONTENT_PER_ARTICLE = 1200


def build_context(articles: list[dict]) -> str:
    parts = []
    for i, article in enumerate(articles, 1):
        content = (article.get("content") or "")[:MAX_CONTENT_PER_ARTICLE]
        part = (
            f"[{i}] {article.get('title', '')} "
            f"({article.get('source', '')}, {article.get('publishedAt', '')})\n{content}"
        )
        parts.append(part)
    return "\n\n".join(parts)[:MAX_CONTEXT_LENGTH]
