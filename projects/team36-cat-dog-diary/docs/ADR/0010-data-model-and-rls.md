# ADR-0010: 데이터 모델과 RLS 정책 — 5 테이블 + β 단일 패턴

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

ADR-0006 (β JWT forward), ADR-0007 (Y-2 영속화), ADR-0008 (BFF API), ADR-0009 (사진 업로드) 결정 위에서 실제 테이블·컬럼·RLS를 정의해야 한다. DESIGN.md §1·§재생성 입력 모델·§사용자 정보 기획으로부터 입출력 스펙도 반영.

## Decision

**5 테이블 + 1 Storage bucket. 모든 테이블 RLS = `auth.uid() = owner_id` 단일 패턴.**

| # | 테이블 | 역할 |
|---|---|---|
| 1 | `profiles` | 사용자 닉네임 (auth.users 1:1) |
| 2 | `pets` | 펫 프로필 (다견 가능, soft delete) |
| 3 | `diaries` | 채택된 일기 (immutable, hard delete) |
| 4 | `diary_generations` | 모든 생성 시도 감사 로그 |
| 5 | `usage_quotas` | 일일 신규 한도 카운터 |
| – | Storage `pet-photos` | 사진. path-based RLS |

## Rationale

### 공통 결정
- **모든 owner FK = `auth.users(id)` 직접 참조** + ON DELETE CASCADE. profiles 외 별도 사용자 테이블 없음.
- **모든 테이블에 `owner_id` denormalize** — RLS 한 줄 + join 없는 query.
- **β 정합** — 사용자 JWT로 supabase-js 호출 → `auth.uid()` 자동 채워짐 → RLS 통과. service_role 키 사용 0.

### 테이블별

#### profiles
- `id`(PK, FK→auth.users), `display_name`(1~24자, trim), `created_at`, `updated_at`.
- **trigger `on_auth_user_created`** — 가입 즉시 자동 row 생성. `display_name = coalesce(raw_user_meta_data->>'name', email local-part)`.
- 이메일 컬럼 미도입 — `auth.users.email`을 클라이언트가 `supabase.auth.getUser()`로 직접.

#### pets
- `name` **자유 입력 1~20자**, trim.
- `species` **자유 입력 1~20자** — cat/dog 톤 분기는 prompt layer + `.claude/rules/tone-guide.md`에서 처리 (D + 3-layer).
- `honorific` 자유 입력 1~20자.
- **`gender`** enum 3개 (`'male' | 'female' | 'unknown'`), `NOT NULL DEFAULT 'unknown'`. 카드 표시(♂/♀/—) + LLM 시스템 프롬프트 메타로 inject. 톤 분기 X (species 분기로 충분).
- **soft delete (`deleted_at`)** — 자식 diaries 보존을 위해. RLS SELECT에 `deleted_at is null` 포함.
- 펫 사진 컬럼 X — 펫 row 헤더 좌측은 종 이모지(🐱/🐶/🐾)만 표시(자유 입력 `species`를 클라이언트에서 매핑, ADR-0013 §종 이모지 매핑). 최근 일기 사진은 row 캐러셀의 일기 카드에서만 노출.

#### diaries
- `source_generation_id` UNIQUE — 어떤 generation을 채택했나.
- `diary_text(50~1000)` / `short_caption(1~100)` / `mood_tag` 7-enum CHECK — generation에서 **복사 (denormalize)**. 읽기 단순.
- `mood_tag in ('행복','신남','평온','졸림','심심','슬픔','까칠')`.
- **hard delete** — 말단 엔티티. BFF 트랜잭션으로 same-session generations + storage object 동반 삭제 (best-effort).
- `entry_date` 미도입 — 사후 입력은 미래 옵션 (YAGNI).
- **immutable** — UPDATE RLS 거부.

#### diary_generations
- `session_id` UUID 묶음 (별도 `diary_sessions` 테이블 X).
- `(session_id, seq)` UNIQUE, `seq smallint check (between 1 and 4)`.
- 입력 snapshot 컬럼: `photo_path`, `keywords(1~1000)`, **`honorific_used`**, **`species_used`**, **`gender_used`** (`pets` 변경 후에도 그 시점 추적).
- **`regen_feedback`** text NULL 허용 1~500자. seq=1은 NULL, 그 외는 사용자 피드백 (선택).
- **`vision_description`** text NULL 허용 1~1000자 CHECK (2026-05-05 추가, migration `20260505020000`). seq=1은 graph가 채우고 BFF가 echo, seq≥2는 BFF가 직전 row에서 forward → graph가 vision LLM skip (ADR-0005 부록 2026-05-05, ADR-0007 §Y-2). legacy row는 NULL → 다음 regenerate에서 self-heal.
- LLM 입력에는 직전 generation 1개만 inject (토큰 안정성).
- `is_adopted` 플래그 X — `diaries.source_generation_id` 역참조.
- **immutable** — UPDATE RLS 거부.
- 미채택 cleanup은 미래 cron job ADR.

