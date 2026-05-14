# 두리번 · Duribeon

여행 중 즉흥 미션 AI — "지금, 여기서만 가능한 골목 퀘스트"를 게임 마스터 톤으로 던져주고, 사진으로 인증까지 받아주는 LangGraph 기반 에이전트 프로토타입.

- **텍스트 LLM**: Upstage Solar (`solar-pro2`) — LangGraph 오케스트레이션
- **비전 LLM**: OpenAI (`gpt-4o`)
- **백엔드**: FastAPI (Python 3.11+)
- **프론트엔드**: SvelteKit + TypeScript + AtoZ 한글 폰트
- **데이터**: 자체 큐레이션 JSON DB (서울 12개 동네, 동네당 6~10곳)

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
│   ├── llm_graphs.py       # LangGraph (generate / regenerate / agent)
│   ├── agent.py            # 비전 호출 + fallback 미션 + 시드 헬퍼
│   ├── seed.py             # 시드 로더 (areas / places)
│   ├── schemas.py          # Pydantic 스키마 (area는 시드로 동적 검증)
│   ├── prompts.py          # 한/영 프롬프트 (SYSTEM / VISION / AGENT)
│   ├── data/seoul_seed.json
│   ├── requirements.txt
│   └── .env.example
├── frontend/               # SvelteKit 앱
│   ├── src/routes/+page.svelte    # 챗 FSM, 액션 디스패처
│   ├── src/lib/ChatBubble.svelte  # 메시지 버블 (text / photo / verdict)
│   ├── src/lib/MissionPanel.svelte  # 우측 미션함 (받기/바꿔/거절)
│   ├── src/lib/{api,types,i18n,storage}.ts
│   ├── src/routes/styles.css      # 밝은 여행 테마
│   ├── static/fonts/              # AtoZ 한글 폰트 9 weight
│   └── package.json
└── docs/
    └── seed-prompt.md      # AI 시드 자동 생성 프롬프트 (별도 파일)
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
| `UPSTAGE_TEXT_MODEL` | `solar-pro2` | 미션 생성 / regenerate / agent |
| `OPENAI_API_KEY` | (필수) | OpenAI 콘솔에서 발급 |
| `OPENAI_VISION_MODEL` | `gpt-4o` | 사진 검증용 (`gpt-4o-mini`로 비용 절감 가능) |
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

채팅창 + 우측 미션함 (모바일에선 우측 드로어).

1. **사전 질문 5단계** — 동네 → 그룹 → 시간 → 분위기 → 회피. 빠른 답변 버튼 또는 자유 텍스트 모두 가능. 자유 텍스트는 LangGraph 에이전트가 의도를 분류해 적절한 액션으로 변환.
2. **미션 5개** — 봇이 미션함에 적재. 각 카드에 **받기 / 바꿔 / 거절** 3개 버튼.
   - **받기** = 채택, 사진 인증 단계로
   - **바꿔** = 같은 장소의 미션 텍스트만 새로 (별도 LangGraph 호출)
   - **거절** = 풀에서 제외 (대체 카드 없음)
   - 풀 헤더의 **✨ 새로 5개 가져와**로 추가 배치 생성
3. **인증** — 사진 클릭 / 드래그 드롭. 비전 LLM이 PASS / FAIL 판정.
4. **재시도** — FAIL 카드에 **🔄 다시 시도** 버튼.
5. **자유 텍스트로 모든 액션** — "이거 별로, 다른 거 줘", "두번째 미션 바꿔줘", "그만 물어봐 알아서 해줘" 등을 받아 에이전트가 액션 디스패치.

### 영속화 (localStorage)

| 키 | 내용 | 수명 |
| --- | --- | --- |
| `duribeon:language` | "ko" / "en" | 영구 |
| `duribeon:journal` | 인증 통과/실패 이력 + 썸네일 (최대 30개) | 영구 (명시적 삭제 가능) |
| `duribeon:chat` | 현재 대화 + step + context + panel | 영구 ("처음부터"로 초기화) |

