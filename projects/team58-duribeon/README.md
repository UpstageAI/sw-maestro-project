# 두리번 · Duribeon

여행 중 즉흥 미션 AI — "지금, 여기서만 가능한 골목 퀘스트" 5개를 게임 마스터 톤으로 던져주고, 사진으로 인증까지 받아주는 단일 에이전트 프로토타입.

- **텍스트 LLM**: Upstage Solar (`solar-pro2`)
- **비전 LLM**: OpenAI (`gpt-4o`)
- **백엔드**: FastAPI (Python 3.11+)
- **프론트엔드**: SvelteKit + TypeScript
- **데이터**: 자체 큐레이션 JSON DB (익선/성수/연남, 각 5곳)

## 사전 준비

| 항목 | 버전 |
| --- | --- |
| Python | 3.11+ |
| Node.js | 20+ (npm 10+) |
| Upstage API 키 | <https://console.upstage.ai/> |
| OpenAI API 키 | <https://platform.openai.com/api-keys> |

## 디렉토리 구조

```text
두리번/
├── backend/                # FastAPI 서버
│   ├── main.py             # 라우트
│   ├── agent.py            # Upstage(텍스트) + OpenAI(비전) 호출
│   ├── seed.py             # 큐레이션 시드 로더 (areas/places)
│   ├── schemas.py          # Pydantic 스키마 (area는 시드로 동적 검증)
│   ├── prompts.py          # 한/영 프롬프트
│   ├── data/seoul_seed.json
│   ├── requirements.txt
│   └── .env.example
└── frontend/               # SvelteKit 앱
    ├── src/routes/+page.svelte
    ├── src/lib/{ChatBubble,MissionPanel}.svelte
    ├── src/lib/{api,types,i18n,storage}.ts
    ├── src/routes/styles.css
    └── package.json
```

## 1. 백엔드 실행

```bash
cd backend
cp .env.example .env        # UPSTAGE_API_KEY, OPENAI_API_KEY 채우기
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

서버가 뜨면 헬스 체크:

```bash
curl http://localhost:8000/api/health
# {"ok":true,"upstage_key":true,"openai_key":true}
```

### 환경 변수 (`backend/.env`)

| 키 | 기본값 | 설명 |
| --- | --- | --- |
| `UPSTAGE_API_KEY` | (필수) | Upstage Console에서 발급 |
| `UPSTAGE_BASE_URL` | `https://api.upstage.ai/v1` | OpenAI 호환 엔드포인트 |
| `UPSTAGE_TEXT_MODEL` | `solar-pro2` | 미션 생성용 |
| `OPENAI_API_KEY` | (필수) | OpenAI 콘솔에서 발급 |
| `OPENAI_VISION_MODEL` | `gpt-4o` | 비전 검증용 (`gpt-4o-mini`로 비용 절감 가능) |
| `CORS_ORIGINS` | `http://localhost:5173` | 콤마 구분으로 다중 허용 |

## 2. 프론트엔드 실행

새 터미널에서:

```bash
cd frontend
cp .env.example .env        # 기본값 그대로 OK
npm install
npm run dev                 # http://localhost:5173
```

브라우저로 <http://localhost:5173> 접속.

### 환경 변수 (`frontend/.env`)

| 키 | 기본값 | 설명 |
| --- | --- | --- |
| `VITE_API_BASE` | `http://localhost:8000` | 백엔드 주소 |

## 사용 흐름

1. **입력** — 자유 텍스트(언어 자동 감지) + 위치 / 그룹 / 분위기 / 회피
2. **미션 5개** — 카드별로 채택, "이 카드만 바꿔" 또는 "전부 다시"
3. **채택** — 상세 보기 + 사진 업로드 (JPG / PNG)
4. **검증** — 게임 마스터의 PASS / FAIL 판정 + 한 줄 코멘트

