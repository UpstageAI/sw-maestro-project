# FE/BE 분리 스펙

## 목표

MVP에서 Streamlit 단일 파일로 구현된 FE/BE를 분리한다.
FastAPI 서버(`server.py`)가 기존 비즈니스 로직을 HTTP API로 노출하고,
React 앱(`frontend/`)이 해당 API를 호출하여 UI를 렌더링한다.

## 배경

`local-mvp-spec.md`에서 "완전한 FE/BE 분리"는 팀 규모 확장 시 다음 개선 항목으로 명시됨.
현재 팀이 FE 작업을 별도로 진행하기로 결정하여 이 스펙을 작성한다.

## 범위

### 포함
- FastAPI 서버 (`server.py`): 수집, 브리핑 생성, 이메일 전송, 설정 조회 엔드포인트
- React 프론트엔드 (`frontend/`): Vite + React + TypeScript + Tailwind CSS + shadcn/ui
- 기사 카드 그리드 UI (3열)
- 단계별 진행 표시 (① 입력 → ② 수집 → ③ 브리핑)

### 제외
- `app.py` (Streamlit) 삭제 — 병행 유지
- `daily_news_agent/` 비즈니스 로직 수정
- 배포 설정 (Docker, CI/CD 등)
- 인증/로그인

## API 설계

### GET /api/settings
현재 실행 환경 설정 반환.

응답:
```json
{
  "ai_mode": "Demo",
  "news_source": "Google only",
  "chroma_path": "data/chroma",
  "collection_name": "...",
  "per_keyword_limit": 3,
  "top_k": 5,
  "email_to_default": "recipient@example.com"
}
```

- `news_source`: `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET`가 모두 설정되어 있으면 `"Naver(한글) + Google"`, 그렇지 않으면 `"Google only"`
- `email_to_default`: `.env`의 `EMAIL_TO_DEFAULT` 값, FE 이메일 입력 필드 기본값으로 사용

### POST /api/collect
뉴스 수집 및 Vector DB 저장.

요청:
```json
{
  "interest": "AI 산업 동향",
  "keyword_text": "AI, 반도체, 스타트업",
  "per_keyword_limit": 3
}
```

응답: `CollectionResult` (기사 목록 포함)

### POST /api/briefing
수집된 기사를 바탕으로 브리핑 생성.

요청: `CollectionResult` + `top_k`

응답: `BriefingResult` (브리핑 마크다운 + 선별 기사 목록 포함)

### POST /api/send-email
브리핑 결과를 이메일로 전송.

요청:
```json
{
  "recipient": "user@example.com",
  "briefing_result": { ... }
}
```

응답: `{ "success": true }`

## 프론트엔드 컴포넌트

```
App
├── Header
├── Sidebar (설정값 조정, AI 모드 뱃지, 뉴스 소스 뱃지)
└── Main
    ├── StepIndicator
    ├── InputSection
    ├── ActionButtons
    ├── CollectionMetrics
    ├── BriefingSection (마크다운 렌더링)
    ├── ArticleGrid (3열 카드)
    └── EmailSection
```

## 실행 방법

```bash
# 백엔드
uvicorn server:app --reload --port 8000

# 프론트엔드
cd frontend && npm run dev
```

## Naver 연동 대응 (2026-05-09-naver-search-integration.md 반영)

`server.py`는 `app.py`와 동일하게 `NewsRouter`를 통해 Naver/Google을 라우팅한다.

- `Settings.naver_client_id`/`naver_client_secret`가 모두 있으면 `NaverNewsClient`를 `NewsRouter`에 주입
- 없으면 `naver_client=None` (Google only)
- `/api/settings` 응답에 `news_source` 필드 포함
- React Sidebar에 뉴스 소스 뱃지 표시 (`Naver+Google` / `Google only`)

## UI 디자인 개선 이력 (2026-05-09)

전체 컴포넌트 디자인을 Toss 앱 스타일에 가깝게 개선.

