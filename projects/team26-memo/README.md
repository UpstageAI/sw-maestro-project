<div align="center">

# 🎯 MeetFlow AI

**회의록을 5초 만에 회의 요약·놓친 안건·다음 회의 안건·실행 항목으로 자동 변환하는 AI SaaS**

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.39-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Tests](https://img.shields.io/badge/tests-35%20passed-brightgreen)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()

</div>

---

## 📌 한눈에 보기

| | |
|---|---|
| **무엇을 하나요?** | 회의 안건과 회의록(STT/메모)을 입력하면 ① 요약 ② 다루지 못한 안건 ③ 다음 회의 안건 ④ 담당자·기한 포함 실행 항목을 자동 생성합니다 |
| **누가 쓰나요?** | 매주 회의록을 정리해야 하는 PM·팀 리드, 진행 사항 추적이 어려운 분산 팀, 회의 후 액션 아이템을 놓치는 모든 팀 |
| **왜 좋은가요?** | LLM 키 없이도 **오프라인 한국어 휴리스틱**으로 즉시 동작, 키가 있으면 OpenAI / Gemini / Anthropic 중 자유 선택, 외부 호출 실패 시 자동으로 오프라인 폴백 |
| **얼마나 빠른가요?** | 평균 응답 ~10ms (오프라인) / ~2~5초 (LLM) |

---

## ✨ 주요 기능

- 🧠 **멀티 LLM 프로바이더 추상화** — `LLM_PROVIDER` 환경변수 하나로 OpenAI · Gemini · Anthropic · Offline 즉시 전환
- 🛡️ **자동 폴백 (Graceful Degrade)** — 외부 LLM 실패/타임아웃 시 한국어 휴리스틱으로 무중단 응답
- 🇰🇷 **한국어 특화 추출기** — 한국 성씨 88종, 호칭 패턴(`홍길동 님이`), 일반명사 231개 블록리스트로 인명 오탐 최소화
- 📅 **자연어 날짜 파싱** — `2026-05-10`, `5월 10일`, `오늘`, `내일`, `다음주 월요일` 모두 인식
- 🎯 **누락 안건 자동 탐지** — 안건 vs 회의록 키워드 자카드 유사도(임계 0.25)로 빠뜨린 안건을 표시
- 📋 **다음 회의 안건 자동 제안** — 누락 안건 + 미해결 토픽을 결합해 차기 안건 초안 생성
- 🎨 **모던 SaaS 대시보드 UI** — Streamlit 기반, 그라디언트 카드 / 통계 칩 / 다운로드 / 예시 데이터 채우기
- 🐳 **Docker Compose 1-Command 배포** — `docker compose up` 한 줄로 풀스택 실행
- ✅ **35개 자동화 테스트** — pytest + FastAPI TestClient 로 회귀 보호

---

## 🏗️ 아키텍처

```
┌────────────────────────┐         POST /analyze         ┌──────────────────────────────┐
│   Streamlit Frontend   │  ──────────────────────────▶  │      FastAPI Backend         │
│   (port 8501)          │   {agenda, transcript}        │      (port 8000)             │
│                        │  ◀──────────────────────────  │                              │
│   • 입력 폼            │   {summary, missed_agenda,    │   ┌──────────────────────┐  │
│   • 결과 카드          │    next_agenda, action_items} │   │  build_provider()    │  │
│   • CSV/MD 다운로드    │                                │   │     │                │  │
└────────────────────────┘                                │     ▼                    │  │
                                                          │   ┌──────────────────┐  │  │
                                                          │   │ FallbackProvider │  │  │
                                                          │   └──────┬───────────┘  │  │
                                                          │          │ 실패 시       │  │
                                                          │   ┌──────┴───────────┐  │  │
                                                          │   │ OpenAI / Gemini  │  │  │
                                                          │   │ Anthropic /      │  │  │
                                                          │   │ Offline (휴리스틱)│  │  │
                                                          │   └──────────────────┘  │  │
                                                          └──────────────────────────────┘
```

### 디렉터리 구조

```
MeetingMoment/
├── backend/                    # FastAPI 백엔드
│   ├── app.py                  # 엔트리포인트, 라우팅, 미들웨어
│   ├── schemas.py              # Pydantic 요청/응답 모델
│   ├── llm.py                  # LLM 프로바이더 추상화 + build_primary_provider
│   ├── prompts.py              # 한국어 시스템/유저 프롬프트 + RETRY_HINTS
│   ├── extractor.py            # 오프라인 한국어 휴리스틱 엔진
│   ├── requirements.txt
│   ├── Dockerfile.backend
│   ├── .env.example
│   ├── agents/                 # LLM 연결 보강 에이전트
│   │   ├── __init__.py
│   │   ├── mainAgent.py        # 품질 검사, 재시도, offline 폴백 총괄
│   │   └── subAgent.py         # LLM 1회 호출, 청킹, 타임아웃, Rate Limit
│   └── tests/                  # pytest (35 cases)
│       ├── test_app.py         # API 엔드포인트 + Fallback
│       └── test_extractor.py   # 인명/날짜/액션/누락안건
├── frontend/                   # Streamlit 대시보드
│   ├── ui.py                   # MeetFlow AI UI (MT 샘플 포함)
│   ├── requirements.txt
│   └── Dockerfile.frontend
├── docker-compose.yml          # 풀스택 오케스트레이션
└── README.md
```

---

## 🚀 빠른 시작

### 옵션 A — Docker Compose (권장, 1 줄)

```bash
docker compose up --build
```

- 프론트엔드: <http://localhost:8501>
- 백엔드 API: <http://localhost:8000>
- 헬스체크: <http://localhost:8000/healthz>

### 옵션 B — 로컬 Python (개발용 / Docker 없이)

Docker 없이 호스트 머신에서 직접 두 개의 프로세스(백엔드 + 프론트엔드)를 띄우는 방법입니다. 이 README의 모든 명령은 **Windows PowerShell** 기준이며, macOS/Linux는 `python3 -m venv venv && source venv/bin/activate` 로 가상환경 활성화 부분만 바꿔 사용하면 됩니다.

#### 0) 사전 준비

- Python **3.11+** 설치 (`python --version` 으로 확인)
- 8000(백엔드) / 8501(프론트엔드) 포트가 사용 중이지 않을 것
- (선택) LLM API 키 — 없어도 **오프라인 모드**로 즉시 동작

#### 1) 저장소 클론 & 가상환경

```powershell
git clone https://github.com/<your-org>/MeetingMoment.git
cd MeetingMoment

# 가상환경 (백엔드/프론트 공용)
python -m venv venv
.\venv\Scripts\Activate.ps1

# 의존성 설치 (백엔드 + 프론트엔드 모두)
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

#### 2) (선택) LLM 프로바이더 설정

기본값은 `offline` 입니다. 외부 LLM을 쓰려면 아래 중 하나를 환경변수로 설정하세요.

```powershell
# OpenAI 사용 예
$env:LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "sk-..."

# Gemini 사용 예
# $env:LLM_PROVIDER = "gemini" ; $env:GEMINI_API_KEY = "AIza..."

# Anthropic 사용 예
# $env:LLM_PROVIDER = "anthropic" ; $env:ANTHROPIC_API_KEY = "sk-ant-..."
```

> 키가 잘못됐거나 호출이 실패해도 자동으로 오프라인 휴리스틱으로 폴백되므로 서비스가 멈추지 않습니다.

#### 3) 백엔드 실행 (터미널 #1)

```powershell
# 프로젝트 루트에서
$env:PYTHONPATH = (Get-Location).Path
python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000 --reload
```

정상 기동 확인 (다른 창):
```powershell
# 200 OK + provider 이름이 출력되어야 함
curl http://127.0.0.1:8000/healthz
# 예: {"status":"ok","provider":"offline","version":"1.0.0"}
```

#### 4) 프론트엔드 실행 (터미널 #2)

```powershell
# 새 PowerShell 창에서
cd MeetingMoment
.\venv\Scripts\Activate.ps1

$env:BACKEND_URL = "http://127.0.0.1:8000/analyze"
python -m streamlit run frontend/ui.py `
    --server.port 8501 `
    --server.headless true `
    --browser.gatherUsageStats false
```

브라우저에서 <http://localhost:8501> 접속 → 사이드바 **"📋 예시 데이터 채우기"** → **"✨ AI 분석 시작"** 클릭.

좌측 사이드바의 **시스템 상태** 카드에 초록색 펄스가 떠 있으면 백엔드가 정상 연결된 것입니다.

#### 5) 종료 / 재시작

```powershell
# 각 터미널에서 Ctrl+C 로 정지

# 포트가 점유된 채로 안 끊길 때 (PowerShell)
Get-NetTCPConnection -LocalPort 8000 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
Get-NetTCPConnection -LocalPort 8501 | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }
```

#### 6) 자주 겪는 문제

| 증상 | 원인 / 해결 |
|---|---|
| `ModuleNotFoundError: backend` | `$env:PYTHONPATH` 를 프로젝트 루트로 설정했는지 확인 |
| 사이드바에 빨간 "백엔드 연결 불가" | 백엔드가 안 떠 있거나 `BACKEND_URL` 이 다름. `/healthz` 로 직접 확인 |
| `Address already in use` | 위의 5) 명령으로 8000/8501 점유 프로세스 종료 |
| Streamlit이 `localhost`만 듣고 외부에선 안 보임 | `--server.address 0.0.0.0` 옵션 추가 |
| LLM 호출 시 타임아웃 | 자동 폴백되어 결과는 나옴. 더 길게 기다리려면 `backend/app.py` 의 `REQUEST_TIMEOUT_SEC` 조정 |

