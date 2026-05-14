# ADR-0007: 일기 영속화 모델 — 즉시 영속 + 두 테이블 분리

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

기획 §1: 한 일기 작성 세션에서 **재생성 최대 3회** (1차 + 재생성 3 = 총 4번 생성). 사용자가 1개를 선택해 채택, 나머지는 버림.

영속화의 두 모델:

- **X — 임시 캐시 + 채택본 영속**: 시도들은 Redis/Postgres temp row에 임시 저장, 채택 시 promote. cleanup job 필요.
- **Y — 모든 generation 즉시 영속**: 모든 시도가 즉시 DB에 저장. 채택은 표시일 뿐.

채택 표시 sub-옵션:
- Y-1: 단일 테이블 + `is_adopted` 플래그
- Y-2: `diaries`(채택본) / `diary_generations`(시도·운영 메타) 두 테이블

## Decision

### Y — 즉시 영속

모든 generation을 `diary_generations`에 즉시 INSERT. 임시 저장소 없음.

자동 safety retry로 인한 내부 재시도는 **DB에 영속하지 않고** LangGraph state에만 머문다. 통과한 결과 1개만 row가 됨.

### Y-2 — 두 테이블 분리

- `diary_generations`: 모든 시도 + **입력 snapshot** (`photo_path`, `keywords`, `honorific_used`, `species_used`, `regen_feedback`) + **vision 산출 echo** (`vision_description`, 2026-05-05 추가 — 같은 session 내 regenerate 시 vision LLM skip 위해 매 row echo, 컬럼 정의는 ADR-0010, graph 분기는 ADR-0005 부록 2026-05-05). 운영 메타 (token / cost / trace_id)는 LangSmith trace로 보존 (ADR-0012). DB는 입력/출력 snapshot만 영속.
- `diaries`: 채택본의 사용자 데이터(`diary_text`, `short_caption`, `mood_tag`, `photo_path`, `pet_id`, `owner_id`, `diary_date`). `source_generation_id` FK로 어느 시도가 채택됐는지 역참조.

## Rationale

### Y 채택 근거
1. 인프라 컴포넌트 ↓ — Redis/cleanup job 불필요.
2. **단일 진실 소스** — 카운트 enforce를 DB 한 곳에서. 임시-영속 일관성 버그 클래스 제거.
3. **관측성 무료** — 모든 시도의 token/cost/trace_id 자동 보존.
4. **프롬프트 평가 데이터** — 버려진 시도까지 보존 → 프롬프트 튜닝의 진짜 데이터.

### Y-2 채택 근거
1. **의미적 정합** — 사용자 콘텐츠와 운영 메타는 다른 종류의 데이터.
2. **피드 쿼리 단순** — `SELECT * FROM diaries`만으로 끝.
3. **RLS 정책 단순** — `diaries`는 owner-bound, `diary_generations`은 운영 관점.
4. **2차 기능(텍스트 편집·SNS 공유)** 시 `diaries`만 만지면 됨.

## Alternatives Considered

### X (임시 캐시 + 채택본 영속)
- **탈락 이유**: 인프라 +1, 일관성 부담, 관측성·평가 데이터 손실. MVP 가치 ↓.

### Y-1 (단일 테이블 + 플래그)
- **탈락 이유**: 운영 메타와 사용자 콘텐츠 컬럼 혼재 → RLS·SELECT 작성 시 컬럼 노출 신경. 피드 쿼리에 항상 `is_adopted=true` 강제.

## Consequences

### Pros
- 인프라 단순 (DB만).
- 모든 시도 trace·비용 자동 영속.
- 데이터 모델 의미 분리 명확.

### Cons
- DB row 누적 (사이드 프로젝트 규모에선 무시 가능 — 일 8회 × 사용자수).
- 채택 변경(MVP 미지원) 시 `diaries` row 교체 필요.

### 후속 조치
- 마이그레이션: `diaries`, `diary_generations` 두 테이블 + RLS.
- DB row 누적 부담 시점 도래 시 90일 후 `diary_generations` cleanup job 추가 (현재 미적용).
