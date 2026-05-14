# 냥멍일기 AI/LangGraph 코드 분석

반려동물 사진과 키워드를 입력하면 1인칭 일기를 생성하는 AI 파이프라인 전체를 추적한다.

---

## 1. 전체 흐름

```
클라이언트 (브라우저)
  │ POST /api/diaries/generate
  ▼
Next.js BFF (apps/web)
  │ 인증 · 한도 검증 · signed URL 발급
  │ POST ${AI_GATEWAY_URL}/diary/generate
  │   X-Internal-Secret, Authorization: Bearer <JWT>
  ▼
FastAPI AI Gateway (apps/ai-gateway)  — Railway us-east4
  │ 미들웨어: X-Internal-Secret → Bearer JWT 검증
  │ LangGraph StateGraph 실행
  │   ├─ Vision Agent: GPT-4o-mini Vision → 사진 묘사
  │   └─ Diary Agent: GPT-4o-mini → 1인칭 일기 + 캡션 + 무드태그
  │ SSE stream (6종 이벤트)
  ▼
BFF mediateStream
  │ vision_done 가로채기 (DB 저장용)
  │ result 이벤트 → diary_generations INSERT + usage_quotas 차감
  │ meta 이벤트 emit (generation_id, 잔여 횟수)
  ▼
클라이언트 consumeDiaryStream
  │ onNode / onPartial / onRetry 콜백 → 진행 UI 갱신
  └─ result + meta 수집 → GenerateResponse 반환
```

**핵심 파일 맵**

| 레이어 | 파일 |
|---|---|
| LangGraph 그래프 | `apps/ai-gateway/src/ai_gateway/graph.py` |
| 상태 스키마 | `apps/ai-gateway/src/ai_gateway/state.py` |
| Vision Agent | `apps/ai-gateway/src/ai_gateway/agents/vision.py` |
| Diary Agent | `apps/ai-gateway/src/ai_gateway/agents/diary.py` |
| 프롬프트 로더 | `apps/ai-gateway/src/ai_gateway/prompts_loader.py` |
| FastAPI 앱 + SSE | `apps/ai-gateway/src/ai_gateway/main.py` |
| 보안 미들웨어 | `apps/ai-gateway/src/ai_gateway/middleware.py` |
| API 계약 모델 | `apps/ai-gateway/src/ai_gateway/contracts.py` |
| BFF Gateway 호출 | `apps/web/src/lib/server/gateway.ts` |
| BFF SSE 중재 | `apps/web/src/lib/server/diary-stream.ts` |
| 클라이언트 API | `apps/web/src/lib/api/diaries.ts` |
| generate route | `apps/web/src/app/api/diaries/generate/route.ts` |
| regenerate route | `apps/web/src/app/api/diaries/regenerate/route.ts` |

---

## 2. LangGraph 워크플로우 (`graph.py`)

### 토폴로지

```
START
  │
  ▼
prepare_context          ← noop entry (입력 sanity 훅 예약용)
  │
  ▼ conditional: _route_vision
  │
  ├─ vision_description == None ──► analyze_image
  │                                     │
  └─ vision_description 있음 ────────────┘
                                         │
                                         ▼
                                    write_diary
                                         │
                                         ▼
                                    safety_check
                                         │
                                         ▼ conditional: should_retry
                                         │
                                ┌────────┴────────┐
                                │                 │
                      violation && count < 2    otherwise
                                │                 │
                                ▼                 ▼
                           write_diary           END
                       (vision 재호출 없음)
```

### 노드 역할

| 노드 | 책임 | 파일 |
|---|---|---|
| `prepare_context` | 진입점. 현재 noop — Pydantic 검증으로 충분 | `graph.py` |
| `analyze_image` | 사진 URL → 한국어 묘사 1단락 | `agents/vision.py` |
| `write_diary` | vision 묘사 + 키워드 → 1인칭 일기 생성 | `agents/diary.py` |
| `safety_check` | 호칭 substring + 길이 검증 | `agents/diary.py` |

### 조건부 엣지

**`_route_vision`** — `prepare_context` 다음

```python
def _route_vision(state: DiaryState) -> str:
    return "write_diary" if state.get("vision_description") else "analyze_image"
```

`regenerate` 요청 시 BFF가 직전 `vision_description`을 forward하면 `analyze_image`를 완전히 건너뜀. 이미지 토큰 재소비 없음.

**`should_retry`** — `safety_check` 다음

```python
def should_retry(state: DiaryState) -> str:
    if state["safety_violation"] and state["safety_retry_count"] < SAFETY_MAX_CALLS:  # 2
        return "write_diary"
    return END
```

