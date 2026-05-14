# schemas/ — 공통 데이터 모델

> **담당**: 전원이 import. 변경은 `[interface-change]` PR로만 (5명 react 후 머지).

## 역할

5개 슬라이스(A~E)의 **인터페이스 계약**. 모든 모듈은 `from schemas.models import ...`로 import한다. 이 파일이 바뀌면 전원의 코드가 영향받으므로 단독 결정 금지.

**Supabase 테이블 매핑**: `CalendarEvent` → `calendar_events`, `HealthSnapshot` → `health_snapshots`, `WorkoutRecord` → `workout_records`. Python 쪽은 `Model.model_validate(row)`, Flutter 쪽은 `fromJson(row)` 로 변환.

## 모델 (Pydantic v2)

### 도메인 모델

| 모델 | 용도 | 생성/소비 |
|---|---|---|
| `CalendarEvent` | 사용자 일정 1건 | `tools.get_calendar` → Agent / FE 카드 |
| `HealthSnapshot` | 1일치 수면·활동량·HR | `tools.get_health` → Agent / FE 카드 |
| `WorkoutRecord` | 과거 운동 1건 | `tools.get_workouts` → Agent / FE 카드 |
| `WorkoutSlot` | 추천 운동 1건 | Agent → FE |
| `MuscleFatigueState` | 1일치 부위별 피로도 | Agent → FE 레이더 차트 |
| `ScheduleProposal` | 슬롯 + 피로도 타임라인 묶음 | Agent → FE |
| `AgentResponse` | (비스트림) 챗 응답 + 제안 | 테스트·단순 호출용 |

### API 모델 (FastAPI ↔ Flutter Web)

| 모델 | 용도 |
|---|---|
| `ChatRequest` | `POST /agent/chat` 요청 본문 |
| `ChatChunk` | `POST /agent/chat` SSE 스트림 청크 1개 |

`ChatChunk.type`별 `payload` 스키마 (이미 락 — 변경은 `[interface-change]` PR로):

| type | payload |
|---|---|
| `text` | `{ "delta": "응답 토큰 일부" }` |
| `tool_call` | `{ "name": "get_calendar", "args": { ... } }` |
| `proposal` | `ScheduleProposal.model_dump(mode="json")` |
| `done` | `{ "thread_id": "..." }` |
| `error` | `{ "message": "..." }` |

## 변경 절차

1. PR 제목에 `[interface-change]` 태그 + 변경 이유를 PR 설명에 (왜 필요한지)
2. `models.py` + 영향받는 모든 호출부를 **하나의 PR**에 묶어 수정
3. **5명 모두 react** 후 머지, 머지 직후 팀 채널 공지

## 작업 시 주의

- `Field(ge=, le=)`로 범위 제약을 모델에 박아두기 — 호출 측에서 검증 안 해도 됨
- `int | None = None`처럼 PEP 604 union 사용 (Python 3.11+)
- 새 필드는 **기본값 있는 옵셔널**로 추가하면 호환성 유지에 좋음
- 직렬화 출력은 `model.model_dump(mode="json")` 사용 (Flutter Web의 JSON 디코더 호환)
- API 모델(요청/응답·SSE 청크)도 여기에 정의. backend/api/ 라우터는 import만.
