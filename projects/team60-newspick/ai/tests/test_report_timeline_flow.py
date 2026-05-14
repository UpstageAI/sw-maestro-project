import json

from newspick_ai.report.timeline_flow import TimelineFlowGenerator


class FakeChatClient:
    def __init__(self, response):
        self._response = response
        self.last_messages: list[dict] | None = None

    def complete(self, messages: list[dict]) -> str:
        self.last_messages = messages
        return json.dumps(self._response, ensure_ascii=False)


def test_timeline_sorted_by_source_count_desc_and_flow_by_category():
    fake_flow = [
        {"category": "테크", "description": "테크 흐름 요약"},
        {"category": "경제", "description": "경제 흐름 요약"},
        {"category": "이슈", "description": "이슈 흐름 요약"},
    ]
    fake_client = FakeChatClient(fake_flow)

    articles = [
        {
            "id": "a1", "title": "첫 기사", "category": "테크",
            "publishedAt": "2026-05-12T09:00:00+09:00",
            "sourceCount": 3, "summary": ["테크 요약 첫 문장"],
        },
        {
            "id": "a2", "title": "두번째 기사", "category": "경제",
            "publishedAt": "2026-05-12T18:00:00+09:00",
            "sourceCount": 1, "summary": [],
        },
        {
            "id": "a3", "title": "세번째 기사", "category": "이슈",
            "publishedAt": "2026-05-12T12:00:00+09:00",
            "sourceCount": 2, "summary": None,
        },
    ]

    result = TimelineFlowGenerator(chat_client=fake_client).generate(articles)

    # 많이 다뤄진 순(sourceCount 내림차순): a1(3) → a3(2) → a2(1)
    assert [item.articleId for item in result.timeline] == ["a1", "a3", "a2"]
    assert result.timeline[0].sourceCount == 3
    assert result.timeline[1].sourceCount == 2
    assert result.timeline[2].sourceCount == 1

    assert result.timeline[0].category == "테크"
    assert result.timeline[0].timeLabel == "09:00"
    assert result.timeline[0].summary == "테크 요약 첫 문장"
    assert result.timeline[1].summary is None
    assert result.timeline[2].summary is None

    assert len(result.flow) == 3
    assert result.flow[0].category == "테크"
    assert result.flow[0].description == "테크 흐름 요약"
    assert result.flow[1].category == "경제"
    assert result.flow[2].category == "이슈"


def test_timeline_flow_generator_uses_fallback_when_model_fails():
    class FailingClient:
        def complete(self, messages: list[dict]) -> str:
            raise RuntimeError("too_many_requests")

    articles = [
        {"id": "a1", "title": "첫 기사", "publishedAt": "2026-05-12T09:00:00+09:00"},
    ]

    result = TimelineFlowGenerator(chat_client=FailingClient()).generate(articles)

    assert [item.articleId for item in result.timeline] == ["a1"]
    assert len(result.flow) == 1
    assert result.flow[0].category == "기타"
    assert result.flow[0].description