위반이 있으면 `write_diary`로만 돌아감 — vision은 재호출 안 함. 최대 2회 (첫 호출 + retry 1회).

### 그래프 컴파일

```python
@lru_cache(maxsize=1)
def get_diary_graph() -> Any:
    builder = StateGraph(DiaryState)
    # ... 노드/엣지 등록 ...
    return builder.compile()
```

`@lru_cache(maxsize=1)`로 서버 프로세스 당 1회만 컴파일. 요청마다 재컴파일 비용 없음.

---

## 3. DiaryState Schema (`state.py`)

```python
class DiaryState(TypedDict):
    # 메타
    session_id: str          # 생성 세션 식별자 (1 session = 최대 4회 시도)
    seq: int                 # 시도 순번 (1=첫 생성, 2~4=재생성)

    # 입력 — BFF가 채워서 전달
    pet_id: str
    honorific: str           # 사용자 자유 입력 호칭 (1~20자)
    species: str             # 원문 그대로 (예: "냥이", "고양이", "cat")
    gender: Gender           # "male" | "female" | "unknown"
    photo_signed_url: str    # Supabase Storage GCS signed URL (3600초)
    keywords: str            # 사용자 키워드 (1~1000자)
    recent_diaries: list[str]  # 최근 채택 일기 최대 3건 (문체 컨텍스트)

    # 재생성 전용 (seq >= 2)
    previous_diary_text: Optional[str]
    regen_feedback: Optional[str]  # 사용자 피드백 (1~500자)

    # analyze_image 산출 → write_diary 소비
    vision_description: Optional[str]

    # write_diary 산출 → safety_check 소비 → SSE result emit
    diary_text: Optional[str]      # 200~400자 1인칭 일기
    short_caption: Optional[str]   # 1~100자 제목
    mood_tag: Optional[MoodTag]    # 7-enum

    # 안전 retry (DB 영속 안 함)
    safety_retry_count: int        # write_diary 호출 횟수 (0부터)
    safety_violation: Optional[SafetyViolation]
```

**TypedDict default reducer**: 각 노드는 변경할 필드만 `dict`로 return. 나머지 필드는 이전 값 유지.

---

## 4. Vision Agent (`agents/vision.py`)

### 역할

사진을 직접 보는 유일한 노드. 이미지 토큰은 여기서만 1회 소비. `write_diary`는 이 산출 텍스트만 보고 작문한다.

### LLM 설정

```python
@lru_cache(maxsize=1)
def _vision_llm() -> Any:
    get_settings()  # OPENAI_API_KEY os.environ export 보장
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,  # 낮게 — 같은 사진에 대한 묘사 변동 최소화 (retry 일관성)
    ).with_structured_output(VisionAnalysis)
```

`temperature=0.2`: safety retry 시 `analyze_image`는 재호출 안 하지만, 향후 vision을 재호출하는 경우를 위한 일관성 확보.

### Structured Output Schema

```python
class VisionAnalysis(BaseModel):
    description: str = Field(min_length=100, max_length=600)
```

단일 필드. 길이 강제로 너무 짧거나 긴 묘사 방지.

### 메시지 구성

```python
messages = [
    SystemMessage(content=build_vision_system_message(state)),
    HumanMessage(content=[
        {"type": "text", "text": "이 사진을 묘사해주세요."},
        {
            "type": "image_url",
            "image_url": {
                "url": state["photo_signed_url"],
                "detail": "low",   # 저해상도 토큰 절약
            },
        },
    ])
]
```

`detail="low"`: OpenAI Vision의 low 해상도 모드. 사진 묘사에는 충분하고 토큰 비용이 크게 감소.

### State 업데이트

```python
return {"vision_description": result.description}
```

`vision_description` 1개 필드만 업데이트. `write_diary`가 user 프롬프트에 이 값을 넣는다.

---

## 5. Diary Agent (`agents/diary.py`)

### 역할

`vision_description` + 키워드로 1인칭 일기 3종(diary_text, short_caption, mood_tag)을 생성한다.

### LLM 설정

```python
@lru_cache(maxsize=1)
def _diary_llm() -> Any:
    get_settings()
    return ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.7,  # 창의적 작문 — 재생성 시 다양성 확보
    ).with_structured_output(DiaryGenerationResult)
```

`temperature=0.7`: vision(0.2)보다 높게. 재생성 시 매번 다른 결과 기대.

### Structured Output Schema (`contracts.py`)

