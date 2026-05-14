# Backend Tools README

이 폴더는 backend Agent가 외부 검색/RAG 도구를 호출할 때 쓰는 코드입니다.
다른 AI 코딩 도구가 이 폴더를 수정할 때는 이 문서를 먼저 읽고, 기존 도구의 요청/응답 계약을 유지합니다.

## KiprisTool

파일: `backend/app/tools/kipris_tool.py`

`KiprisTool`은 KIPRIS Plus의 `getAdvancedSearch` API를 직접 호출하는 특허·실용 공개·등록공보 검색 도구입니다.
외부 `langchain_kipris_tools` 패키지를 쓰지 않고 Python 표준 라이브러리만 사용합니다.

### 목적

- KIPRIS 실제 서버에 `getAdvancedSearch` 요청을 보냅니다.
- XML 응답을 backend에서 쓰기 쉬운 dataclass로 변환합니다.
- LLM tool 또는 backend Agent가 특허 검색 결과를 근거 자료로 쓸 수 있게 합니다.

### 환경 변수

```text
KIPRIS_API_KEY=
```

API 키는 코드에 하드코딩하지 않습니다. 로컬에서는 repo 루트 `.env` 또는 `backend/.env`에 넣고, 공유용 예시는 `.env.example`에 키 이름만 둡니다.

### 주요 클래스

- `KiprisTool`
  - `get_advanced_search(...)`로 KIPRIS `getAdvancedSearch` API를 호출합니다.
  - Python `snake_case` 인자를 KIPRIS 문서의 camelCase 파라미터로 변환합니다.
  - `search_for_context(...)`, `search_title_for_context(...)`, `search_applicant_for_context(...)`로 LangChain tool에서 쓰기 좋은 JSON 문자열을 반환합니다.
- `KiprisSearchResult`
  - 응답 헤더, count, record 목록을 담습니다.
  - `result_code == "00"`이면 `success=True`입니다.
- `KiprisPatentRecord`
  - 특허 1건의 출원번호, 발명의 명칭, 출원인, 초록 등을 담습니다.
- `getKiprisTools`
  - `LangChain`의 `Tool` 객체 목록을 반환합니다.
  - 반환 tool 이름은 `search_kipris_patents`, `search_kipris_patents_by_title`, `search_kipris_patents_by_applicant`입니다.

### 중요한 구현 주의사항

KIPRIS 실제 응답은 record가 다음처럼 `body` 아래에 들어옵니다.

```xml
<response>
  <body>
    <items>
      <item>...</item>
    </items>
  </body>
  <count>...</count>
</response>
```

따라서 XML 파싱 시 `./items/item`처럼 루트 바로 아래만 찾으면 안 됩니다.
현재 파서는 `.//items/item`으로 중첩 위치와 상관없이 record를 찾습니다.

KIPRIS 문서에 오타처럼 보이는 파라미터명도 실제 API와 맞추기 위해 그대로 유지합니다.

- `internationOpenNumber`
- `internationOpenDate`
- `rightHoler`

### 검색어 선택

`word` 자유검색은 KIPRIS 쪽에서 넓게 매칭될 수 있습니다. 정확도를 올려야 하면 아래 필드를 우선 조합합니다.

- `invention_title`
- `applicant`
- `ipc_number`
- `application_number`
- `register_number`

예시:

```python
from backend.app.tools import KiprisTool

tool = KiprisTool()
result = tool.get_advanced_search(
    applicant="현대자동차",
    invention_title="자동차",
    page_no=1,
    num_of_rows=3,
)

for record in result.records:
    print(record.application_number, record.invention_title, record.applicant_name)
```

LangChain agent에 넘길 KIPRIS tool 목록이 필요할 때:

```python
from backend.app.tools import getKiprisTools

tools = getKiprisTools()
```

ChromaDB tool까지 포함한 전체 backend 특허 검색 tool 목록이 필요하면 package-level `getTools()`를 사용합니다.

```python
from backend.app.tools import getTools

tools = getTools()
```

### 테스트

관련 테스트 파일: `backend/tests/test_kipris_tool.py`

repo 루트에서 실행합니다.

```bash
python -m unittest backend/tests/test_kipris_tool.py
```

테스트는 다음을 확인합니다.

- KIPRIS 문서 필드와 Python 인자 매핑
- 실제 KIPRIS XML 구조 파싱
- `KIPRIS_API_KEY`가 있을 때 실제 KIPRIS 서버에서 record를 1건 이상 받는지

실제 서버 테스트는 네트워크와 API 키 상태에 영향을 받습니다. `resultCode=31`이면 보통 API 키의 서비스 이용 기간이 만료된 상태입니다.

## ChromaPatentTool

파일: `backend/app/tools/chroma_patent_tool.py`

`ChromaPatentTool`은 `migration/init_database.py`로 ChromaDB에 적재한 KIPRIS patent collection을 조회하는 RAG 도구입니다.
실제 ChromaDB `HttpClient` 연결은 `backend/app/storage/chormaDB.py`의 `ChromaDBConnection`이 담당하고,
`ChromaPatentTool`은 그 객체를 감싸 patent 도메인에서 쓰기 좋은 tool 형태로 제공합니다.

