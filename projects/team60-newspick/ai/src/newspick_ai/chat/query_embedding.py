MAX_QUERY_LENGTH = 500


class QueryEmbedder:
    def __init__(self, embedding_client=None):
        self._client = embedding_client

    def embed(self, query: str) -> list[float]:
        if not query.strip():
            raise ValueError("query must not be blank")
        client = self._client or self._default_client()
        return client.embed_query(query.strip()[:MAX_QUERY_LENGTH])

    def _default_client(self):
        from newspick_ai.solar.embeddings import SolarEmbeddingClient

        return SolarEmbeddingClient()
