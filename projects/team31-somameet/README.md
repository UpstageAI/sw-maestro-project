# SomaMeet (소마밋)

> 개인 일정의 세부 내용을 노출하지 않고 여러 사람의 공통 가능 시간을 빠르게 찾는 **개인정보 보호 일정 조율 서비스**.
> SW마에스트로 AI 기술교육 31기 31조(소마밋팀) MVP 프로젝트입니다.

---

## 프로젝트 한 줄

가능/바쁜 시간 정보만 모아 LLM Agent가 후보 시각과 공유 메시지를 함께 만들어주는 일정 조율 서비스. 개인 일정의 제목, 장소, 설명은 **저장되지도 LLM으로 전송되지도 않습니다**.

대상 사용자: SW마에스트로 연수생, 팀원, 멘토, 엑스퍼트, 코치 — 여러 사람과 반복적으로 일정을 맞춰야 하지만 개인 일정 전체를 공개하기는 부담스러운 경우.

---

## 팀 31조 — 소마밋

| 담당 | 역할 |
|------|------|
| 박세종 | PM, 통합 레포/마일스톤 관리, 통합 기획서 작성 |
| 지상근 | 백엔드 owner — API/DB/스케줄러/테스트 |
| 이중곤 | 프론트엔드 UX owner — 후보/타임테이블 화면, LLM 검증 보강 |
| 홍지연 | 입력 어댑터/메시지 흐름/README, 최종 발표 |
| 안수빈 | 사용자 시나리오 QA, 수동 입력 UX 점검, 데모 스크립트/테스트 데이터 |

최종 발표(2026-05-15 데모데이)는 홍지연이 맡고, 박세종이 발표 준비/진행을 서포트합니다.

---

## 핵심 흐름 (MVP)

1. 회의 생성 (제목, 날짜 범위 또는 후보 날짜, 길이, 위치, 시간대)
2. 공유 URL + QR 코드를 참여자에게 배포
3. 참여자 등록: **닉네임 + 4자리 PIN(선택) + 필수 참여자 토글(선택)**
4. 가용 시간 입력
   - 직접 입력: 30분 단위 캘린더형 그리드
   - ICS 파일: 파싱 후 그리드에 pre-fill → 사용자가 검토/수정 → 저장
5. 1명 이상 제출되면 결과 가능
   - **결과 보기** (`/calculate`) — 결정론적(deterministic) 후보, LLM 호출 없음
   - **추천받기** (`/recommend`) — Upstage solar-pro3 LLM이 후보별 이유 + 공유 메시지 초안 생성
6. 후보 선택 → 메시지 검토 다이얼로그 → 회의 확정 → 공유 메시지 복사

---

## 핵심 결정사항 요약

기획서 `구현_위임_스펙.md` (v3) 및 v1~v4 추가 스펙(Phase 1~Phase 53)에서 잠긴 결정사항입니다.

### 통합 베이스
- 5월 6일 3차 오프라인 회의에서 5개 데모 비교 후 채택
- **백엔드**: SomaMeet_Sanggeun (API 계약/DB/권한/스케줄러/ICS/테스트)
- **프론트엔드 비주얼**: SomaMeet_Joonggon (shadcn/ui 16개, Tailwind 토큰, Pretendard)
- **부분 흡수**: SomaMeet_Sejong (QR 패턴), Somatime_Jiyeon (PIN 본인 확인)

### 데이터/권한
- **PIN 평문 저장** (Q7 / MVP 단순화 — 운영 진입 시 bcrypt 전환 필요)
- **organizer_token 제거** (v3.2 Path B) — 공유 URL 보유자라면 누구나 calculate/recommend/confirm 가능. 사고 방지는 `ShareMessageDialog` 2단계 게이트와 race 보호용 409 `already_confirmed`로 흡수
- **참여자 쿠키**: `somameet_pt_{slug}` HttpOnly. 운영(Vercel↔Railway 크로스 오리진)은 `SameSite=None; Secure; Partitioned` 자동 부착 (CHIPS, 모바일 ITP 대응)
- **참여 인원 입력 제거** (v3.1) — `submitted_count >= 1`이면 결과 가능
- **필수 참여자 토글** (`is_required`, v3.11) — 자기 self-mark 방식, 등록 폼·수정 폼 양쪽에서 가능

