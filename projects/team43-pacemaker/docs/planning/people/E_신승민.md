# E — 신승민 (CRUD health + scenarios 5개 + 프롬프트 튜닝 주도)

## 한 줄 책임

health CRUD 4개 + `data/scenarios/` 5개 시나리오 적재 주도 + `agent/prompts.py` 튜닝 주도 (C와 협업).

> 도메인 분담 확정: D = calendar + workouts, **E = health + scenarios + 프롬프트 튜닝 주도**.

## 주 디렉토리·파일

- `tools/data_tools.py` — `get_/create_/update_/delete_health_snapshot` (CRUD 4개)
- `data/health.json` — 데모 페르소나 컨디션 데이터
- `data/scenarios/*.json` — **5개 시나리오 적재 주도** (KPI 1~5 모두)
- `agent/prompts.py` — **튜닝 주도** (C가 골격 작성, E가 시나리오 케이스 보면서 다듬음)
- `backend/api/data.py` — health 라우터(현재 501 stub)에 위임 채우기

## 합의 (이미 락)

- **C와**: Tool 시그니처 — `tools/CLAUDE.md`에 박힘. schemas/models.py와 1:1.
- **D와**: 도메인 분담 확정 (D=calendar/workouts, E=health). 시나리오 매칭 코드는 KPI 번호로 분담 (E=2·4·5, D=1·3).
- **A와**: `/data/health` REST 응답 = Tool 반환값 그대로 (Pydantic 모델).
- 변경 필요 시: `[interface-change]` PR + 5명 react.

## 일자별 to-do

| 날짜 | 할 일 | 합격 기준 |
|---|---|---|
| **5/4 (월)** | `data/health.json` 더미 5건 + `tools.get_health` JSON 파싱 1차 / 시나리오 5종 이름·개요 메모 | `pytest`에서 1주 범위 호출 시 리스트 반환 |
| **5/5 (화)** | `get_health` 완성 + `create_health_snapshot` write 1개 / Swagger에서 GET /data/health 200 검증 | `POST /data/health`로 새 스냅샷 추가 |
| **5/6 (수)** | `update_/delete_health_snapshot` 마무리 / 1주치 더미 데이터 보강 (수면 부족 케이스) | health CRUD 4종 모두 200/204 |
| **5/7 (목)** | `data/scenarios/` 5개 파일 적재 (full_week, sleep_deprived, consecutive_muscle, multiturn, free 1개) | scenarios/ 5개 파일 존재, 입력+기대응답 명시 |
| **5/8 (금)** ★ | write Tool atomic 갱신 / 시나리오 데이터로 end-to-end 검증 + C와 프롬프트 1차 튜닝 | health 변경이 agent 응답에 반영, 시나리오 1개라도 통과 |
| **5/9 (토)** | KPI 2·4·5 시나리오 매칭 코드 (`pytest -m kpi`) — D와 분담 / 프롬프트 본격 튜닝 (C와) | `pytest -m kpi` 2·4·5번 통과 |
| **5/10 (일)** | 데모용 health 데이터 + 시나리오 5개 최종 점검 (페르소나 톤) | 데모 시연 무사고 |

## KPI 시나리오 — 본인 영향 (시나리오 운영 주도)

- **2번** 피로도 높음 회피 — health + workouts 누적 (D와 공동 데이터, E가 시나리오 매칭)
- **4번** 멀티턴 재조정 — `scenarios/multiturn.json`
- **5번** 추천 부위와 레이더 일치 — proposal 데이터 검증
- (1·3번은 D 주도, E는 시나리오 데이터 형식만 가이드)

## 프롬프트 튜닝 주도

- C가 5/4에 시스템 프롬프트 골격 작성
- E가 5/8 통합 후 실제 응답을 보면서 다듬음 (페르소나 톤, 강도 하향, 변경 사유 멘트 등)
- 변경은 PR로, C 리뷰 필수

## 자주 볼 문서·CLAUDE.md

- `tools/CLAUDE.md` ← 본인 슬라이스 (CRUD 시그니처, atomic write)
- `data/CLAUDE.md` ← scenarios/ 구조 + 페르소나
- `schemas/CLAUDE.md` ← Pydantic 모델 (`HealthSnapshot`)
- `agent/CLAUDE.md` + `agent/prompts.py` ← 튜닝 대상
- `backend/CLAUDE.md` ← `/data/*` 라우터 위임 패턴

## 흔한 함정

- `tools/data_tools.py`는 D와 같이 만짐 → **함수 단위 PR**로 쪼갬 (PR 제목에 `[tools] create_health_snapshot 구현`)
- write는 read-modify-write — 동시성 걱정 없지만 atomic하게 (임시 파일 → `os.replace`)
- `resting_hr`은 옵셔널 — 없는 경우 처리
- 새 필드 추가는 `[interface-change]` PR (`schemas/models.py` 먼저 수정 + 5명 react)
- 시나리오 5개 적재는 단순 데이터 작업이지만 **기대 응답까지 명시**해야 함 (없으면 매칭 코드 짤 수 없음)