## API 엔드포인트

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/api/health` | 키 설정 여부 확인 |
| `GET` | `/api/areas` | 큐레이션된 동네 목록 (시드 JSON 기반) |
| `POST` | `/api/lang/detect` | `{text}` → `{language: "ko"\|"en"}` |
| `POST` | `/api/missions/generate` | 컨텍스트 → 미션 5개 |
| `POST` | `/api/missions/verify` | multipart (`photo`, `mission_json`, `language`) → `{ok, reason, comment}` |

## 새 동네 추가하기

코드 수정 없이 [`backend/data/seoul_seed.json`](backend/data/seoul_seed.json) 한 파일만 고치면 됩니다.

```jsonc
{
  "areas": [
    // 기존 익선/성수/연남 + 새 동네 추가
    {
      "id": "mapo",
      "name_ko": "망원동",
      "name_en": "Mangwon-dong",
      "match_ko": ["망원"],            // 자유 텍스트 인식 키워드
      "match_en": ["mangwon"]
    }
  ],
  "places": [
    // 새 동네 장소 5곳 이상 (id 접두어 통일 권장: mapo_01...)
    {
      "id": "mapo_01",
      "area": "mapo",
      "name_ko": "...", "name_en": "...",
      "category": "food | place | experience",
      "tags": [...],
      "desc_ko": "30자 내외 한 줄 설명",
      "desc_en": "...",
      "offbeat_score": 0.8
    }
  ]
}
```

백엔드는 `Context.area` validator가 시드의 area id를 동적으로 받아 검증하고, 프론트는 부팅 시 `/api/areas`를 fetch해서 빠른 답변 버튼·자유 텍스트 매처·라벨을 모두 자동 구성합니다. 동네당 장소 5곳 이상 권장 (그 미만이면 swap·reroll 시 LLM 부담 ↑, fallback 미션이 자주 나옴).

### AI로 시드 자동 생성 (ChatGPT / Gemini / Claude)

시드를 한 번에 통째로(동네 10~15곳 + 동네당 6~10곳, 총 60~150곳) 만드는 프롬프트는 별도 파일로 분리돼 있습니다 — [`docs/seed-prompt.md`](docs/seed-prompt.md). 파일 전체를 그대로 복사해서 상용 챗봇에 붙여넣어 사용하세요.

#### 사전 준비 — 웹 검색 반드시 켜기

검색 안 켜면 환각으로 가짜 가게가 섞입니다. 모델별 활성화:

| 모델 | 검색 활성화 |
| --- | --- |
| ChatGPT | GPT-4o / o3 / o4-mini — 웹 브라우징 자동 사용 |
| Gemini | 2.5 Pro 기본 검색 활성화 |
| Claude | claude.ai 입력창 옆 도구 메뉴에서 "웹 검색" 켜기 |

#### 조정 가능 변수

[`docs/seed-prompt.md`](docs/seed-prompt.md) 안에 굵게 표시된 숫자 — 원하면 파일 편집 후 복사:

- 목표 동네 수: **12** (10~15 권장)
- 동네당 장소 수: **8** (6~10 권장)
- 총 장소 수 목표: **96** 이상 (최소 60곳)

#### 사용 후 절차

1. AI 응답에서 JSON 전체 복사 (마크다운 펜스 안에 들어왔다면 펜스 제거)
2. JSON 유효성 빠르게 확인:

   ```bash
   python3 -c "import json; d=json.load(open('seed_new.json')); print('areas', len(d['areas']), 'places', len(d['places']))"
   ```

3. `backend/data/seoul_seed.json`에 덮어쓰기 (기존 데이터를 대체할지, 합칠지 선택)
4. 백엔드 재시작 — `uvicorn --reload`라면 자동 반영
5. 검증 호출:
   - `curl http://localhost:8000/api/areas` 로 새 동네 목록 확인
   - 프론트 새로고침 → 첫 질문 빠른답변에 새 동네 자동 노출 확인

#### 자주 발생하는 이슈

- **출력 잘림** — 모델 토큰 한도 초과. 다음 메시지로 "places 배열 이어서 출력해줘"로 받아 합치거나, 동네 수를 8개로 줄여 재요청.
- **`area` 불일치** — places의 area가 areas의 id와 안 맞음. 자가 검증 1번을 강조해 재요청.
- **가짜 가게 섞임** — 모델이 검색 안 켜고 추측. 검색 활성화 재확인 + "검증 안 된 곳은 제외하라" 강조해 재요청.
- **같은 동네 6곳 미만** — 시드 부족 시 swap·reroll에서 fallback 미션이 자주 등장. 해당 동네에서 추가 보충 요청.
- **카테고리 편중** — food만 잔뜩 나오는 경우 자가 검증 4번 ("food/place/experience 모두 최소 1개") 다시 강조해 재요청.

자동 생성된 OpenAPI 문서: <http://localhost:8000/docs>

## 문제 해결

- **`UPSTAGE_API_KEY is not set`** — `backend/.env` 파일을 만들고 키를 채웠는지 확인.
- **CORS 오류** — 프론트 포트가 5173이 아니면 `backend/.env`의 `CORS_ORIGINS`에 추가.
- **미션이 5개 미만으로 잘려 검증 실패** — 큐레이션 후보 부족. `data/seoul_seed.json`의 해당 동 항목 수를 확인하거나 `avoid` 입력을 완화.
- **비전 검증 비용이 부담** — `OPENAI_VISION_MODEL=gpt-4o-mini`로 변경.

## 범위 (MVP)

본 프로토타입은 기획서 v2의 Must-have 5개(F1~F4 + 다국어)만 구현. 세션 메모리·콜렉션 보드·외부 검색 API·계정/로그인은 의도적으로 제외.
