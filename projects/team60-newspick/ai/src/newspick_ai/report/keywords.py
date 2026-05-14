from collections import Counter
from dataclasses import dataclass

from kiwipiepy import Kiwi

_kiwi = Kiwi()

_NOUN_TAGS = {"NNG", "NNP", "SL"}  # 일반명사, 고유명사, 외래어

_STOPWORDS = {
    "것", "수", "등", "때", "곳", "중", "점", "뒤", "앞", "안", "후",
    "더", "이", "그", "저", "한", "및", "또", "각",
    "관련", "내용", "계획", "방안", "분야", "부문", "결과",
    "대비", "지역", "부분", "문제", "이번", "최근",
    "오늘", "어제", "내일", "올해", "내년", "지난해",
}


@dataclass
class Keyword:
    text: str
    weight: int


class KeywordGenerator:
    def generate(self, articles: list[dict]) -> list[Keyword]:
        counter: Counter = Counter()
        for article in articles:
            for word in self._extract_nouns(self._extract_text(article.get("summary", ""))):
                counter[word] += 1

        top = counter.most_common(12)
        if not top:
            return []

        max_count = top[0][1]
        return [
            Keyword(text=word, weight=max(2, min(9, round(count / max_count * 9))))
            for word, count in top
        ]

    @staticmethod
    def _extract_text(summary) -> str:
        if isinstance(summary, list):
            return " ".join(str(s) for s in summary)
        return str(summary) if summary else ""

    @staticmethod
    def _extract_nouns(text: str) -> list[str]:
        tokens = _kiwi.tokenize(text, normalize_coda=True)
        return [
            t.form
            for t in tokens
            if t.tag in _NOUN_TAGS
            and len(t.form) >= 2
            and t.form not in _STOPWORDS
        ]
