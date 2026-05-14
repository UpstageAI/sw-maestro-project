# ADR-0008: BFF API 표면과 일기 세션 모델

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

ADR-0007(Y-2 영속화) 위에서 BFF가 클라이언트에 노출할 endpoint와 "재생성 세션"을 어떻게 표현할지.

## Decision

### C — RPC-ish 분리 (행위 단위 endpoint)

| Method | Path | Body | 책임 |
|---|---|---|---|
| POST | `/api/diaries/generate` | `{ pet_id, photo_path, keywords }` | 첫 생성 — BFF가 새 `session_id` 발급, `pets`에서 `honorific/species/gender` fetch, `diaries`에서 최근 3개 fetch, signed URL 발급 후 Gateway forward, `diary_generations` INSERT (seq=1, snapshot 포함), `usage_quotas` UPSERT |
| POST | `/api/diaries/regenerate` | `{ session_id, pet_id, photo_path, keywords, feedback?: string(1~500) }` | 재생성 — 다음 seq 결정, 재생성 한도 검증, `pets`에서 메타 fetch (snapshot 갱신), 직전 generation 1개 + Gateway forward, INSERT |
| POST | `/api/diaries` | `{ source_generation_id }` | 채택 — generation에서 복사해 `diaries` INSERT |
| DELETE | `/api/diaries/:id` | – | 일기 hard delete + same-session generations 동반 + storage object 삭제 (BFF 트랜잭션 best-effort) |
| GET | `/api/diaries?petId=&cursor=&limit=` | – | 피드 (cursor pagination). 메인은 펫별 row이므로 클라이언트가 펫마다 호출 (펫 수만큼 N개) |
| GET | `/api/usage/today` | – | 오늘 신규 잔여 횟수 |
| POST | `/api/pets` | `{ name, species, honorific, gender }` | 펫 등록 |
| GET | `/api/pets` | – | 본인 펫 목록 (alive만) |
| PATCH | `/api/pets/:id` | `{ name?, species?, honorific?, gender? }` | 펫 정보 수정 |
| DELETE | `/api/pets/:id` | – | 펫 soft delete (`deleted_at = now()` UPDATE, 자식 일기는 보존) |
| PATCH | `/api/profile` | `{ display_name }` | 닉네임 변경 |

### 세션 모델 — UUID만, 별도 자원 테이블 X

- 첫 `/generate` 호출 시 BFF가 `session_id`(UUID) 발급, 응답 포함.
- 클라이언트는 컴포넌트 메모리에 보관 (sessionStorage까지 안 감).
- `/regenerate`는 body로 `session_id` 받음.
- 세션 = 같은 `session_id`를 공유하는 `diary_generations` row들의 집합. 별도 `diary_sessions` 테이블 없음.

### 카운트 정책

- 일일 신규 한도 5회: `usage_quotas(owner_id, quota_date, generations_count)`로 enforce.
- 세션당 재생성 한도 3회: `count(*) FROM diary_generations WHERE session_id = $1`로 enforce.
- **차감 시점은 generation 성공 영속 후** (실패 시 차감 X — 단순한 트랜잭션 단위).
- 자동 safety retry는 한 번의 user 트리거로 카운트 1.

### 응답 페이로드 모양

`/generate`, `/regenerate`는 **SSE (`text/event-stream`)** — JSON 단일 응답 X. 자세한 결정과 이벤트 union은 본 ADR 부록(2026-05-05). 나머지는 JSON:

```jsonc
// /diaries (POST)
{ diary_id }

// /diaries (GET)
{ items: [...], next_cursor }

// /usage/today
{ new_remaining }
```

## Rationale

- **버튼 = endpoint.** UX 행위와 1:1 매핑 → 클라이언트 코드도 `generate()` / `regenerate()`로 의도 명료.
- **카운트 정책 endpoint별 분리** — 한 함수에 분기 안 함.
- **세션 자원 테이블 불필요** — UUID + `diary_generations.session_id`만으로 그룹 표현.
- **클라이언트 새로고침 시 세션 잃어도 OK** — DB의 generation row는 보존, 새 세션으로 시작.

## Alternatives Considered

### A — 단일 endpoint (`POST /api/diaries/generations`, optional session_id)
- **탈락 이유**: 한 함수에 분기 多, 카운트 정책 두 종류 한 곳에 섞임.

### B — REST hierarchy (`/api/diary-sessions/:id/generations`)
- **탈락 이유**: `diary_sessions` 테이블 추가 부담 + UX 행위와 자원 hierarchy 추상도 차이.

## Consequences

### Pros
- 클라이언트 코드 의도가 endpoint 이름에 박힘.
- 카운트 정책 분리 명확.
- 세션 자원 테이블 불필요.

### Cons
- "REST 표준성" 약함 (RPC-ish).
- endpoint 수 +2 (generate vs regenerate).

### 후속 조치
- 마이그레이션: `usage_quotas` 테이블.
- BFF 미들웨어: 모든 `/api/diaries/*` 요청에 세션 검증 + Gateway 호출 시 JWT forward.

---

## 부록 — `/generate`·`/regenerate` SSE 전환 + BFF mediator (2026-05-05)

본 ADR 본문은 `/generate`, `/regenerate` 응답을 단일 JSON으로 가정했지만 구현 단계에서 SSE로 전환됨.

### Why SSE

1. P95 < 8s NFR 지키되 **사용자 체감 latency 단축** — diary partial 누적으로 "쓰는 중" 진행감.
2. graph 노드 단위 라벨 전환 ("사진 분석 중" → "일기 쓰는 중") — `node` 이벤트로 제공.
3. safety retry 발생 시 본문 reset 신호 — `retry` 이벤트.

### BFF mediator 패턴

Gateway SSE를 **그대로 forward 안 함**. BFF가 mediator로 가공:

```
gateway → BFF: node | vision_done | diary_partial | retry | result | error
BFF → 클라이언트: node | diary_partial | retry | result | meta | error
                  (vision_done은 BFF에서 종결, meta는 BFF가 INSERT 후 추가)
```

- `vision_done` 가로채(closure 보관, 클라이언트 forward X) → DB INSERT 시 `vision_description` echo (ADR-0007, ADR-0010).
- `result` 시점에 `diary_generations` INSERT + `usage_quotas` UPSERT(generate만) → 성공 시 `meta` 이벤트 emit.
- 클라이언트는 `meta`까지 받아야 generation 확정 (없으면 INSERT 실패 ⇒ 재생성/채택 차단).

### 이벤트 union (실측)

`packages/shared-types/src/stream.ts` 단일 진실 소스. 7종:

| type | 발신자 | 의미 |
|---|---|---|
| `node` | gateway | graph 노드 시작/종료 (UI 라벨 전환) |
| `vision_done` | gateway | analyze_image 산출. **BFF 종결**, 클라이언트 미수신 |
| `diary_partial` | gateway | write_diary 누적 diary_text (매번 전체) |
| `retry` | gateway | safety violation → 본문 reset |
| `result` | gateway | 최종 산출 (text/caption/mood) |
| `meta` | BFF | INSERT 후 generation_id/session_id/카운터 |
| `error` | gateway/BFF | 종료 신호 |

### 카운트 정책 변경 없음

INSERT/UPSERT 시점·트랜잭션 단위는 본문 §카운트 정책 그대로 — `result` 시점에 한 번. 자동 safety retry는 여전히 user 트리거 카운트 1.
