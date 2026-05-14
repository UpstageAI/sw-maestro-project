# ADR-0013: UI 라우팅 + 메인 구조 + 디자인 시스템 — 4 라우트 + 펫별 row + shadcn/ui

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

ADR-0006~0012로 백엔드·데이터·인프라 결정 완료. 프론트엔드 라우팅·메인 화면 구조·진입 흐름·컴포넌트 라이브러리는 미정. 데이터 영향이 있는 UI 흐름(첫 가입자, 다견 일기 추가, 펫 수정/삭제, 한도 도달)이 데이터 모델 결정과 충돌하지 않도록 본 ADR로 캡처.

## Decision

| 축 | 선택 |
|---|---|
| 라우트 | **4개**: `/login`, `/`, `/pets/new`, `/pets/[id]/edit`, `/diaries/new` (`/settings` 라우트 X — 드롭다운 popup) |
| 메인 본문 | **펫별 row × 가로 캐러셀** (세로 누적) |
| 일기 추가 진입 | 펫 row 좌측 끝 `+` 카드 → `/diaries/new?pet_id=xxx` (**`pet_id` 쿼리 필수**) |
| 펫 추가 진입 | 메인 헤더 `+ 새 펫 추가` 버튼 → `/pets/new` |
| 펫 수정/삭제 | 펫 row 헤더 우측 ⋯ 메뉴 → 수정 페이지 / 삭제 confirm 모달 |
| 펫 0마리 빈 상태 | 본문 중앙 단일 CTA 카드. **redirect X** |
| 삭제된 펫 노출 | **MVP UI 노출 X** (soft delete 데이터만 보존, 보관함은 미래 ADR) |
| 디자인 시스템 | **shadcn/ui + Tailwind CSS** |
| 색·폰트 톤·다크모드 | MVP 미결정 (구현 시작 후 시각 확인하며) |

## Rationale

### 라우트 4개
- `/settings` 별도 페이지 X — MVP 설정 항목이 닉네임 1개뿐. 우상단 드롭다운 popup이 페이지 낭비 회피.
- `/diaries/new`는 별도 페이지 (모달 X) — 사진 업로드 + 키워드 + AI 결과(8s) + 채택/재생성 흐름이 길어 풀스크린이 직관.
- `/pets/new`와 `/pets/[id]/edit` 분리 — 등록 폼 컴포넌트 재사용. 모바일에서 폼 모달은 답답.
- `/pets` 목록 페이지 X — 메인 펫 row가 곧 목록 역할.

### 메인 = 펫별 row
- 펫이 곧 row, 일기는 그 row의 가로 카드 — 정신모델이 1:1 단순.
- 다견 시 펫 필터 드롭다운보다 직관 (모든 펫이 한눈에).
- 펫 row 헤더 = 펫 메타데이터 진입점 통합 (종 이모지·이름·호칭·성별·⋯ 메뉴).

### 일기 추가 = pet_id 쿼리 필수
- 진입 시점에 펫 컨텍스트 결정 → 페이지 안 펫 선택 단계 X. 다견에서도 동일.
- `pet_id` 누락(직접 URL) → `/` redirect + 토스트 "어떤 펫의 일기인지 먼저 선택해주세요".
- `pet_id`가 다른 사용자 펫 → RLS가 BFF 호출 시 차단 → 404 또는 redirect.
- `pet_id`가 `deleted_at IS NOT NULL` → `/` redirect + 토스트 "삭제된 펫에는 일기를 만들 수 없습니다" (soft delete 펫에 새 일기 생성 차단).

### 펫 수정/삭제 = ⋯ 메뉴
- 펫 row 헤더 클릭 자체는 의도 모호 → ⋯ 메뉴로 명시.
- 인라인 편집 X — 종/성별 등 다항목 폼이 인라인엔 부적합.
- 삭제 confirm 모달 문구: *"펫이 메인에서 사라집니다. 일기는 보관됩니다."*

### 빈 상태 = CTA 카드 단일
- 펫 0마리: 본문 중앙 큰 CTA (제목 + 부제 + 큰 버튼). 일러스트·3단계 안내 X (디자인 비용·1회용).
- 펫 ≥1 + 일기 0개 row: `+` 카드 자체가 CTA. 별도 안내 메시지 X (1개 만들면 사라지는 죽은 공간).
- 강제 redirect X — 사용자 자유도 우선 ("둘러보기" 가능).

### 삭제된 펫 = MVP 미노출
- 펫 삭제 빈도 0에 가까움 (펫이 무지개다리 또는 분양 보낸 케이스).
- 보관함 UI는 빈도 0 화면에 비용 들이는 격 → MVP 보류.
- 데이터는 살아있음 (ADR-0010 soft delete 그대로) → 미래 보관함 도입 시 마이그레이션 0회.

