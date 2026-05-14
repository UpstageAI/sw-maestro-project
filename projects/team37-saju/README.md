# AI 사주 여행 (Saju Travel)

> 지금 나에게 어울리는 국내 여행지를 사주로 찾아드리는 모바일 웹.

생년월일, 출발지, 여행 조건, 선호 스타일을 입력하면 6단계 Agent 파이프라인이 실행되고,
사주 분석과 함께 어울리는 국내 여행지 Top 3가 추천됩니다.

이 레포는 **React/Vite 프론트엔드**와 **Python FastAPI 기반 Vercel Functions 백엔드**가
같이 들어 있는 풀스택 레포입니다.

---

## 주요 화면

| 라우트       | 페이지        | 역할                                                        |
| ------------ | ------------- | ----------------------------------------------------------- |
| `/`          | LandingPage   | 서비스 소개 / 진입                                          |
| `/input`     | InputPage     | Solar API 키, 사주 정보, 출발지, 여행 조건, 선호 스타일 입력 |
| `/analyzing` | AnalyzingPage | 6단계 Agent 진행 시각화 (서버 SSE 스트림 기반)              |
| `/result`    | ResultPage    | 사주 요약, 추천 스타일, 여행지 Top 3, 점수/추천 이유        |

흐름: `/` -> `/input` -> `/analyzing` -> `/result` -> (`/input`으로 다시 / `/` 처음으로)

`/analyzing` 또는 `/result`에 필요한 store 값이 없는 상태로 직접 진입하면 `/input`으로 되돌립니다.

---

## 실행 방법

요구사항:

- Node.js 18+ / npm
- Vercel CLI 또는 `npx vercel`
- Upstage Solar API 키
- Python 런타임 및 백엔드 의존성은 `requirements.txt`, `pyproject.toml` 기준

### 전체 앱 실행 (프론트 + API)

API까지 함께 테스트하려면 Vercel 개발 서버를 사용합니다.

```bash
npm install
npx vercel dev
```

Vercel dev가 Vite 프론트엔드와 `api/` 아래 Python Functions를 함께 띄웁니다.
브라우저에서는 Vercel dev가 출력하는 로컬 주소로 접속하면 됩니다.

### 프론트엔드만 실행

```bash
npm install
npm run dev
```

`npm run dev`는 Vite만 실행합니다. 이 모드에서는 `/api/recommend`,
`/api/recommend/stream` 백엔드 함수가 같이 뜨지 않습니다.

### 빌드 / 검사

```bash
npm run build
npm run lint
npm run preview
```

`npm run build`와 `npm run preview`는 프론트엔드 기준 명령입니다.
프로덕션 배포에서는 Vercel이 Vite 앱과 `api/` Python Functions를 함께 처리합니다.

---

## Solar API 키

현재는 입력 페이지에서 사용자가 Solar API 키를 직접 입력합니다.

- 키는 브라우저 `sessionStorage`에 저장됩니다.
- 프론트엔드는 `/api/recommend/stream` 요청 본문에 `{ apiKey, userInput }` 형태로 전달합니다.
- 백엔드는 전달받은 키를 사용해 Upstage Solar API를 호출합니다.
- 서버 환경변수 `SOLAR_API_KEY`를 fallback으로 사용하는 흐름은 아직 없습니다.

모델과 베이스 URL은 서버 환경변수로 바꿀 수 있습니다.

```bash
SOLAR_MODEL=solar-pro2 SOLAR_BASE_URL=https://api.upstage.ai/v1 npx vercel dev
```

기본값:

- `SOLAR_MODEL=solar-pro2`
- `SOLAR_BASE_URL=https://api.upstage.ai/v1`

---

## 기술 스택

### 프론트엔드

- React 19 + TypeScript
- Vite 6
- React Router 7
- Zustand
- Tailwind CSS 3

### 백엔드

- Python FastAPI
- Vercel Functions (`api/recommend.py`, `api/recommend/stream.py`)
- LangGraph
- Upstage Solar API (OpenAI 호환 chat completions)
- Server-Sent Events (SSE)

---

## 폴더 구조

