import pytest

from newspick_ai.solar.embeddings import (
    SOLAR_PASSAGE_EMBEDDING_MODEL,
    SOLAR_QUERY_EMBEDDING_MODEL,
    SolarEmbeddingClient,
)


class FakeEmbeddingClient:
    def __init__(self):
        self.calls = []

    def embed(self, *, text, model):
        self.calls.append({"text": text, "model": model})
        return [0.1, 0.2, 0.3, 0.4]


def test_embedding_client_uses_passage_and_query_models():
    fake_client = FakeEmbeddingClient()
    client = SolarEmbeddingClient(fake_client)

    passage = client.embed_passage("본문")
    query = client.embed_query("질문")

    assert fake_client.calls[0]["model"] == SOLAR_PASSAGE_EMBEDDING_MODEL
    assert fake_client.calls[1]["model"] == SOLAR_QUERY_EMBEDDING_MODEL
    assert all(isinstance(value, float) for value in passage)
    assert all(isinstance(value, float) for value in query)


def test_embedding_client_rejects_blank_text():
    client = SolarEmbeddingClient(FakeEmbeddingClient())

    with pytest.raises(ValueError):
        client.embed_passage("")
