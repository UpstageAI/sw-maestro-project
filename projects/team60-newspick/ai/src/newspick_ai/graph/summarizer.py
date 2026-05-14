import json
import logging
import re
from typing import Any, Protocol

from newspick_ai.graph.state import RefreshState
from newspick_ai.solar.chat import SolarChatClient


class ChatClient(Protocol):
    def complete(self, messages: list[dict]) -> str:
        ...


FRIENDLY_SUMMARY_SENTENCES = 3
FRIENDLY_SUMMARY_SUFFIX = "요."
EDITORIAL_TEXT_MAX_LENGTH = 260
IMPORTANCE_MAX_LENGTH = 180
TRAILING_SOURCE_NOISE_PATTERN = re.compile(
    r"(◎공감언론|저작권자|무단전재|관련기사|관련 뉴스|많이 본 뉴스|이 시각 관심정보|"
    r"Copyright|\bADVERTISEMENT\b).*",
    re.IGNORECASE | re.DOTALL,
)
logger = logging.getLogger(__name__)


class Summarizer:
    def __init__(self, chat_client: ChatClient | None = None):
        self._chat_client = chat_client or SolarChatClient()

    def run(self, state: RefreshState) -> RefreshState:
        articles = []
        summarized_ids = []

        for article in state["articles"]:
            try:
                raw_output = self._chat_client.complete(
                    [
                        {
                            "role": "system",
                            "content": "너는 원문에 근거해 한국어 기사 요약과 독자 이해 보조 정보를 만드는 뉴스 에디터다.",
                        },
                        {
                            "role": "user",
                            "content": self._prompt(
                                title=article["title"],
                                content=article["content"],
                            ),
                        },
                    ]
                ).strip()
                enrichment = parse_article_enrichment(raw_output, article)
            except Exception as exc:
                logger.warning("AI 요약 실패 [%s]: %s", article.get("id"), exc)
                enrichment = _fallback_enrichment(_source_text(article), article)
            summary = self._friendly_summary(enrichment["summary"], article)

            if not summary:
                summary = _coerce_friendly_summary(_normalize_summary(_source_text(article)))
            if not summary:
                raise ValueError("summary must not be blank")

            next_article = dict(article)
            next_article["summary"] = summary
            next_article["keywords"] = enrichment["keywords"]
            next_article["importance"] = enrichment["importance"]
            next_article["context"] = enrichment["context"]
            next_article["importanceScore"] = enrichment["importanceScore"]
            articles.append(next_article)
            summarized_ids.append(article["id"])

        return {
            "articles": articles,
            "events": [
                *state["events"],
                {
                    "stage": "summarize",
                    "message": f"{len(summarized_ids)}건 요약",
                    "articleIds": summarized_ids,
                },
            ],
        }

    def _friendly_summary(self, summary: list[str], article: dict[str, Any]) -> list[str]:
        if _is_friendly_summary(summary):
            return summary

        try:
            raw_rewrite = self._chat_client.complete(
                [
                    {
                        "role": "system",
                        "content": "기존 요약의 사실만 유지해 한국어 해요체 홈 카드 요약으로 고치는 뉴스 에디터다.",
                    },
                    {
                        "role": "user",
                        "content": self._rewrite_prompt(
                            title=str(article.get("title", "")),
                            summary=summary,
                        ),
                    },
                ]
            ).strip()
            rewritten_summary = parse_summary_rewrite(raw_rewrite)
        except Exception as exc:
            logger.warning("AI 요약 문체 보정 실패 [%s]: %s", article.get("id"), exc)
            return _coerce_friendly_summary(summary)
        if _is_friendly_summary(rewritten_summary):
            return rewritten_summary

        return _coerce_friendly_summary(rewritten_summary or summary)

    @staticmethod
    def _prompt(*, title: str, content: str) -> str:
        return (
            "아래 기사 본문에서 필요한 필드를 추출해 JSON 객체로만 출력하시오.\n"
            "필드는 summary, keywords, importance, context, importanceScore만 사용하시오.\n"
            "summary는 사실 중심 한국어 해요체 문장 정확히 3개 배열로 작성하시오.\n"
            "summary 각 문장은 짧게 쓰고 반드시 '요.'로 끝내시오.\n"
            "summary 각 문장은 '~하고 있어요', '~되고 있어요', '~보이고 있어요'처럼 부드럽고 친화적인 설명형으로 작성하시오.\n"
            "summary 각 문장은 홈 기사 카드에서 3줄 안팎으로 보이도록 짧고 자연스럽게 작성하시오.\n"
            "keywords는 핵심 키워드 3~5개 문자열 배열로 작성하시오.\n"
            "importance는 독자, 시장, 정책, 생활 중 무엇에 어떤 변화가 생기는지 한 문장으로 구체적으로 작성하시오.\n"
            "importance에 '~흐름을 보여준다', '~이기 때문에 중요하다' 같은 형식적 표현을 쓰지 마시오.\n"
            "context는 기사를 이해하는 데 필요한 배경을 친화적인 해요체 1~2문장으로 짧게 작성하시오.\n"
            "context에 본문 전체, HTML, JSON, URL, 코드 조각을 넣지 마시오.\n"
            "importanceScore는 1~10 정수로 작성하시오.\n"
            "원문에 없는 정보, 추측, 평가, 과장 표현을 포함하지 마시오.\n"
            "숫자, 인물명, 기관명, 시점은 원문과 다르게 바꾸지 마시오.\n\n"
            f"제목: {title}\n\n"
            f"본문:\n{content}"
        )

    @staticmethod
    def _rewrite_prompt(*, title: str, summary: list[str]) -> str:
        return (
            "아래 기존 summary 배열의 사실만 유지해 JSON 객체로만 출력하시오.\n"
            "필드는 summary만 사용하시오.\n"
            "summary는 한국어 해요체 문장 정확히 3개 배열로 작성하시오.\n"
            "각 문장은 짧게 쓰고 반드시 '요.'로 끝내시오.\n"
            "새 사실, 추측, 평가, 과장 표현을 추가하지 마시오.\n\n"
            f"제목: {title}\n\n"
            f"기존 summary:\n{json.dumps(summary, ensure_ascii=False)}"
        )