```python
class DiaryGenerationResult(BaseModel):
    diary_text: str = Field(min_length=50, max_length=1000)
    short_caption: str = Field(min_length=1, max_length=100)
    mood_tag: MoodTag  # "행복"|"신남"|"평온"|"졸림"|"심심"|"슬픔"|"까칠"
```

OpenAI structured outputs으로 이 스키마를 강제. 필드 누락이나 타입 오류가 원천 차단된다.

### 3가지 생성 모드

모드 선택 로직 (`prompts_loader.py:build_user_message`):

```python
if state["seq"] == 1:
    mode = "A"
elif state.get("regen_feedback"):
    mode = "B"
else:
    mode = "C"
```

| 모드 | 조건 | 포함 컨텍스트 | 지시 |
|---|---|---|---|
| **A** | `seq == 1` (첫 생성) | vision_description + keywords + recent_diaries | 그대로 일기 작성 |
| **B** | `seq >= 2` + 피드백 있음 | 모드 A + previous_diary_text + regen_feedback | 피드백을 진실로 두고 반영 |
| **C** | `seq >= 2` + 피드백 없음 | 모드 A + previous_diary_text | 톤만 약간 다르게 |

### `write_diary` 노드 실행 흐름

```python
def write_diary(state: DiaryState) -> dict:
    system_text = build_system_message(state)   # 호칭·톤·메타 주입
    user_text = build_user_message(state)       # 모드 A/B/C 선택

    result = _diary_llm().invoke([
        SystemMessage(content=system_text),
        HumanMessage(content=user_text),
    ])

    honorific = state["honorific"]
    return {
        "diary_text": _fix_honorific(result.diary_text, honorific),    # 2차 안전망
        "short_caption": _fix_honorific(result.short_caption, honorific),
        "mood_tag": result.mood_tag,
        "safety_retry_count": state["safety_retry_count"] + 1,        # 호출 횟수 증가
    }
```

### `_fix_honorific` — 2차 안전망

```python
_HONORIFIC_PLACEHOLDERS = ("{{ honorific }}", "{{honorific}}", "{honorific}")

def _fix_honorific(text: str, honorific: str) -> str:
    for pat in _HONORIFIC_PLACEHOLDERS:
        text = text.replace(pat, honorific)
    return text
```

LLM이 system.md의 `{{ honorific }}` placeholder를 그대로 본문에 베끼는 실패 사례를 사후 교정. 3가지 변형 모두 치환.

- **1차 방어**: `system.md`에서 placeholder를 본문에 쓰지 말라고 명시
- **2차 방어**: `write_diary` 후처리에서 치환 (`diary.py`)
- **3차 방어**: `safety_check`에서 honorific substring 검증 후 위반 시 재시도 (`diary.py`)
- **4차 방어**: SSE streaming에서 partial emit 시 재치환 (`main.py`)

---

## 6. Safety Check (`agents/diary.py`)

### 검증 로직

```python
def safety_check(state: DiaryState) -> dict:
    diary = state.get("diary_text") or ""
    caption = state.get("short_caption") or ""
    honorific = state["honorific"]

    if honorific not in diary:
        return {"safety_violation": "honorific_missing"}
    if not 50 <= len(diary) <= 1000:
        return {"safety_violation": "diary_length"}
    if not 1 <= len(caption) <= 100:
        return {"safety_violation": "caption_length"}
    return {"safety_violation": None}
```

**검증 순서**:
1. **호칭 포함 여부** (`honorific_missing`): substring 검사. 사용자가 지정한 호칭이 본문에 등장해야 함
2. **일기 길이** (`diary_length`): 50~1000자 범위 (structured output max=1000, 권장 200~400)
3. **캡션 길이** (`caption_length`): 1~100자 범위

### 재시도 흐름

`safety_violation != None`이고 `safety_retry_count < 2`이면 `write_diary`로 돌아감. vision은 재호출하지 않으므로 `vision_description`은 유지된다. 최대 2회 호출 후에는 violation이 있어도 END.

```
SafetyViolation = Literal["honorific_missing", "diary_length", "caption_length"]
```

---

## 7. 프롬프트 시스템

### 로딩 구조 (`prompts_loader.py`)

```python
_PROMPT_PKG = "ai_gateway.prompts.diary_v1"

# 모듈 import 시 1회만 읽어 캐싱
_SYSTEM_TMPL  = files(_PROMPT_PKG).joinpath("system.md").read_text()
_USER_TMPL    = files(_PROMPT_PKG).joinpath("user_template.md").read_text()
_TONE_GUIDE   = files(_PROMPT_PKG).joinpath("tone_guide.md").read_text()
_VISION_SYSTEM_TMPL = files(_PROMPT_PKG).joinpath("vision_system.md").read_text()
```

