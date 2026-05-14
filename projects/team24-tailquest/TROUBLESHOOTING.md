# 트러블슈팅 & 개선 이력 (2026-05)

이 프로젝트(`tail-question`)에서 진행한 운영 배포·버그 픽스·UX 개선 기록.
시간 순으로 묶음 단위 정리. 각 항목: **증상 → 원인 → 픽스 → 변경 파일** 구조.

---

## 1. EC2 초기 배포

**목표**: fresh Ubuntu 26.04 EC2를 production-ready 상태로 만들기.

| 단계 | 결과 |
|---|---|
| 2GB swap 구성 (`/swapfile`, swappiness=10, /etc/fstab 영구화) | RAM 951Mi → 가상 2.95GiB |
| Python 3.12 (uv로 설치 — 시스템 3.14는 chromadb의 PyO3 호환 한계) | venv 구축 |
| Node 22.22 (Ubuntu 기본 패키지 — NodeSource 스크립트가 30분 멈춤 → 폴백) | npm ci 정상 |
| nginx 1.28.3 + certbot 4.0 + Let's Encrypt | 도메인 200 |
| `tq-backend.service`, `tq-frontend.service` (systemd) | 자동 부팅 + 재시작 |
| `.env` chmod 600 + `EnvironmentFile`로 시크릿 격리 | UPSTAGE_API_KEY 노출 방지 |

**외부 DB 미설치** — 사용자 결정. Chroma(파일 기반 SQLite) + `.materials/` 디렉토리만 영구화.

**상세 플랜**: 로컬 plan 파일 (저장소 비포함)

---

## 2. GitHub 레포 푸시 + CI/CD

**증상**: 초기 코드는 git 저장소가 아니었음. 자동 배포 파이프라인 부재.

**픽스**:
- 루트 `.gitignore` 작성 — `*.pem`, `.env`, `.env.*`, `.chroma/`, `.materials/`, `node_modules/`, `.venv/` 등 민감/빌드 산출물 차단
- `git init -b main` 후 `soma17th-ai24/tail-quest`로 푸시 (private)
- GitHub Actions 워크플로 3개:
  - `.github/workflows/deploy-backend.yml` — `backend/**` 변경 시 rsync → `uv pip install -e .` → `systemctl restart tq-backend`
  - `.github/workflows/deploy-frontend.yml` — `frontend/**` 변경 시 rsync → `npm ci && npm run build` → `systemctl restart tq-frontend`
  - `.github/workflows/ci.yml` — PR/push에 백엔드 import 스모크 + 프론트 mock 빌드 검증
- GitHub Secrets 3개 등록 (`gh secret set`): `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`

**uv pip 픽스**: 첫 deploy-backend 실패 (`.venv/bin/pip: No such file`) — `uv venv`는 pip 미포함. 워크플로를 `uv pip install -e . --python .venv/bin/python`으로 교체.

---

## 3. 분석 프롬프트 — "잘 모르겠어요" 응답 메타 회피

**증상**: 사용자가 "잘 모르겠습니다" 답변 시, 시스템이 모범답안을 가르치는 대신 메타 텍스트만 출력
> "짧게 설명드리면, 핵심 개념을 한 문장으로 정리할 수 있을 정도면 신입 면접에서는 충분합니다. 다음 질문은 알고 계신 분야로 넘어가볼게요."

**원인**: `backend/app/graph/prompts.py`의 `ANALYZER_SYSTEM` Step 2가 LLM에게 메타 구조를 전달했고("(3) '이 정도만 알아두시면 충분합니다' 같은 친절한 마무리"), Solar가 그 메타 어휘를 그대로 explanation 본문으로 복제.

**픽스** (`backend/app/graph/prompts.py`):
- Step 2 재작성: explanation을 **답의 실체**로 시작 강제 (예: "Spring Boot는 ~")
- 금지 어휘 명시: "충분합니다", "정리할 수 있을 정도면", "다음 질문으로 넘어가겠습니다", "짧게 설명드리면"
- one-shot 좋은 예 + 나쁜 예 동시 제공 (Spring Framework vs Spring Boot 케이스)
- mock 템플릿(`nodes.py:148-150`)도 같은 정신으로 정합

