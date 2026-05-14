# Stock Manager

한국 주식 시세 데이터를 기반으로 AI 투자 리포트를 생성하고, 리포트에 대한 후속 질문까지 대화형으로 처리하는 서비스입니다.

FastAPI 백엔드가 한국투자증권 OpenAPI에서 종목 시세와 일봉 데이터를 수집하고, LangGraph 기반 파이프라인이 수집, 컨텍스트 추출, 리포트 생성을 순차적으로 실행합니다. Streamlit 프론트엔드에서는 종목 코드를 입력해 리포트를 생성하고 차트, 요약 지표, 백엔드 처리 추적, 챗봇 응답을 한 화면에서 확인할 수 있습니다.

## 주요 기능

- 한국 주식 종목 코드 기반 시세 조회
- 최근 일봉 데이터 기반 캔들 차트 표시
- LangGraph 멀티 에이전트 워크플로우로 리포트 생성
- Upstage Solar 기반 리포트 및 챗봇 응답 생성
- KIS API 키 없이도 실행 가능한 mock 데모 모드
- 수집, 추출, 생성 단계별 처리 trace 제공
- Docker Compose를 통한 백엔드와 프론트엔드 동시 실행

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Backend | FastAPI, Uvicorn, Pydantic Settings |
| Frontend | Streamlit, Plotly, Pandas |
| Agent Workflow | LangGraph, LangChain Core |
| LLM | Upstage Solar API, OpenAI-compatible client |
| Stock Data | 한국투자증권 OpenAPI, mock JSON fallback |
| Runtime | Python 3.13, Docker, Docker Compose |

## 프로젝트 구조

```text
.
├── app/
│   ├── api.py               # FastAPI 엔드포인트
│   ├── config.py            # 환경 변수 설정
│   ├── kis_client.py        # 한국투자증권 OpenAPI 클라이언트
│   ├── stocks.py            # live/mock 종목 데이터 처리
│   ├── llm.py               # Upstage Solar 래퍼 및 stub fallback
│   └── agents/
│       ├── graph.py         # LangGraph 리포트 생성 플로우
│       ├── collector.py     # 종목 데이터 수집 및 청킹
│       ├── extractor.py     # 컨텍스트 추출
│       ├── reporter.py      # 투자 리포트 생성
│       └── chatbot.py       # 후속 질문 처리
├── frontend/
│   └── streamlit_app.py     # Streamlit UI
├── data/
│   └── demo_stocks.json     # mock 모드용 데모 데이터
├── scripts/
│   └── verify_demo_mode.py  # mock 모드 API 검증 스크립트
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 실행 모드

### Mock 모드

KIS API와 Upstage API 키 없이도 실행 가능한 데모 모드입니다. 발표, 리뷰, 로컬 확인에는 이 모드를 가장 쉽게 사용할 수 있습니다.

```env
DATA_MODE=mock
```

이 모드에서는 `data/demo_stocks.json`의 고정 데이터를 사용합니다. `UPSTAGE_API_KEY`가 없으면 LLM 응답은 stub 문구로 대체됩니다.

### Live 모드

실제 한국투자증권 OpenAPI와 Upstage Solar API를 사용합니다.

```env
DATA_MODE=live
KIS_APP_KEY=your_kis_app_key
KIS_APP_SECRET=your_kis_app_secret
KIS_BASE_URL=https://openapi.koreainvestment.com:9443

UPSTAGE_API_KEY=your_upstage_api_key
UPSTAGE_API_BASE=https://api.upstage.ai/v1
LLM_MODEL=solar-mini
```

`STOCK_DATA_MODE`를 별도로 지정하면 `DATA_MODE`보다 우선 적용됩니다.

## 로컬 실행

### 1. 환경 변수 준비

```bash
cp .env.example .env
```

공유용 저장소에는 실제 API 키를 넣지 마세요. `.env`는 개인 로컬 환경에서만 사용하고, Git에 커밋하지 않습니다.

### 2. 의존성 설치

```bash
python3 -m pip install -r requirements.txt
```

### 3. 백엔드 실행

```bash
python3 -m uvicorn app.api:app --reload --host 127.0.0.1 --port 8000
```

상태 확인:

```bash
curl http://127.0.0.1:8000/health
```

### 4. 프론트엔드 실행

```bash
API_BASE=http://127.0.0.1:8000 streamlit run frontend/streamlit_app.py
```

브라우저에서 접속:

```text
http://127.0.0.1:8501
```

## Docker 실행

백엔드와 프론트엔드를 함께 실행합니다.

```bash
docker compose up --build -d
```

접속 주소:

- Backend: `http://localhost:8000`
- Frontend: `http://localhost:8501`

로그 확인:

```bash
docker compose logs -f
```

종료:

```bash
docker compose down
```

서비스별 실행도 가능합니다.

```bash
docker compose up --build -d api
docker compose up --build -d ui
```

## 주요 API

| Method | Path | 설명 |
| --- | --- | --- |
| GET | `/health` | 서버 상태, 데이터 모드, KIS/LLM 준비 상태 확인 |
| GET | `/api/stocks` | 종목 목록 조회 |
| GET | `/api/stocks/{symbol}` | 단일 종목 상세 시세 및 일봉 조회 |
| POST | `/report` | 종목 리포트 생성 |
| POST | `/chat` | 리포트/종목 관련 후속 질문 처리 |

리포트 생성 예시:

```bash
curl -X POST http://127.0.0.1:8000/report \
  -H "Content-Type: application/json" \
  -d '{"symbol":"005930"}'
```

챗봇 질문 예시:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"최근 변동성은 어때?","symbol":"005930","history":[]}'
```

## 검증

mock 모드에서 백엔드가 정상 동작하는지 빠르게 확인할 수 있습니다.

```bash
DATA_MODE=mock python3 -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

다른 터미널에서:

```bash
python3 scripts/verify_demo_mode.py --base-url http://127.0.0.1:8000 --expect-mode mock
```

확인 항목:

- `/health` 응답
- 종목 목록 조회
- `005930` 상세 조회
- 없는 종목의 `404` 처리

## 보안 주의

- `.env`와 `.cache`는 커밋하지 않습니다.
- KIS App Key, App Secret, Upstage API Key는 README, 이슈, PR, 스크린샷에 포함하지 않습니다.
- API 키가 공개 저장소에 올라갔다면 즉시 폐기하고 재발급합니다.
- 발표나 피드백 요청처럼 외부에 공유할 때는 `DATA_MODE=mock`으로도 충분히 기능 흐름을 보여줄 수 있습니다.

## 피드백 포인트

리뷰어가 아래 관점으로 피드백을 주면 프로젝트 개선에 도움이 됩니다.

- 리포트 생성 흐름이 사용자가 이해하기 쉬운지
- live/mock 모드 전환이 충분히 명확한지
- 투자 정보 표현에서 오해 소지가 없는지
- LangGraph trace가 디버깅과 발표에 충분한 정보를 주는지
- 프론트엔드에서 종목 검색, 차트, 챗봇 흐름이 자연스러운지