`importlib.resources.files`로 패키지 내 텍스트 파일을 로드. 서버 시작 시 1회만 읽고 메모리에 유지한다.

### `normalize_species` — 종 정규화

```python
def normalize_species(species_text: str) -> Literal["cat", "dog", "other"]:
    s = species_text.lower().strip()
    cat_kw = ("고양이", "냥이", "냥", "cat", "kitty", "kitten")
    dog_kw = ("강아지", "멍멍이", "멍멍", "댕댕이", "dog", "puppy")
    if any(k in s for k in cat_kw): return "cat"
    if any(k in s for k in dog_kw): return "dog"
    return "other"
```

사용자 자유 입력 species("냥이", "고양이", "cat" 등)를 3가지 정규화 키로 압축. 매칭 실패 시 `other`. 이 결과로 `tone_guide.md`에서 주입할 섹션(§1/§2/§3)을 결정한다.

### tone_guide.md 파싱 (`_split_tone_sections`)

```python
def _split_tone_sections(text: str) -> dict[str, str]:
    # "## §0", "## §1", "## §2", "## §3" 헤더 기준으로 분할
    # 결과: {"common": ..., "cat": ..., "dog": ..., "other": ...}
```

`tone_guide.md`를 4개 섹션으로 파싱. `§0 공통`은 항상, `§1/§2/§3` 중 종에 맞는 1개만 system 메시지에 주입.

### system.md 치환 흐름

```python
def build_system_message(state: DiaryState) -> str:
    species_norm = normalize_species(state["species"])
    return (
        _SYSTEM_TMPL
        .replace("{{ tone_common }}", _TONE_SECTIONS["common"])
        .replace("{{ tone_species }}", _TONE_SECTIONS[species_norm])
        .replace("{{ species_raw }}", state["species"])
        .replace("{{ gender }}", state["gender"])
        .replace("{{ honorific }}", state["honorific"])
    )
```

`system.md`의 `{{ placeholder }}` 5개를 런타임에 치환. `tone_common`과 `tone_species`는 `tone_guide.md`에서 파싱한 해당 섹션 전체 텍스트가 들어간다.

### system.md 구조

```
너는 한국어 1인칭 반려동물 일기 작가다...

## 공통 가이드 (항상 적용)
{{ tone_common }}           ← §0 공통 전체

## 종별 가이드 (이 호출에서 적용되는 1섹션)
{{ tone_species }}          ← §1/§2/§3 중 1개

## 이번 펫 메타
- 종(사용자 원문): {{ species_raw }}
- 성별: {{ gender }}
- 호칭: {{ honorific }}

## 출력
diary_text | short_caption | mood_tag
```

### tone_guide.md 핵심 내용

**§0 공통** (항상 inject):
- 1인칭 한국어, `honorific` substring 1회 이상 필수
- `diary_text` 200~400자, `short_caption` 1~100자
- 7-enum mood 중 정확히 1개
- 사실 환각 금지, PII/의학 조언 금지
- 이전 시도 문장 반복 금지

**§1 고양이**: 도도하고 우아한 어조, "~인 것이다", "흥", 햇볕/그루밍/박스 모티프, 감정 절제
**§2 강아지**: 명랑 직설, "~했어!", "후욱후욱", 산책/간식/현관 모티프, 꼬리·귀 묘사 적극
**§3 기타**: 종 중립적, 호기심 위주, 강한 캐릭터 색 금지, 관측 가능한 것만

### user_template.md 모드 파싱 (`_split_user_modes`)

```python
def _split_user_modes(text: str) -> dict[str, str]:
    # "## 모드 A", "## 모드 B", "## 모드 C" 헤더 기준으로 분할
    # 결과: {"A": ..., "B": ..., "C": ...}
```

### vision_system.md 치환

```python
def build_vision_system_message(state: DiaryState) -> str:
    return (
        _VISION_SYSTEM_TMPL
        .replace("{{ species_raw }}", state["species"])
        .replace("{{ gender }}", state["gender"])
    )
```

호칭·톤·키워드는 vision agent의 책임 밖. species/gender만 fill.

---

## 8. SSE 스트리밍 (`main.py`)

### 이벤트 타입