### shadcn/ui + Tailwind
- Next.js App Router + RSC 표준. 다른 라이브러리(Chakra/Mantine)는 RSC 호환 모호 또는 제한적.
- 컴포넌트 코드 직접 복사(`npx shadcn add <name>`) → 톤 커스터마이징 자유.
- AI 도구(v0/Claude Code/Cursor) 호환 최상 → 구현 속도.
- MIT 라이선스 + Radix base만 의존 → 번들 가벼움.

## 라우트별 책임

| 라우트 | 인증 | 책임 |
|---|---|---|
| `/login` | 미인증 | Google OAuth 단일 버튼. 인증 후 `/` redirect. |
| `/` | 인증 | 메인. 펫 row × 가로 캐러셀, 빈 상태 CTA, 우상단 닉네임 드롭다운. |
| `/pets/new` | 인증 | 펫 등록 폼 (이름·종·호칭·성별). 제출 후 `/`로. |
| `/pets/[id]/edit` | 인증 | 펫 수정 폼. 등록 폼 컴포넌트 재사용. |
| `/diaries/new` | 인증 + `pet_id` 쿼리 | 사진+키워드 입력 → 결과 → 채택(`/`로)/재생성(seq 증가). |

미인증 시 모든 인증 라우트는 `/login` redirect.

## 데이터 로딩 흐름

### 메인 (`/`) 진입 시
1. GET `/api/pets` → 펫 목록 (alive만)
2. 각 펫마다 병렬 GET `/api/diaries?petId=&limit=N` → row 가로 캐러셀 데이터
3. GET `/api/usage/today` → 오늘 신규 잔여 횟수 (펫 row의 `+ 일기` 카드 disable 판단)

펫이 N개면 호출 N+2회. **MVP 스케일(펫 1~3)에선 무방.** 미래 펫 수 늘거나 latency 이슈 시 통합 endpoint(`GET /api/feed`) 도입 ADR.

### 한도 도달 처리
- `new_remaining = 0`이면 메인 모든 펫 row의 `+ 일기` 카드 **disable + 회색** 처리. 클릭 시 토스트: *"오늘 새 일기 한도(5회)를 모두 썼어요. 자정에 초기화돼요."*
- `/diaries/new?pet_id=xxx` 직접 진입 시도도 같은 검증 → `/` redirect + 동일 토스트.
- 재생성 한도(세션당 3회) 도달은 `/diaries/new` 페이지 안에서 "다시 만들기" 버튼 disable + 안내 텍스트.

### 종 이모지 매핑
- 펫 row 헤더 좌측 시각 식별자. 펫 사진을 별도로 두지 않음 — 자유 입력 `species`를 클라이언트가 이모지로 매핑.
- `species` 자유 입력 → 클라이언트에서 `normalizeSpecies(text) → 🐱 | 🐶 | 🐾` 매핑.
- 단순 substring/keyword 매칭: "고양이"·"cat"·"냥이" → 🐱, "강아지"·"dog"·"멍멍이" → 🐶, 그 외 → 🐾.
- 매핑 함수는 구현 시점 자유 확장 가능. 본 ADR은 정책만 명시.

## Alternatives Considered

- **5라우트 (`/settings` 별도 페이지)** — 닉네임 1개에 페이지 1개는 낭비.
- **일기 생성 = 메인 모달** — 결과/재생성 흐름 길어 풀스크린이 자연.
- **메인 = 단일 그리드 + 펫 필터 드롭다운** — 다견 정신모델이 펫별 row보다 약함.
- **펫 0마리 → `/pets/new` 강제 redirect** — 자유도 ↓, "둘러보기" 막힘.
- **펫 삭제 시 hard delete + cascade** — "추억 보존" 의도 포기. soft delete + UI 미노출이 절충.
- **보관함 별도 페이지/팝업** — 빈도 0 화면, 미래 ADR로 충분.
- **MUI / Chakra / Mantine** — RSC 호환 모호 또는 톤 강제.
- **DaisyUI** — 톤 한정, 커스터마이징 제한.

## Consequences

### Pros
- 라우트 적음 → 라우터 복잡도 낮음.
- 펫 row 메타포가 데이터 모델(pet → diaries 1:N)과 1:1 매핑.
- shadcn은 코드 소유 → 미래 톤 변경 자유.
- AI 도구로 컴포넌트 빠르게 생성 가능.