### 알고리즘
- 슬롯 단위 30분, KST(Asia/Seoul) 고정
- 오프라인 버퍼 0/30/60/90/120분, online은 0, **any는 offline과 동일** (Q8 — 안전 우선)
- 회의 길이 30/60/90/120/150/180분
- 후보 간 시작 시각 **최소 120분 간격** 강제 (v3.27, deterministic·LLM 양쪽 모두 enforce)
- 3-tier 추천 우선순위:
  1. 전원 가능(`is_full_match`) 윈도우만
  2. 그게 없으면 필수 참여자 모두 가능한 윈도우 중 best `available_count`만
  3. 그것도 없으면 전체 윈도우 중 best `available_count`만
- 미제출 참여자(`confirmed_at IS NULL`)는 ghost-free 처리 방지를 위해 스케줄링 풀에서 제외 (v3.16)

### LLM
- 단일 provider: **Upstage solar-pro3** (OpenAI 호환 SDK) 또는 결정론적 `template`
- `/calculate` = LLM 호출 0
- `/recommend` = LLM 1회 호출 + 검증 실패 시 최대 3회 재시도 = **최대 4회**
- 4회 실패 시 deterministic fallback (응답 `source: "deterministic_fallback"`)
- 네트워크 오류는 즉시 fallback (재시도 없음)
- LLM 입력에 **이벤트 제목/장소/설명 절대 미포함** — `tests/acceptance/test_acceptance_S1_S11.py` S11에서 prompt spy로 강제
- system prompt는 한국 직장인 생활 리듬 가이드 포함 (오전 10~12시·오후 2~5시 선호, 점심·퇴근·러시아워 회피)
- frontend 5분 client-side 추천 쿨타임 (localStorage)

### UX
- 회의 생성 성공 즉시 `/m/{slug}`로 navigate (success 카드 없음)
- 회의 페이지 좌우 2열 레이아웃 (날짜 ≤ 5일일 때) + 그 외 1열 스택
- 캘린더형(세로) 타임테이블 (rows=시간, cols=날짜) + `grid-row span`으로 같은 카운트 run 단일 div 렌더
- 5초 polling으로 다른 참여자 제출 즉시 반영 (탭 백그라운드 스킵, mid-edit 보호)
- 회의 설정 수정 가능 (`PATCH /api/meetings/{slug}/settings`, 확정 전까지)
- ICS는 parse-only 후 manual 그리드에 pre-fill → 사용자 검토/수정 → 저장 (commit 전 한 번 더 확인)
- "주말 포함" 체크박스 UI 제거 (v3.21, 항상 true) — 컬럼은 dead code로 잔존

---

## 기술 스택

### Backend (`backend/`)

| 분류 | 사용 기술 |
|------|-----------|
| 런타임 | Python 3.11 |
| 웹 프레임워크 | FastAPI 0.109+, Uvicorn[standard] |
| ORM / 마이그레이션 | SQLAlchemy 2.x, Alembic |
| 검증 | Pydantic v2, pydantic-settings, python-dotenv |
| LLM | Upstage solar-pro3 via `openai` SDK (OpenAI 호환) / 결정론적 `template` |
| 캘린더 | `icalendar` |
| 테스트 | pytest, pytest-asyncio, freezegun |
| DB | 기본 SQLite, 운영 PostgreSQL (psycopg2-binary) |
| 린트 | ruff |

### Frontend (`frontend/`)

| 분류 | 사용 기술 |
|------|-----------|
| 빌드 | Vite 5 |
| 언어/UI | React 18, TypeScript 5.6 |
| 라우팅 | react-router-dom v6 |
| 스타일 | TailwindCSS v3, shadcn/ui 패턴, Radix UI (label/popover/progress/separator/slot/tabs) |
| 폼 | react-hook-form + zod, `@hookform/resolvers` |
| 컴포넌트 보조 | class-variance-authority, clsx, tailwind-merge |
| 폰트/아이콘 | Pretendard, lucide-react |
| 날짜/QR | react-day-picker (단일/범위/다중), qrcode.react, date-fns |
| 테스트 | Playwright |

### 배포

- **Backend**: Railway (Dockerfile + Procfile, alembic 자동 migrate 후 uvicorn)
- **Frontend**: Vercel (`vercel.json`, `*.vercel.app` 와일드카드 CORS 자동 허용)
- **로컬**: `docker-compose.yml`로 백엔드만 컨테이너화 (프론트는 `pnpm dev`)

---

