# 냥멍일기 기획

> 작성일: 2026-05-01
> 갱신: 2026-05-03 — MVP 아키텍처 재정의 후 기획 디테일(입출력·UX) 보강

## 서비스 정의 & MVP 범위

### 한 줄 정의
**반려동물 사진 + 일과 키워드 → 반려동물 1인칭 시점의 일기**를 자동 생성·아카이빙하는 서비스.

### MVP에 포함되는 것 (✅)
- Google 로그인
- 반려동물 프로필 등록 (다견 가능, 펫별 호칭·종·성별 설정)
- 사진 업로드(JPG/PNG, ≤10MB) + 키워드(≤1,000자) 입력
- AI 일기 생성 (Vision 멀티모달, 반려동물 1인칭, 한국어)
- 재생성 (최대 3회, 즉 총 4회 생성)
- 최근 3개 일기 참조한 연속성 표현
- 일기 저장 + 카드형 피드 조회 (펫별 가로 캐러셀 row, 세로 누적)
- 닉네임 표시(메인 인삿말) + 우상단 드롭다운 popup으로 닉네임 변경
- 펫 프로필 수정·삭제 (soft delete — 메인 미노출, 일기는 DB 보존, 보관함은 미래)

### MVP에서 빠지는 것 (❌ → 2차)
- 사용자 직접 텍스트 편집
- RAG 기반 의미 검색
- Kakao/Apple 로그인
- 푸시 알림, 리마인더
- 호칭 입력 검증 (PII/abuse) — Reflection 또는 Validation Agent로 미래 도입
- LangGraph Reflection / 자체 critique — ADR-0005 참조

### 비기능 요구사항 (NFR)
- **응답 시간**: 일기 생성 P95 < 8초 (Vision 호출 포함)
- **가용성**: MVP는 99% 목표
- **확장성**: 사용자 1만 명 / 일일 일기 5만 건까지 수직 확장 대응
- **비용**: 사용자당 월 LLM 비용 ≤ 200원 가정

---

## 입력 스펙 (일기 1건 작성)

| 항목 | 형식 | 비고 |
|---|---|---|
| 사진 | JPG/PNG, ≤10MB, **1장** | 클라이언트에서 long edge 1024px 리사이즈. 여러 장은 미래 옵션 |
| 키워드 | 자유 텍스트, **1~1,000자** | LLM이 자유 형식으로 파싱. 구조화·태그 X |
| 펫 선택 | 다견 시 명시, 단견 시 자동 | 펫 단위로 호칭 등 설정 |
| 일기 날짜 | 자동(오늘) | `created_at::date`로 처리. 사후 입력은 미래 옵션 |

### 이름 정책

- 펫별로 **자유 입력** (1~20자, trim). 호칭과 동일 한도 — 펫 자유입력 항목 일관성.

### 호칭 정책

- 펫별로 **자유 입력** (1~20자, trim).
- 예: "누나", "오빠", "이쁜아빠", "삼촌" 등.
- LLM 시스템 프롬프트에 한국어 조사·어미 가이드 명시.
- 입력 검증(PII/abuse/형식)은 MVP 미포함 — 미래 Reflection critique 또는 별도 Validation Agent ADR.

### 성별 정책

- 펫별 enum 3종 (`male` / `female` / `unknown`), default `unknown`.
- 펫 카드·row 헤더에 아이콘(♂/♀/—) 표시.
- LLM 시스템 프롬프트 메타로 inject — 호칭("오빠/누나")과 함께 1인칭 자기 표현 일관성 확보.
- 톤 가이드(`tone-guide.md`) 분기는 species만 — 성별 분기 X (케이스 폭증 회피).

---

## 재생성 입력 모델

### 인터랙션
- 첫 결과 카드 또는 직전 재생성 결과를 보고 "다시 만들기" 클릭.
- 모달에서 **피드백 자유 텍스트** (선택, 1~500자). 빈 입력도 허용 — 그냥 "다시"도 valid.

### 한도
- session당 재생성 3회 = **총 4회 시도** (seq=1~4).
- session 종료 = 어느 generation을 채택해서 일기로 저장 또는 그냥 닫음.

### LLM 입력 (재생성 시)
- 첫 생성 입력 (photo + keywords + pet_context) +
- **직전 generation 1개**의 `diary_text` +
- 사용자 재생성 피드백 (있으면).

토큰 안정성을 위해 직전 1개만 inject — seq=4여도 seq=3 한 row만.

---

## 출력 스펙 (일기 1건)

| 필드 | 타입 | 비고 |
|---|---|---|
| `diary_text` | text **200~400자** | 한국어 1인칭. 프롬프트로 강제, 후처리 강제 X |
| `short_caption` | text 한 줄 | 피드 카드 제목 역할 |
| `mood_tag` | enum **7개** | 행복 / 신남 / 평온 / 졸림 / 심심 / 슬픔 / 까칠. structured outputs로 강제, DB는 `text + CHECK` |
| 사진 분석 중간 산출 | (LangGraph state·LangSmith trace에만) | 사용자 노출 X |

