import pytest

from newspick_ai.chat.retriever import ArticleRetriever


class FakeRepository:
    async def search_by_embedding(self, vector, limit):
        return [
            {
                "id": f"a{i}",
                "title": f"기사{i}",
                "content": f"내용{i}",
                "source": "테스트",
                "publishedAt": "2026-05-12T09:00:00Z",
                "score": (6 - i) * 0.1,
            }
            for i in range(1, 6)
        ]


@pytest.mark.asyncio
async def test_article_retriever_returns_top_k_from_repository():
    result = await ArticleRetriever(repository=FakeRepository()).retrieve([0.1, 0.2], top_k=3)

    assert len(result) == 3
    assert result[0]["score"] >= result[1]["score"] >= result[2]["score"]
    for item in result:
        for field in ["id", "title", "content", "source", "publishedAt", "score"]:
            assert field in item
