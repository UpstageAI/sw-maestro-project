import json

from newspick_ai.graph.quiz_generator import QuizGenerator


class FakeChatClient:
    def __init__(self):
        self.messages = []

    def complete(self, messages):
        self.messages.append(messages)
        return json.dumps(
            [
                {
                    "question": "AI 기술은 기사 작성 시간을 줄이고 검수 품질을 높이는 방향으로 활용되고 있다.",
                    "answer": True,
                    "explanation": "본문에서 AI가 기사 작성 시간을 줄이고 검수 품질을 높였다고 설명한다.",
                },
                {
                    "question": "이 기사는 스포츠 경기 결과만 다룬다.",
                    "answer": False,
                    "explanation": "기사 주제는 AI 기술이다.",
                },
            ],
            ensure_ascii=False,
        )


def test_quiz_generator_creates_single_article_comprehension_question():
    fake = FakeChatClient()
    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 뉴스",
                "summary": "AI가 뉴스 제작 시간을 줄였다.",
                "content": "AI 기술이 기사 작성 시간을 줄이고 검수 품질을 높였다.",
            }
        ],
        "events": [],
    }

    output = QuizGenerator(chat_client=fake).run(state)

    article = output["articles"][0]
    assert len(article["quizzes"]) == 1
    assert article["quizzes"][0]["id"] == "article_001_quiz_001"
    for quiz in article["quizzes"]:
        assert set(quiz) == {"id", "question", "answer", "explanation"}
        assert isinstance(quiz["question"], str)
        assert type(quiz["answer"]) is bool
        assert isinstance(quiz["explanation"], str)
    assert "AI 뉴스" in fake.messages[0][1]["content"]
    assert "O/X 퀴즈 1개" in fake.messages[0][1]["content"]
    assert "기사 핵심 주장, 원인, 영향, 배경" in fake.messages[0][1]["content"]
    assert "제목만 바꾼 문제" in fake.messages[0][1]["content"]
    assert "'기사에 따르면'으로 시작하지 말고" in fake.messages[0][1]["content"]
    assert output["events"][0]["stage"] == "generate_quiz"


def test_quiz_generator_converts_ox_answers_to_boolean():
    class OxAnswerClient:
        def complete(self, messages):
            return json.dumps(
                [
                    {
                        "question": "AI 기술은 기사 작성 시간을 줄인다.",
                        "answer": "O",
                        "explanation": "기사에서는 AI가 작성 시간을 줄인다고 설명한다.",
                    }
                ],
                ensure_ascii=False,
            )

    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 뉴스",
                "summary": "AI가 뉴스 제작 시간을 줄였다.",
                "content": "AI 기술이 기사 작성 시간을 줄이고 검수 품질을 높였다.",
            }
        ],
        "events": [],
    }

    article = QuizGenerator(chat_client=OxAnswerClient()).run(state)["articles"][0]

    assert article["quizzes"][0]["answer"] is True


def test_quiz_generator_rejects_generic_topic_question():
    class GenericClient:
        def complete(self, messages):
            return json.dumps(
                [
                    {
                        "question": "이 기사는 'AI 뉴스'와 관련된 내용을 다룬다.",
                        "answer": True,
                        "explanation": "제목에 AI 뉴스가 나온다.",
                    }
                ],
                ensure_ascii=False,
            )

    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 뉴스",
                "summary": "AI가 뉴스 제작 시간을 줄였다.",
                "content": "AI 기술이 기사 작성 시간을 줄이고 검수 품질을 높였다.",
            }
        ],
        "events": [],
    }

    article = QuizGenerator(chat_client=GenericClient()).run(state)["articles"][0]

    assert article["quizzes"][0]["question"] == "AI가 뉴스 제작 시간을 줄였다."
    assert "이 기사는" not in article["quizzes"][0]["question"]
    assert not article["quizzes"][0]["question"].startswith("기사에 따르면")


def test_quiz_generator_creates_fallback_quiz_when_model_output_is_invalid():
    class InvalidClient:
        def complete(self, messages):
            return "not json"

    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 뉴스",
                "summary": "AI가 뉴스 제작 시간을 줄였다.",
                "content": "AI 기술이 기사 작성 시간을 줄이고 검수 품질을 높였다.",
            }
        ],
        "events": [],
    }

    article = QuizGenerator(chat_client=InvalidClient()).run(state)["articles"][0]

    assert article["quizzes"][0]["answer"] is True
    assert article["quizzes"][0]["explanation"]
    assert "이 기사는" not in article["quizzes"][0]["question"]


def test_quiz_generator_creates_fallback_quiz_when_model_fails():
    class FailingClient:
        def complete(self, messages):
            raise RuntimeError("too_many_requests")

    state = {
        "articles": [
            {
                "id": "article_001",
                "title": "AI 뉴스",
                "summary": "AI가 뉴스 제작 시간을 줄였다.",
                "content": "AI 기술이 기사 작성 시간을 줄이고 검수 품질을 높였다.",
            }
        ],
        "events": [],
    }

    article = QuizGenerator(chat_client=FailingClient()).run(state)["articles"][0]

    assert article["quizzes"][0]["answer"] is True
    assert article["quizzes"][0]["explanation"]