---

## 사용자 정보 / 헤더 UX

### 닉네임
- 자유 입력, **1~24자** (trim).
- 가입 직후 Google `raw_user_meta_data.name`을 자동 채움. 없으면 email local-part로 fallback.
- 우상단 설정 탭에서 변경 가능. unique 제약 없음, 변경 횟수 제한 없음.
- 검증(PII/abuse)은 MVP 미포함 — 호칭과 동일 정책 (미래 Reflection/Validation).

### 메인 인삿말
- 형식 **고정**: `"안녕하세요 {nickname}님"`. 시간대/이벤트 분기는 미래 옵션.

### 설정 (페이지 X — 드롭다운 popup)
- 메인 우상단 아바타/닉네임 클릭 → 드롭다운 popup. 별도 `/settings` 라우트 없음.
- 항목: 닉네임 변경 입력란 + 연결된 Google 계정 이메일 표시(read-only). 이메일 변경 X (OAuth 고정).
- MVP에선 이 둘 외 항목 없음.

---

## 라우팅 & 메인 구조 (요약 — 상세는 ADR-0013)

### 라우트 (4개)
- `/login` — Google 로그인 단일 버튼.
- `/` — 메인. 미인증 시 `/login` redirect.
- `/pets/new`, `/pets/[id]/edit` — 펫 등록/수정 폼.
- `/diaries/new?pet_id=xxx` — 일기 생성. `pet_id` 쿼리 필수.

### 메인 본문
- 펫별 row × 가로 캐러셀(최신순). 펫이 늘어나면 row가 세로로 누적.
- 펫 row 헤더: 종 이모지(🐱/🐶/🐾) + 이름 + 호칭 + 성별 아이콘(♂/♀/—) + 우측 끝 ⋯ 메뉴 (수정/삭제). 펫 사진은 헤더에 두지 않음 — 일기 카드의 사진 썸네일이 시각 정체성을 담당.
- 펫 row 좌측 끝 `+ 새 일기` 카드 → `/diaries/new?pet_id=xxx`.
- 메인 헤더(로고바 하단) 또는 펫 row들 마지막에 `+ 새 펫 추가` 버튼 → `/pets/new`.

### 빈 상태
- 펫 0마리: 본문 중앙 단일 CTA 카드 — "🐾 첫 반려동물을 등록해주세요" + 큰 버튼.
- 펫 ≥1 + 일기 0개 row: `+ 새 일기` 카드 1개만 (별도 안내 X).

### 펫 삭제 정책
- soft delete. 메인에서 미노출, 새 일기 생성 차단.
- confirm 모달 문구: *"펫이 메인에서 사라집니다. 일기는 보관됩니다."*
- 보관함 UI는 MVP 미도입 (미래 ADR).

---

## 피드 / 상세 UX

### 피드 카드
사진 thumbnail · `short_caption`(제목) · `diary_text` 1~2줄 미리보기 · **mood 칩(이모지+라벨)** · 날짜.

### 상세 화면
사진(큰 사이즈, signed URL 새로 발급) · `short_caption`(제목) · `diary_text` 전체 · 날짜.
**SNS 게시용 이미지 다운로드/공유** — 9:16(1080×1920) PNG 캡처 → Web Share API(모바일에서 인스타·카톡 등 시스템 공유 시트) 또는 직접 다운로드. 상세 결정은 ADR-0013 부록 참조.
2차 기능: 사용자 직접 텍스트 편집.

### mood 이모지 매핑 (제안 — 프론트에서 매핑, DB는 한글 라벨만 저장)

| mood | 이모지 |
|---|---|
| 행복 | 😊 |
| 신남 | 🥳 |
| 평온 | 😌 |
| 졸림 | 😴 |
| 심심 | 🥱 |
| 슬픔 | 🥺 |
| 까칠 | 😤 |

---

## 관련 ADR

- ADR-0001: LLM = OpenAI GPT-4o-mini
- ADR-0002: BaaS = Supabase
- ADR-0003: AI Gateway = FastAPI + LangGraph
- ADR-0005: LangGraph 워크플로우 토폴로지 (가벼운 그래프 + Reflection 보류)
- ADR-0006: 시스템 신뢰 경계 + 인증 (B + β JWT forward)
- ADR-0007: 영속화 모델 (Y-2 즉시 영속 + 두 테이블)
- ADR-0008: BFF API 표면 + 세션 모델 (C 분리)
- ADR-0009: 사진 업로드 흐름 (a 클라이언트 직접 + Storage RLS)
- ADR-0010: 데이터 모델 + RLS (5 테이블 + β 단일 패턴)
- ADR-0011: AI Gateway 호스팅 (Railway us-east4 + 공유 비밀 헤더)
- ADR-0012: 관측성 (LangSmith Developer Free + base logs)
- ADR-0013: UI 라우팅 + 메인 구조 + 디자인 시스템 (shadcn/ui + Tailwind)