**검증**: 라이브 API 호출로 실제 답변 확인 — "Spring Framework는 의존성 주입(DI)과 IoC 컨테이너를 중심으로 한 자바 애플리케이션 프레임워크이며, ... Spring Boot는 ..."

---

## 4. 자동 로그인 잔존 (서버 재시작 시 로그인 화면 강제)

**증상**: 백엔드 재시작 후에도 브라우저 localStorage의 userId가 유지되어 `/login`을 건너뛰고 바로 `/chat`으로 진입.

**원인**: `frontend/lib/user.ts`의 `tq:user_id`가 localStorage 영구 저장.

**픽스**:
- `backend/app/main.py`: 프로세스별 무작위 `BOOT_ID` 생성, `/health`에 포함
- `frontend/lib/user.ts`: `syncWithServerBoot()` 헬퍼 — `/health`의 `boot_id`를 캐시한 값과 비교, 다르면 `tq:user_id` 삭제
- `app/page.tsx` + `app/login/page.tsx`: 라우팅 전에 sync 호출

**효과**: 서버 재시작마다 BOOT_ID 갱신 → 다음 페이지 로드 시 mismatch 감지 → userId 클리어 → `/login`으로.

---

## 5. 로고 정렬 / 클릭 라우팅 / "면접 시작" 광클

**증상 1 — 로고가 와이드 스크린에서 중앙 부근에 위치**:
- `top-nav.tsx`의 inner div가 `max-w-airbnb mx-auto`(1280px 컨테이너 중앙 정렬)을 사용 → 로고가 컨테이너 시작점에 붙어 시각적으로 가운데로 보임.
- **픽스**: `max-w-airbnb mx-auto` → `w-full`로 교체. 로고가 뷰포트 좌측 끝에 붙음.

**증상 2 — 로고 클릭 시 `/chat`으로**:
- `href="/"` → `/`가 로그인 시 `/chat`로 라우팅하므로 새 면접 시작 의도와 어긋남.
- **픽스**: `top-nav.tsx`의 Link `href="/onboarding"`으로 변경.

**증상 3 — "면접 시작" 광클 시 세션 2개 생성**:
- 근본 원인: React 18 Strict Mode의 dev 더블 발화 — `chat-shell.tsx`의 mount useEffect가 두 번 실행되어 `generateSeedQuestion`이 2회 호출 → DB 세션 2개.
- **픽스 1**: `chat-shell.tsx`에 `seedFiredRef = useRef(false)` 추가 — 두 번째 발화는 ref 체크 후 early return.
- **픽스 2**: `onboarding/page.tsx` + `materials/page.tsx`에 `starting` state로 첫 클릭 후 disable + "시작 중…" 라벨.

---

## 6. GitHub 자료 추가 — 60회/h Rate Limit

**증상**:
> GitHub 수집 실패: Client error '403 rate limit exceeded' for url 'https://api.github.com/...'

**원인**: 익명 GitHub API 호출은 IP당 60회/시간. 자료 1개 추가가 수십~수백 호출(트리 + blob) 누적.

**픽스**:
- `backend/app/config.py`: `github_token: str` 설정 추가
- `backend/app/ingestion/github.py`: 토큰 있으면 `Authorization: Bearer ...` 헤더 부착 → 60→5,000회/h
- `backend/app/api/materials.py`: 403 rate-limit 에러를 한국어 안내로 변환 ("backend/.env에 GITHUB_TOKEN=ghp_... 를 추가하면 5,000회/h로 늘어납니다.")
- `backend/.env.example`에 `GITHUB_TOKEN=` 항목 추가

**적용**: 사용자 fine-grained PAT (`github_pat_...`) 발급 → 로컬 `.env` + EC2 `.env` 등록 → 양쪽 백엔드 재시작. GitHub API 검증: `X-RateLimit-Limit: 5000` 응답 확인.

---

## 7. 첫 질문 citation 조작 / 키워드 seed 하드코드 / 온보딩 Step 3

