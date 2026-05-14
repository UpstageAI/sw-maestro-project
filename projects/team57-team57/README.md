# Review Agent

소상공인 리뷰 응대 및 반복 불만 분석 AI Agent의 MVP 구현 프로젝트입니다.

현재는 3단계까지 구현되어 있으며, 아래 항목이 포함되어 있습니다.

- 프로젝트 기본 구조
- SQLite 스키마 및 초기화 로직
- Repository 계층
- Mock LLM provider
- 샘플 리뷰 데이터
- README 및 문서 초안
- LangGraph 기반 Agent node/edge 실행
- Streamlit 단일 페이지 UI
- 답글 수정 및 피드백 저장

## 프로젝트 소개

이 프로젝트는 소상공인이 리뷰를 붙여넣으면 리뷰를 구조화해 저장하고, 이후 Agent가 감정 분석, 유형 분류, 답글 생성, 반복 불만 분석까지 이어서 수행할 수 있도록 설계된 MVP입니다.

이번 과제의 핵심은 상용 서비스 완성도가 아니라 다음 Agent 구성 요소를 직접 구현하고 설명 가능한 형태로 남기는 것입니다.

- node / edge
- tool calling
- state
- memory
- persistence
- feedback loop

현재는 mock provider 기반 Agent 플로우와 Streamlit 데모 UI까지 연결된 상태입니다.

## 실행 방법

### 1. uv 사용

```bash
uv sync
```

### 2. 앱 실행

현재 `make run`은 Streamlit UI를 실행합니다.

```bash
make run
```

또는

```bash
uv run streamlit run app.py
```

LangGraph 데모 실행:

```bash
uv run python run_graph_demo.py --scenario both --reset-db
```

또는 `uv`가 없으면

```bash
python3 run_graph_demo.py --scenario both --reset-db
```

### 3. Streamlit 실행

현재 `app.py`는 단일 페이지 Streamlit UI입니다.

```bash
uv run streamlit run app.py
```

## 환경변수 설정

`.env.example`를 복사해 `.env`를 생성하세요.

```bash
cp .env.example .env
```

provider 우선순위:

1. `ANTHROPIC_API_KEY`
2. `OPENAI_API_KEY`
3. 키가 없으면 `MockProvider`

현재도 API 키가 없으면 `MockProvider`가 기본 동작합니다.

## Agent 구조 설명

### State

현재 `ReviewAgentState`는 아래 필드를 포함합니다.

- `store_id`
- `session_id`
- `raw_input_text`
- `parsed_reviews`
- `store_context`
- `classified_reviews`
- `drafted_replies`
- `saved_review_ids`
- `pattern_summary`
- `checklist`
- `execution_log`
- `warnings`
- `errors`

### Node

구현된 LangGraph node 구성:

1. `InputParserNode`
2. `ContextLoaderNode`
3. `ClassifierAgentNode`
4. `ReplyDrafterAgentNode`
5. `PersistenceToolNode`
6. `PatternAgentNode`
7. `ChecklistAgentNode`

### Edge

구현된 기본 흐름:

`InputParserNode -> ContextLoaderNode -> ClassifierAgentNode -> ReplyDrafterAgentNode -> PersistenceToolNode -> PatternAgentNode -> ChecklistAgentNode -> END`

### Tool Calling

SQLite 저장/조회 동작은 tool-like function 형태로 분리했습니다.

- `load_store_context_tool`
- `load_recent_feedback_tool`
- `save_reviews_tool`
- `load_negative_review_patterns_tool`

### Memory

메모리는 SQLite 기반으로 설계됩니다.

- 매장 컨텍스트 저장
- 리뷰 분석 결과 누적
- 사장님 수정 답글 저장
- 피드백 이벤트 저장

### Feedback Loop

사용자가 수정한 답글은 `feedback_events` 및 `reviews.edited_reply`에 저장되고, 다음 실행 시 최근 수정 예시로 다시 주입됩니다.

## 데모 시나리오

상세 시나리오는 [docs/demo_scenarios.md](/Users/parksewon/Documents/New%20project%202/review-agent/docs/demo_scenarios.md) 에 정리했습니다.

## 데모 영상 촬영 가이드

### 어떤 화면을 먼저 보여줄지