### Cons
- 펫이 매우 많아질 경우 (10마리+) 메인 세로 스크롤 길어짐. MVP 스케일에선 비현실적.
- shadcn 컴포넌트는 직접 관리 — 업데이트 자동 X. 단점이자 자유도.

### 후속 조치
- `apps/web/` Next.js 14 (App Router) + Tailwind + shadcn 초기 세팅.
- 라우트별 페이지 컴포넌트 + `<PetForm />` 공유 컴포넌트.
- 펫 row 컴포넌트 (헤더 + 가로 캐러셀 + ⋯ 메뉴).
- 빈 상태 CTA 컴포넌트.
- `/diaries/new` 진입 가드 (`pet_id` 검증, deleted_at 검증) — BFF route handler에서.
- 색·폰트·다크모드는 시각 작업 시작 후 별도 ADR 또는 본 ADR 부록.
- 미래 ADR — 보관함 UI (펫 삭제 빈도 발생 시).

---

## 부록 — 시각 톤 초기 방향성 (2026-05-03, 변경 가능)

> 본 부록은 **방향성**만 명시. 구체 색 코드·토큰 값은 시각 작업 진행하며 자유롭게 조정. ADR 갱신 없이 변경해도 무방.

| 축 | 초기 선택 |
|---|---|
| 톤 방향성 | 따뜻한 동물 친화 — 베이지/크림/연갈색 base + 부드러운 오렌지·연한 분홍 계열 강조색 |
| 폰트 | Pretendard (한국어 가변 폰트, self-host, OFL) |
| 다크모드 | **MVP 미포함**. shadcn 자연 지원이라 미래 추가 비용 작음 |
| 모서리 곡률 | 둥근 카드 (`--radius` ≈ `1rem`) |
| 구체 색 hex/토큰 | **미정** — 구현 시점에 결정 |

### 왜 이 방향성
- 도메인(반려동물 일기) = 친근함·따뜻함이 본질. 차가운 미니멀은 거리감.
- Pretendard는 한국어 가변 폰트 표준 + 무료 + CDN 의존 없이 self-host.
- 다크모드는 비영리 사이드 + 데모데이 케이스라 야간 사용 빈도 작음.

---

## 부록 — 디자인 시스템 v2 매거진 풍 (2026-05-05)

본문/§부록(2026-05-03) 시각 톤 방향성을 시각 작업 단계에서 다음과 같이 구체화·갱신. 도메인 친근함은 유지하되 모던/풀스크린/큼직 매거진 톤으로 전체 페이지를 재정렬.

### 톤 — Mocha + Peach + Deep 색블록

- **Light** (그대로): `--background: #f4ece1` 크림, `--card: #fffaf3`, `--primary: #946652` Mocha, `--accent: #ffbe98` Peach Fuzz
- **Deep** (신규): `--deep: #2d2018` (hero 색블록), `--deep-soft: #3d2a1f` (펫 row 교차), `--deep-border: #5a3f2e`
- 메인: hero deep + 펫 row 교차(light/deep-soft) + 하단 CTA cream
- 일기 생성·펫 폼 페이지: hero deep + 본문 cream 2-블록

### 모서리 — 1rem → 0.5rem

`--radius: 0.5rem` (이전 1rem). `rounded-md` 기준으로 카드/버튼/입력 정렬. sharp 톤 + 친근함 절충.

### Display 폰트 — Cafe24Ssurround Bold

`--font-display`(Cafe24Ssurround Bold) 추가 — Hero h1·펫 이름·stat 숫자 등 큰 typography. 기존 Pretendard는 본문, Cafe24SsurroundAir는 헤더 워드마크 그대로 유지.

### 레이아웃

- 모든 페이지 `max-w-[1600px]` + generous padding(`px-10`)
- **PetRow**: 매거진 헤더 — 큰 display 펫 이름 + `Est. {year}` stamp + 일기/함께한 날 stat. 카드 `w-72` fixed + 가로 스크롤(본문 §캐러셀 정합)
- **DiaryCard**: 풀블리드 사진 + 하단 gradient overlay에 캡션·날짜, `aspect-[3/4]`
- **EmptyStateCard**: 작은 카드 → deep section 풀스크린 hero

### 헤더 — 통합 + 활성 표시

- `SiteHeader` = async server component → user/profile 자체 fetch → 호출 측 `<SiteHeader />` 한 줄로 모든 페이지 동일
- nav 2개: **메인 / 새 펫**. `NavLink`(client)가 `usePathname`으로 활성 비교, 활성 nav `font-bold + text-foreground`
- "새 일기"는 헤더 nav에 두지 않음 — 본문 §일기 추가 진입대로 **펫 row 좌측 끝 `+` 카드**가 유일 진입(`pet_id` 컨텍스트 필수). 헤더 nav에 두면 다견 사용자에게 "어떤 펫인가" 모호함 발생
- sticky 제거 — 스크롤과 같이 흘러감(사용자 선호)
- `pets/new`를 server component로 변환 + `NewPetClient` 분리(인증 가드 추가)

