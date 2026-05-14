import pytest

from newspick_ai.chat.answer_streamer import AnswerStreamer


class FakeSolarStreamClient:
    async def stream(self, messages: list[dict]):
        yield "안녕"
        yield "하세요"


@pytest.mark.asyncio
async def test_answer_streamer_yields_token_events_from_fake_solar_stream():
    events = []
    async for event_name, data in AnswerStreamer(chat_client=FakeSolarStreamClient()).stream("질문", "컨텍스트"):
        events.append((event_name, data))

    assert events[0][0] == "token"
    assert "".join(d["text"] for _, d in events) == "안녕하세요"
    assert all(name != "done" for name, _ in events)
