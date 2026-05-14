# backend/ — FastAPI 게이트웨이

> **담당**: `chat.py`는 B(박장우)+C(이유준). `/data/*` REST 엔드포인트 없음 — Flutter가 Supabase 직접 호출.

## 역할

LangGraph Agent와 Flutter Web 사이의 **챗 전용** HTTP 게이트웨이. 데이터 CRUD는 Flutter가 Supabase 직접 호출 — FastAPI는 `/agent/chat` SSE와 `/health` ping만 담당.

## 엔드포인트

| Method | Path | 책임 슬라이스 | 비고 |
|---|---|---|---|
| POST | `/agent/chat` (SSE) | B/C | `agent.run_agent_stream` → `ChatChunk` 시퀀스 |
| GET | `/health` | — | 부팅 확인 ping |

## 합의 포인트 (이미 락)

- **`ChatChunk.type`별 payload**: 이미 schemas/CLAUDE.md 표에 박힘:
  - `text`: `{ "delta": "응답 토큰 일부" }`
  - `tool_call`: `{ "name": "get_calendar", "args": {...} }`
  - `proposal`: `ScheduleProposal.model_dump(mode="json")`
  - `done`: `{ "thread_id": "..." }`
  - `error`: `{ "message": "..." }`
- **CRUD**: Flutter → Supabase 직접 (FastAPI `/data/*` 엔드포인트 없음). D/E `tools/data_tools.py`는 Agent 전용 Supabase 접근 — 시그니처 락 유지.
- **CORS**: `/agent/chat` 엔드포인트만 남으므로 `localhost:*` 허용 유지.
- **변경 필요 시**: PR 제목에 `[interface-change]` 태그 + 5명 react 후 머지.

## 실행

```bash
uvicorn backend.main:app --reload
# Swagger: http://localhost:8000/docs
```

## 작업 시 주의

- 라우터 핸들러는 **얇게**. 비즈니스 로직은 `tools/`, `agent/`에. 라우터는 검증·직렬화·에러 매핑만.
- `from schemas.models import ...` 사용. 라우터에서 새 모델 정의 금지.
- 새 엔드포인트는 `[interface-change]` PR로만 추가.
- 실제 LLM 호출은 `agent/nodes.py` 한 곳에서만 (`backend/api/chat.py`에서 OpenAI 직접 호출 금지).
- `backend/api/data.py`는 더 이상 없음 — Flutter가 Supabase 직접 호출.