- **헤더**: `bg-slate-900` 다크 헤더 + 인디고 아이콘 로고 + AI 모드 뱃지 글로우 효과
- **컬러 팔레트**: blue-600 → indigo-600 / emerald로 통일 (primary 버튼, 슬라이더, 태그, 링크)
- **카드**: `rounded-xl` → `rounded-2xl`, `shadow-sm` 추가, hover 시 `hover:shadow-lg hover:-translate-y-0.5` 애니메이션
- **버튼**: 아이콘 추가 (다운로드 / 문서 아이콘), 스피너 애니메이션 로딩 상태, hover 시 shadow 강화
- **StepIndicator**: 완료 단계 체크마크 원형 뱃지, 활성 단계 shadow 추가
- **CollectionMetrics**: 녹색 배경 → 흰 카드, 숫자를 `text-3xl font-bold`로 강조, 항목별 컬러 구분 (indigo/emerald/slate)
- **Sidebar**: 섹션 헤더 uppercase 레이블 추가, 슬라이더 min/max 숫자 표시
- **ArticleCard**: 제목 hover 시 indigo 컬러 전환, 원문 보기 버튼을 indigo 배경 pill로 변경
- **EmailSection**: 이메일 아이콘 추가, 성공/오류 메시지를 컬러 배경 pill로 개선
- **입력 필드**: focus 시 `ring-2 ring-indigo-100` 포커스 링 추가
- **로딩 인디케이터**: `animate-pulse` → 스피너 SVG + 인디고/슬레이트 배경으로 변경

## 이메일 HTML 템플릿 추가 (2026-05-09)

`daily_news_agent/mail_sender.py`에 HTML 이메일 렌더링 추가. 기존 plain text 발송에서 HTML 멀티파트로 변경.

- `_build_briefing_html`: 다크 헤더(Daily News Agent 로고 + 날짜/관심분야) + 브리핑 섹션 + 기사 카드(태그, 원문보기 버튼) + 푸터
- `_markdown_to_html`: 브리핑 마크다운(`## 제목`, `- 항목`, `**굵게**`, `[링크](url)`)을 인라인 스타일 HTML로 변환
- `_inline_markdown`: `[text](url)` → `<a>` 링크, `**bold**` → `<strong>` 변환
- `build_briefing_email_payload`에 `html_text` 필드 추가 — 기존 `plain_text`는 폴백으로 유지

## UI 버그 수정 이력

- **브리핑 링크 오버플로**: 긴 URL이 카드 밖으로 넘어가는 문제 → prose 영역에 `break-words`, `[&_a]:break-all` 추가
- **브리핑 링크 클릭**: 마크다운 내 plain URL이 클릭 안 되는 문제 → `remark-gfm` 플러그인 추가 + `<a target="_blank">` 처리
- **이메일 기본값 미반영**: `EMAIL_TO_DEFAULT` 설정값이 FE 입력 필드에 채워지지 않는 문제 → `/api/settings`에 `email_to_default` 추가, `EmailSection`에서 `useEffect`로 반영
- **새로고침 시 상태 초기화**: 브리핑 결과가 새로고침 후 사라지는 문제 → `localStorage`에 `collectionResult`, `briefingResult` 저장/복원
- **Demo 모드 링크 표시**: 브리핑에 긴 URL이 그대로 노출 → `ai_client.py`에서 `[원문 보기](url)` 마크다운 형식으로 변경
- **Upstage 모드 링크 표시**: LLM이 긴 URL을 출력하는 문제 → `summarizer.py` 프롬프트에 `[원문 보기](url)` 형식 명시
- **브리핑 마크다운 스타일 미적용**: `prose` 클래스가 동작 안 하는 문제 → `@tailwindcss/typography` 플러그인 설치 및 적용

## 검증 기준

- `GET /api/settings` 응답 정상 (`news_source`, `email_to_default` 필드 포함)
- Demo 모드에서 수집 → 브리핑 전체 플로우 동작
- 기사 카드 3열 그리드 표시
- 브리핑 마크다운 내 URL 클릭 시 새 탭으로 열림
- 이메일 입력 필드에 `EMAIL_TO_DEFAULT` 값 자동 입력
- Naver 키 없을 때 사이드바에 `Google only` 표시
- 이메일 전송 버튼 동작 (SMTP 설정 시)
- `python3 -m compileall server.py` 통과