```text
project/
├─ index.html
├─ package.json
├─ requirements.txt
├─ pyproject.toml
├─ vercel.json                     # Vercel Functions 설정 + SPA rewrite
├─ vite.config.ts                  # Vite React 설정
├─ tailwind.config.js
├─ api/                            # 백엔드: Python Vercel Functions
│  ├─ recommend.py                 # POST /api/recommend (JSON 응답)
│  ├─ recommend/
│  │  └─ stream.py                 # POST /api/recommend/stream (SSE 응답)
│  └─ _lib/
│     ├─ pipeline.py               # input validation + LangGraph 실행
│     ├─ graph.py                  # Agent graph 구성
│     ├─ solar.py                  # Solar API 클라이언트
│     ├─ bazi.py                   # 사주/오행 계산
│     ├─ destinations.py           # 여행지 데이터
│     ├─ travel_styles.py          # 여행 스타일 데이터
│     └─ agents/
│        ├─ input_validation.py
│        ├─ saju_analysis.py
│        ├─ travel_style_mapping.py
│        ├─ destination_retrieval.py
│        ├─ ranking.py
│        └─ response_generation.py
└─ src/                            # 프론트엔드
   ├─ main.tsx
   ├─ App.tsx                      # 라우터 정의
   ├─ index.css
   ├─ api/
   │  └─ recommend.ts              # SSE 스트림 파서
   ├─ components/
   │  ├─ common/
   │  ├─ input/
   │  ├─ analyzing/
   │  └─ result/
   ├─ pages/
   │  ├─ LandingPage.tsx
   │  ├─ InputPage.tsx
   │  ├─ AnalyzingPage.tsx
   │  └─ ResultPage.tsx
   ├─ store/
   │  ├─ useTravelStore.ts
   │  └─ useApiKeyStore.ts
   ├─ types/
   │  └─ index.ts
   ├─ mocks/
   └─ utils/
```

---

## API

### `POST /api/recommend`

전체 파이프라인을 실행한 뒤 최종 결과와 이벤트 로그를 JSON으로 반환합니다.

### `POST /api/recommend/stream`

전체 파이프라인을 실행하면서 진행 이벤트를 SSE로 스트리밍합니다.
프론트엔드의 `/analyzing` 화면은 이 엔드포인트를 사용합니다.

요청 본문:

```json
{
  "apiKey": "upstage-solar-api-key",
  "userInput": {
    "birthDate": "1995-05-14",
    "birthHour": "사시(09-11)",
    "departure": "서울",
    "travelRange": "4시간 이내",
    "travelDuration": "1박 2일",
    "preferredStyles": ["숲", "조용한 곳"]
  },
  "model": "solar-pro2"
}
```

`model`은 선택값입니다.

---

## 6-Agent 파이프라인

`POST /api/recommend/stream` 호출 시 다음 6개 단계가 순차 실행됩니다.
각 단계는 `agent_start` / `agent_done` 이벤트를 내보내고, 마지막에는
`pipeline_done` 또는 `error` 이벤트로 종료됩니다.

| 순서 | Agent                     | 역할                                                                 |
| ---- | ------------------------- | -------------------------------------------------------------------- |
| 1    | input-validation          | API 키, 생년월일, 시주, 출발지, 여행 조건 등 입력 검증               |
| 2    | saju-analysis             | 결정론적 4주 계산, 오행 분포, 보완 원소 산출, Solar 기반 내러티브    |
| 3    | travel-style-mapping      | 부족한 오행을 보완하는 여행 스타일, 선호/기피 태그, 근거 생성        |
| 4    | destination-retrieval     | 거리 필터, 오행 친화도, 태그/스타일 매칭으로 후보 여행지 추출        |
| 5    | ranking                   | 사주 적합도, 선호 매칭, 거리 점수 기반 Top 3 랭킹 및 추천 이유 생성 |
| 6    | response-generation       | 최종 헤드라인과 스타일 사유 생성                                     |

### 점수 가중치

- 사주 적합도 0.5
- 선호 매칭 0.3
- 거리 0.2

### 결정론 + LLM fallback

- 4주(년주, 월주, 일주, 시주) 계산과 오행 분포는 결정론적으로 계산합니다.
- Solar 호출이 실패해도 fallback 내러티브/추천 이유로 파이프라인이 끝까지 완주하도록 구성되어 있습니다.

---

## 배포

Vercel 기준으로 구성되어 있습니다.

- `api/recommend.py` -> `/api/recommend`
- `api/recommend/stream.py` -> `/api/recommend/stream`
- `vercel.json`에서 API가 아닌 모든 경로는 `/index.html`로 rewrite되어 SPA 라우팅이 동작합니다.
- `api/_lib/**`는 Vercel Function 배포 시 함께 포함됩니다.

---

## 직접 진입 / 새로고침 처리

| 케이스                                      | 동작                                                              |
| ------------------------------------------- | ----------------------------------------------------------------- |
| `/analyzing` 진입 시 `userInput`이 없음     | `/input`으로 이동                                                 |
| `/analyzing` 진입 시 API 키가 유효하지 않음 | `/input`으로 이동                                                 |
| `/result` 진입 시 `pipelineResult`가 없음   | `/input`으로 이동                                                 |
| `/result`에서 "조건 바꿔서 다시 받기"      | 결과만 초기화 후 `/input`으로 이동                                |
| `/result`에서 "처음으로"                   | 입력, 결과, API 키 전체 초기화 후 `/`로 이동                      |

---

## 면책

본 결과는 재미와 참고용입니다. 실제 운세 상담이 아니며 의학적, 법률적, 재정적 조언으로 사용할 수 없습니다.