## 디렉터리 구조

```
team31-somameet/
├── backend/
│   ├── app/
│   │   ├── api/              # meetings, participants, auth, availability, recommend, timetable
│   │   ├── core/             # config, dependencies, errors
│   │   ├── db/               # SQLAlchemy 2.x 모델, 세션, base
│   │   ├── schemas/          # Pydantic v2 입출력 스키마
│   │   ├── services/         # scheduler, ics_parser, availability, tokens, timezones
│   │   │   └── llm/          # base, prompts, upstage, template
│   │   └── main.py           # FastAPI 앱 팩토리 (load_dotenv, CORS regex, 라우터 등록)
│   ├── alembic/
│   │   └── versions/         # 03f766...initial → b1c2..v3 → c2d3..drop_target → d3e4..drop_organizer → e4f5..is_required
│   ├── tests/
│   │   ├── unit/             # scheduler, ics_parser, tokens, llm 어댑터
│   │   ├── integration/      # meeting flow, recommend
│   │   └── acceptance/       # 스펙 시나리오 S1~S11 + v3 시나리오 (S1b/S12~S15)
│   ├── Dockerfile
│   ├── Procfile              # Railway 배포용
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── CreateMeetingPage.tsx
│   │   │   ├── MeetingPage.tsx
│   │   │   └── meeting/      # JoinSection, AvailabilitySection, ManualAvailabilityForm,
│   │   │                     # IcsUploadForm, MeetingSummary, TimetableSection,
│   │   │                     # CurrentParticipantCard, EditMeetingDialog, RecommendButton
│   │   ├── components/
│   │   │   ├── ui/           # shadcn/ui 17개 (Joonggon 이식)
│   │   │   ├── AvailabilityGrid.tsx     # 캘린더형 그리드 (transpose)
│   │   │   ├── Timetable.tsx            # 캘린더형 + grid-row span 셀 병합
│   │   │   ├── DateRangeOrPicker.tsx    # 범위/개별 선택 탭
│   │   │   ├── CopyableUrl.tsx, QrPanel.tsx, ShareMessageDialog.tsx, CandidateList.tsx
│   │   ├── lib/              # api, types, datetime, availabilityCells, cn
│   │   └── App.tsx
│   ├── tests/e2e/            # Playwright (E1_full_flow.spec.ts)
│   ├── vercel.json
│   └── package.json
└── docker-compose.yml
```

---

## 빠른 시작 (Quick Start)

### 사전 요구사항

- Python 3.11+
- Node.js 20+ + pnpm
- (선택) Docker 24+

### 1. 백엔드 실행

```bash
cd backend
cp .env.example .env                               # 필요 시 LLM_PROVIDER, UPSTAGE_API_KEY 설정
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m alembic upgrade head                     # SQLite DB 생성 + 모든 마이그레이션 적용
uvicorn app.main:app --reload --port 8000
```

> **중요**: 새로운 마이그레이션이 추가될 때마다 반드시 `python -m alembic upgrade head`를 실행하세요. v3.1 → v3.2 사이의 컬럼 drop 마이그레이션 누락이 회의 생성 INSERT 실패의 원인이 된 적이 있습니다.

기본값 `LLM_PROVIDER=template`은 결정론적 메시지 템플릿이므로 API 키 없이도 전체 흐름이 동작합니다. 실제 Upstage 추천을 켜려면 `.env`에서:

```env
LLM_PROVIDER=upstage
UPSTAGE_API_KEY=<your-key>
```

- API: <http://localhost:8000>
- 헬스체크: <http://localhost:8000/api/health>
- OpenAPI 문서: <http://localhost:8000/docs>

### 2. 프론트엔드 실행

```bash
cd frontend
pnpm install
pnpm dev
```

- 개발 서버: <http://localhost:5173>
- 백엔드 base URL은 환경 변수 `VITE_API_BASE_URL`로 오버라이드 (기본 `http://localhost:8000`)

### 3. Docker Compose 사용 (백엔드만)

```bash
cp backend/.env.example backend/.env
docker compose up --build
```

- API: <http://localhost:8000>
- SQLite DB는 호스트의 `./backend/data/`에 영속화

---

## 환경 변수

