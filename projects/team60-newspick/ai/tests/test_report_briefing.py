import json

from newspick_ai.report.briefing import BriefingGenerator


class FakeChatClient:
    def __init__(self, response: dict):
        self._response = response
        self.last_messages: list[dict] | None = None

    def complete(self, messages: list[dict]) -> str:
        self.last_messages = messages
        return json.dumps(self._response, ensure_ascii=False)


def test_briefing_generator_returns_headline_and_summary():
    fake_client = FakeChatClient({"headline": "오늘의 핵심", "summary": "세 가지 흐름"})
    clusters = [
        {"cluster_id": 0, "title": "AI 기술 혁신"},
        {"cluster_id": 1, "title": "반도체 시장 변화"},
    ]

    result = BriefingGenerator(chat_client=fake_client).generate(clusters)

    assert result.headline == "오늘의 핵심"
    assert result.summary == "세 가지 흐름"

    prompt_content = fake_client.last_messages[0]["content"]
    assert "AI 기술 혁신" in prompt_content
    assert "반도체 시장 변화" in prompt_content


def test_briefing_generator_uses_fallback_when_model_fails():
    class FailingClient:
        def complete(self, messages: list[dict]) -> str:
            raise RuntimeError("too_many_requests")

    result = BriefingGenerator(chat_client=FailingClient()).generate(
        [{"title": "AI 기술 혁신"}]
    )

    assert result.headline == "AI 기술 혁신"
    assert "오늘 수집된 주요 기사" in result.summary