---

## 📖 사용 방법

### 1️⃣ 웹 UI 사용

1. <http://localhost:8501> 접속
2. **회의 안건** 입력 (번호 매김 권장)
   ```
   1. Q3 마케팅 전략 검토
   2. 신규 기능 로드맵 논의
   3. 예산 배분 확정
   ```
3. **회의록** 입력 (`[시각] 화자: 발언` 형식 권장)
   ```
   [10:00] 김철수: Q3 마케팅 전략부터 보시죠.
   [10:10] 김철수: Q3 마케팅 예산안은 이영희 님이 5월 10일까지 정리해 주세요.
   [10:15] 이영희: 신규 기능 요구사항 문서는 박민준 님이 5월 7일까지 작성하기로 하시죠.
   ```
4. **AI 분석 시작** 클릭 → 4개 카드(요약/누락/다음/실행항목)가 자동 생성
5. 우측 상단 **다운로드** 로 Markdown 또는 CSV 내보내기

### 2️⃣ REST API 직접 호출

```bash
# 헬스체크
curl http://localhost:8000/healthz
# → {"status":"ok","provider":"offline","version":"1.0.0"}

# 분석 요청
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "agenda": "1. Q3 마케팅 전략\n2. 신규 기능 로드맵",
    "transcript": "[10:10] 김철수: 예산안은 이영희 님이 5월 10일까지 정리 부탁드립니다."
  }'
```