### Backend (`backend/.env`)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./somameet.db` | SQLAlchemy URL. 운영은 Postgres 권장 |
| `APP_BASE_URL` | `http://localhost:5173` | 프론트엔드 origin (CORS + 공유 URL 생성) |
| `CORS_EXTRA_ORIGINS` | `""` | 추가 허용 origin (콤마 구분). `*.vercel.app`은 정규식으로 자동 허용 |
| `SESSION_SECRET` | dev 기본값 | 운영에서는 32자 이상 랜덤 값 권장 (현재 단기 사용처 0) |
| `COOKIE_SAMESITE` | `lax` | 운영(크로스 오리진) `none` |
| `COOKIE_SECURE` | `false` | 운영 HTTPS `true`. `none + true` 조합 시 `Partitioned` 자동 부착 |
| `LLM_PROVIDER` | `template` | `template` 또는 `upstage` |
| `UPSTAGE_API_KEY` | `""` | <https://console.upstage.ai>에서 발급 |
| `UPSTAGE_BASE_URL` | `https://api.upstage.ai/v1` | OpenAI 호환 endpoint |
| `UPSTAGE_MODEL` | `solar-pro3` | 사용 모델 |
| `UPSTAGE_TIMEOUT_SECONDS` | `45` | 단일 호출 타임아웃 |

### Frontend

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | 백엔드 base URL |

---

## 주요 API 엔드포인트

전부 `/api` 프리픽스. 응답은 JSON. 에러는 `{ error_code, message, suggestion, ... }` 형식.

| 메서드 | 경로 | 권한 | 설명 |
|--------|------|------|------|
| `POST` | `/api/meetings` | 누구나 | 회의 생성 (range / picked 모드) |
| `GET` | `/api/meetings/{slug}` | URL만 | 회의 상세 + 진행률 + `submitted_nicknames` + `required_nicknames` + 본인 `my_busy_blocks` |
| `PATCH` | `/api/meetings/{slug}/settings` | URL만 (확정 전) | 회의 설정 수정. 확정 후 호출 시 409 `already_confirmed` |
| `POST` | `/api/meetings/{slug}/calculate` | URL만 (1명+ 제출) | 결정론적 후보 (LLM 0회) |
| `POST` | `/api/meetings/{slug}/recommend` | URL만 (1명+ 제출) | LLM 1회 + 재시도 최대 3회 + 후보별 reason/share_message_draft |
| `POST` | `/api/meetings/{slug}/confirm` | URL만 | 시각 확정 + 공유 메시지 저장. race 시 409 `already_confirmed` |
| `POST` | `/api/meetings/{slug}/participants` | 누구나 | 등록 — PIN 매칭 시 재진입(login) 통합 처리 |
| `POST` | `/api/meetings/{slug}/participants/login` | PIN 보유자 | PIN 재진입 (frontend는 더 이상 호출 안 함, API 호환용으로 유지) |
| `PATCH` | `/api/meetings/{slug}/participants/me` | 본인 쿠키 | 닉네임/PIN/`is_required` 토글 (`exclude_unset` 기반 부분 업데이트) |
| `POST` | `/api/meetings/{slug}/availability/manual` | 본인 쿠키 | 수동 가용 시간 제출 (last-write-wins, 빈 제출 허용) |
| `POST` | `/api/meetings/{slug}/availability/ics/parse` | 본인 쿠키 | ICS 파일 파싱만 (DB 저장 없음). frontend가 manual 그리드에 pre-fill |
| `POST` | `/api/meetings/{slug}/availability/ics` | 본인 쿠키 | (legacy) ICS 즉시 commit. frontend 미사용, 외부 호환용 유지 |
| `GET` | `/api/meetings/{slug}/timetable` | URL만 | 시간대별 가용 인원 |
| `GET` | `/api/health` | 누구나 | 헬스체크 |

### 에러 코드 카탈로그(주요)

| `error_code` | HTTP | 설명 |
|--------------|------|------|
| `meeting_not_found` | 404 | 회의 없음 |
| `participant_required` | 403 | 본인 인증 필요 |
| `invalid_pin` | 401 | PIN 불일치 |
| `pin_not_set` | 409 | PIN 미설정 닉네임 |
| `nickname_conflict` | 409 | 닉네임 중복 |
| `insufficient_responses` | 409 | 1명도 제출 안 함 |
| `ics_parse_failed` | 400 | ICS 파싱 실패 |
| `validation_error` | 400 | Pydantic 검증 실패 |
| `candidate_not_in_windows` | 400 | 후보가 추천 windows 밖 |
| `slot_not_on_grid` / `slot_duration_mismatch` / `slot_out_of_range` | 400 | 확정 슬롯 검증 실패 |
| `already_confirmed` | 409 | 이미 확정된 회의 (race 보호) |
| `llm_unavailable` | 503 | LLM 호출 불가 (template 전환 권장) |
| `slug_collision` | 503 | slug 생성 5회 재시도 실패 |