| 타입 | 방향 | 내용 |
|---|---|---|
| `node` | gateway → client | `{"type": "node", "node": "analyze_image", "phase": "start"}` |
| `vision_done` | gateway → BFF (차단) | `{"type": "vision_done", "vision_description": "..."}` |
| `diary_partial` | gateway → client | `{"type": "diary_partial", "diary_text": "현재까지 누적 텍스트"}` |
| `retry` | gateway → client | `{"type": "retry", "reason": "safety_violation"}` |
| `result` | gateway → client | `{"type": "result", "diary_text": "...", "short_caption": "...", "mood_tag": "..."}` |
| `meta` | BFF → client | `{"type": "meta", "generation_id": "...", "session_id": "...", "regenerate_remaining": 3, "today_new_remaining": 4}` |

`vision_done`은 BFF `mediateStream`에서 가로채서 클라이언트로 forward하지 않는다. DB에 `vision_description` 저장 후 다음 재생성 요청 시 활용.

### `_stream_graph` 핵심 로직

```python
async def _stream_graph(state, config) -> AsyncIterator[bytes]:
    accumulated = ""      # write_diary LLM tool_call args 누적
    last_partial = ""     # 중복 emit 방지
    write_starts = 0      # write_diary 시작 횟수 (≥2 → retry 이벤트)
    final_output = None

    async for event in get_diary_graph().astream_events(state, config, version="v2"):
        kind = event["event"]
        node = event.get("metadata", {}).get("langgraph_node")
        is_node_chain = event.get("name") == node  # 노드 자체의 chain만 (sub-runnable 필터)

        if kind == "on_chain_start" and node in _TRACKED_NODES and is_node_chain:
            if node == "write_diary":
                write_starts += 1
                if write_starts >= 2:       # retry 시작
                    yield _sse({"type": "retry", "reason": "safety_violation"})
                    accumulated = ""        # buffer 초기화
                    last_partial = ""
            yield _sse({"type": "node", "node": node, "phase": "start"})

        elif kind == "on_chain_end":
            if node in _TRACKED_NODES and is_node_chain:
                yield _sse({"type": "node", "node": node, "phase": "end"})
                if node == "analyze_image":     # vision_done 이벤트 emit
                    vd = event["data"]["output"].get("vision_description")
                    if vd:
                        yield _sse({"type": "vision_done", "vision_description": vd})

        elif kind == "on_chat_model_stream" and node == "write_diary":
            # structured output: tool_call_chunks에서 partial JSON args 추출
            for tc in (event["data"]["chunk"].tool_call_chunks or []):
                if args := tc.get("args"):
                    accumulated += args
            partial = _extract_diary_text(accumulated)
            if partial and partial != last_partial:
                last_partial = partial
                yield _sse({"type": "diary_partial", "diary_text": _fix_honorific(partial, honorific)})

    if final_output:
        yield _sse({"type": "result", ...})
```

### `_extract_diary_text` — partial JSON 파싱

```python
_DIARY_TEXT_RE = re.compile(r'"diary_text"\s*:\s*"((?:[^"\\]|\\.)*)')

def _extract_diary_text(buffer: str) -> str | None:
    m = _DIARY_TEXT_RE.search(buffer)
    if not m: return None
    raw = m.group(1)
    if raw.endswith("\\"):
        raw = raw[:-1]   # trailing backslash = escape 미완성 → 제거
    try:
        return json.loads(f'"{raw}"')
    except json.JSONDecodeError:
        return None
```

OpenAI structured outputs는 항상 유효한 JSON prefix를 스트림하므로 정규식으로 `diary_text` 값을 점진적으로 추출 가능. `json.loads`로 escape sequence 디코딩.

### `astream_events` 이벤트 필터

```python
_TRACKED_NODES = {"analyze_image", "write_diary", "safety_check"}
```

같은 노드 내 sub-runnable(with_structured_output wrapping 등)도 `langgraph_node` metadata를 propagate해 `on_chain_start`가 중복 fire됨. `event["name"] == node` 조건으로 노드 자체의 chain만 필터링.

### SSE 응답 헤더

```python
StreamingResponse(
    ...,
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",   # nginx 프록시 버퍼링 차단 → 즉시 flush
    },
)
```

---

## 9. 보안 미들웨어 (`middleware.py`)

### 2중 인증 레이어

```
request
  │
  ▼ internal_secret_middleware (outer — 마지막 등록)
  │  X-Internal-Secret 헤더 검증 (BFF 출처 확인)
  │
  ▼ jwt_middleware (inner — 먼저 등록)
  │  Authorization: Bearer <JWT> 검증 (사용자 인증)
  │  → request.state.user_id = sub
  │
  ▼ endpoint
```