def parse_article_enrichment(raw: str, article: dict[str, Any]) -> dict[str, Any]:
    payload = _parse_json_object(raw)
    if payload is None:
        return _fallback_enrichment(raw, article)

    summary = _normalize_summary(payload.get("summary")) or _normalize_summary(raw)
    keywords = _normalize_keywords(payload.get("keywords")) or _fallback_keywords(article)
    raw_reference = _raw_reference(article)
    importance = _normalize_editorial_text(
        payload.get("importance"),
        max_length=IMPORTANCE_MAX_LENGTH,
        raw_reference=raw_reference,
    ) or _first_sentence(_summary_text(summary))
    context = _normalize_editorial_text(
        payload.get("context"),
        max_length=EDITORIAL_TEXT_MAX_LENGTH,
        raw_reference=raw_reference,
    ) or _fallback_context(article, summary, keywords)
    importance_score = _normalize_importance_score(payload.get("importanceScore"))

    return {
        "summary": summary,
        "keywords": keywords,
        "importance": importance,
        "context": context,
        "importanceScore": importance_score,
    }


def parse_summary_rewrite(raw: str) -> list[str]:
    payload = _parse_json_object(raw)
    if payload is None:
        return _normalize_summary(raw)

    return _normalize_summary(payload.get("summary")) or _normalize_summary(raw)


def _parse_json_object(raw: str) -> dict[str, Any] | None:
    candidates = [raw.strip()]
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", raw.strip(), re.DOTALL | re.IGNORECASE)
    if fenced:
        candidates.insert(0, fenced.group(1).strip())

    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def _fallback_enrichment(raw: str, article: dict[str, Any]) -> dict[str, Any]:
    summary = _normalize_summary(raw) or _normalize_summary(_source_text(article))
    keywords = _fallback_keywords(article)
    return {
        "summary": summary,
        "keywords": keywords,
        "importance": _first_sentence(_summary_text(summary)),
        "context": _fallback_context(article, summary, keywords),
        "importanceScore": 5,
    }


