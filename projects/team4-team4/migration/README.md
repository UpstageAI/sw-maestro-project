# ChromaDB Migration Utilities

이 폴더는 `localhost:8001`에서 실행 중인 ChromaDB 개발 데이터를 Parquet 파일로 내보내고, 다른 개발자가 같은 데이터를 자기 로컬 ChromaDB에 다시 적재하기 위한 데이터 마이그레이션 유틸리티 폴더입니다.

## 기본 대상

- Chroma URL: `http://localhost:8001`
- Tenant: `default_tenant`
- Database: `brainrot_patent`
- Collection: `kipris_patents_v2`
- Embedding: MongoDB 원본의 `embedded_v2`
- Document: `desc_v1`
- Metadata: KIPRIS 특허 원본 필드 일부

`embedded_v2`는 `solar-embedding-1-large-passage`로 생성된 4096차원 벡터입니다. 이 유틸리티는 새 embedding model을 호출하지 않고, ChromaDB에 이미 들어 있는 embedding을 그대로 dump/restore합니다.

## 파일 설명

- `dump_database.py`: ChromaDB collection을 batch로 읽어서 Parquet 파일로 저장합니다.
- `init_database.py`: Parquet dump를 읽어서 ChromaDB collection에 batch upsert합니다.
- `dump_database.sh`: 의존성을 준비하고 새 dump를 `.tmp`에 만든 뒤 성공 시 최종 dump 파일로 교체합니다.
- `init_database.sh`: 의존성을 준비하고 dump 파일을 현재 로컬 ChromaDB에 적재합니다.
- `requirements.txt`: dump/init에 필요한 Python 의존성입니다.
- `dumps/`: 생성된 Parquet dump가 들어갑니다. 이 폴더는 `.gitignore` 대상입니다.
- `pydeps/`: shell script가 로컬 설치하는 Python 의존성 폴더입니다. `.gitignore` 대상입니다.

## 빠른 사용법

ChromaDB가 `localhost:8001`에 떠 있어야 합니다.

새 dump 만들기:

```bash
./migration/dump_database.sh
```

dump로 DB 초기화하기:

```bash
./migration/init_database.sh
```

## Parquet 파일 전달과 배치

ChromaDB 초기 설정을 위해서는 KIPRIS patent dump Parquet 파일을 팀원에게 별도로 받아야 합니다. dump 파일은 용량이 크고 재생성 가능한 데이터라 git에 커밋하지 않습니다.

팀원에게 받을 파일 이름은 다음으로 통일합니다.

```text
kipris_patents_v2.parquet
```

받은 파일은 아래 경로에 그대로 넣습니다.

```text
migration/dumps/kipris_patents_v2.parquet
```

파일명이 다르면 기본 `init_database.sh`가 찾지 못합니다. 다른 이름으로 받은 경우에는 위 이름으로 바꾸거나 `DUMP_FILE` 환경 변수로 직접 지정합니다.

```bash
DUMP_FILE=migration/dumps/받은파일명.parquet ./migration/init_database.sh
```

초기 설정 순서:

1. ChromaDB를 `localhost:8001`에 실행합니다.
2. 전달받은 `kipris_patents_v2.parquet`를 `migration/dumps/`에 넣습니다.
3. row 수를 확인합니다.
4. `./migration/init_database.sh`를 실행합니다.
5. 출력의 `chroma_count`가 dump row 수와 맞는지 확인합니다.

row 수 확인:

```bash
PYTHONPATH=migration/pydeps python3 -c "import pyarrow.parquet as pq; f=pq.ParquetFile('migration/dumps/kipris_patents_v2.parquet'); print(f.metadata.num_rows)"
```

기본 적재 대상은 다음과 같습니다.

```text
tenant: default_tenant
database: brainrot_patent
collection: kipris_patents_v2
```

## Dump 정책

`dump_database.sh`는 기존 최종 dump 파일이 있으면 새 dump가 끝까지 성공할 때까지 보존합니다.

기본 파일:

```text
migration/dumps/kipris_patents_v2.parquet
```

안전하게 만들기 위해 실제 dump는 먼저 아래 임시 파일에 기록됩니다.

```text
migration/dumps/kipris_patents_v2.parquet.tmp
```

dump가 끝까지 성공하면 `.tmp` 파일을 최종 `.parquet` 파일로 바꿉니다. 중간에 중단되면 기존 최종 dump는 그대로 두고, 작성 중이던 partial dump는 `.tmp` 파일로 남깁니다.

## Batch 설정

기본 batch 크기:

- dump: `250`
- init: `100`

embedding이 4096차원이라 한 번에 너무 많이 읽거나 쓰면 HTTP payload와 메모리가 커집니다. 로컬 Mac 기준으로 위 값이 느리지만 안정적인 기본값입니다.

필요하면 환경 변수로 조절할 수 있습니다.

```bash
DUMP_BATCH_SIZE=500 ./migration/dump_database.sh
INIT_BATCH_SIZE=200 ./migration/init_database.sh
```

## 다른 ChromaDB 주소 사용

```bash
CHROMA_URL=http://localhost:8001 ./migration/dump_database.sh
CHROMA_URL=http://localhost:8001 ./migration/init_database.sh
```

DB 이름이나 collection 이름을 바꾸려면 다음 환경 변수를 사용합니다.

```bash
CHROMA_DATABASE=brainrot_patent \
CHROMA_COLLECTION=kipris_patents_v2 \
./migration/init_database.sh
```

## 현재 dump 상태

현재 `dumps/kipris_patents_v2.parquet`가 있다면 partial dump일 수 있습니다. 이전 긴급 중단 시점에는 전체 `49,495`건 중 `16,750`건만 포함된 partial dump가 만들어졌습니다.

정확한 row 수 확인:

```bash
PYTHONPATH=migration/pydeps python3 -c "import pyarrow.parquet as pq; f=pq.ParquetFile('migration/dumps/kipris_patents_v2.parquet'); print(f.metadata.num_rows)"
```

전체 dump가 필요하면 `dump_database.sh`를 다시 실행합니다.

## AI Agent 작업 규칙

- `dumps/`와 `pydeps/`는 생성물입니다. 코드 리뷰나 커밋 대상이 아닙니다.
- 기존 dump를 새로 만들 때는 `dump_database.sh`를 사용합니다.
- 수동으로 삭제할 때도 `migration/dumps/kipris_patents_v2.parquet`와 `.tmp`만 대상으로 합니다.
- ChromaDB collection schema는 `id`, `document`, `metadata_json`, `embedding` Parquet 컬럼에 의존합니다.
- `init_database.py`는 `upsert`를 사용하므로 같은 id를 다시 넣어도 중복 생성 대신 갱신됩니다.