FastAPI `app.middleware("http")` 등록 순서와 실행 순서는 역방향. `jwt_middleware`를 먼저 add하면 `internal_secret_middleware`가 outer가 됨.

### X-Internal-Secret 검증

```python
async def internal_secret_middleware(request, call_next):
    if request.url.path in PUBLIC_PATHS:   # {"/health"}
        return await call_next(request)
    provided = request.headers.get("X-Internal-Secret")
    if provided != settings.internal_shared_secret:
        return JSONResponse(401, {"error": {"code": "UNAUTHENTICATED", ...}})
    return await call_next(request)
```

BFF만 알고 있는 공유 시크릿. Railway 외부에서 gateway에 직접 접근하는 것을 차단.

### Bearer JWT 검증 (Supabase JWKS)

```python
_jwks_client = PyJWKClient(
    settings.jwks_url,     # {SUPABASE_URL}/auth/v1/.well-known/jwks.json
    cache_keys=True,
    lifespan=300,          # 5분 TTL 캐싱
)

decoded = jwt.decode(
    token,
    signing_key.key,
    algorithms=["RS256", "ES256"],
    audience="authenticated",
)
request.state.user_id = decoded["sub"]
```

Supabase가 발급한 사용자 JWT를 JWKS로 검증. `sub` claim을 `request.state.user_id`에 저장해 endpoint와 LangSmith trace에 전달.

### LangSmith trace PII 회피

```python
def _hash_user_id(user_id: str) -> str:
    return hashlib.sha256(user_id.encode()).hexdigest()[:16]

config = {
    "metadata": {
        "owner_id_hash": _hash_user_id(user_id),  # sub 원문 노출 금지
        ...
    }
}
```

`user_id`(Supabase sub UUID) 원문이 LangSmith에 노출되지 않도록 SHA256 해시의 앞 16자리만 사용.

---

## 10. BFF → Gateway 연동

### `gatewayStream` (`lib/server/gateway.ts`)

