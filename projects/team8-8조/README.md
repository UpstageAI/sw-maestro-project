# Daily News Agent

관심 분야를 입력하면 Google News RSS에서 하루치 뉴스를 수집하고, 로컬 Chroma Vector DB에 저장한 뒤, 관련 기사를 선별해 일일 뉴스 브리핑을 생성하는 로컬 데모입니다.

## MVP 범위

- 뉴스 소스는 키워드별로 Naver Search News API(한글) 또는 Google News RSS(그 외)로 자동 라우팅됩니다.
- 관심 키워드는 최대 3개를 입력합니다.
- 기사 수집 범위는 최근 하루(`when:1d`)로 제한합니다.
- Vector DB는 로컬 Chroma를 사용합니다.
- Upstage API key가 있으면 Upstage embedding/chat 모델을 사용합니다.
- Upstage API key가 없으면 demo 모드로 실행되어 전체 흐름과 출력 형태를 확인할 수 있습니다.
- Naver Client ID/Secret이 없으면 한글 키워드도 Google News RSS로 자동 우회합니다.

## 구조

```text
.
├── app.py              # Streamlit UI (레거시)
├── server.py           # FastAPI 서버
├── frontend/           # React 프론트엔드
├── daily_news_agent/
│   ├── ai_client.py
│   ├── config.py
│   ├── models.py
│   ├── naver_news.py
│   ├── news_source.py
│   ├── preprocessor.py
│   ├── summarizer.py
│   ├── vector_store.py
│   └── workflow.py
├── docs/
│   └── specs/
├── data/
├── tests/
├── AGENTS.md
├── .env.example
├── requirements.txt
└── README.md
```

## 개발 문서

- 개발 규칙: [`AGENTS.md`](AGENTS.md)
- 로컬 MVP 스펙: [`docs/specs/2026-05-04-local-mvp-spec.md`](docs/specs/2026-05-04-local-mvp-spec.md)
- FE/BE 분리 스펙: [`docs/specs/2026-05-09-fe-be-separation-spec.md`](docs/specs/2026-05-09-fe-be-separation-spec.md)
- 브리핑 품질 평가: [`docs/quality/news-briefing-evaluation.md`](docs/quality/news-briefing-evaluation.md)

## 로컬 실행 (React + FastAPI)

터미널 두 개를 열어 각각 실행합니다.

**백엔드 (FastAPI)**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn server:app --reload --port 8000
```

두 번째 실행부터는 venv 활성화 후 바로 uvicorn을 실행합니다.

```bash
source .venv/bin/activate
uvicorn server:app --reload --port 8000
```

**프론트엔드 (React)**

```bash
cd frontend
npm install
npm run dev
```

두 번째 실행부터는 `npm install` 없이 바로 실행합니다.

```bash
cd frontend
npm run dev
```

브라우저에서 `http://localhost:5173`으로 접속합니다.

```text
관심 분야: AI 산업 동향
검색 키워드 3개: AI, 반도체, 스타트업
```

기본 설정은 API 호출 시간을 줄이기 위해 키워드별 기사 3건, 브리핑 기사 5건으로 제한합니다. 먼저 `뉴스 수집 및 저장`을 누른 뒤, 수집이 끝나면 `브리핑 생성`을 눌러 결과를 확인합니다.

## 로컬 실행 (Streamlit, 레거시)

```bash
streamlit run app.py
```

## Upstage API 설정

`.env` 파일에 API key를 넣으면 demo 모드 대신 Upstage 모델을 사용합니다.

```env
UPSTAGE_API_KEY=your_api_key_here
UPSTAGE_BASE_URL=https://api.upstage.ai/v1
UPSTAGE_CHAT_MODEL=solar-pro3
UPSTAGE_DOCUMENT_EMBEDDING_MODEL=solar-embedding-1-large-passage
UPSTAGE_QUERY_EMBEDDING_MODEL=solar-embedding-1-large-query
```

API key는 repository에 커밋하지 않습니다.

## Naver Search API 설정

한글 키워드 수집 품질을 위해 Naver Search API(news 엔드포인트)를 사용합니다. [Naver Developers](https://developers.naver.com/apps/) 콘솔에서 앱을 등록하고 "검색" API를 추가하면 Client ID와 Client Secret을 발급받을 수 있습니다.

```env
NAVER_CLIENT_ID=your_client_id
NAVER_CLIENT_SECRET=your_client_secret
```

두 값이 모두 설정되어 있으면 한글이 포함된 키워드는 Naver로, 그 외 키워드는 Google News RSS로 라우팅됩니다. 키가 없거나 Naver 호출이 실패하면 `errors`에 안내 메시지를 남기고 Google News RSS로 자동 우회합니다.

## 테스트

현재 테스트는 외부 API나 네트워크 없이 실행됩니다.

```bash
python3 -m unittest discover -s tests
```

## 현재 workflow

```text
관심 분야 입력
→ 검색 키워드 최대 3개 정규화
→ 키워드별 한국어 감지 → Naver(한글) 또는 Google News RSS(그 외) 호출
→ Naver 키 누락/호출 실패 시 Google News RSS로 자동 우회
→ 제목/요약/링크/출처/발행일 정제
→ 중복 링크 제거
→ 기사별 embedding 생성
→ Chroma Vector DB 저장
→ 검색 키워드 metadata filter와 관심 분야 query embedding으로 similarity search
→ Top-K 기사로 브리핑 생성
→ React 화면 출력
```

## 다음 개선 후보

- LLM 기반 관심 분야 키워드 확장
- 기사 자동 태깅 파이프라인 추가
- 날짜, 출처, 키워드 메타데이터 필터링 강화
- 하루 1회 자동 수집 스케줄러 추가
- ~~팀 개발을 위한 FE/BE/DE/AI workflow 분리~~ (완료)
