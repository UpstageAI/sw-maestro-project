import pytest

from newspick_ai.chat.query_embedding import QueryEmbedder
from newspick_ai.solar.embeddings import SOLAR_QUERY_EMBEDDING_MODEL


class FakeEmbeddingClient:
    model = SOLAR_QUERY_EMBEDDING_MODEL

    def embed_query(self, text: str) -> list[float]:
        return [0.2, 0.4, 0.6, 0.8]


def test_query_embedding_uses_query_model_and_returns_vector():
    fake = FakeEmbeddingClient()
    result = QueryEmbedder(embedding_client=fake).embed("오늘 AI 뉴스")

    assert fake.model == "solar-embedding-1-large-query"
    assert isinstance(result, list)
    assert all(isinstance(v, float) for v in result)

    with pytest.raises(ValueError):
        QueryEmbedder(embedding_client=fake).embed("")

    with pytest.raises(ValueError):
        QueryEmbedder(embedding_client=fake).embed("   ")
