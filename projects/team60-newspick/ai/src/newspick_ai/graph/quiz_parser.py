import json
from typing import Any, TypedDict


class Quiz(TypedDict):
    id: str
    question: str
    answer: bool
    explanation: str


class QuizParseError(ValueError):
    pass


def parse_quiz_output(raw: str) -> list[Quiz]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as error:
        raise QuizParseError("quiz output must be valid JSON") from error

    if not isinstance(payload, list):
        raise QuizParseError("quiz output must be a JSON array")

    return [_parse_quiz(item) for item in payload]


def _parse_quiz(item: Any) -> Quiz:
    if not isinstance(item, dict):
        raise QuizParseError("quiz item must be an object")

    missing = [
        field
        for field in ("id", "question", "answer", "explanation")
        if field not in item
    ]
    if missing:
        raise QuizParseError(f"quiz item missing required field: {missing[0]}")

    if not isinstance(item["id"], str):
        raise QuizParseError("quiz id must be a string")
    if not isinstance(item["question"], str):
        raise QuizParseError("quiz question must be a string")
    if type(item["answer"]) is not bool:
        raise QuizParseError("quiz answer must be a boolean")
    if not isinstance(item["explanation"], str):
        raise QuizParseError("quiz explanation must be a string")

    return {
        "id": item["id"],
        "question": item["question"],
        "answer": item["answer"],
        "explanation": item["explanation"],
    }
