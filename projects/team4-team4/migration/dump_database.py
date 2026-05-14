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
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "dumps" / "kipris_patents_v2.parquet"

# Parquet에 저장할 컬럼 구조입니다.
# id: ChromaDB document id, document: desc_v1 본문,
# metadata_json: Chroma metadata를 JSON 문자열로 직렬화한 값,
# embedding: 4096차원 embedded_v2 float vector입니다.
SCHEMA = pa.schema(
    [
        pa.field("id", pa.string()),
        pa.field("document", pa.string()),
        pa.field("metadata_json", pa.string()),
        pa.field("embedding", pa.list_(pa.float32())),
    ]
)


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


# 역할: collection 이름으로 ChromaDB 내부 collection id(UUID)를 찾습니다.
# chroma_url: ChromaDB 서버 주소입니다. 예: http://localhost:8001
# tenant: ChromaDB tenant 이름입니다. 기본값은 default_tenant입니다.
# database: ChromaDB database 이름입니다. 기본값은 brainrot_patent입니다.
# collection_name: 찾을 collection 이름입니다. 기본값은 kipris_patents_v2입니다.
def get_collection_id(chroma_url: str, tenant: str, database: str, collection_name: str) -> str:
    collections = request_json(
        "GET",
        f"{chroma_url}/api/v2/tenants/{tenant}/databases/{database}/collections?limit=1000",
    )
    for collection in collections:
        if collection["name"] == collection_name:
            return collection["id"]
    raise RuntimeError(f"collection not found: {tenant}/{database}/{collection_name}")


# 역할: ChromaDB collection에 저장된 row 개수를 조회합니다.
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


# 역할: ChromaDB collection에서 한 페이지 분량의 문서를 가져옵니다.
# chroma_url: ChromaDB 서버 주소입니다.
# tenant: ChromaDB tenant 이름입니다.
# database: ChromaDB database 이름입니다.
# collection_id: dump 대상 collection UUID입니다.
# limit: 한 번에 가져올 row 수입니다. embedding payload가 커서 너무 크게 잡지 않습니다.
# offset: 전체 collection에서 몇 번째 row부터 가져올지 나타냅니다.
def get_batch(
    chroma_url: str,
    tenant: str,
    database: str,
    collection_id: str,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{chroma_url}/api/v2/tenants/{tenant}/databases/{database}/collections/{collection_id}/get",
        {
            "limit": limit,
            "offset": offset,
            "include": ["documents", "metadatas", "embeddings"],
        },
    )


# 역할: ChromaDB /get 응답을 Parquet writer가 쓸 수 있는 Arrow Table로 변환합니다.
# batch: ChromaDB가 반환한 ids/documents/metadatas/embeddings dict입니다.
# metadata는 Parquet map 구조 대신 JSON 문자열로 저장해 schema 충돌을 줄입니다.
def to_table(batch: dict[str, Any]) -> pa.Table:
    ids = batch.get("ids") or []
    documents = batch.get("documents") or []
    metadatas = batch.get("metadatas") or []
    embeddings = batch.get("embeddings") or []
    if not (len(ids) == len(documents) == len(metadatas) == len(embeddings)):
        raise RuntimeError("ChromaDB returned arrays with different lengths")

    metadata_json = [
        json.dumps(metadata or {}, ensure_ascii=False, sort_keys=True)
        for metadata in metadatas
    ]
    return pa.Table.from_arrays(
        [
            pa.array(ids, type=pa.string()),
            pa.array(documents, type=pa.string()),
            pa.array(metadata_json, type=pa.string()),
            pa.array(embeddings, type=pa.list_(pa.float32())),
        ],
        schema=SCHEMA,
    )


# 역할: CLI 인자를 읽고 ChromaDB collection 전체를 batch 단위로 Parquet에 dump합니다.
# --chroma-url: ChromaDB 서버 주소입니다.
# --tenant: ChromaDB tenant 이름입니다.
# --database: ChromaDB database 이름입니다.
# --collection: dump할 collection 이름입니다.
# --output: 생성할 Parquet 파일 경로입니다.
# --batch-size: ChromaDB에서 한 번에 읽어올 row 수입니다.
def main() -> int:
    parser = argparse.ArgumentParser(description="Dump a ChromaDB collection to Parquet.")
    parser.add_argument("--chroma-url", default=DEFAULT_CHROMA_URL)
    parser.add_argument("--tenant", default=DEFAULT_TENANT)
    parser.add_argument("--database", default=DEFAULT_DATABASE)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-size", type=int, default=250)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    collection_id = get_collection_id(args.chroma_url, args.tenant, args.database, args.collection)
    total = get_count(args.chroma_url, args.tenant, args.database, collection_id)
    print(f"source={args.tenant}/{args.database}/{args.collection} id={collection_id}")
    print(f"count={total} output={args.output}")

    started = time.time()
    written = 0
    writer: pq.ParquetWriter | None = None
    try:
        for offset in range(0, total, args.batch_size):
            batch = get_batch(
                args.chroma_url,
                args.tenant,
                args.database,
                collection_id,
                args.batch_size,
                offset,
            )
            table = to_table(batch)
            if writer is None:
                writer = pq.ParquetWriter(
                    args.output,
                    SCHEMA,
                    compression="zstd",
                    use_dictionary=["id", "document", "metadata_json"],
                )
            writer.write_table(table)
            written += table.num_rows
            print(f"dumped={written}/{total}", flush=True)
    finally:
        if writer is not None:
            writer.close()

    elapsed = time.time() - started
    print(f"done dumped={written} elapsed_sec={elapsed:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