**증상 1 — 마크다운 미사용 시에도 citation 표시**:
- 사용자: "참고자료가 README.md#Special Thanks to로 나오는데 질문은 Spring Boot 개념"
- 원인: `_try_material_seed`가 chunk를 받아 LLM에 넘긴 뒤 LLM이 chunk를 실제로 사용했는지 무관하게 citations 무조건 부착.
- **픽스** (`backend/app/graph/nodes.py:_try_material_seed`): chunk(heading + text 400자) 토큰과 LLM 생성 question 토큰의 자카드 overlap ≥2 일 때만 citation 부착. "Special Thanks" 같은 비기술 섹션은 자동 누락.

**증상 2 — 키워드 입력 시 항상 같은 템플릿**:
- 사용자가 "쿠버네티스" 키워드 입력 → 항상 "혹시 쿠버네티스에 대해 알고 계신 내용을 자유롭게 설명해주실 수 있나요?"
- 원인: `_pick_seed_angle`이 키워드당 단일 일반 템플릿만 pool에 넣음. LLM이 그대로 echo.
- **픽스**: `_keyword_seed_angles(kw)` 헬퍼 신설 — 4종 angle (정의·등장 배경·작동 원리·비교) 펼쳐 pool에 추가. prompt rule 2도 "표현은 본인 말로 자연스럽게 변형 필수, 통째 복사 금지" 강화 + 나쁜 예 명시.
- 검증: `쿠버네티스` 입력 → "Docker Swarm이나 OpenShift가 있다면, 어떤 점에서 차이가 있는지…" 자연스러운 비교 질문 생성.

**증상 3 — 온보딩 Step 3 ("참고할 자료가 있나요?") 불필요**:
- **픽스** (`frontend/app/onboarding/page.tsx`): `STEPS` 2개로 축소, `Step3Materials` 컴포넌트 삭제, "다음" 버튼이 step 2에서 `/materials`로 직행.

**증상 4 — 도메인 + 키워드 동시 선택 (XOR 위반)**:
- **픽스**: `onToggle`에서 `setCustomKeywords([])`, `onKeywordsChange`에서 `setDomainIds([])`. KeywordInput `max=1`. UI 카피 "둘 중 하나만" 명시. canAdvance도 XOR 체크.

**증상 5 — 분석 패널 truncation (`...`)**:
- 원인: `analysis-rail.tsx`의 question 텍스트에 `line-clamp-3` 적용.
- **픽스**: clamp 제거, `whitespace-pre-wrap` + `break-keep`로 전체 표시. AnalysisCard를 토글로 (default 접힘, 클릭 펼침).

---

## 8. 로컬 서버 500 — Next.js dev proxy 타임아웃

**증상**: 꼬리질문에 "잘 모르겠습니다" 답변 시 브라우저 콘솔에 500 에러.

**원인**: 백엔드는 살아있고 처리 중 (analyzer + retriever + question_generator + Solar tool_calling 누적). Next.js dev rewrite 프록시의 기본 타임아웃 30초를 초과해 ECONNRESET 발생. 운영(EC2)은 nginx가 직접 8000으로 프록시하므로 영향 없음.

**픽스** (`frontend/next.config.mjs`):
```js
experimental: { proxyTimeout: 120_000 }  // 30s → 120s
```

---

## 9. 우측 분석 레일 재구성 + 사이드바 + 백엔드 속도 (6개 묶음)

**픽스 묶음**:

| # | 변경 | 파일 |
|---|---|---|
| 1 | 분석 이력을 최상단으로 이동, 각 turn 카드 토글 안에 질문·답변 평가·질문 의도·약점 노트·참조 자료 통합 (`HistoryEntryCard`) | `analysis-rail.tsx` 전면 재작성 |
| 2 | 사이드바 점수 pill 제거. 도메인 비고 키워드 있으면 `사용자 지정 · 쿠버네티스` 표시 (`scopeLabel` 헬퍼) | `session-sidebar.tsx` |
| 3 | 세션 전환 시 분석 이력 6개로 부풀림 — `AbortController` + `propSessionId` deps + `seededSessionsRef: Set<string>`로 race fix. 진입 시 `setTurns([])`로 이전 세션 잔여 즉시 클리어 | `chat-shell.tsx` mount effect 재구성 |
| 4 | "세션 진행 중" pill 제거 (정적 라벨, 가치 없음) | `chat-shell.tsx:518-521` |
| 5 | 우측 레일 외부 wrapper에 `pt-md pr-xl pb-md` 추가 (상단바와 시각적 여백) | `chat-shell.tsx` |
| 6 | 백엔드 속도 개선 — 30s → 12~15s | (아래 상세) |

