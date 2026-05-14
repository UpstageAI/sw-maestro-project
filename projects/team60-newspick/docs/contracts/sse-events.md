# SSE 이벤트 계약

> Spring 의 `/api/refresh-stream`, `/api/chat-stream` 과 Python 의 `/refresh-stream`, `/chat-stream` 은 **동일한** 이벤트 스키마를 사용한다 (Spring 은 단순 프록시).

## 이벤트 종류

| 이벤트 명 | 출현 위치 | 데이터 형식 |
|---|---|---|
| `step` | refresh-stream | `{ step: "collect" \| "summarize", current: number, total: number }` |
| `warn` | refresh-stream | `{ step: string, message: string }` |
| `done` | refresh-stream | `{ articleIds: string[] }` |
| `done` | chat-stream | `{ articles?: ArticleCardSummary[] }` (`docs/contracts/json-schemas/article-card-summary.json`) |
| `token` | chat-stream | `{ token: string }` |
| `error` | both | `{ code: string, message: string }` |

## 예시

### refresh-stream

```
event: step
data: {"step":"collect","current":0,"total":12}

event: step
data: {"step":"collect","current":7,"total":12}

event: step
data: {"step":"collect","current":12,"total":12}

event: step
data: {"step":"summarize","current":0,"total":8}

event: warn
data: {"step":"summarize","message":"article 5: review_required"}

event: step
data: {"step":"summarize","current":8,"total":8}

event: done
data: {"articleIds":["article_001","article_002","..."]}
```

### chat-stream

```
event: token
data: {"token":"오픈"}

event: token
data: {"token":"AI는 "}

event: token
data: {"token":"최근 "}

event: done
data: {"articles":[{"id":"article_001","title":"...","source":"...","publishedAt":"..."}]}
```

## ArticleCardSummary

chat-stream의 `done.articles` item은 `docs/contracts/json-schemas/article-card-summary.json`을 따른다. 필수 필드는 다음 4개로 고정한다.

- `id`: 기사 상세 route에 사용하는 article id
- `title`: 참고 기사 카드에 표시할 제목
- `source`: 언론사 또는 출처명
- `publishedAt`: ISO-8601 date-time 문자열

`content`, `summary`, `score`는 chat-stream done article card payload에 포함하지 않는다.

## 계약 보장

- 이벤트 이름은 위 6종 외에 추가하지 않는다 (계약 깨짐).
- 데이터는 항상 valid JSON.
- `done` 이벤트가 도달하면 클라이언트는 `EventSource.close()`.
- `error` 이벤트가 도달하면 클라이언트는 사용자에게 에러 표시 후 close.
- 서버는 60초 이상 idle 시 `: keepalive\n\n` (SSE comment) 로 연결 유지.

## 트랙별 책임

- **AI**: Python `/refresh-stream`, `/chat-stream` 엔드포인트가 위 스키마대로 이벤트 발행.
- **BE**: Spring 이 Python SSE 를 그대로 프록시. 스키마 변형 X.
- **FE**: `EventSource` 로 위 6종 이벤트만 listener 등록. `addEventListener("message", ...)` 같은 익명 이벤트는 무시.

> 본 문서는 `docs/architecture/realtime-ui-states.md` 와 정합한다. 두 문서가 어긋나면 본 문서가 우선 (계약).