## API 엔드포인트

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/api/health` | 키 설정 여부 확인 |
| `GET` | `/api/areas` | 큐레이션된 동네 목록 (시드 JSON 기반) |
| `POST` | `/api/lang/detect` | `{text}` → `{language: "ko"\|"en"}` |
| `POST` | `/api/missions/generate` | 컨텍스트 → 미션 5개 (LangGraph 5단계 + 재시도) |
| `POST` | `/api/missions/regenerate` | `{place_id}` → 같은 장소의 새 미션 1개 |
| `POST` | `/api/missions/verify` | multipart (`photo`, `mission_json`, `language`) → `{ok, reason, comment}` |
| `POST` | `/api/agent/message` | 자유 텍스트 → `{bot_response, actions}` |

자동 생성된 OpenAPI 문서: <http://localhost:8000/docs>

## LangGraph 구조

[`backend/llm_graphs.py`](backend/llm_graphs.py)에 3개의 StateGraph가 정의돼 있습니다.

### GENERATE_GRAPH — 미션 5개 생성

```text
START → prepare → call_llm → validate → (재시도 ≤2회 ↻ | finalize) → END
```

- **prepare**: 시드에서 후보 추출, 회피 필터, 시드 고갈 시 fallback으로 후보 5+ 확보
- **call_llm**: Upstage Solar 호출. 재시도 시 시스템 프롬프트에 *"이전 시도 실패: ..."* 힌트 추가
- **validate**: JSON 파싱 + 화이트리스트 + 중복 제거
- **finalize**: 부족하면 결정적 fallback 미션으로 5개 채움

### REGENERATE_GRAPH — 단일 미션 재생성

같은 형태, 단일 미션만. "바꿔" 버튼 또는 에이전트의 `regenerate_mission` 액션이 호출.

### AGENT_GRAPH — 자유 텍스트 의도 분류

```text
START → call_llm → validate → END
```

채팅창에 자유 텍스트가 입력되면 백엔드 에이전트가 받아 **bot_response + actions** 반환.

지원 액션 12종:

| 카테고리 | 액션 |
| --- | --- |
| 컨텍스트 설정 | `set_context_area / group / time_budget / mood / avoid` |
| 미션 생성 진행 | `proceed_to_generate` |
| 패널 미션 조작 | `regenerate_mission / reject_mission / pick_mission` |
| 풀 조작 | `reroll_all / generate_more` |
| 전체 | `reset_chat` |

프론트의 `executeAgentAction()` 디스패처가 받아서 기존 핸들러로 실행.

**예시**:

- "익선 친구 둘 알아서 해줘" → `[set_area, set_group, proceed_to_generate]`
- "두번째 미션 바꿔" → `[regenerate_mission(index=2)]`
- "그만 처음부터" → `[reset_chat]`

## 새 동네 추가하기

코드 수정 없이 [`backend/data/seoul_seed.json`](backend/data/seoul_seed.json) 한 파일만 고치면 됩니다.

```jsonc
{
  "areas": [
    // 기존 + 새 동네 추가
    {
      "id": "mapo",
      "name_ko": "망원동",
      "name_en": "Mangwon-dong",
      "match_ko": ["망원"],            // 자유 텍스트 인식 키워드
      "match_en": ["mangwon"]
    }
  ],
  "places": [
    // 새 동네 장소 6곳 이상 (id 접두어 통일 권장: mapo_01...)
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

백엔드는 `Context.area` validator가 시드의 area id를 동적으로 받아 검증, 프론트는 부팅 시 `/api/areas`를 fetch해 빠른 답변 버튼·자유 텍스트 매처·라벨을 자동 구성. 자연어 에이전트도 매 요청마다 시드의 `available_areas`를 함께 받아 시드 안에서만 동네를 선택합니다.

동네당 장소 6곳 이상 권장 (그 미만이면 swap·reroll 시 LLM 부담 ↑, fallback 미션이 자주 나옴).

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

## 문제 해결

- **`UPSTAGE_API_KEY is not set`** — `backend/.env` 파일을 만들고 키를 채웠는지 확인.
- **CORS 오류** — 프론트 포트가 5173이 아니면 `backend/.env`의 `CORS_ORIGINS`에 추가.
- **`unknown area: 'xxx'`** — 에이전트가 시드에 없는 동네를 골랐을 때. 프론트가 가드해 안내 메시지로 표시 (백엔드 500 안 남). 발생 시 시드 동네 더 추가하거나 사용자에게 시드 동네 중 하나 선택 요청.
- **미션이 5개 미만으로 잘려 검증 실패** — 큐레이션 후보 부족. `data/seoul_seed.json`의 해당 동 항목 수를 확인하거나 `avoid` 입력을 완화. LangGraph가 최대 2회 재시도 후에도 부족하면 결정적 fallback 미션으로 채움 — 진짜 0개일 때만 500.
- **자연어 에이전트 응답이 어색** — `prompts.py`의 `AGENT_SYSTEM_KO/EN` 가이드라인 조정. 또는 `_chat_model(temperature=...)` 낮춰 안정성 ↑.
- **비전 검증 비용이 부담** — `OPENAI_VISION_MODEL=gpt-4o-mini`로 변경.

## 범위 (MVP)

기획서 v2의 Must-have 5개(F1~F4 + 다국어)를 모두 구현하고, 다음을 추가로 확장:

- 우측 미션함 + 모바일 드로어
- 받기 / 바꿔 / 거절 액션 분리
- 사진 드래그·드롭
- 자연어 에이전트 (자유 텍스트 → 의도 분류 → 액션 디스패치, LangGraph 기반)
- 채팅/저널 localStorage 영속화
- 12개 시드 동네 + 데이터 드리븐 area 검증

의도적으로 제외: 외부 검색 API · 계정/로그인 · 멀티 사용자 동기화 · 실시간 영업시간 검증.