**Issue 6 상세**:
- `web_search.py`: `asyncio.wait_for(timeout=5.0)`로 Tavily 호출 5초 캡 (무한 대기 방지)
- `nodes.py:knowledge_retriever_node`: `len(chunks) >= 2 && max(score) >= 0.4` 조건 추가 — Chroma가 충분하면 web fallback 자체 생략 (자료 첨부 세션은 거의 항상 skip)
- `nodes.py`: `tool_calling_chat`의 `max_iters` 3곳 모두 `2 → 1` (round-trip 1회면 충분, Solar 호출 1회당 ~2-3s 절감)

---

## 10. "면접관이 첫 질문을 준비중입니다" 영구 stuck

**증상**: GitHub 자료 첨부 후 "면접 시작" 클릭 시 로딩 화면에서 안 넘어감. 백엔드 로그엔 `POST /sessions/seed 200 OK` 정상.

**원인**: Issue 9에서 도입한 `AbortController`가 React 18 Strict Mode dev double-fire와 충돌:
1. ChatShell mount → 첫 effect → 시드 호출 시작 (`ctrl1`)
2. Strict Mode가 cleanup 강제 호출 → `ctrl1.abort()`
3. 두 번째 effect → `seededSessionsRef.has("__new__")` true → early return
4. 시드 응답 도착 → `aborted=true` 가드로 commit + `setSeeding(false)` 모두 차단
5. 결과: BE 200 OK인데 FE는 영구 `seeding=true`

**픽스** (`frontend/next.config.mjs`):
```js
reactStrictMode: false  // dev 더블 발화 제거
```
- 운영 build는 strict mode 자동 single-fire이므로 영향 없음

---

## 11. 분석 카드 표시 미세 조정

**증상 1 — 답변 점수(`75점` 등) 표시 부담**:
- **픽스**: `HistoryEntryCard`의 답변 평가 섹션에서 `{turn.score}점` 블록 제거. 퀄리티 pill(`충실`/`모름·짧음`/`오답`)만 표시.

**증상 2 — 참조자료 chunk 텍스트가 너무 길게 노출**:
- 원인: chunk 전체 텍스트 렌더 (큰 코드블록·TOC·연속 공백 포함).
- **픽스 1차** — `trimChunkExcerpt(text)`: 첫 문단 추출 + 240자 cap + `line-clamp-3`.
- **픽스 2차** — `trimChunkExcerpt(text, question)`: 질문 토큰 추출(한글 조사 제거 + stopword 필터) → 문단별 매칭 점수 → 최고 점수 문단 → 첫 매칭 키워드를 중앙으로 240자 윈도우. 결과: 질문과 진짜 관련 있는 부분만 노출.

---

## 12. **답변 안 한 질문이 분석 이력에 나타나는 버그** (Critical)

**증상**: 사용자가 답변하지 않은 follow-up 질문이 분석 이력 + 대화 흐름에 나타남.
> "request 스코프... 이 질문이 안 보였었고, 격리 수준 질문에 답변했어. 새로고침하니 답변하지 않았던 질문이 나타나."

**원인 진단** — LangGraph 노드 문제 아님. **`backend/app/api/sessions.py:247`의 `/sessions` 엔드포인트가 매 submit 마지막에 `result.follow_ups[0]`를 무조건 turn으로 pre-allocate** + **FE는 답변 품질이 `uncertain`/`incorrect`면 그 follow-up을 무시하고 `/sessions/seed`로 도메인 switchSeed를 새로 만듦** — 사용자가 절대 보지 못한 follow-up turn이 DB에 orphan으로 누적.