---

## 테스트

### Backend

```bash
cd backend
pip install -e ".[dev]"
pytest                          # 전체 (현재 114 passed, 1 skipped)
pytest -m unit                  # scheduler, ICS 파서, 토큰, LLM 어댑터
pytest -m integration           # meeting flow, recommend
pytest -m acceptance            # S1~S11 + S1b + S12~S15 시나리오
```

스킵되는 1개는 `UPSTAGE_API_KEY`가 없을 때의 Upstage live 검증 테스트입니다. 키 발급 후 다시 실행해 privacy invariant(S11)를 라이브로 한 번 더 확인하는 절차가 권장됩니다.

### Frontend (E2E)

```bash
cd frontend
pnpm test:e2e              # CLI (E1_full_flow.spec.ts)
pnpm test:e2e:ui           # Playwright UI 모드
```

E1은 골든패스 + 캘린더형 타임테이블의 `grid-row span` 셀 병합 어설션 + 스크린샷 캡처(`test-results/timetable-merged.png`)를 자동 수행합니다.

---

## 사용자 흐름 (3분 데모)

1. `/`에서 회의 생성 — 제목, 날짜(범위 탭 또는 개별 선택 탭), 회의 길이(30~180분), 진행 방식(온라인/오프라인/상관없음), 이동 버퍼(0~120분), 시작·종료 시간
2. 생성 즉시 `/m/{slug}`로 이동. 회의 페이지 상단에 **공유 URL + QR 코드**
3. 참여자 단일 폼: **닉네임 + 4자리 PIN(선택) + 필수 참여자 체크박스(선택)**
   - 같은 닉네임 + PIN 입력 시 자동 재진입(login) 처리
4. 가용 시간 입력
   - **직접 입력 탭**: 30분 단위 캘린더형 그리드 드래그
   - **ICS 탭**: 파일 선택 → "ICS 불러오기" → 자동으로 직접 입력 탭 점프 + 그리드에 pre-fill → 검토/수정 → "가용 시간 저장"
5. 5초 polling으로 다른 참여자 제출 즉시 반영. 제출자 chip(★ 필수 / ✓ 일반)과 "필수 미제출" 경고가 함께 표시
6. **결과 보기** — deterministic 후보. 한 번 더 보고 싶으면 **추천받기**(LLM, 5분 쿨타임)
7. 후보 선택 → 메시지 검토 다이얼로그(2단계 게이트) → 확정 → 공유 메시지 복사

---

## 개인정보 보호 원칙

> **계산은 결정론적 코드, 설명만 LLM**.

- DB 스키마에 이벤트 제목/장소/설명 컬럼 **없음** (`busy_blocks` 테이블은 `start_at`, `end_at`만 보유)
- ICS 파서가 시작/종료 시간만 추출하고 SUMMARY/LOCATION/DESCRIPTION을 폐기
- LLM 호출 payload에 포함되는 항목:
  - 회의 메타데이터: `title`, `location_type`, `duration_minutes`, `offline_buffer_minutes`
  - candidate windows: 시작/종료 시각, available_count, available/unavailable 닉네임
- LLM payload에 절대 포함되지 않는 항목: 이벤트 제목, 장소, 설명, 외부 캘린더 토큰
- `tests/acceptance/test_acceptance_S1_S11.py` S11 시나리오가 prompt spy로 invariant를 강제

`my_busy_blocks` 응답은 본인 쿠키 보유자에게만 자기 자신의 블록을 노출합니다 (cross-leak 없음). 미제출 참여자는 `null` 반환으로 "첫 진입 시 그리드 100% 채움" 버그를 방지합니다 (v3.25).

---

## 보안 한계 (MVP)

운영 진입 전 반드시 점검할 항목:

