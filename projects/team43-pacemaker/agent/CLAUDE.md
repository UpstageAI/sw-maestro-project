# agent/ — LangGraph Agent

> **담당**: C(이유준). graph + nodes + prompts 단독.

## 파일 분담

- **`graph.py`** — `StateGraph` 정의, 노드 연결, 컴파일, **진입점 두 개**:
  - `run_agent(user_input, session_state) -> AgentResponse` (비스트림 — 테스트·단순 호출용)
  - `run_agent_stream(user_input, thread_id) -> AsyncIterator[ChatChunk]` (FastAPI `/agent/chat` SSE)
- **`nodes.py`** — 개별 노드 함수 (think / call_tool / compose_schedule / refine), **외부 LLM 호출은 여기에만**
- **`prompts.py`** — 시스템 프롬프트 (ReAct 강제), 페르소나 톤, 멀티턴 재조정 템플릿

다른 모듈에서 OpenAI/LLM을 직접 호출하지 말 것. 전부 `nodes.py`로 라우팅.

## ReAct 강제 패턴

시스템 프롬프트로 다음 3단계를 **반드시 순서대로** 거치게 강제:

1. `get_calendar` — 사용자 일정 확인
2. `get_health` — 최근 수면·활동량 확인
3. `get_workouts` — 최근 운동 기록 확인

위 단계 결과만 근거로 `ScheduleProposal`을 도출 (환각 방지).

## 그래프 골격 (예시)

```
[user_input]
    ↓
[think] ─→ tool 호출 필요? ─yes→ [call_tool] → [think]
    ↓ no
[compose_schedule] → ChatChunk(proposal) → ChatChunk(done)
```

수정 요청 시:
```
[user_input(피드백)] → [refine] → 변경된 ScheduleProposal
```

## SSE 스트림 규약 (B와 합의)

`run_agent_stream`이 yield하는 `ChatChunk.type`별 의미:

| type | 언제 |
|---|---|
| `text` | LLM 토큰 단위 응답 (delta 누적은 FE가 처리) |
| `tool_call` | Tool 호출 시작 알림 (FE가 "캘린더 확인 중…" 노출) |
| `proposal` | `ScheduleProposal` 완성 (FE가 카드/그래프 갱신) |
| `done` | 세션 종료 (`thread_id` 포함) |
| `error` | 실패 (FE가 에러 토스트) |

payload 상세는 `schemas/CLAUDE.md` 참고.

## 메모리

LangGraph 체크포인터는 `memory/` 모듈에서 정의. `graph.py`에서 컴파일할 때 `checkpointer=...` 인자로 주입. 멀티턴 동안 동일 `thread_id`로 호출.

## stub → 실구현 순서

- 5/4: `run_agent_stream`이 더미 청크 yield (이미 구현됨)
- 5/5: stub Tool 호출로 그래프 1회 실행, `tool_call` 청크 emit
- 5/6: 실제 LLM 호출, 실제 Tool 연결, `ScheduleProposal` 도출
- 5/7: 멀티턴 메모리, refine 노드 추가
- 5/8: 통합 테스트 (FastAPI ↔ Flutter 까지)

## 작업 시 주의

- 한 노드 = 한 책임 (조건 분기는 conditional edge로 빼기)
- 노드 함수의 입력/출력 dict 키는 명확히 명명 (`messages`, `tool_calls`, `proposal` 등)
- LLM 호출은 `langchain_openai.ChatOpenAI`, 모델은 `gpt-4o`
- API 키는 `os.getenv("OPENAI_API_KEY")`로 읽고, 없으면 명확히 에러
- FE가 받을 청크 포맷이 바뀌면 B와 PR 코멘트로 합의 후 `schemas/CLAUDE.md` 같이 수정 (`[interface-change]` 태그 + 5명 react)
