import json
import logging
import re
from typing import Any, Protocol

from newspick_ai.graph.state import RefreshState
from newspick_ai.solar.chat import SolarChatClient


class ChatClient(Protocol):
    def complete(self, messages: list[dict]) -> str:
        ...


logger = logging.getLogger(__name__)


class QuizGenerator:
    def __init__(self, chat_client: ChatClient | None = None):
        self._chat_client = chat_client or SolarChatClient()

    def run(self, state: RefreshState) -> RefreshState:
        articles = []
        generated_ids = []

        for article in state["articles"]:
            try:
                raw_output = self._chat_client.complete(
                    [
                        {
                            "role": "system",
                            "content": "너는 기사 내용에 근거한 한국어 O/X 퀴즈를 만드는 뉴스 에디터다.",
                        },
                        {
                            "role": "user",
                            "content": self._prompt(
                                title=article["title"],
                                summary=article["summary"],
                                content=article["content"],
                            ),
                        },
                    ]
                )
                quizzes = parse_quizzes(raw_output, article)
            except Exception as exc:
                logger.warning("AI 퀴즈 생성 실패 [%s]: %s", article.get("id"), exc)
                quizzes = []
            if not quizzes:
                quizzes = fallback_quizzes(article)

            next_article = dict(article)
            next_article["quizzes"] = quizzes
            articles.append(next_article)
            if quizzes:
                generated_ids.append(article["id"])

        return {
            "articles": articles,
            "events": [
                *state["events"],
                {
                    "stage": "generate_quiz",
                    "message": f"{len(generated_ids)}건 퀴즈 생성",
                    "articleIds": generated_ids,
                },
            ],
        }

    @staticmethod
    def _prompt(*, title: str, summary: str, content: str) -> str:
        return (
            "아래 기사에 대해 한국어 O/X 퀴즈 1개를 JSON 배열로만 출력하시오.\n"
            "각 항목은 question, answer, explanation 필드를 가진다.\n"
            "answer는 true 또는 false boolean 값이어야 한다.\n"
            "question은 제목 확인이 아니라 기사 핵심 주장, 원인, 영향, 배경 중 하나를 이해했는지 묻는 실제 독해형 문장으로 작성하시오.\n"
            "'이 기사는 ... 다룬다', '...와 관련된 내용이다'처럼 제목만 바꾼 문제를 만들지 마시오.\n"
            "question은 '기사에 따르면'으로 시작하지 말고 실제 시험의 O/X 명제처럼 '~다'로 끝내시오.\n"
            "단순 숫자 암기보다 기사에서 왜 중요하거나 어떤 변화가 생기는지 확인하는 문제를 우선하시오.\n"
            "explanation은 정답 근거를 본문 내용에 기대어 한 문장으로 구체적으로 작성하시오.\n"
            "원문에 없는 정보로 문제를 만들지 마시오.\n\n"
            f"제목: {title}\n\n"
            f"요약:\n{summary}\n\n"
            f"본문:\n{content}"
        )


def parse_quizzes(raw: str, article: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, list):
        return []

    quizzes = []
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            continue

        question = _normalize_text(item.get("question"))
        answer = _normalize_answer(item.get("answer"))
        explanation = _normalize_text(item.get("explanation"))
        if not question or answer is None or not explanation:
            continue
        if _is_low_quality_question(question):
            continue

        quizzes.append(
            {
                "id": f"{article['id']}_quiz_{index:03d}",
                "question": question,
                "answer": answer,
                "explanation": explanation,
            }
        )
        if len(quizzes) == 1:
            break

    return quizzes


def fallback_quizzes(article: dict[str, Any]) -> list[dict[str, Any]]:
    title = _normalize_text(article.get("title")) or "기사의 핵심 내용"
    summary = _summary_text(article.get("summary")) or title
    statement = _first_sentence(summary)
    if not statement:
        statement = _first_sentence(_normalize_text(article.get("content")))
    if not statement:
        statement = _normalize_text(article.get("title")) or "기사의 핵심 내용"
    statement = _strip_sentence_end(statement)
    explanation = f"요약과 본문에서 확인되는 핵심 근거는 '{statement}'예요."

    return [
        {
            "id": f"{article['id']}_quiz_001",
            "question": _to_quiz_statement(statement),
            "answer": True,
            "explanation": explanation,
        }
    ]


def _normalize_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _normalize_answer(value: Any) -> bool | None:
    if type(value) is bool:
        return value
    if isinstance(value, str):
        answer = value.strip().upper()
        if answer == "O":
            return True
        if answer == "X":
            return False
    return None


def _is_low_quality_question(question: str) -> bool:
    return bool(
        re.search(r"이 기사는.+(다룬다|관련된 내용|관련이 있다|주제다)", question)
        or re.search(r"기사의 주제는", question)
        or question.startswith("기사에 따르면")
    )


def _summary_text(summary: Any) -> str:
    if isinstance(summary, list):
        return " ".join(str(sentence).strip() for sentence in summary if str(sentence).strip())
    if isinstance(summary, str):
        return summary.strip()
    return ""


def _first_sentence(text: str) -> str:
    match = re.search(r"[^.!?。！？]+[.!?。！？]", text)
    if match:
        return match.group(0).strip()
    return text[:120].strip() or "기사 요약에 근거한 설명임."


def _strip_sentence_end(text: str) -> str:
    return re.sub(r"[.!?。！？]+$", "", text).strip()


def _to_quiz_statement(text: str) -> str:
    statement = _strip_sentence_end(text)
    replacements = (
        ("하고 있어요", "하고 있다"),
        ("되고 있어요", "되고 있다"),
        ("중이에요", "중이다"),
        ("받았어요", "받았다"),
        ("했어요", "했다"),
        ("있어요", "있다"),
        ("이에요", "이다"),
        ("예요", "이다"),
    )
    for old, new in replacements:
        if statement.endswith(old):
            statement = statement[: -len(old)] + new
            break
    return f"{statement}."
