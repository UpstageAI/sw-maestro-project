from newspick_ai.chat.answer_streamer import AnswerStreamer
from newspick_ai.chat.context_builder import build_context
from newspick_ai.chat.query_embedding import QueryEmbedder
from newspick_ai.chat.retriever import ArticleRetriever


class ChatService:
    def __init__(self, embedder=None, retriever=None, streamer=None):
        self._embedder = embedder or QueryEmbedder()
        self._retriever = retriever or ArticleRetriever()
        self._streamer = streamer or AnswerStreamer()

    async def stream(self, message: str):
        vector = self._embedder.embed(message)
        articles = await self._retriever.retrieve(vector, top_k=5)
        context = build_context(articles)

        async for event_name, data in self._streamer.stream(message, context):
            yield event_name, data

        cards = [
            {
                "id": a["id"],
                "title": a["title"],
                "source": a["source"],
                "publishedAt": a["publishedAt"],
            }
            for a in articles
        ]
        yield "done", {"articles": cards}