- **PIN 평문 저장** (Q7) — 운영 진입 시 bcrypt 해시 전환 필요. `participants.pin` 컬럼 마이그레이션 + 등록/로그인 핸들러 비교 로직 변경
- **abuse 방어 미적용** — confirm/추천/닉네임 변경에 server-side rate-limit 없음. 현재는 frontend 5분 쿨타임만
- **Path B (organizer 제거)** — 공유 URL 보유자는 누구나 확정 가능. 사고 방지는 다이얼로그 2단계 게이트와 `already_confirmed` 409 race 보호로 흡수
- **외부 캘린더 OAuth 미연동** (Q3) — Google free/busy 등은 5/10 데모 범위 외
- **모바일 cross-site cookie**: `Partitioned` 자동 부착으로 Chrome 114+/Safari 17+는 OK. 그 미만 또는 강한 ITP 환경은 본질적으로 same-origin 통합(Vercel rewrite proxy)이 필요

---

## 알려진 미해결 사항(Open Questions)

- `meetings.include_weekends` 컬럼은 v3.21에서 dead code화 — 후속 cleanup 라운드에서 컬럼/마이그레이션/필터 제거 예정
- `api.loginParticipant` (frontend)는 dead code — 호출처 0
- 타임테이블 metric은 raw 30분 가용 카운트, 추천 엔진은 회의 길이+버퍼 적용 — 사용자 혼란 가능 (운영 가이드: 버퍼 조정으로 해결)
- Tailwind v3 + hex CSS-var의 `bg-primary/<alpha>` 비호환 — `Timetable`만 inline rgba로 우회. 본질 해결은 토큰을 RGB 트리플 형식으로 변환
- `tests/e2e/scripts/{smoke_permissions,verify_gemini_live}.py` — Path B 변화로 깨질 수 있음. 별도 정리 필요
- 필수 참여자 trust 모델: 자기 self-mark만. 대규모/공개 도입 시 abuse 방어 모델 검토 필요

---

## 마일스톤

| 날짜 | 목표 |
|------|------|
| 2026-04-29 | 1차 오프라인 회의 — 주제 결정 (개인정보 보호 공유캘린더) |
| 2026-05-01 | 2차 오프라인 회의 — 팀명/프로젝트명 SomaMeet 확정, 기획서 분담 |
| 2026-05-02 | 1차 기획서 제출 (Google Docs) |
| 2026-05-03 | 2차 온라인 코칭 — 각자 AI로 데모 개발 시작 |
| 2026-05-05 | 3차 온라인 코칭 — 각자 데모 발표 |
| 2026-05-06 | 3차 오프라인 회의 — 5개 데모 비교, 통합 베이스/역할/마일스톤 확정 |
| 2026-05-08 | 4차 오프라인 회의 — MVP 점검 |
| **2026-05-10 23:59** | **데모 코드 제출 마감** |
| 2026-05-13 | 발표/데모 리허설 |
| 2026-05-14 | 최종 제출 (배포/자료/캡처) |
| **2026-05-15 13:30~15:30** | **최종 발표 / 데모데이** |

---

## 참고 문서

본 README의 결정 근거가 되는 원본 문서들은 통합 기획 레포(`somameet/`)에 있습니다.

- `회의록/2026-04-29_1차_오프라인_회의록_보고용_초안.md` — 주제 선정
- `회의록/2026-05-01_2차_오프라인_회의록_보고용.md` — 팀명/기획서 분담
- `회의록/2026-05-03_2차_온라인_코칭_회의록.md` — AI 활용 배틀 합의
- `회의록/2026-05-06_3차_오프라인_회의_데모분석_및_회의방향.md` — 5개 데모 비교 + 통합 베이스 결정
- `기획서/구현_위임_스펙.md` (v3) — API/DB/권한/알고리즘/LLM 경계 단일 기준 문서
- `기획서/구현_위임_스펙_추가.md` (v1, Phase 1~12) — Joonggon 비주얼 흡수, target 제거, Path B
- `기획서/구현_위임_스펙_추가v2.md` (v2, Phase 9~26) — 즉시 navigate, 캘린더형 transpose, 단일 폼 통합
- `기획서/구현_위임_스펙_추가v3.md` (v3, Phase 27~47) — 5초 polling, 필수 참여자, 3-tier, 설정 수정
- `기획서/구현_위임_스펙_추가v4.md` (v4, Phase 48~53) — ICS parse-then-prefill, Partitioned 쿠키, 2시간 spread 강제
- `프로젝트_맥락.md` — 프로젝트 개요/원칙/MVP 범위
- `전체일정.md` — 회의/코칭/제출 마감 일정
