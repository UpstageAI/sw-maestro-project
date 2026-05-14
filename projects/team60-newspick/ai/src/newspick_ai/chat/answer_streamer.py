class AnswerStreamer:
    def __init__(self, chat_client=None):
        self._client = chat_client

    async def stream(self, question: str, context: str):
        client = self._client or self._default_client()
        prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
        async for token in client.stream([{"role": "user", "content": prompt}]):
            if token:
                yield "token", {"text": token}

    def _default_client(self):
        from newspick_ai.solar.chat import SolarChatClient

        return SolarChatClient()
