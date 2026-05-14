import re

from newspick_ai.graph.state import RefreshState


MAX_SUMMARY_LENGTH = 500
MIN_SENTENCE_COUNT = 1
MAX_SENTENCE_COUNT = 5


class SummaryValidator:
    def run(self, state: RefreshState) -> RefreshState:
        articles = []

        for article in state["articles"]:
            next_article = dict(article)
            summary = _summary_text(article.get("summary", ""))

            if self._is_valid(summary):
                next_article["status"] = "summarized"
            else:
                next_article["status"] = "summary_invalid"

            articles.append(next_article)

        return {
            "articles": articles,
            "events": [
                *state["events"],
                {
                    "stage": "validate_summary",
                    "message": f"{len(articles)}건 요약 검증",
                    "articleIds": [article["id"] for article in articles],
                },
            ],
        }

    def _is_valid(self, summary: str) -> bool:
        if not summary.strip():
            return False

        if len(summary) > MAX_SUMMARY_LENGTH:
            return False

        sentence_count = len(re.findall(r"[^.!?。！？]+[.!?。！？]", summary))
        if sentence_count == 0 and summary.strip():
            sentence_count = 1

        return MIN_SENTENCE_COUNT <= sentence_count <= MAX_SENTENCE_COUNT


def _summary_text(summary: object) -> str:
    if isinstance(summary, list):
        return " ".join(str(sentence) for sentence in summary)
    return str(summary)
