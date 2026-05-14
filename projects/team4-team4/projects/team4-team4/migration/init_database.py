from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq


DEFAULT_CHROMA_URL = "http://localhost:8001"
DEFAULT_TENANT = "default_tenant"
DEFAULT_DATABASE = "brainrot_patent"
DEFAULT_COLLECTION = "kipris_patents_v2"
DEFAULT_INPUT = Path(__file__).resolve().parent / "dumps" / "kipris_patents_v2.parquet"


# 역할: ChromaDB v2 REST API에 JSON 요청을 보내고 JSON 응답을 반환합니다.
# method: "GET", "POST" 같은 HTTP method입니다.
# url: 호출할 ChromaDB REST endpoint 전체 URL입니다.
# payload: POST 요청에 실어 보낼 JSON body이며, GET 요청이면 None을 넣습니다.
def request_json(method: str, url: str, payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed: HTTP {exc.code}: {body}") from exc


# 역할: restore 대상 ChromaDB database가 없으면 생성합니다.
# chroma_url: ChromaDB 서버 주소입니다. 예: http://localhost:8001
# tenant: ChromaDB tenant 이름입니다. 기본값은 default_tenant입니다.
# database: 생성하거나 재사용할 database 이름입니다.
def ensure_database(chroma_url: str, tenant: str, database: str) -> None:
    url = f"{chroma_url}/api/v2/tenants/{tenant}/databases"
    try:
        request_json("POST", url, {"name": database})
    except RuntimeError as exc:
        message = str(exc)
        if "already exists" not in message and "Unique constraint" not in message:
            raise


# 역할: restore 대상 collection을 가져오거나 없으면 새로 생성합니다.
# chroma_url: ChromaDB 서버 주소입니다.
# tenant: ChromaDB tenant 이름입니다.
# database: ChromaDB database 이름입니다.
# collection: 생성하거나 재사용할 collection 이름입니다.
# 반환값은 ChromaDB 내부 collection id(UUID)입니다.
def get_or_create_collection(
    chroma_url: str,
    tenant: str,
    database: str,
    collection: str,
) -> str:
    response = request_json(
        "POST",
        f"{chroma_url}/api/v2/tenants/{tenant}/databases/{database}/collections",
        {
            "name": collection,
            "get_or_create": True,
            "metadata": {
                "project": "brainrot-patent",
                "source": "parquet dump",
                "embedding_model": "solar-embedding-1-large-passage",
                "embedding_source_field": "desc_v1",
                "dimensions": 4096,
            },
        },
    )
    return response["id"]


# 역할: ChromaDB collection에 현재 저장된 row 개수를 조회합니다.
# chroma_url: ChromaDB 서버 주소입니다.
# tenant: ChromaDB tenant 이름입니다.
# database: ChromaDB database 이름입니다.
# collection_id: collection 이름이 아니라 ChromaDB가 반환한 UUID입니다.
def get_count(chroma_url: str, tenant: str, database: str, collection_id: str) -> int:
    return int(
        request_json(
            "GET",
            f"{chroma_url}/api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/count",
        )
    )


# 역할: Parquet에서 읽은 한 batch를 ChromaDB collection에 upsert합니다.
# chroma_url: ChromaDB 서버 주소입니다.
# tenant: ChromaDB tenant 이름입니다.
# database: ChromaDB database 이름입니다.
# collection_id: 적재 대상 collection UUID입니다.
# ids: ChromaDB document id 목록입니다. MongoDB _id 문자열을 사용합니다.
# documents: ChromaDB document 본문 목록입니다. desc_v1 값입니다.
# embeddings: 4096차원 embedded_v2 vector 목록입니다.
# metadatas: 특허 제목, 출원번호, 등록상태 같은 metadata dict 목록입니다.
def upsert_batch(
    chroma_url: str,
    tenant: str,
    database: str,
    collection_id: str,
    ids: list[str],
    documents: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict[str, Any]],
) -> None:
    request_json(
        "POST",
        f"{chroma_url}/api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/upsert",
        {
            "ids": ids,
            "documents": documents,
            "embeddings": embeddings,
            "metadatas": metadatas,
        },
    )


# 역할: PyArrow Table 한 batch를 ChromaDB upsert 입력 배열들로 변환합니다.
# table: Parquet에서 batch 단위로 읽은 Arrow Table입니다.
# 반환값은 ids, documents, embeddings, metadatas 네 배열입니다.
def table_rows(table: Any) -> tuple[list[str], list[str], list[list[float]], list[dict[str, Any]]]:
    ids = table.column("id").to_pylist()
    documents = table.column("document").to_pylist()
    metadata_json = table.column("metadata_json").to_pylist()
    embeddings = table.column("embedding").to_pylist()
    metadatas = [json.loads(value or "{}") for value in metadata_json]
    return ids, documents, embeddings, metadatas


# 역할: CLI 인자를 읽고 Parquet dump를 ChromaDB collection에 batch 단위로 restore합니다.
# --input: 읽을 Parquet dump 파일 경로입니다.
# --chroma-url: ChromaDB 서버 주소입니다.
# --tenant: ChromaDB tenant 이름입니다.
# --database: ChromaDB database 이름입니다.
# --collection: restore할 collection 이름입니다.
# --batch-size: ChromaDB에 한 번에 upsert할 row 수입니다.
def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a ChromaDB collection from Parquet.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--chroma-url", default=DEFAULT_CHROMA_URL)
    parser.add_argument("--tenant", default=DEFAULT_TENANT)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--batch-size", type=int, default=100)
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Parquet dump not found: {args.input}")

    ensure_database(args.chroma_url, args.tenant, args.database)
    collection_id = get_or_create_collection(
        args.chroma_url,
        args.tenant,
        args.database,
        args.collection,
    )
    parquet_file = pq.ParquetFile(args.input)
    total = parquet_file.metadata.num_rows
    print(f"target={args.tenant}/{args.database}/{args.collection} id={collection_id}")
    print(f"input={args.input} rows={total}")

    started = time.time()
    imported = 0
    for batch in parquet_file.iter_batches(batch_size=args.batch_size):
        # iter_batches()는 RecordBatch를 반환하므로 Table로 감싸서 컬럼 접근 방식을 통일합니다.
        table = pa.Table.from_batches([batch])
        ids, documents, embeddings, metadatas = table_rows(table)
        upsert_batch(
            args.chroma_url,
            args.tenant,
            args.database,
            collection_id,
            ids,
            documents,
            embeddings,
            metadatas,
        )
        imported += len(ids)
        print(f"imported={imported}/{total}", flush=True)

    final_count = get_count(args.chroma_url, args.tenant, args.database, collection_id)
    elapsed = time.time() - started
    print(f"done imported={imported} chroma_count={final_count} elapsed_sec={elapsed:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
