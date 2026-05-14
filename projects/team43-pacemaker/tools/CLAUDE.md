# tools/ — Agent 데이터 Tool (CRUD)

> **담당**: D(박영준) — calendar + workouts (CRUD 8개). E(신승민) — health (CRUD 4개) + 시나리오·프롬프트 튜닝 주도.
> 같은 파일(`data_tools.py`)을 둘이 만지므로 **함수 단위 PR**로 쪼개기.

## 원칙

> 유저가 FE에서 보는 모든 데이터는 agent도 그대로 본다. (`docs/planning/plan.md`)

→ A의 화면에 뜨는 모든 항목에는 read+write Tool이 모두 노출되어야 함.
→ FastAPI 라우터(`backend/api/data.py`)는 이 Tool들에 얇게 위임.

## 시그니처 (락)

```python
# Read
def get_calendar(start: date, end: date) -> list[CalendarEvent]: ...
def get_health(start: date, end: date)   -> list[HealthSnapshot]: ...
def get_workouts(start: date, end: date) -> list[WorkoutRecord]: ...

# Write — calendar 패턴, health/workouts 동일
def create_calendar_event(event: CalendarEvent) -> CalendarEvent: ...
def update_calendar_event(event_id: str, patch: dict) -> CalendarEvent: ...
def delete_calendar_event(event_id: str) -> None: ...
```

`[start, end]`는 양 끝 포함. Supabase 테이블에서 읽고 쓴다 (Agent 전용 접근 — Flutter는 Supabase SDK 직접 호출).

## 구현 가이드

- 파일 경로는 `pathlib.Path(__file__).parent.parent / "data" / "..."` 같은 상대 위치로 (CWD 의존 X)
- 파싱은 Pydantic의 `Model.model_validate(dict)` 사용 — 타입 안전
- 빈 결과는 빈 리스트 `[]`. None 반환 금지.
- 날짜 비교는 `event.start_at.date()` 같이 `date` 타입으로 통일
- write는 read-modify-write로 atomic하게 (임시 파일 → 원자적 rename 권장)

## LangGraph Tool 등록

5/6 이후 LangGraph 노드에서 호출할 때는 `@tool` 데코레이터로 감싼 래퍼를 별도로 둔다:

```python
from langchain_core.tools import tool

@tool
def calendar_tool(start: str, end: str) -> list[dict]:
    """이번 주 사용자 캘린더를 조회한다."""
    events = get_calendar(date.fromisoformat(start), date.fromisoformat(end))
    return [e.model_dump(mode="json") for e in events]
```

순수 함수(`get_calendar`)와 LLM용 래퍼(`calendar_tool`)는 **반드시 분리**. 테스트는 순수 함수 기준으로 작성.

## 시나리오·프롬프트 튜닝 (D/E 추가 책임)

`docs/planning/plan.md` D/E 항목의 추가 책임:
- **유저 시나리오 정의** (3~5개) — `data/scenarios/*.json`에 입력 데이터 + 기대 응답 적재
- **테스트 데이터** — `data/scenarios/`로 격리. 기본 `data/*.json`은 데모 페르소나용.
- **프롬프트 깎기** — 시나리오가 잘 동작하도록 `agent/prompts.py` 튜닝 (C와 협업)

## 협업 룰

- PR 제목에 `[tools] create_calendar_event 구현` 식으로 자기 함수 명시
- 같은 파일 동시 수정이 필요한 PR이 두 개 이상이면 PR 코멘트로 머지 순서 합의
- import 추가는 알파벳 정렬 유지