### 후속 조치 / 메모

- 펫 사진 thumbnail 컬럼 도입(Phase β) 시 hero photo collage 빈 슬롯에 펫 사진 채우는 방향으로 자연 전환
- 디자인 토큰 utility 생성이 Tailwind v4 + Turbopack에서 일부 누락되는 이슈는 `@layer utilities` 명시 정의로 우회. 향후 Tailwind 픽스되면 cleanup 가능 (`globals.css` `@layer utilities`의 `.bg-deep`, `.bg-deep-soft`, `.text-deep`, `.border-deep-border`, `.font-display`)
- Tilted/perspective 카드 효과는 미차용 — 펫 일상 사진은 luxury frame과 톤 충돌

---

## 부록 — SNS 게시용 이미지 다운로드 (2026-05-08)

DESIGN.md §상세 화면의 "SNS 공유" 2차 기능을 활성화. 일기 카드를 SNS(인스타 스토리/피드 등)에 공유 가능한 9:16 이미지로 export.

> 본 부록은 2026-05-08에 클라이언트 캡처(`html-to-image`)로 1차 결정·구현했으나, 같은 날 OS별 폰트 fallback으로 인한 텍스트 시각 크기 차이(모바일/데스크탑)가 발견되어 **서버 렌더(`next/og` + Satori)로 결정 변경**. 변경 사유는 §결정 변경 (2026-05-08) 참조.

### Decision (final)

| 축 | 선택 |
|---|---|
| 비율 | **9:16 (1080×1920)** — Stories/Reels 표준 |
| 레이아웃 | 사진 60% (1080×1152) + 텍스트 영역 40% (1080×768) |
| 콘텐츠 | 사진(좌상단 펫 이름 칩) + mood pill + caption + diary_text + 날짜 + "🐾 냥멍일기" 워터마크 |
| 렌더링 | **서버 렌더** — `GET /api/diaries/:id/sns-image` → `next/og` `ImageResponse` (Satori) → PNG |
| Runtime | **Edge** (`export const runtime = "edge"`) — Next 16 + Turbopack + Node runtime 조합에서 jest worker가 retry 한도 초과로 crash하던 문제 회피 |
| UX | 일기 상세 다이얼로그에서 view 전환(`detail` ↔ `sns-preview`) — 서버 fetch → 미리보기 → [SNS 공유] / [다운로드] |
| 다운로드 | Web Share API (모바일 인스타/카톡 직접 공유) + `<a download>` (데스크톱·share 미지원 환경 fallback) |
| 본문 폰트 | 글자수 구간별 (≤220자 30px / ≤320자 26px / ≤400자 22px) |
| 폰트 자체 | Pretendard Regular/Bold(.otf) + Cafe24Ssurround(.woff) self-host — `apps/web/public/fonts/`. Edge runtime에서 `fetch(${origin}/fonts/...)`로 로드 후 모듈-level 캐시. Satori `fonts` 옵션으로 명시 전달 → 글리프 path로 직접 그려 OS 무관 동일 |
| 펫 이름 노출 | 서버 route handler에서 `pets` 별도 select (단일 일기 단일 호출이라 RLS·성능 부담 작음) |
| 캐시 | `Cache-Control: private, max-age=3600, immutable` — 일기는 immutable이라 같은 일기 재호출은 브라우저 캐시(~0초) |
| 동시성 | 폰트 fetch는 auth/DB 쿼리와 병렬 시작, `pets`/`diary_generations` 두 query는 `Promise.all`로 병렬 |
| 파일명 | `냥멍일기-{YYYYMMDD}-{HHMMSS}.png` (다운로드 시점 로컬 시간) |

### Rationale

- **서버 렌더**: 클라이언트 캡처는 디바이스 시스템 폰트로 fallback되어 OS별로 글리프가 달라짐(아래 §결정 변경 참조). Satori는 woff2/otf의 글리프 path를 직접 그려 환경 무관 byte-단위 동일 PNG 보장.
- **9:16 단일**: 4:5(피드 세로) 옵션 분기는 사이드프로젝트 복잡도. 200~400자 일기는 9:16 텍스트 영역에서 자연스럽게 다 들어감.
- **다이얼로그 view 전환**: 별도 다이얼로그 X (중첩 어색). 같은 다이얼로그에서 콘텐츠만 swap → 자연스러운 흐름.
- **미리보기 단계**: Web Share API와 다운로드 두 옵션이 있어 사용자가 결과 보고 선택하는 단계가 자연스러움.