def _normalize_summary(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(sentence).strip() for sentence in value if str(sentence).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []

        sentences = [
            sentence.strip()
            for sentence in re.findall(r"[^.!?。！？]+[.!?。！？]?", text)
            if sentence.strip()
        ]
        return sentences or [text]
    return []


def _source_text(article: dict[str, Any]) -> str:
    raw = _collapse_whitespace(
        " ".join(
            str(article.get(key, ""))
            for key in ("description", "content", "title")
            if article.get(key)
        )
    )
    if not raw:
        return ""
    raw = TRAILING_SOURCE_NOISE_PATTERN.sub("", raw)

    segments = re.split(r"[\r\n]+", raw)
    if len(segments) == 1:
        segments = re.split(r"(?<=[.!?。！？])\s+", raw)

    cleaned = []
    for segment in segments:
        text = _collapse_whitespace(segment)
        if not text or _looks_like_raw_text(text):
            continue
        if len(text) <= 100 and re.search(
            r"(광고|ADVERTISEMENT|구독|기사제보|무단전재|재배포|관련기사|관련 뉴스|댓글|공유|프린트|글자크기)",
            text,
            re.IGNORECASE,
        ):
            continue
        cleaned.append(text)

    return _collapse_whitespace(" ".join(cleaned)) or raw


def _summary_text(summary: list[str]) -> str:
    return " ".join(summary)


def _is_friendly_summary(summary: list[str]) -> bool:
    return len(summary) == FRIENDLY_SUMMARY_SENTENCES and all(
        sentence.strip().endswith(FRIENDLY_SUMMARY_SUFFIX) for sentence in summary
    )


def _coerce_friendly_summary(summary: list[str]) -> list[str]:
    sentences = [sentence.strip() for sentence in summary if sentence.strip()]
    if not sentences:
        return []

    sentences = sentences[:FRIENDLY_SUMMARY_SENTENCES]
    while len(sentences) < FRIENDLY_SUMMARY_SENTENCES:
        sentences.append(sentences[-1])

    return [_coerce_friendly_sentence(sentence) for sentence in sentences]


def _coerce_friendly_sentence(sentence: str) -> str:
    stripped = sentence.strip()
    if stripped.endswith(FRIENDLY_SUMMARY_SUFFIX):
        return stripped

    text = re.sub(r"[.!?。！？]+$", "", stripped).strip()
    if text.endswith("요"):
        return f"{text}."
    if text.endswith("다") and not text.endswith("입니다"):
        return f"{text}고 볼 수 있어요."
    if text.endswith("입니다"):
        return f"{text}."
    return f"{text}에 대해 먼저 알아두면 좋아요."


def _normalize_keywords(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    keywords = []
    seen = set()
    for item in value:
        keyword = str(item).strip()
        if keyword and keyword not in seen:
            keywords.append(keyword)
            seen.add(keyword)
    return keywords[:5]


def _normalize_editorial_text(
    value: Any,
    *,
    max_length: int,
    raw_reference: str = "",
) -> str:
    if isinstance(value, list):
        text = " ".join(str(item).strip() for item in value if str(item).strip())
    elif isinstance(value, str):
        text = value.strip()
    else:
        return ""

    text = _collapse_whitespace(text)
    if not text or _looks_like_raw_text(text, raw_reference):
        return ""
    return _trim_to_sentences(text, max_length)


def _normalize_importance_score(value: Any) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        return 5
    return min(10, max(1, score))


def _fallback_keywords(article: dict[str, Any]) -> list[str]:
    text = f"{article.get('title', '')} {article.get('content', '')}"
    tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", text)
    keywords = []
    seen = set()
    for token in tokens:
        if token not in seen:
            keywords.append(token)
            seen.add(token)
        if len(keywords) == 5:
            break
    return keywords or ["뉴스"]


def _first_sentence(summary: str) -> str:
    match = re.search(r"[^.!?。！？]+[.!?。！？]", summary)
    if match:
        return match.group(0).strip()
    return summary[:120].strip() or "기사의 핵심 내용을 이해하는 데 중요함."


def _fallback_context(
    article: dict[str, Any],
    summary: list[str] | None = None,
    keywords: list[str] | None = None,
) -> str:
    background = _background_sentence(article, summary)
    if not background:
        return ""

    topics = [keyword for keyword in (keywords or []) if keyword][:2]
    if topics:
        prefix = f"{'·'.join(topics)}는 이 기사를 이해하는 핵심 배경이에요."
    else:
        title = _background_topic(article)
        prefix = f"{title}을 이해하려면 기사에서 다룬 배경을 함께 보면 좋아요."

    return _trim_to_sentences(f"{prefix} {background}", EDITORIAL_TEXT_MAX_LENGTH)


def _background_sentence(article: dict[str, Any], summary: list[str] | None = None) -> str:
    candidates = [
        *(summary or []),
        article.get("description"),
        article.get("content"),
    ]
    raw_reference = _raw_reference(article)

    for candidate in candidates:
        text = _normalize_editorial_text(
            candidate,
            max_length=140,
            raw_reference=raw_reference,
        )
        if text:
            return _coerce_friendly_sentence(text)

    return ""


def _background_topic(article: dict[str, Any]) -> str:
    title = _collapse_whitespace(str(article.get("title", "")))
    return title[:32].strip(" .!?。！？") or "이 기사"


def _raw_reference(article: dict[str, Any]) -> str:
    return _collapse_whitespace(
        " ".join(
            str(article.get(key, ""))
            for key in ("content", "rawText", "raw_text")
            if article.get(key)
        )
    )


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _looks_like_raw_text(text: str, raw_reference: str = "") -> bool:
    if len(text) > 500:
        return True
    if re.search(r"```|</?[a-zA-Z][^>]*>|https?://", text):
        return True
    if re.search(r'^\s*[\[{]|"(?:content|rawText|raw_text|html|body)"\s*:', text):
        return True
    if re.search(r"\b(?:function|const|let|var)\b", text):
        return True

    sentence_count = len(re.findall(r"[^.!?。！？]+[.!?。！？]", text))
    if sentence_count > 3 and len(text) > EDITORIAL_TEXT_MAX_LENGTH:
        return True

    if raw_reference and len(text) > 140:
        if raw_reference.startswith(text) or text in raw_reference:
            return True

    return False


def _trim_to_sentences(text: str, max_length: int) -> str:
    if len(text) <= max_length:
        return text

    sentences = [
        sentence.strip()
        for sentence in re.findall(r"[^.!?。！？]+[.!?。！？]", text)
        if sentence.strip()
    ]
    if sentences:
        trimmed = " ".join(sentences[:2]).strip()
        if trimmed and len(trimmed) <= max_length:
            return trimmed

    return text[:max_length].rstrip()
