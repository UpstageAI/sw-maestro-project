# MeetFlow-AI

> AI-powered meeting transcript analysis API built with LangGraph and FastAPI.

회의 전사문을 입력하면 **핵심 요약 → 결정 사항 → 다음 회의 안건**을 순차적으로 분석해 SSE 스트리밍으로 반환합니다.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI |
| AI Orchestration | LangGraph |
| LLM | Upstage Solar Pro |
| Deployment | Railway |

---

## API Endpoints

### `POST /analyze`

전사문을 분석해 모든 노드의 결과를 한 번에 반환합니다.

**Request**
```json
{
  "transcript": "회의 전사문 내용"
}
```

**Response**
```json
{
  "summary": "핵심 요약 내용",
  "decision": "결정 사항 내용",
  "agenda": "다음 회의 안건 내용"
}
```

---

### `POST /analyze/stream`

노드 작업이 완료될 때마다 SSE로 실시간 스트리밍합니다.

**Request**
```json
{
  "transcript": "회의 전사문 내용"
}
```

**Response** `text/event-stream`

```
data: {"node": "input",    "status": "active"}
data: {"node": "input",    "status": "done"}
data: {"node": "summary",  "status": "active"}
data: {"node": "summary",  "status": "done",  "content": ["...", "...", "..."]}
data: {"node": "decision", "status": "active"}
data: {"node": "decision", "status": "done",  "content": ["...", "...", "..."]}
data: {"node": "agenda",   "status": "active"}
data: {"node": "agenda",   "status": "done",  "content": ["...", "...", "..."], "complete": true}
```

---

## Graph Architecture

```
START → summary_node → decision_node → agenda_node → END
```

각 노드는 Upstage Solar Pro 모델을 호출해 독립적인 분석을 수행합니다.

---

## Getting Started

### 1. 환경 변수 설정

```bash
cp .env.example .env
```

`.env` 파일에 Upstage API 키를 입력합니다.

```env
UPSTAGE_API_KEY=your_api_key_here
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. 서버 실행

```bash
uvicorn main:app --reload
```

서버가 시작되면 `http://localhost:8000/docs`에서 Swagger UI를 확인할 수 있습니다.

---

## Deployment

Railway에 배포되어 있으며, 아래 URL에서 API를 사용할 수 있습니다.

**Base URL:** `https://meetflow-ai-production.up.railway.app`

- Swagger UI: `https://meetflow-ai-production.up.railway.app/docs`
