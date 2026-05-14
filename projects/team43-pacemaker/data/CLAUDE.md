# data/ — 가상 데이터 (Supabase + 시딩용 JSON)

> **담당**: D(박영준) — `calendar_events`, `workout_records` 테이블 + 시딩 JSON. E(신승민) — `health_snapshots` 테이블 + `scenarios/` 5개 적재 주도.

실제 Google Calendar / Apple Health 연동은 **MVP 범위 외**. **단일 진실 소스는 Supabase 테이블** — `calendar.json` 등 JSON 파일은 초기 시딩 입력용이고 직접 읽지 않는다. `schemas/models.py` 모델이 Supabase 테이블 스키마와 1:1 매핑.

## 디렉토리

```
data/
├── calendar.json      # Supabase calendar_events 시딩 입력 (D)
├── health.json        # Supabase health_snapshots 시딩 입력 (E)
├── workouts.json      # Supabase workout_records 시딩 입력 (D)
├── seed.py            # Supabase에 JSON 데이터를 올리는 시딩 스크립트 (D/E)
└── scenarios/         # D/E가 정의하는 데모/테스트 시나리오 3~5개
    └── <scenario>.json
```

**Supabase 테이블**: `calendar_events`, `health_snapshots`, `workout_records`. 실제 CRUD는 Flutter → Supabase SDK, Agent → `tools/data_tools.py` → supabase-py 로 이루어짐.

## 페르소나 (기본 데이터)

> 20대 후반 백엔드 개발자. 잦은 야근으로 평일 일정이 불규칙. 스마트워치로 수면 측정. 헬스/러닝/홈트를 번갈아 하지만 매주 계획이 흔들림.

새 데이터를 추가할 때 **이 페르소나에 일관**되게 작성.

## 스키마 (schemas/models.py와 1:1 매칭)

### `calendar.json`
```json
{"start_at": "2026-05-04T09:00:00", "end_at": "...", "title": "스탠드업", "is_busy": true}
```
- `start/end`는 ISO 8601 (시간대 없음, 로컬 가정)
- `is_busy: false`는 운동 가능한 빈 시간 (점심·퇴근 후 등)

### `health.json`
```json
{"date": "2026-05-03", "sleep_hours": 7.8, "activity_minutes": 45, "resting_hr": 59}
```
- `sleep_hours`는 float, `activity_minutes`는 int (분)
- `resting_hr`은 옵셔널

### `workouts.json`
```json
{"date": "2026-05-02", "type": "헬스", "duration_min": 55, "muscles": ["어깨", "삼두"], "intensity": 3}
```
- `muscles`는 한국어 부위명 (FE 레이더 차트 라벨과 일치)
- `intensity`는 1~5

## KPI 시나리오 씨딩 (seed_scenario.py)

DB를 해당 KPI 시나리오 데이터로 초기화한 뒤 채팅 UI로 end-to-end 검증할 때 사용.

```bash
# 프로젝트 루트에서 실행
python data/seed_scenario.py <1~5>

# 예시
python data/seed_scenario.py 1   # KPI 3: 꽉 찬 일주일
python data/seed_scenario.py 3   # KPI 1+2: 충돌 0회 + 하체 회피
python data/seed_scenario.py 4   # KPI 4: 멀티턴 재조정
```

**동작**: calendar_events / health_snapshots / workout_records 전체 삭제 → 시나리오 데이터 삽입.
날짜는 실행 시점의 현재 주 월요일 기준으로 자동 조정되므로 언제 실행해도 된다.

| 번호 | 파일 | KPI | 채팅 검증 방법 |
|---|---|---|---|
| 1 | `01_full_week.json` | KPI 3 | "이번 주 운동 추천해줘" → 모든 슬롯 10분 이하인지 확인 |
| 2 | `02_sleep_deprived.json` | KPI 2a | "이번 주 운동 추천해줘" → 강도 ≤2인지 확인 |
| 3 | `03_consecutive_muscle.json` | KPI 1+2b | "이번 주 운동 추천해줘" → 일정 충돌 없음 + 하체 미포함 확인 |
| 4 | `04_multiturn.json` | KPI 4 | 1턴 추천 후 "화요일은 피곤할 것 같아" → 화요일만 변경 확인 |
| 5 | `05_free.json` | KPI 5 | "이번 주 운동 추천해줘" → 가슴·삼두 미포함 + 레이더 확인 |

> **주의**: 씨딩 후 DB에는 시나리오 데이터만 남는다. 데모용 실제 데이터가 필요하면 `seed.py`로 복원.

## scenarios/ — 데모·테스트 시나리오 (D/E)

KPI 5개 + 엣지 케이스를 시나리오 단위로 묶어 보관. 데모 시연용 + 테스트용.

각 시나리오 파일은 (예시 구조):
```json
{
  "name": "꽉 찬 일주일 → 10분 대체 루틴",
  "calendar": [...],
  "health": [...],
  "workouts": [...],
  "expected": {
    "should_propose_short_routine": true,
    "max_slot_minutes": 10
  }
}
```

권장 시나리오:
- **빈 시간 0**: 1주 내내 일정이 꽉 찬 캘린더 → 10분 대체 루틴 제안
- **수면 부족**: 평균 5시간 이하 → 강도 하향
- **연속 부위**: 같은 부위 3일 연속 → 피로도 누적 → 회피
- **멀티턴 재조정**: "화요일은 빼줘" → 해당 일자만 변경
- (자유 1개)

## 작업 시 주의

- 새 필드 추가 전엔 `schemas/models.py` 모델 수정 → Supabase 테이블 스키마 변경 → `seed.py` 반영 순서로
- 한국어 키워드(`title`, 운동명, 부위명)는 한글 유니코드 그대로 (escape 금지)
- JSON 파일은 시딩 레퍼런스. **직접 읽어서 데이터 소스로 쓰지 말 것** — Supabase에서 읽는다
- JSON 검증: `python -c "import json; json.load(open('data/<file>.json'))"` 통과해야 PR
