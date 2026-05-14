from newspick_ai.solar.chat import SOLAR_CHAT_MODEL, SolarChatClient


class FakeChatClient:
    def __init__(self):
        self.calls = []

    def complete(self, *, messages, model):
        self.calls.append({"messages": messages, "model": model})
        return f"{messages[-1]['content']} 응답"


def test_chat_solar_uses_injected_client_and_returns_text():
    fake_client = FakeChatClient()

    response = SolarChatClient(fake_client).complete(
        [{"role": "user", "content": "안녕"}]
    )

    assert response == "안녕 응답"
    assert fake_client.calls[0]["model"] == SOLAR_CHAT_MODEL
    assert fake_client.calls[0]["messages"][0]["role"] == "user"
