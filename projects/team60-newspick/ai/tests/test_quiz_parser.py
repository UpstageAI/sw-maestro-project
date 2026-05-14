import json

import pytest

from newspick_ai.graph.quiz_parser import QuizParseError, parse_quiz_output


def test_quiz_parser_rejects_missing_answer_field():
    valid = json.dumps(
        [
            {
                "id": "quiz_001",
                "question": "AI가 기사 요약에 사용되었다.",
                "answer": True,
                "explanation": "기사에는 AI 요약 사용이 언급된다.",
                "ignored": "field",
            }
        ],
        ensure_ascii=False,
    )
    missing_answer = json.dumps(
        [
            {
                "id": "quiz_001",
                "question": "AI가 기사 요약에 사용되었다.",
                "explanation": "기사에는 AI 요약 사용이 언급된다.",
            }
        ],
        ensure_ascii=False,
    )
    string_answer = json.dumps(
        [
            {
                "id": "quiz_001",
                "question": "AI가 기사 요약에 사용되었다.",
                "answer": "true",
                "explanation": "기사에는 AI 요약 사용이 언급된다.",
            }
        ],
        ensure_ascii=False,
    )

    quizzes = parse_quiz_output(valid)

    assert quizzes == [
        {
            "id": "quiz_001",
            "question": "AI가 기사 요약에 사용되었다.",
            "answer": True,
            "explanation": "기사에는 AI 요약 사용이 언급된다.",
        }
    ]
    with pytest.raises(QuizParseError):
        parse_quiz_output(missing_answer)
    with pytest.raises(QuizParseError):
        parse_quiz_output(string_answer)
