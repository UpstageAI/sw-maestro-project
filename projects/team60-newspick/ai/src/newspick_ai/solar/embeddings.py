from typing import Any

from newspick_ai.env import require_environment


SOLAR_PASSAGE_EMBEDDING_MODEL = "solar-embedding-1-large-passage"
SOLAR_QUERY_EMBEDDING_MODEL = "solar-embedding-1-large-query"

# Solar embedding model has a 4000-token limit.
# Korean text averages ~2-3 BPE tokens per character, so 1500 chars ≈ 3000-4500 tokens.
# Truncate conservatively to stay within the limit.
_EMBEDDING_MAX_CHARS = 1500


class SolarEmbeddingClient:
    def __init__(self, client: Any | None = None):
        self._client = client
        self._real_clients: dict[str, Any] = {}

    def embed_passage(self, text: str) -> list[float]:
        return self._embed(text, SOLAR_PASSAGE_EMBEDDING_MODEL)

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text, SOLAR_QUERY_EMBEDDING_MODEL)

    def _embed(self, text: str, model: str) -> list[float]:
        if not text.strip():
            raise ValueError("embedding text must not be blank")

        text = text[:_EMBEDDING_MAX_CHARS]
        client = self._client or self._client_for_model(model)

        if hasattr(client, "embed"):
            vector = client.embed(text=text, model=model)
        elif hasattr(client, "embed_query"):
            vector = client.embed_query(text)
        else:
            raise TypeError("embedding client must provide embed or embed_query")

        return [float(value) for value in vector]

    def _client_for_model(self, model: str):
        if model not in self._real_clients:
            from langchain_upstage import UpstageEmbeddings

            env = require_environment(("UPSTAGE_API_KEY",))
            self._real_clients[model] = UpstageEmbeddings(
                model=model,
                api_key=env["UPSTAGE_API_KEY"],
            )

        return self._real_clients[model]