응답:
```json
{
  "summary": "예산안은 이영희 님이 5월 10일까지 정리 부탁드립니다.",
  "missed_agenda": "1. 신규 기능 로드맵",
  "next_agenda": "1. 신규 기능 로드맵 (이월)",
  "action_items": [
    { "who": "이영희", "when": "2026-05-10", "what": "예산안은 이영희 님이 5월 10일까지 정리 부탁드립니다" }
  ]
}
```

### 3️⃣ Python 클라이언트

```python
import requests

resp = requests.post(
    "http://localhost:8000/analyze",
    json={"agenda": "...", "transcript": "..."},
    timeout=30,
)
data = resp.json()
for item in data["action_items"]:
    print(f"[{item['when']}] {item['who']} — {item['what']}")
```

---

## ⚙️ LLM 프로바이더 설정

`backend/.env` 파일을 생성하고 원하는 프로바이더를 선택합니다.

```env
# 1) 오프라인 (기본값, 키 불필요)
LLM_PROVIDER=offline

# 2) OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini

# 3) Google Gemini
# LLM_PROVIDER=gemini
# GEMINI_API_KEY=...
# GEMINI_MODEL=gemini-1.5-flash

# 4) Anthropic Claude
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-3-5-haiku-latest
```

> 💡 **자동 폴백**: 외부 LLM 호출이 실패/타임아웃되면 백엔드는 자동으로 오프라인 휴리스틱으로 응답하고, 응답에 `_fallback=true` 디버그 키를 포함합니다(클라이언트에는 노출되지 않음).

---

## 🔌 API 레퍼런스

### `GET /healthz`

| 응답 | 설명 |
|---|---|
| `200` | `{ "status": "ok", "provider": "offline", "version": "1.0.0" }` |

### `GET /`

서비스 메타데이터 반환.

### `POST /analyze`

**Request**

| 필드 | 타입 | 제약 |
|---|---|---|
| `agenda` | string | 비어있지 않음, ≤ 10,000자 |
| `transcript` | string | 비어있지 않음, ≤ 200,000자 |