### Alternatives Considered

- **클라이언트 캡처(`html-to-image`)** — 1차 채택했다가 OS별 폰트 차이로 탈락 (§결정 변경 참조).
- **HTML5 Canvas 직접 그리기** — 한국어 줄바꿈/keep-all/letter metric 직접 구현 부담 큼.
- **즉시 다운로드 (미리보기 X)** — 공유/다운로드 분기를 위한 미리보기 단계가 더 자연.
- **mood pill에 이모지 추가(DESIGN.md §mood 매핑)** — 기존 카드(`diary-card.tsx`)는 dot+라벨이라 SNS 이미지만 이모지 추가하면 시각 일관성 깨짐. SNS 이미지에서도 dot+라벨 유지.

### Consequences / 후속

- `DialogContent`에 `max-h-[90vh] overflow-y-auto` 동시 추가 — 작은 viewport에서 일기 상세 다이얼로그가 화면을 넘어가던 부수 문제 수정.
- Route handler 추가: `apps/web/src/app/api/diaries/[id]/sns-image/route.tsx` (Edge runtime).
- 폰트 self-host: `apps/web/public/fonts/Pretendard-Regular.otf` + `Pretendard-Bold.otf` + `Cafe24Ssurround.woff` (각 ~1.5MB / 1.6MB / 400KB). git에 포함. Edge runtime fetch로 로드 후 모듈-level 캐시.
- `apps/web/src/proxy.ts` matcher에 `woff|otf|ttf` 추가 — 폰트 fetch가 인증 redirect에 막히지 않게 (기존 `woff2`만 있음).
- 응답 시간: 첫 호출은 photo fetch + 폰트 fetch + Satori 렌더가 직렬 일부 + 병렬 일부로 ~1~2초. 두 번째 호출부터는 폰트 모듈 캐시 + 같은 일기면 브라우저 Cache-Control로 ~0초.
- 미리보기 화면 우상단 "SNS 게시용 9:16" 안내 텍스트 제거 (사용자 피드백 — 비율 정보는 부록 등에 있고, 화면 자체로 자명).
- 미래 — 4:5(피드 세로) 옵션, 다중 일기 콜라주, 사용자 정의 워터마크 등은 별도 결정. `vercel.json`에 edge region(`icn1` 등) 명시는 supabase 지역과 latency 감안 후 검토.

### 결정 변경 (2026-05-08)

> 1차 결정(클라이언트 캡처)을 같은 날 서버 렌더로 변경.

**문제 발견:** 같은 일기에 대해 모바일 웹과 데스크탑 웹에서 **출력 PNG의 텍스트 시각 크기가 다르게 나타남.** PNG 자체는 두 환경 모두 1080×1920 (비율 문제 X).

**원인 진단:**
1. `SnsImageCanvas`의 `font-family`는 시스템 폰트 fallback chain. 디바이스마다 fallback이 달라 (iOS=Apple SD Gothic Neo, Windows=Malgun Gothic, Android=Noto Sans CJK 등) 같은 `font-size:30px`도 글리프 metrics가 달라 시각 크기 차이.
2. `next/font/local`로 self-host한 PretendardVariable을 `var(--font-pretendard)` 명시도 시도했으나, html-to-image의 SVG-to-image 변환 단계에서 SVG `<img>` 안 inline `@font-face`가 적용 안 됨 (브라우저 공통 한계).
3. `getFontEmbedCSS`로 명시 호출 + `fontEmbedCSS` 옵션으로 woff2 base64(~3.3MB)를 SVG에 inject까지 시도했지만 결과 PNG 바이트는 여전히 동일 크기(180KB) — 폰트 데이터가 PNG 렌더에 사용되지 않음.

**Decision:** 클라이언트 캡처 라이브러리(`html-to-image`)는 본질적으로 디바이스 폰트에 의존 → 서버 렌더로 전환. `next/og` `ImageResponse`는 Satori 기반으로 woff2/otf의 글리프 path를 직접 그리므로 환경 무관 byte-동일 PNG 보장.

**제거된 것:**
- `html-to-image` 의존성
- `apps/web/src/components/sns-image-canvas.tsx` + CSS module
- `PetRow → DiaryCard → DiaryDetailDialog`의 `petName` prop drilling (서버에서 직접 select)

**검증:** 데스크탑·모바일 viewport에서 같은 일기 PNG의 SHA-256/byte 길이 일치 (Satori는 결정론적 렌더).