- 먼저 사이드바의 매장 컨텍스트 영역을 보여줍니다.
- 그다음 `데모 모드 초기화` 버튼으로 샘플 매장과 누적 리뷰 memory를 준비합니다.
- 이후 메인 영역의 리뷰 입력 박스와 샘플 리뷰 버튼을 보여줍니다.

### 어떤 버튼을 누를지

1. `데모 모드 초기화`
2. `샘플 리뷰 A 불러오기` 또는 `샘플 리뷰 B 불러오기`
3. `분석 시작`
4. 리뷰별 `수정 답글 저장`

### 백엔드 동작은 어떤 패널에서 확인할지

- `Agent 실행 흐름` 영역에서 node 순서를 설명합니다.
- `백엔드 실행 로그` 패널에서 node별 입력/출력 요약, 실행 시간, DB 저장 여부를 설명합니다.
- 사이드바의 `개발자 확인용 DB 상태` expander에서 실제 DB 저장 결과를 확인합니다.

### 프론트엔드 구성은 어떤 영역으로 설명할지

- 사이드바: 매장 컨텍스트 입력/수정
- 메인 상단: 리뷰 붙여넣기, 샘플 리뷰 버튼, 분석 시작 버튼
- 중간: 요약 카드, 반복 불만 TOP 3, 개선 체크리스트
- 하단: 리뷰별 결과, 답글 수정 입력란, 실행 로그, 백엔드 실행 로그

### Agent의 node, edge, tool calling, memory를 영상에서 어떻게 설명할지

- node:
`Agent 실행 흐름`과 `백엔드 실행 로그`에서 `InputParserNode`부터 `ChecklistAgentNode`까지 순서대로 설명합니다.
- edge:
`분석 시작` 클릭 후 node가 다음 node로 이어지는 흐름을 보여주며 edge를 설명합니다.
- tool calling:
`PersistenceToolNode`와 `ContextLoaderNode`가 DB tool-like function을 호출하는 구조를 설명합니다.
- memory:
`데모 모드 초기화` 후 누적 리뷰가 seed되고, `PatternAgentNode`가 이를 다시 조회하는 장면으로 설명합니다.
- feedback loop:
답글을 수정 저장한 뒤 다음 분석에서 최근 수정 답글 샘플 수가 반영되는 장면으로 설명합니다.

## In-scope / Out-of-scope

### In-scope

- SQLite 기반 persistence
- Mock 기반 전체 플로우 검증 가능 구조
- LangGraph 확장 가능한 node 분리 구조
- Streamlit 단일 페이지 앱으로 확장 가능한 프로젝트 구조

### Out-of-scope

- 외부 리뷰 플랫폼 API 연동: 확장 예정
- 자동 답글 발행: 확장 예정
- 관리자/권한 체계: 확장 예정
- 정교한 통계 대시보드: 확장 예정

## 발표 때 설명할 포인트

### 이 서비스에서 Agent라고 볼 수 있는 이유

- 입력 리뷰를 파싱하고
- 매장 컨텍스트를 불러오고
- 분류와 답글 생성을 수행하고
- 누적 데이터를 저장하고
- 다음 실행에 피드백을 반영하는 순차적 의사결정 흐름이 있기 때문입니다.

### 어떤 node가 어떤 역할을 하는지

node별 역할은 [docs/agent_architecture.md](/Users/parksewon/Documents/New%20project%202/review-agent/docs/agent_architecture.md) 에 정리했습니다.

### tool calling이 어디에 들어가는지

DB 저장/조회와 안전 필터 함수를 tool-like function으로 분리해 Agent node에서 호출하도록 설계합니다.

### memory가 어떻게 동작하는지

SQLite의 `stores`, `review_sessions`, `reviews`, `feedback_events`가 각각 장기 기억 저장소 역할을 담당합니다.

### 피드백이 어떻게 다음 답글에 반영되는지

사용자 수정 답글을 저장하고 최근 수정 이력을 다시 prompt 예시에 주입하는 방식으로 반영합니다.

## 현재 구현 범위

현재 완료 기준:

- DB 초기화 가능
- Repository CRUD 가능
- 샘플 리뷰 로드 가능
- Mock provider 응답 가능
- LangGraph graph를 mock provider로 end-to-end 실행 가능
- Streamlit UI에서 리뷰 분석, 결과 확인, 답글 수정 저장 가능