**Response (200)**

| 필드 | 타입 | 설명 |
|---|---|---|
| `summary` | string | 회의 핵심 요약 (~280자) |
| `missed_agenda` | string | 다루지 못한 안건 목록 |
| `next_agenda` | string | 다음 회의 추천 안건 |
| `action_items` | `ActionItem[]` | `{ who, when, what }` 배열 |

**Errors**

| 코드 | 상황 |
|---|---|
| `422` | 검증 실패 (빈 문자열, 길이 초과, 누락 필드, 잘못된 JSON) |
| `500` | 내부 오류 (`{ "detail": "..." }`) |

대화형 문서: <http://localhost:8000/docs>

---

## 🧪 테스트

```bash
cd MeetingMoment
$env:PYTHONPATH = (Get-Location).Path
python -m pytest backend/tests/ -v
```

```
backend/tests/test_extractor.py ........................  20 passed
backend/tests/test_app.py       ........................  15 passed
================================ 35 passed in 0.69s =================================
```

테스트 커버리지:
- ✅ 인명 추출 (한국 성씨 + 블록리스트 + 호칭 패턴)
- ✅ 날짜 파싱 (ISO / 한글 / 상대표현)
- ✅ 액션 문장 분류 + 담당자/기한/내용 분리
- ✅ 안건 분리 + 누락 탐지(자카드 유사도)
- ✅ `/analyze` 정상/거절(422)/거대 입력
- ✅ LLM 응답 JSON 파싱(코드펜스/trailing comma)
- ✅ FallbackProvider 폴백 동작

---

## 📈 성공 지표

기획서가 약속하는 핵심 수치를 한곳에 모았습니다. 각 지표의 상세 정의·측정 방식은 본문 해당 섹션을 참고하세요. 기계 가독 버전은 [`docs/success_metrics.json`](docs/success_metrics.json) 에 동일하게 유지됩니다.

| 분류 | 지표 | 목표/현재값 | 출처 섹션 |
|---|---|---|---|
| 성능 | 평균 응답 시간 (오프라인) | ~10ms | 한눈에 보기 |
| 성능 | 평균 응답 시간 (LLM) | 2~5초 | 한눈에 보기 |
| 품질 | 자동화 테스트 통과 | 35건 (extractor 20 + app 15) | 테스트 |
| 품질 | 누락 안건 탐지 자카드 유사도 임계값 | 0.25 | 주요 기능 |
| 품질 | 한국어 인명 추출 사전 | 한국 성씨 88종 + 블록리스트 231개 | 주요 기능 |
| 품질 | 출력 요약 길이 | ~280자 | API 레퍼런스 |
| 가용성 | 입력 제약 (안건) | ≤ 10,000자 | API 레퍼런스 |
| 가용성 | 입력 제약 (회의록) | ≤ 200,000자 | API 레퍼런스 |
| 가용성 | 지원 LLM 프로바이더 수 | 4종 (OpenAI · Gemini · Anthropic · Offline) | 주요 기능 |
| 가용성 | 외부 LLM 실패 시 동작 | 자동 오프라인 폴백 (무중단) | 주요 기능 |

---

## 🛠️ 기술 스택

| 영역 | 기술 |
|---|---|
| **Backend** | Python 3.12, FastAPI 0.115, Pydantic 2.9, Uvicorn 0.30 |
| **Frontend** | Streamlit 1.39, Requests |
| **LLM SDK** | openai 1.51, google-generativeai 0.8, anthropic 0.34 |
| **Test** | pytest 8.3, httpx 0.27 (TestClient) |
| **Infra** | Docker, Docker Compose, python:3.12-slim |

---

## 📊 개발 현황

- ✅ 프론트엔드 MeetFlow AI 리브랜딩 (커밋 `c78a6e2`)
- ✅ 백엔드 + LLM 추상화 + 35 테스트 (커밋 `d3514df`)
- ✅ Docker Compose 풀스택 오케스트레이션
- 🔜 회의록 STT 업로드 직접 처리
- 🔜 사용자 인증 + 회의 히스토리 저장
- 🔜 Slack / Notion / Jira 연동

---

## 🤝 기여

```bash
git checkout -b feat/your-feature
# 변경 후
python -m pytest backend/tests/ -v
git commit -m "feat: 설명"
git push origin feat/your-feature
```

---

## 📄 라이선스

MIT License © 2026 MeetFlow AI Team