#### usage_quotas
- `(owner_id, quota_date)` composite PK.
- `quota_date` = **KST 자정 기준** — `(now() at time zone 'Asia/Seoul')::date`. 한국 사용자 자정에 quota reset.
- `generations_count smallint check (0~5)` — 일일 신규(seq=1)만 카운트. 재생성 한도는 `diary_generations` count로 별도.
- BFF 트랜잭션: `diary_generations INSERT` 성공 후 UPSERT increment. 5 초과 returning이면 rollback + 429.
- **Trigger 가드 (보안 boundary)**:
  - INSERT 시 `generations_count = 1` 강제 — 사용자가 fake INSERT로 0 시작 차단.
  - UPDATE 시 `new.generations_count > old.generations_count` 강제 — 사용자가 직접 UPDATE로 reset 차단.
  - β 패턴이라 사용자 JWT로 RLS 통과 가능하므로 trigger가 추가 가드 (RLS UPDATE 정책만으론 reset 우회 가능).

### Storage bucket `pet-photos`
- private. path: `{owner_id}/diaries/{yyyy}/{mm}/{uuid}.{ext}` (ADR-0009).
- 모든 op (SELECT/INSERT/UPDATE/DELETE) 정책: `(storage.foldername(name))[1] = auth.uid()::text`.

## RLS 정책 매트릭스

| 테이블 | SELECT | INSERT | UPDATE | DELETE |
|---|---|---|---|---|
| profiles | `uid = id` | (trigger only, security definer) | `uid = id` | (CASCADE only) |
| pets | `uid = owner_id and deleted_at is null` | `uid = owner_id` | `uid = owner_id` | (CASCADE only) |
| diaries | `uid = owner_id` | `uid = owner_id` | (정책 X — immutable) | `uid = owner_id` |
| diary_generations | `uid = owner_id` | `uid = owner_id` | (정책 X — immutable) | `uid = owner_id` |
| usage_quotas | `uid = owner_id` | `uid = owner_id` | `uid = owner_id` | (정책 X) |

표준 양식: INSERT는 `WITH CHECK`, UPDATE는 `USING + WITH CHECK`, SELECT/DELETE는 `USING`.

## Alternatives Considered

- **profiles 미도입** (Q7-A 첫 추천) — 닉네임 노출 기획 추가되어 도입 확정.
- **species enum 강제** (cat/dog만, 또는 사전 분류) — 자유 입력 + prompt 3-layer가 더 단순. 햄스터·거북이 등 수용.
- **pets hard delete** — 자식 일기의 펫 정보 손실. soft delete가 직관적.
- **diaries soft delete** — 말단 엔티티라 효용 없음. "지운 것은 사라진다".
- **`entry_date` 미리 도입** — YAGNI. 미래 사후 입력 도입 시 마이그레이션 1회 비용 작음.
- **`is_adopted` 플래그** — truth가 두 곳에 분산. `diaries`가 single source of truth.
- **generation INSERT trigger로 quota 자동 increment** — 디버그 어려움. BFF 명시적 SQL이 가시성 ↑.

## Consequences

### Pros
- RLS 단일 패턴 → 마이그레이션·리뷰 가독성 높음. 새 테이블 추가 시 동일 템플릿.
- denormalize로 owner-bound query 단순. join 없는 피드 조회.
- generation immutable + snapshot → 디버그·평가셋 회귀 가능.
- 직관적: 펫 추억 보존 / 일기는 사용자 의도 그대로 hard delete.

### Cons
- BFF가 트랜잭션 책임 다수 (diary 삭제 시 generation + storage 동반, quota UPSERT).
- denormalize는 INSERT 시점 owner_id 일관성을 BFF가 보장해야 — RLS `WITH CHECK`가 1차 가드.

### 후속 조치
- `supabase/migrations/` 마이그레이션 SQL 작성 (본 ADR 결정 그대로).
- `.claude/rules/tone-guide.md` 작성 — Q9 grill 끝나기 전.
- ADR-0005 부록(Q9)에 LangGraph state 명시 (`previous_generation`, `regen_feedback` 필드).
- 미래 ADR — 미채택 generation cleanup cron, 사용자별 timezone 컬럼.
