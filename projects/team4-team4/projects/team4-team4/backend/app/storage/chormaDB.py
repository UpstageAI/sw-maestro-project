from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


DEFAULT_CHROMA_HOST = "localhost"
DEFAULT_CHROMA_PORT = 8001
DEFAULT_CHROMA_TENANT = "default_tenant"
DEFAULT_CHROMA_DATABASE = "brainrot_patent"
DEFAULT_CHROMA_COLLECTION = "kipris_patents_v2"
DEFAULT_CHROMA_TIMEOUT_SECONDS = 120
DEFAULT_COLLECTION_METADATA = {
    "project": "brainrot-patent",
    "source": "mongodb://localhost:20060/crawler_db.kipris_patents",
    "embedding_model": "solar-embedding-1-large-passage",
    "embedding_source_field": "desc_v1",
    "dimensions": 4096,
}


@dataclass(frozen=True)
class ChromaDBDocument:
    """ChromaDB v2 REST 응답의 document 1건입니다."""

    id: str
    document: str
    metadata: dict[str, Any]
    distance: float | None = None

    @property
    def mongo_id(self) -> str:
        """원본 MongoDB `_id`입니다. migration metadata가 없으면 Chroma id를 씁니다."""
        return str(self.metadata.get("mongo_id") or self.id)

    @property
    def title(self) -> str:
        """특허 발명의 명칭입니다."""
        return str(self.metadata.get("inventionTitle") or "")

    @property
    def description(self) -> str:
        """RAG 본문으로 쓰는 설명입니다. migration에서는 `desc_v1`입니다."""
        return str(self.metadata.get("desc_v1") or self.document)

    def to_dict(self) -> dict[str, Any]:
        """LangChain tool 응답으로 직렬화하기 쉬운 dict로 변환합니다."""
        return {
            "id": self.id,
            "mongo_id": self.mongo_id,
            "title": self.title,
            "description": self.description,
            "distance": self.distance,
            "metadata": self.metadata,
        }


