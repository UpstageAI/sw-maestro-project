from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

try:
    from app.storage import ChromaDBConnection, ChromaDBDocument
except ImportError:
    from backend.app.storage import ChromaDBConnection, ChromaDBDocument


DEFAULT_QUERY_EMBEDDING_MODEL = "solar-embedding-1-large-query"


@dataclass(frozen=True)
class ChromaPatentDocument:
    """migration scripts가 적재한 patent 문서 1건입니다."""

    id: str
    document: str
    metadata: dict[str, Any]
    distance: float | None = None

    @property
    def mongo_id(self) -> str:
        return str(self.metadata.get("mongo_id") or self.id)

    @property
    def title(self) -> str:
        return str(self.metadata.get("inventionTitle") or "")

    @property
    def description(self) -> str:
        return str(self.metadata.get("desc_v1") or self.document)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "mongo_id": self.mongo_id,
            "title": self.title,
            "description": self.description,
            "distance": self.distance,
            "metadata": self.metadata,
        }


class ChromaPatentTool:
    """마이그레이션된 ChromaDB KIPRIS collection을 조회하는 backend RAG tool입니다.

    ChromaDB 연결과 v2 REST 호출은 `backend.app.storage.chormaDB.ChromaDBConnection`에
    위임합니다. 이 tool은 patent 도메인에서 쓰기 좋은 객체와 embedding 검색 메서드만 제공합니다.
    """

    def __init__(
        self,
        db: ChromaDBConnection | None = None,
        openai_client: Any | None = None,
        query_embedding_model: str = DEFAULT_QUERY_EMBEDDING_MODEL,
    ) -> None:
        self.db = db or ChromaDBConnection.from_env()
        self.openai_client = openai_client
        self.query_embedding_model = query_embedding_model

    @classmethod
    def from_env(cls) -> "ChromaPatentTool":
        """환경변수로 ChromaPatentTool을 생성합니다."""
        from openai import OpenAI

        api_key = _get_env("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_BASE_URL") or None
        return cls(
            db=ChromaDBConnection.from_env(),
            openai_client=OpenAI(api_key=api_key, base_url=base_url),
            query_embedding_model=os.getenv(
                "OPENAI_QUERY_EMBEDDING_MODEL",
                DEFAULT_QUERY_EMBEDDING_MODEL,
            ),
        )

    def count(self) -> int:
        """현재 patent collection에 적재된 문서 수를 반환합니다."""
        return self.db.count()

    def get_by_id(self, patent_id: str) -> ChromaPatentDocument | None:
        """MongoDB `_id`와 같은 Chroma document id로 patent 1건을 조회합니다."""
        documents = self.db.get_documents(ids=[patent_id])
        return _to_patent_document(documents[0]) if documents else None

    def list_documents(
        self,
        limit: int = 10,
        offset: int = 0,
        where: dict[str, Any] | None = None,
    ) -> list[ChromaPatentDocument]:
        """patent collection 문서를 페이지 단위로 조회합니다."""
        documents = self.db.get_documents(limit=limit, offset=offset, where=where)
        return [_to_patent_document(document) for document in documents]

    def query(
        self,
        query: str,
        match_count: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[ChromaPatentDocument]:
        """자연어 query를 embedding한 뒤 patent collection에서 유사도 검색합니다."""
        embedding = self.embed_query(query)
        return self.query_by_embedding(
            embedding=embedding,
            match_count=match_count,
            where=where,
        )

    def query_by_embedding(
        self,
        embedding: list[float],
        match_count: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[ChromaPatentDocument]:
        """이미 생성된 embedding으로 patent collection 유사도 검색을 수행합니다."""
        documents = self.db.query_embeddings(
            query_embeddings=[embedding],
            n_results=match_count,
            where=where,
        )
        return [_to_patent_document(document) for document in documents]

    def search_for_context(self, query: str, match_count: int = 5) -> str:
        """LangChain agent에 넘길 수 있는 JSON 문자열 검색 결과를 반환합니다."""
        matches = self.query(query=query, match_count=match_count)
        return _to_json(
            {
                "query": query,
                "count": len(matches),
                "results": [_compact_patent_document(match) for match in matches],
            }
        )

    def get_by_id_for_context(self, patent_id: str) -> str:
        """LangChain agent에 넘길 수 있는 JSON 문자열 단건 조회 결과를 반환합니다."""
        normalized_id = patent_id.strip()
        document = self.get_by_id(normalized_id)
        if document is None:
            return _to_json(
                {
                    "id": normalized_id,
                    "found": False,
                    "result": None,
                }
            )

        return _to_json(
            {
                "id": normalized_id,
                "found": True,
                "result": _compact_patent_document(document),
            }
        )

    def count_for_context(self, _: str = "") -> str:
        """LangChain agent에 넘길 수 있는 JSON 문자열 collection count를 반환합니다."""
        return _to_json(
            {
                "collection": self.db.collection,
                "count": self.count(),
            }
        )

    def embed_query(self, query: str) -> list[float]:
        """검색용 query embedding을 생성합니다."""
        if self.openai_client is None:
            raise RuntimeError("openai_client is required to embed query text")

        response = self.openai_client.embeddings.create(
            model=self.query_embedding_model,
            input=query,
        )
        return response.data[0].embedding


def getTools(tool: ChromaPatentTool | None = None) -> list[Any]:
    """LangChain agent가 사용할 Chroma patent Tool 목록을 반환합니다.

    자연어 검색 tool은 query embedding API가 필요하므로 기본값에서는 `from_env()`로 생성합니다.
    테스트나 직접 주입이 필요하면 `tool` 인자로 ChromaPatentTool 인스턴스를 넘깁니다.
    """
    try:
        from langchain.tools import Tool
    except ImportError:
        from langchain_core.tools import Tool

    patent_tool = tool or ChromaPatentTool.from_env()

    return [
        Tool.from_function(
            name="search_kipris_patents_chroma",
            description=(
                "한국어 발명 아이디어나 기술 설명과 의미적으로 가까운 KIPRIS 특허를 "
                "ChromaDB에서 검색합니다. 입력은 한국어 자연어 query 하나입니다."
            ),
            func=patent_tool.search_for_context,
        ),
        Tool.from_function(
            name="get_kipris_patent_by_id",
            description=(
                "ChromaDB에 저장된 KIPRIS 특허를 MongoDB _id/Chroma id로 1건 조회합니다. "
                "입력은 예: 690dc67fa424e6f6ab885b4a"
            ),
            func=patent_tool.get_by_id_for_context,
        ),
        Tool.from_function(
            name="count_kipris_patents_chroma",
            description=(
                "현재 ChromaDB KIPRIS 특허 collection에 저장된 문서 수를 확인합니다. "
                "입력은 사용하지 않습니다."
            ),
            func=patent_tool.count_for_context,
        ),
    ]


def _to_patent_document(document: ChromaDBDocument) -> ChromaPatentDocument:
    return ChromaPatentDocument(
        id=document.id,
        document=document.document,
        metadata=document.metadata,
        distance=document.distance,
    )


def _compact_patent_document(document: ChromaPatentDocument) -> dict[str, Any]:
    metadata = document.metadata
    return {
        "id": document.id,
        "mongo_id": document.mongo_id,
        "title": document.title,
        "description": document.description,
        "distance": document.distance,
        "applicantName": metadata.get("applicantName"),
        "applicationNumber": metadata.get("applicationNumber"),
        "applicationDate": metadata.get("applicationDate"),
        "registerNumber": metadata.get("registerNumber"),
        "registerStatus": metadata.get("registerStatus"),
        "ipcNumber": metadata.get("ipcNumber"),
        "source_collection": metadata.get("source_collection"),
    }


def _to_json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False)


def _get_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value
