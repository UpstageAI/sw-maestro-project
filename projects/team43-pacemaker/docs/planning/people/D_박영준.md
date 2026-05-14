# D — 박영준 (CRUD calendar + workouts + Tech Lead)

## 한 줄 책임

calendar + workouts CRUD Tool 8개 + FastAPI 라우터 위임. **Tech Lead** — 매일 EOD에 main 동작 점검.

> 도메인 분담 확정: **D = calendar + workouts**, E = health + scenarios 5개 + 프롬프트 튜닝 주도.

## 주 디렉토리·파일

- `tools/data_tools.py` — `get_/create_/update_/delete_calendar_event` + `_workout` (CRUD 8개)
- `data/calendar.json`, `data/workouts.json` — 데모 페르소나 데이터 (Supabase 시딩 입력용)
- (Tech Lead 부수업) main 일일 점검, 통합 디버깅 보조

## 합의 (이미 락)

- **C와**: Tool 시그니처 — `tools/CLAUDE.md`에 박힘. schemas/models.py와 1:1.
- **A와**: `/data/*` REST 응답 = Tool 반환값 그대로 (Pydantic 모델).
- 변경 필요 시: `[interface-change]` PR + 5명 react.

## 일자별 to-do

| 날짜 | 할 일 | 합격 기준 |
|---|---|---|
| **5/4 (월)** | `data/calendar.json` 더미 5건 + `tools.get_calendar` JSON 파싱 1차 / **(Tech Lead)** 5명 PR 머지 상태 EOD 점검 | `pytest`에서 1주 범위 호출 시 리스트 반환 |
| **5/5 (화)** | `get_calendar` 완성 + `tools.get_workouts` Supabase 연결 + `create_calendar_event` write 1개 | Supabase에 새 이벤트 추가 확인 |
| **5/6 (수)** | `update_/delete_calendar_event` + `_workout` CRUD 일부 / 1주치 더미 데이터 보강 (충돌·빈시간 케이스) | calendar/workouts 모두 4종 CRUD 200/204 |
| **5/7 (목)** | calendar/workouts CRUD 마무리 / Tech Lead — A·B·C·E 슬라이스 진행률 점검 (PR 리뷰 밀린 것 핑) | 본인 8 CRUD 모두 동작 / 팀 PR 정체 0 |
| **5/8 (금)** ★ | write Tool atomic 파일 갱신 (임시 파일 → `os.replace`) / B의 F7 호출 검증 / Tech Lead — 통합 디버깅 보조 | 등록 버튼 → `calendar.json` 무손실 갱신, end-to-end 1회 성공 |
| **5/9 (토)** | KPI 1·3 시나리오 매칭 코드 (`pytest -m kpi`) — E와 분담 / 프롬프트 튜닝 보조 | `pytest -m kpi` 1·3번 통과 |
| **5/10 (일)** | 데모용 calendar/workouts 데이터 최종 점검 / Tech Lead — `git tag v1.0-demo` push | 데모 시연 무사고 |

## KPI 시나리오 — 본인 영향

- **1번** 일정 충돌 — calendar 데이터 품질 + 시나리오 매칭 코드 (E와 분담)
- **3번** 빈 시간 0 주 — calendar 시나리오 데이터 + 매칭 코드
- **연속 부위** workouts 데이터 (피로도 누적 검증용)

## Tech Lead 책임

- 매일 EOD에 `git pull && uvicorn backend.main:app --reload && pytest`로 main 동작 점검
- 팀 PR 정체 시 팀 채널에 핑 (영업시간 기준 4시간 넘으면)
- 5/8 통합일 디버깅 보조 (FastAPI ↔ Agent ↔ Tool 흐름 점검)
- 5/10 `git tag v1.0-demo` 생성 + push

## 자주 볼 문서·CLAUDE.md

- `tools/CLAUDE.md` ← 본인 슬라이스 (CRUD 시그니처, atomic write)
- `data/CLAUDE.md` ← scenarios/ 구조 + 페르소나
- `schemas/CLAUDE.md` ← Pydantic 모델 (`CalendarEvent`, `WorkoutRecord`)
- `backend/CLAUDE.md` ← FastAPI 구조 (Flutter는 Supabase 직접 호출, Agent만 tools/ 경유)
- `agent/CLAUDE.md` ← C가 어떻게 Tool을 호출하는지 (`@tool` 래퍼)

## 흔한 함정

- `tools/data_tools.py`는 E와 같이 만짐 → **함수 단위 PR**로 쪼갬 (PR 제목에 `[tools] create_calendar_event 구현`)
- write는 read-modify-write — 동시성 걱정 없지만 atomic하게 (임시 파일 → `os.replace`)
- 한국어 키워드(부위명, title) escape 금지 — JSON 한글 그대로
- 새 필드 추가는 `[interface-change]` PR (`schemas/models.py` 먼저 수정 + 5명 react)
- "유저가 FE에서 보는 모든 데이터는 agent도 본다" — A 화면에 새 필드 추가하려면 D/E도 Tool 추가 필수
- Tech Lead 점검 부담 = 매일 ~10분이면 충분. 무거운 코드 작업 시간 잡아먹지 말 것