```typescript
export async function gatewayStream(
  path: "/diary/generate" | "/diary/regenerate",
  body: unknown,
  accessToken: string,
): Promise<Response> {
  const res = await fetch(`${process.env.AI_GATEWAY_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Internal-Secret": process.env.INTERNAL_SHARED_SECRET!,
      Authorization: `Bearer ${accessToken}`,  // 사용자 JWT forward
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  // ...
  return res;   // ReadableStream 포함
}
```

BFF에서 사용자 JWT를 그대로 gateway로 forward. Gateway는 이 JWT로 Supabase JWKS 검증 후 `user_id`를 추출한다.

### `mediateStream` (`lib/server/diary-stream.ts`)

```typescript
export function mediateStream(
  upstream: ReadableStream<Uint8Array>,
  onResult: ResultEventHandler,
): ReadableStream<Uint8Array> {
  return new ReadableStream({
    async start(controller) {
      let visionDescription: string | null = null;
      let resultPayload: ResultPayload | null = null;

      // SSE 파싱 루프
      while (true) {
        // buffer에서 "\n\n" 기준으로 이벤트 추출
        // ...

        if (event.type === "vision_done") {
          visionDescription = event.vision_description;
          continue;               // 클라이언트로 forward 안 함
        }

        emit(event);              // 그 외는 모두 forward

        if (event.type === "result") {
          resultPayload = { ... };
        }
      }

      // stream 종료 후 DB 처리
      if (resultPayload) {
        const meta = await onResult(resultPayload, visionDescription);
        emit(meta);               // meta 이벤트 추가 emit
      }
    },
  });
}
```

`vision_done`을 가로채 `visionDescription` 변수에 저장. `result` 이벤트 수신 후 `onResult` 콜백(DB INSERT + quota 처리)을 호출하고 반환된 `meta` 이벤트를 추가 emit.

---

## 11. API Routes 검증 레이어

### `POST /api/diaries/generate` (`generate/route.ts`)

```
1. 사용자 인증 & access_token 추출
2. Zod 검증: { pet_id, photo_path, keywords }
3. 펫 메타 조회 (RLS가 owner + alive 강제)
4. 한도 검증: usage_quotas.generations_count < 5 (Asia/Seoul 자정 기준)
5. Storage object info: MIME(jpg/png), size(≤10MB) 검증
6. createSignedUrl(photo_path, 3600)
7. diaries 최근 3건 조회 (recent_diaries 컨텍스트)
8. gatewayStream("/diary/generate", body, accessToken)
9. mediateStream: result → diary_generations INSERT + usage_quotas 차감 → meta emit
```

`session_id`는 BFF에서 `crypto.randomUUID()`로 생성. Gateway는 이 ID를 그대로 사용.

### `POST /api/diaries/regenerate` (`regenerate/route.ts`)

```
1. 사용자 인증 & access_token 추출
2. Zod 검증: { session_id, pet_id, photo_path, keywords, feedback? }
3. 펫 메타 조회
4. 같은 session 최신 generation 조회 → nextSeq = lastSeq + 1
5. nextSeq > 4 → REGEN_QUOTA_EXCEEDED (session당 최대 3회 재생성)
6. createSignedUrl(photo_path, 3600)
7. diaries 최근 3건 조회
8. lastGen.vision_description forward → gateway가 analyze_image skip
9. gatewayStream("/diary/regenerate", body, accessToken)
10. mediateStream: result → diary_generations INSERT (usage_quotas 차감 없음) → meta emit
```

`vision_description` forward: 재생성 시 vision LLM을 재호출하지 않아 비용·지연 절감. 첫 generation에서 저장된 값을 DB에서 조회해 전달.

---

## 12. 클라이언트 AI 연동 (`lib/api/diaries.ts`)

### `consumeDiaryStream`

```typescript
async function consumeDiaryStream(
  res: Response,
  callbacks: DiaryStreamCallbacks,
): Promise<{ result: ResultEvent; meta: MetaEvent }> {
  // SSE 파싱 루프
  while (true) {
    // buffer에서 "\n\n" 기준 이벤트 추출
    switch (event.type) {
      case "node":         callbacks.onNode?.(event.node, event.phase); break;
      case "diary_partial": callbacks.onPartial?.(event.diary_text); break;
      case "retry":        callbacks.onRetry?.(event.reason); break;
      case "result":       resultEvent = event; break;
      case "meta":         metaEvent = event; break;
      case "error":        streamError = event.message; break;
      case "vision_done":  break;  // BFF가 이미 차단 — type-exhaustive용
    }
  }
  // result + meta 둘 다 받아야 정상 완료
  return { result: resultEvent, meta: metaEvent };
}
```

### `generateDiary` / `regenerateDiary`

```typescript
export async function generateDiary(
  input: GenerateRequest,
  callbacks: DiaryStreamCallbacks = {},
): Promise<GenerateResponse> {
  const res = await fetch("/api/diaries/generate", { method: "POST", body: JSON.stringify(input) });
  const { result, meta } = await consumeDiaryStream(res, callbacks);
  return {
    session_id: meta.session_id,
    generation_id: meta.generation_id,
    diary_text: result.diary_text,
    short_caption: result.short_caption,
    mood_tag: result.mood_tag,
    regenerate_remaining: meta.regenerate_remaining,
    today_new_remaining: meta.today_new_remaining ?? 0,
  };
}
```

### UI 상태 머신 (`new-diary-client.tsx`)

```
input
  │ generateDiary() 호출
  ▼
loading
  │ onNode("analyze_image", "start") → phase: "analyzing_image"
  │ onNode("write_diary", "start")   → phase: "writing"
  │ onRetry()                        → phase: "retrying" (900ms lock)
  │ onPartial(text)                  → diary_text 점진 표시
  ▼
result
  │ 결과 표시 + 재생성/채택 버튼
```

---

## 13. 데이터 모델 (AI 관련 테이블)

### `diary_generations` — 모든 AI 시도 기록

```sql
id               uuid PRIMARY KEY
owner_id         uuid NOT NULL (FK → auth.users)
pet_id           uuid NOT NULL (FK → pets)
session_id       uuid NOT NULL
seq              integer NOT NULL CHECK (1 ≤ seq ≤ 4)

-- 입력 스냅샷
photo_path       text NOT NULL
keywords         text NOT NULL
honorific_used   text NOT NULL
species_used     text NOT NULL
gender_used      gender NOT NULL
regen_feedback   text  (NULL 가능, 1~500자)
vision_description text (NULL 가능, 1~1000자)  -- analyze_image 산출

-- LLM 산출
diary_text       text NOT NULL CHECK (50 ≤ length ≤ 1000)
short_caption    text NOT NULL CHECK (1 ≤ length ≤ 100)
mood_tag         mood_tag NOT NULL

