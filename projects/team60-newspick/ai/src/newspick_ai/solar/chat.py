from typing import Any

from newspick_ai.env import require_environment


SOLAR_CHAT_MODEL = "solar-pro2"


class SolarChatClient:
    def __init__(self, client: Any | None = None, model: str = SOLAR_CHAT_MODEL):
        self._client = client
        self.model = model

    async def stream(self, messages: list[dict]):
        client = self._client or self._create_client()
        if hasattr(client, "astream"):
            async for chunk in client.astream(messages):
                yield self._response_text(chunk)
        else:
            yield self.complete(messages)

    def complete(self, messages: list[dict]) -> str:
        client = self._client or self._create_client()

        if hasattr(client, "complete"):
            response = client.complete(messages=messages, model=self.model)
        elif hasattr(client, "invoke"):
            response = client.invoke(messages)
        else:
            raise TypeError("chat client must provide complete or invoke")

        return self._response_text(response)

    def _create_client(self):
        from langchain_upstage import ChatUpstage

        env = require_environment(("UPSTAGE_API_KEY",))
        return ChatUpstage(
            model=self.model,
            api_key=env["UPSTAGE_API_KEY"],
        )

    @staticmethod
    def _response_text(response: Any) -> str:
        if isinstance(response, str):
            return response

        content = getattr(response, "content", response)
        if isinstance(content, str):
            return content

        if isinstance(content, list):
            return "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in content
            )

        return str(content)