class ChromaDBConnection:
    """migration 적재 방식과 같은 ChromaDB HttpClient collection 연결 객체입니다.

    이 객체는 embedding 생성이나 RAG 판단을 하지 않습니다. ChromaDB tenant/database/collection
    접근과 count/get/query 요청만 담당합니다.
    """

    def __init__(
        self,
        host: str = DEFAULT_CHROMA_HOST,
        port: int = DEFAULT_CHROMA_PORT,
        tenant: str = DEFAULT_CHROMA_TENANT,
        database: str = DEFAULT_CHROMA_DATABASE,
        collection: str = DEFAULT_CHROMA_COLLECTION,
        timeout_seconds: int = DEFAULT_CHROMA_TIMEOUT_SECONDS,
    ) -> None:
        self.host = host
        self.port = port
        self.tenant = tenant
        self.database = database
        self.collection = collection
        self.timeout_seconds = timeout_seconds
        self._client: Any | None = None
        self._collection: Any | None = None
        self._collection_id: str | None = None

    @classmethod
    def from_env(cls) -> "ChromaDBConnection":
        """CHROMA_* 환경변수로 ChromaDBConnection을 생성합니다."""
        return cls(
            host=os.getenv("CHROMA_HOST", DEFAULT_CHROMA_HOST),
            port=int(os.getenv("CHROMA_PORT", DEFAULT_CHROMA_PORT)),
            tenant=os.getenv("CHROMA_TENANT", DEFAULT_CHROMA_TENANT),
            database=os.getenv("CHROMA_DATABASE", DEFAULT_CHROMA_DATABASE),
            collection=os.getenv("CHROMA_COLLECTION", DEFAULT_CHROMA_COLLECTION),
            timeout_seconds=int(
                os.getenv("CHROMA_TIMEOUT_SECONDS", DEFAULT_CHROMA_TIMEOUT_SECONDS)
            ),
        )

    @property
    def client(self) -> Any:
        """CHROMA_HOST/CHROMA_PORT 기준 ChromaDB HttpClient를 캐시합니다."""
        if self._client is None:
            try:
                import chromadb
            except ImportError as exc:
                raise RuntimeError("chromadb package is not installed") from exc

            os.environ.pop("SSLKEYLOGFILE", None)
            self._client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                tenant=self.tenant,
                database=self.database,
            )
        return self._client

    @property
    def chroma_collection(self) -> Any:
        """collection 이름으로 Chroma collection 객체를 가져오거나 생성합니다."""
        if self._collection is None:
            try:
                self._collection = self.client.get_or_create_collection(
                    name=self.collection,
                    metadata=DEFAULT_COLLECTION_METADATA,
                )
            except Exception as exc:
                raise RuntimeError("chromadb HttpClient collection lookup failed") from exc
        return self._collection

    @property
    def collection_id(self) -> str:
        """Chroma collection id를 반환합니다."""
        if self._collection_id:
            return self._collection_id

        try:
            self._collection_id = str(self.chroma_collection.id)
        except RuntimeError:
            response = self.request_json(
                "POST",
                self._collections_url(),
                {
                    "name": self.collection,
                    "get_or_create": True,
                    "metadata": DEFAULT_COLLECTION_METADATA,
                },
            )
            self._collection_id = str(response["id"])
        return self._collection_id

    def count(self) -> int:
        """현재 collection에 적재된 document 수를 반환합니다."""
        try:
            return int(self.chroma_collection.count())
        except RuntimeError:
            return int(self.request_json("GET", self.collection_url("count")))

    def get_documents(
        self,
        ids: list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> list[ChromaDBDocument]:
        """ChromaDB get API로 document를 조회합니다."""
        try:
            response = self.chroma_collection.get(
                ids=ids,
                limit=limit,
                offset=offset,
                where=where,
                include=include or ["documents", "metadatas"],
            )
        except RuntimeError:
            payload: dict[str, Any] = {
                "include": include or ["documents", "metadatas"],
            }
            if ids is not None:
                payload["ids"] = ids
            if limit is not None:
                payload["limit"] = limit
            if offset is not None:
                payload["offset"] = offset
            if where:
                payload["where"] = where
            response = self.request_json("POST", self.collection_url("get"), payload)
        return parse_chroma_get_response(response)

    def query_embeddings(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 5,
        where: dict[str, Any] | None = None,
        include: list[str] | None = None,
    ) -> list[ChromaDBDocument]:
        """ChromaDB query API로 embedding 유사도 검색을 수행합니다."""
        try:
            response = self.chroma_collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where,
                include=include or ["documents", "metadatas", "distances"],
            )
        except RuntimeError:
            payload: dict[str, Any] = {
                "query_embeddings": query_embeddings,
                "n_results": n_results,
                "include": include or ["documents", "metadatas", "distances"],
            }
            if where:
                payload["where"] = where
            response = self.request_json("POST", self.collection_url("query"), payload)
        return parse_chroma_query_response(response)

    def collection_url(self, action: str = "") -> str:
        """현재 collection id 기준 Chroma REST URL을 만듭니다."""
        base = f"{self._collections_url()}/{self.collection_id}"
        return f"{base}/{action}" if action else base

    def request_json(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        """ChromaDB v2 REST API를 호출하고 JSON 응답을 반환합니다."""
        os.environ.pop("SSLKEYLOGFILE", None)
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {body}") from exc

    def _collections_url(self) -> str:
        return (
            f"http://{self.host}:{self.port}/api/v2/tenants/{self.tenant}"
            f"/databases/{self.database}/collections"
        )


def parse_chroma_get_response(response: dict[str, Any]) -> list[ChromaDBDocument]:
    """Chroma get API 응답을 ChromaDBDocument 목록으로 변환합니다."""
    ids = response.get("ids") or []
    documents = response.get("documents") or []
    metadatas = response.get("metadatas") or []

    results: list[ChromaDBDocument] = []
    for index, item_id in enumerate(ids):
        results.append(
            ChromaDBDocument(
                id=str(item_id),
                document=str(_get_index(documents, index, "")),
                metadata=dict(_get_index(metadatas, index, {}) or {}),
            )
        )
    return results


def parse_chroma_query_response(response: dict[str, Any]) -> list[ChromaDBDocument]:
    """Chroma query API 응답의 첫 번째 query 결과를 ChromaDBDocument 목록으로 변환합니다."""
    ids = _get_index(response.get("ids") or [], 0, [])
    documents = _get_index(response.get("documents") or [], 0, [])
    metadatas = _get_index(response.get("metadatas") or [], 0, [])
    distances = _get_index(response.get("distances") or [], 0, [])

    results: list[ChromaDBDocument] = []
    for index, item_id in enumerate(ids):
        results.append(
            ChromaDBDocument(
                id=str(item_id),
                document=str(_get_index(documents, index, "")),
                metadata=dict(_get_index(metadatas, index, {}) or {}),
                distance=_get_index(distances, index, None),
            )
        )
    return results


def _get_index(values: list[Any], index: int, default: Any) -> Any:
    if index >= len(values):
        return default
    return values[index]