UNIQUE (session_id, seq)
```

`vision_description`은 regenerate 요청 시 BFF가 조회해 gateway에 forward. analyze_image를 재실행하지 않아도 되는 근거.

### `diaries` — 사용자가 채택한 일기

```sql
id                    uuid PRIMARY KEY
owner_id              uuid NOT NULL
pet_id                uuid NOT NULL
source_generation_id  uuid UNIQUE  (FK → diary_generations)
diary_text            text NOT NULL CHECK (50 ≤ length ≤ 1000)
short_caption         text NOT NULL CHECK (1 ≤ length ≤ 100)
mood_tag              mood_tag NOT NULL
```

`source_generation_id UNIQUE`: 동일 generation을 두 번 채택 불가.

### `usage_quotas` — 일일 생성 한도

```sql
(owner_id, quota_date)  composite PK
quota_date              date  -- KST 자정 기준
generations_count       integer CHECK (0 ≤ count ≤ 5)
```

`seq == 1` 호출만 카운트. 재생성은 카운트 안 함. DB trigger가 INSERT 시 `generations_count=1` 강제, UPDATE 시 increment only.

---

## 14. 의존성 (ai-gateway)

`apps/ai-gateway/pyproject.toml`:

```toml
langgraph>=0.2.50           # StateGraph, astream_events
langchain-openai>=0.3.0     # ChatOpenAI, with_structured_output
langchain-core>=0.3.0       # SystemMessage, HumanMessage
pydantic>=2.0               # BaseModel, Field (structured outputs schema)
pydantic-settings>=2.6.0    # BaseSettings (환경변수)
fastapi>=0.115.0            # API 서버
uvicorn[standard]>=0.32.0   # ASGI 서버
pyjwt[crypto]>=2.10.0       # JWT 검증 + JWKS
```

---

## 15. 실행 예시 (cat, seq=1)

```
POST /api/diaries/generate
  body: { pet_id: "...", photo_path: "abc/diaries/2026/05/xxx.jpg", keywords: "낮잠 창가 햇볕" }

→ generate/route.ts
  - 인증 ✓, 펫 조회 ✓, 한도 검증 (3/5) ✓
  - signed URL 발급: https://...supabase.co/storage/v1/object/sign/pet-photos/...?token=...
  - recent_diaries: ["저번에도 낮잠..."]
  - session_id = crypto.randomUUID() = "sess-xxx"
  - gatewayStream("/diary/generate", { session_id: "sess-xxx", seq: 1, species: "냥이", ... })

→ ai-gateway middleware
  - X-Internal-Secret ✓
  - Bearer JWT ✓ → request.state.user_id = "user-uuid"

→ LangGraph
  _initial_state: vision_description=None, safety_retry_count=0

  [prepare_context] → {}
  [_route_vision] → "analyze_image"  (vision_description == None)

  [analyze_image]
    system: "너는 반려동물 사진 분석가다... 종: 냥이, 성별: female"
    user: image_url (detail=low)
    → VisionAnalysis(description="창가에 웅크린 흰 고양이. 눈을 반쯤 감고...")
    state: vision_description = "창가에 웅크린 흰 고양이..."
    SSE: node(analyze_image, end), vision_done(...)

  [write_diary]
    system: "너는 1인칭 일기 작가... §0 공통... §1 고양이... 호칭: 언니"
    user(모드 A): "사진 묘사: 창가에 웅크린... 키워드: 낮잠 창가 햇볕 최근: [...]"
    → DiaryGenerationResult(
        diary_text="오늘도 언니가 출근한 후 나는 창가를 독점했지...",
        short_caption="오늘도 내 자리",
        mood_tag="평온"
      )
    state: diary_text=..., short_caption=..., mood_tag="평온", safety_retry_count=1
    SSE: node(write_diary, start/end), diary_partial×여러번, result(...)

  [safety_check]
    "언니" in diary_text? ✓
    50 ≤ len(diary_text) ≤ 1000? ✓
    1 ≤ len(short_caption) ≤ 100? ✓
    → safety_violation = None

  [should_retry] → END

→ mediateStream (BFF)
  - vision_done 가로채기 → visionDescription = "창가에 웅크린..."
  - result 수신 → diary_generations INSERT(vision_description 포함)
  - usage_quotas UPDATE (4/5)
  - meta emit: { generation_id: "gen-xxx", session_id: "sess-xxx", regenerate_remaining: 3, today_new_remaining: 1 }

→ consumeDiaryStream (client)
  - onNode: analyze_image start/end → phase: "analyzing_image"
  - onNode: write_diary start/end → phase: "writing"
  - onPartial×여러번 → diary_text 점진 표시
  - result + meta 수집

→ GenerateResponse
  { session_id, generation_id, diary_text, short_caption, mood_tag, regenerate_remaining: 3, today_new_remaining: 1 }
```
