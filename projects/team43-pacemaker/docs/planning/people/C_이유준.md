# C — 이유준 (LangGraph Agent + Memory)

## 한 줄 책임

LangGraph Agent — prompt + graph + nodes + 체크포인터. `run_agent_stream` 진입점에서 FE 규격(`ChatChunk`)에 맞춰 SSE 청크 emit.

> **부담 분산 (D/E와 협업)**: 시스템 프롬프트 초안만 C 단독, 시나리오 케이스 제공·튜닝은 E 주도. KPI 자동화는 D/E가 시나리오 매칭 코드 짜고 C는 그래프 검증만. → C는 LangGraph 학습 + 그래프 골격에 집중.

## 주 디렉토리·파일

- `agent/graph.py` — `StateGraph` 컴파일, `run_agent`/`run_agent_stream` 진입점
- `agent/nodes.py` — think / call_tool / compose_schedule / refine. **외부 LLM 호출 단독 위치**
- `agent/prompts.py` — 시스템 프롬프트, 페르소나 톤, refine 템플릿
- `memory/` — 체크포인터 (InMemorySaver → SqliteSaver)
- `backend/api/chat.py` — B와 합의된 SSE 라우터에 `run_agent_stream` 위임

## 합의 (이미 락)

- **B와**: `ChatChunk.type` 5종 payload 키 — `schemas/CLAUDE.md` 표에 박힘. 변경 시 `[interface-change]` PR.
- **D/E와**: Tool 시그니처(`get_/create_/update_/delete_*`) — `tools/CLAUDE.md`에 박힘. LangGraph `@tool` 데코레이터로 래핑해 호출.

## 일자별 to-do

| 날짜 | 할 일 | 합격 기준 |
|---|---|---|
| **5/4 (월)** | `run_agent_stream` 더미 청크 emit (이미 구현됨) / 시스템 프롬프트 초안 (ReAct 3단계 강제 문구) | `pytest`에서 stream iterator 동작 |
| **5/5 (화)** | stub Tool 호출로 그래프 1회 실행 성공 / `tool_call` 청크 emit 시작 | 입력 → think → tool_call(stub) → done 흐름 1회 통과 |
| **5/6 (수)** | 페르소나 톤 프롬프트 완성 / 빈 시간 탐색 + 운동 매칭 로직 (스케줄 도출) | stub LLM이라도 `ScheduleProposal` 청크가 yield됨 |
| **5/7 (목)** | LangGraph 체크포인터(InMemorySaver), refine 노드, 재조정 프롬프트 | 같은 `thread_id` 두 번째 호출 시 이전 제안 기억 |
| **5/8 (금)** ★ | 실제 LLM(GPT-4o) 호출 / ReAct 3단계 로그로 검증 | end-to-end에서 진짜 GPT 응답이 청크로 도달 |
| **5/9 (토)** | 그래프 디버깅 (시나리오 매칭 코드는 D/E) | KPI 시나리오 5개 모두 통과 (`pytest -m kpi`) |
| **5/10 (일)** | 데모 멘트 페르소나 톤 일관성 / 회귀 테스트 | 데모 시연 무사고 |

## KPI 시나리오 — 본인 영향 (메인 책임)

- **1번** 일정 충돌 0회 (10회 생성)
- **2번** 피로도 높음 부위 회피 0회
- **3번** 빈 시간 0인 주에 10분 대체 루틴 제안
- **4번** 멀티턴 재조정 — refine 노드 + 체크포인터

## 자주 볼 문서·CLAUDE.md

- `agent/CLAUDE.md` ← 본인 슬라이스 (그래프 골격, ReAct, SSE 청크 의미표)
- `memory/CLAUDE.md` ← 체크포인터 패턴
- `tools/CLAUDE.md` ← D/E가 노출한 함수 시그니처 (LangGraph `@tool` 래핑)
- `schemas/CLAUDE.md` ← Pydantic 모델 + ChatChunk
- `backend/CLAUDE.md` ← `/agent/chat` 라우터 합의

## 흔한 함정

- **외부 LLM 호출은 `agent/nodes.py` 한 곳에만** — `backend/api/chat.py`나 다른 모듈에서 OpenAI 직접 호출 금지
- ReAct 3단계 강제 — 시스템 프롬프트로만 강제 (LangGraph 그래프 구조로도 강제 가능하면 더 안전)
- `run_agent`(비스트림)도 보존 — 테스트·단순 호출용
- `OPENAI_API_KEY` 없으면 명확히 에러 — silent fallback 금지
- Tool 래퍼와 순수 함수 분리: `get_calendar`(D/E) ↔ `calendar_tool`(C가 `@tool`로 래핑)