### 기본 연결값

마이그레이션 스크립트 기준 기본 target은 다음과 같습니다.

```text
CHROMA_HOST=localhost
CHROMA_PORT=8001
CHROMA_TENANT=default_tenant
CHROMA_DATABASE=brainrot_patent
CHROMA_COLLECTION=kipris_patents_v2
```

적재 원본은 MongoDB의 `crawler_db.kipris_patents`입니다.

### 적재 구조

`migration/init_database.py`는 Parquet dump row를 다음 형태로 ChromaDB에 저장합니다.

- Chroma document id: MongoDB `_id` 문자열
- Chroma document: MongoDB `desc_v1`
- Chroma embedding: MongoDB `embedded_v2`
- Chroma metadata:
  - `mongo_id`
  - `source_collection=crawler_db.kipris_patents`
  - `inventionTitle`
  - `desc_v1`
  - `applicantName`
  - `applicationNumber`
  - `registerNumber`
  - `registerStatus`
  - `embedded_v2_model`
  - `embedded_v2_dimensions`
  - 그 외 migration script의 metadata field 목록

### 주요 클래스

- `ChromaDBConnection`
  - 위치: `backend/app/storage/chormaDB.py`
  - `chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT, tenant=..., database=...)`로 연결합니다.
  - `count()`, `get_documents(...)`, `query_embeddings(...)`로 실제 ChromaDB collection을 조회합니다.
  - 기본 host/port/tenant/database/collection은 migration script와 같습니다.
- `ChromaPatentTool`
  - 내부에서 `ChromaDBConnection`을 사용합니다.
  - `count()`로 collection 문서 수를 조회합니다.
  - `get_by_id(patent_id)`로 MongoDB `_id`와 같은 Chroma document id를 조회합니다.
  - `list_documents(limit, offset)`로 페이지 단위 조회를 합니다.
  - `query_by_embedding(embedding, match_count)`으로 이미 만들어진 embedding 기반 유사도 검색을 합니다.
  - `query(query, match_count)`로 자연어를 query embedding으로 변환한 뒤 검색합니다.
  - `search_for_context(query)`, `get_by_id_for_context(patent_id)`, `count_for_context("")`로 LangChain tool에서 쓰기 좋은 JSON 문자열을 반환합니다.
- `ChromaPatentDocument`
  - `id`, `document`, `metadata`, `distance`를 담습니다.
  - `mongo_id`, `title`, `description` property로 자주 쓰는 metadata를 쉽게 읽습니다.
- `getTools`
  - `LangChain`의 `Tool` 객체 목록을 반환합니다.
  - 반환 tool 이름은 `search_kipris_patents_chroma`, `get_kipris_patent_by_id`, `count_kipris_patents_chroma`입니다.

### 사용 예시

이미 적재된 문서를 id로 조회할 때:

```python
from backend.app.tools import ChromaPatentTool

tool = ChromaPatentTool()
document = tool.get_by_id("690dc67fa424e6f6ab885b4a")

if document:
    print(document.mongo_id)
    print(document.title)
    print(document.description)
```

이미 만든 4096차원 embedding으로 검색할 때:

```python
from backend.app.tools import ChromaPatentTool

tool = ChromaPatentTool()
matches = tool.query_by_embedding(embedding, match_count=5)

for match in matches:
    print(match.distance, match.title)
```

자연어 query로 검색할 때는 embedding API 환경변수가 필요합니다.

```python
from backend.app.tools import ChromaPatentTool

tool = ChromaPatentTool.from_env()
matches = tool.query("태양전지 효율 개선", match_count=5)
```

LangChain agent에 넘길 tool 목록이 필요할 때:

```python
from backend.app.tools import getTools

tools = getTools()
```

이미 만든 `ChromaPatentTool` 인스턴스를 주입할 수도 있습니다.

```python
from backend.app.tools import ChromaPatentTool, getTools

patent_tool = ChromaPatentTool.from_env()
tools = getTools(patent_tool)
```

필수 환경변수:

```text
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.upstage.ai/v1
OPENAI_QUERY_EMBEDDING_MODEL=solar-embedding-1-large-query
```

### 검증

관련 테스트 파일: `backend/tests/test_chroma_patent_tool.py`

repo 루트에서 실행합니다.

```bash
python3 -m unittest backend/tests/test_chorma_db.py backend/tests/test_chroma_patent_tool.py
```

이 테스트는 fake 객체를 쓰지 않고 실제 `localhost:8001` ChromaDB에 접근합니다.
로컬 ChromaDB가 떠 있고 `kipris_patents_v2` migration이 완료된 상태여야 합니다.
실행하면 count, collection id, 조회된 patent id/title/source, embedding query 결과 distance를 출력합니다.

직접 확인할 때는 다음처럼 실행합니다.

```python
from backend.app.tools import ChromaPatentTool

tool = ChromaPatentTool()
print(tool.count())

document = tool.get_by_id("690dc67fa424e6f6ab885b4a")
print(document.title if document else "not found")
```