세션 `s_66c11ba6` 6 turns 분석:
- t_785bb981 (Q1, follow_up, "잘 모르겠습니다") → 답변 ✓
- **t_9e1c2a77 (@RequestScope, follow_up, no answer)** ← Q1 submit이 만든 orphan, 사용자 못 봄
- t_11125e3d (Q3, seed, "잘 모르겠습니다") → 답변 ✓ (FE switchSeed)
- **t_e55f4773 (dirty/non-repeatable read, follow_up, no answer)** ← Q3 submit이 만든 orphan
- t_8eff0bea (Q5, seed, no answer) ← Q3의 switchSeed (현재 활성)

**픽스 (2건)**:

1. **미래 방지** — `backend/app/services/session_store.py`에 `delete_trailing_unanswered_turn()` 헬퍼 추가, `backend/app/api/sessions.py`의 `/sessions/seed` 핸들러가 `session_id`를 받으면 `append_turn` 직전에 호출. 즉 FE가 switchSeed로 pivot할 때 BE가 직전에 만든 orphan을 자동 청소.

2. **기존 데이터 청소** — `backend/cleanup_orphans.py` 일회성 스크립트:
   - 각 세션에서 *마지막* unanswered turn(= 활성 질문)은 보존, 그 외 unanswered는 모두 삭제
   - 실행 결과: 3개 세션에서 총 6개 orphan 제거 (s_6f787d2b: 3개, s_9af0f760: 1개, s_66c11ba6: 2개)
   - s_66c11ba6에서 정확히 사용자가 보고한 Q2(@RequestScope) + Q4(dirty read) 삭제됨

---

## 부록 — 일관된 디자인 토큰

전 변경에서 다음 디자인 시스템 일관 유지 (Airbnb 스타일 토큰):
- 스페이싱: `xs`, `sm`, `md`, `lg`, `xl`
- 색상: `bg-canvas`, `bg-surface-soft`, `bg-surface-strong`, `bg-rausch`(Airbnb red)
- 텍스트: `text-ink`, `text-muted`, `text-subtle`, `text-on-primary`, `text-on-dark`
- 타이포: `text-display-{lg,md,sm}`, `text-title-{md,sm}`, `text-body-{md,sm}`, `text-caption-sm`, `text-uppercase-tag`
- 컴포넌트: `pill`, `btn-primary`, `btn-secondary`, `btn-tertiary-text`, `rounded-md`, `border-hairline`

`max-w-airbnb` (1280px) 컨테이너는 본문 영역에만 적용, 상단 nav는 `w-full`.

---

## 부록 — 운영 / 로컬 환경 차이

| 항목 | 로컬 (dev) | 운영 (EC2 nginx) |
|---|---|---|
| 프록시 | Next.js dev rewrite (120s timeout) | nginx → 직접 backend:8000 (300s) |
| Strict Mode | OFF (AbortController 충돌) | 자동 single-fire (production build) |
| .env | `backend/.env` (chmod 600) | `/home/ubuntu/tail-question/backend/.env` (chmod 600) |
| 시드 키 | `UPSTAGE_API_KEY`, `TAVILY_API_KEY`, `GITHUB_TOKEN` | 동일 (별도 등록) |
| 자동 배포 | 수동 재시작 | `git push` → GitHub Actions → systemctl restart |
| Boot ID | 매 재시작 갱신 → 자동 재로그인 강제 | 동일 |

---

## 변경 통계 (대략)

| 카테고리 | 파일 수 | 주요 영향 |
|---|---|---|
| 백엔드 graph (prompts/nodes/workflow) | 4 | 프롬프트 메타 회피 + citation 조건부 + 키워드 seed 다양화 + 속도 |
| 백엔드 API/services/storage | 4 | orphan 청소 + boot_id + GITHUB_TOKEN |
| 프론트 chat 컴포넌트 | 5 | 분석 레일 재구성 + race fix + 사이드바 정리 |
| 프론트 onboarding/page | 2 | XOR + Step 3 제거 |
| 프론트 next.config | 1 | proxyTimeout + strict mode off |
| CI/CD 워크플로 | 3 | deploy-be/fe + ci |
| 운영 인프라 | — | swap, nginx, certbot, systemd, GITHUB_TOKEN |
