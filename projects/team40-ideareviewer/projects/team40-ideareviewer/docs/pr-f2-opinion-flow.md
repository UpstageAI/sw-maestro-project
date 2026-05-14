# PR — F2 Opinion: 페르소나 카드 + A/B 병렬 1차 의견 플로우

**브랜치:** `5/feature/f1-opinion`  → `main`
**커밋 16개, 23 파일 변경 (+5602 / −10)**
**작업 기간:** 2026-05-05 ~ 2026-05-07

---

## 한 줄 요약

원본 페르소나 데이터(HuggingFace Nemotron Korean) → LLM 정제 → 런타임용 페르소나 카드 → **고정 기획안 1개를 A/B 두 페르소나에게 병렬로 던져 1차 의견을 받는 LangGraph 0.2 idiom 플로우**까지의 end-to-end MVP.

## WHY

목표는 "기획자가 모르는 반응"을 두 페르소나로부터 뽑아내는 것. 단일 LLM에 "두 사람 입장에서 의견 줘" 하면 평균화되므로, **각 페르소나에게 독립 컨텍스트로 LLM을 호출 → A/B로 분기**하는 구조가 필요.

또한 페르소나가 LLM에 **자기 정체성을 정확히 흉내내게** 하려면 카드 자체가 priming-free + 정체성-안정해야 함 → 카드 정제 프롬프트 자체가 별도 엔지니어링 영역이 됨.

## 전체 아키텍처

```
[OFFLINE / batch]
  data/personas/raw_personas.seed.json (HF Nemotron 원본)
        │
        │  scripts/generate_user_cards.py  (solar-pro3, reasoning=low)
        │     • 정체성 공통 / one_line_summary / life_context / 신호 다양성 / speaking_style 규칙
        ▼
  data/personas/persona_cards.seed.json  (.gitignored — 산출물)

[RUNTIME / langgraph]
  run_fixed_input_parallel_review()
    │
    ▼
  prepare_fixed_review_state
    │  load_default_persona_pair() + build_fixed_brief()
    │  → state["persona_a"], state["persona_b"], state["brief"]
    │
    │  Send fan-out (conditional edges)
    ├─────────► f2_opinion(OpinionTask{a, persona_a, brief})  ──► state["opinion_a"]
    └─────────► f2_opinion(OpinionTask{b, persona_b, brief})  ──► state["opinion_b"]
                  │
                  │  ChatUpstage(solar-pro3, reasoning=high)
                  │  with_structured_output(OpinionGenerationOutput, include_raw=True)
                  │  RetryPolicy(max_attempts=3, retry_on=9 exception types)
                  ▼
                END
```

핵심 결정:
- **Send API fan-out** — N=2 함수 → 단일 노드 + Send N개. 페르소나 N 확장 시 코드 변경 0.
- **ProjectState slot key 유지** (`opinion_a`/`opinion_b`) — `state.py` 임의 수정 금지 주석 준수.
- **카드 생성은 오프라인** — 런타임은 카드를 로드만 함.
- **LLM 호출은 f2_opinion 단일 지점**. 카드 정제는 별도 스크립트.

## 변경 영역 (4개 레이어)

### 1. 스키마 (Pydantic)

| 파일 | 역할 |
|---|---|
| `schemas.py` | `RawNemotronPersona`, `TargetUserPersonaCard`, `PersonaSignal`, `ServicePlanInput`, `Opinion`, `ReactionPoint`, `Review`, `PointFeedback` |
| `state.py` | `ProjectState` TypedDict — slot key 형식(`opinion_a`/`opinion_b`). 임의 수정 금지 |

`PersonaSignal`은 `text + source_field + evidence`로 근거 추적 가능. 페르소나 카드의 user_goals/pain_points/positive_triggers/negative_triggers는 모두 `list[PersonaSignal]`.

### 2. 카드 정제 (오프라인 LLM)

| 파일 | 역할 |
|---|---|
| `scripts/generate_user_cards.py` | `RawNemotronPersona` → `TargetUserPersonaCard` LLM 정제 |
| `services/persona_repository.py` | 카드 JSON 로드 유틸 |

**카드 정제 프롬프트는 5번 반복 진화** (이번 브랜치에서):
| Ver | 패치 | 해결한 문제 |
|---|---|---|
| v1 | 베이스라인 LLM 정제 | — |
| v2 | "X이지 Y가 아닙니다" 부정문 추가 | 페르소나 B 농부 오해 (시도) |
| v3 | 부정문 제거, 동사 중심 일상 묘사 | 부정문 priming + 메타 누설 |
| v4 | occupation 표면값/추론 라벨 차단 + 신호 다양성 8개 중 동일 영역 3개 한도 | A "무직" 표면 노출 + B "농부" 라벨 + B 신호 편향 |
| v5 (현재) | life_context "나는" 1인칭 강제 + 일반 소비자 추상 신호 회피 | B 정체성 흔들림 + 추상 신호 |

각 라운드마다 `persona_cards.seed.json` 재생성 → `f2_opinion` 실측 → 다음 라운드 결정. **상세 trail은 [docs/reviews/f2_opinion.md](reviews/f2_opinion.md) v1~v9** (카드 prompt 자체는 가장 최근 라운드는 미로깅, 직접 prompt diff 참조).

### 3. F2 의견 생성 노드

| 파일 | 역할 |
|---|---|
| `nodes/f2_opinion.py` | 페르소나 1명의 1차 의견 생성. Send payload(`OpinionTask`) 입력 |
| `fixtures.py` | `FIXED_RAW_INPUT` + `build_fixed_brief()` 단일 진실 원천 |

**핵심 안전장치:**
- `OpinionGenerationOutput` Pydantic 스키마로 `min/max_length=3` 강제 (긍정 3 + 부정 3)
- `with_structured_output(include_raw=True)` — 파싱 실패 시 raw + parsing_error 동시 노출 (디버깅)
- `_normalize_points` 후처리 — `point_id`(예: `a_pos_01`)를 server-side 단일 진실 원천으로 강제. 프롬프트는 id 강제하지 않음 (이중 강제 제거)
- `_normalize_opinion` — `persona_id`를 카드의 `card_id`로 강제 덮어씀

**프롬프트는 9번 반복 진화** ([docs/reviews/f2_opinion.md](reviews/f2_opinion.md)):
| Ver | takeaway |
|---|---|
| v9 | 노드 시그니처 `state` → `OpinionTask` payload, LLM lazy singleton, point_id 이중강제 제거 |
| v8 | f2_referenece.py 비교에서 LangChain idiom만 선별 흡수 |
| v7 | concerns priming 제거 — f2는 prompted-free 1차 반응 노드 |
| v6 | reasoning 단계 절차적 지시 cargo 제거 (API가 이미 하는 일 프롬프트가 다시 시키지 않음) |
| v5 | solar-pro3 reasoning=high에 맞춘 프롬프트 재구조 |
| v4 | ChatUpstage sampling 파라미터를 직접 인자로 (model_kwargs 회피) |
| v3 | solar-pro3 전환 (pricing 동일) |
| v2 | solar-pro2 적합성 분석 |
| v1 | 코드 구조/품질 리뷰 |

### 4. LangGraph 병렬 플로우

| 파일 | 역할 |
|---|---|
| `graph.py` | StateGraph 빌드 + Send fan-out + RetryPolicy + 모듈 레벨 컴파일 |

**v2 라운드(이번 세션) 핵심 변화** ([docs/reviews/parallel_f2_opinion_graph.md](reviews/parallel_f2_opinion_graph.md) v2):

| 측면 | Before (v1) | After (v2) |
|---|---|---|
| Fan-out | `f2_opinion_a`/`f2_opinion_b` 두 함수 + 노드 두 개 등록 | 단일 `f2_opinion` 노드 + Send 2개 |
| Retry | 30줄짜리 수동 `_retry_branch` (try/except + sleep) | `RetryPolicy(max_attempts=3, retry_on=...)` 4줄 |
| 그래프 컴파일 | 호출마다 `build_parallel_opinion_graph()` 새로 컴파일 | 모듈 로드 시 `_DEFAULT_GRAPH` 1회 컴파일 |
| 고정 입력 | f2_opinion + graph 양쪽에 분산 (concerns 포함 여부도 다름) | `fixtures.py`로 단일 진실 원천 |
| 빈 스텁 노드 | f0_parse, f1_select, f3_review 0바이트 파일 | 삭제 (구현 시 새로 만들기) |
| LLM 인스턴스 | 매 invoke마다 `_create_llm()` + `load_dotenv()` | `@functools.cache _get_chain()` lazy singleton |

**graph.py 154 → 110줄 (-29%), 외부 동작 동일.**

`graph.py` v1 (Codex 작성) 결정 사항은 그대로 유지됨:
- 병렬 orchestration은 LangGraph가, retry는 노드 단위 격리
- ProjectState 불변
- A/B `opinion_a`/`opinion_b` slot 분리
- `run_fixed_input_parallel_review` 단일 진입점

## 검증

### 자동 검증
- `python -c "import ast; ast.parse(...)"` — 5개 변경 파일 syntax OK
- `import graph` — `_DEFAULT_GRAPH` 모듈 로드 시 컴파일 OK
- 기존 테스트 `tests/test_f2_opinion_contract.py`, `tests/test_generate_user_cards.py`, `tests/test_schemas.py` 존재 (회귀 보호)

### 수동 실측 (`scripts/test_f2_opinion.py`)
v1~v5 카드로 동일 입력에 대한 f2 출력 품질 변화를 측정:

| 페르소나 | v1 카드 | v2 | v3 | v4 | v5 |
|---|---|---|---|---|---|
| A (84세 시장 상인 할머니) | 4/6 — 입장 혼란 (소비자 vs 상인) | 5/6 — 메타 누설 1 | 5/6 — anchor 1 약함 | **6/6** ✅ | 5/6 (would_use 흔들림) |
| B (67세 농산물 상하차 노동자) | 2/6 — 농부로 오해 | 5/6 — 1 어색 | 5/6 — anchor 약함 | 4/6 — 정체성 흔들림 | **5/6** ✅ |

**핵심 인사이트:**
- 카드 prompt가 부정문 priming, 메타 누설, occupation 표면값, 추론 라벨, 신호 편향, 1인칭 누락, 추상 신호 등 7가지 문제를 prompt-level에서 해결
- A의 would_use 분산 (Run1 True, Run2 False)은 카드의 pain 약점 → LLM 본질적 분산 영역, prompt 추가 패치 ROI 낮음
- B는 v5 1인칭 강제로 정체성 안정, 분산이 와도 의향 일관

### 실측 명령 (재현 가능)
```bash
# 카드 재생성 (Upstage API key 필요)
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/generate_user_cards.py --mode llm

# 단일 노드 직접 실행
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/test_f2_opinion.py

# 병렬 그래프 실행
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/test_parallel_f2_opinion.py
```

## 의도적 보류 (Tier 3 — 이 브랜치 범위 밖)

향후 f3 도입 또는 UX 요구 시 다룰 항목:

- **async / streaming** — `await app.ainvoke(...)` + `astream_events(version="v2")`. UI 붙는 시점에.
- **checkpointer** — `MemorySaver` / `SqliteSaver`. f3 reentry 또는 재개 가능성 들어갈 때.
- **`RunnableConfig` 메타데이터** — `tags=["persona_a"]`, `metadata={"persona_id": ...}` 바인딩. LangSmith 페르소나별 필터링.
- **`template_format="mustache"`** — 페르소나 텍스트에 `{`/`}` 들어올 때 ChatPromptTemplate 충돌 대비.
- **N 가변 페르소나** — `state["opinions"]: dict[str, Opinion]`로 변경. 현재는 슬롯형(`opinion_a`/`opinion_b`) 유지로 보류.
- **f3_review 노드** — 상대 의견 교차 피드백 (스키마 `Review`/`PointFeedback`은 이미 있음). 빈 스텁은 이번 브랜치에서 삭제.
- **카드 prompt diminishing returns 영역** — display_name 작성 규칙, pain vs negative_triggers 의미 구분, pain 페르소나 정합성 가이드. v5에서 7개 문제 해결 후 잔여 문제는 LLM 분산 영역으로 판단.

## 리뷰 로그 (자세한 결정 trail)

- **[docs/reviews/f2_opinion.md](reviews/f2_opinion.md)** — `nodes/f2_opinion.py` 자체의 9개 버전 진화 (코드 구조 → 모델 적합성 → 프롬프트 cargo 제거 → concerns priming → idiom 흡수 → Send payload 시그니처)
- **[docs/reviews/parallel_f2_opinion_graph.md](reviews/parallel_f2_opinion_graph.md)** — `graph.py` 2개 버전 (v1 Codex 초기 구현, v2 LangGraph 0.2 idiom 재작성)

각 버전 섹션은 immutable. 결정이 뒤집힌 경우 `Correction (vN §M)` 항목으로 새 버전 안에 명시. 자세한 사유/대안 비교는 해당 버전 본문 참조.

## 리뷰어 체크리스트

- [ ] 카드 정제 프롬프트의 7가지 가이드(부정문 금지 / occupation 표면값 차단 / 추론 라벨 차단 / 신호 다양성 / 1인칭 / 추상 회피 / source_field·evidence 분리)가 의도대로 이해되는가?
- [ ] f2 노드의 안전장치(`min/max_length=3`, `include_raw=True`, `_normalize_points`, `_normalize_opinion`)가 LLM 출력의 어떤 종류 실패를 잡는지 명확한가?
- [ ] LangGraph Send fan-out 패턴이 `state.py` 미수정 제약과 어떻게 양립하는가? (slot key 유지 + payload 기반 노드 시그니처)
- [ ] RetryPolicy의 9종 retry_on이 실제로 일어날 수 있는 실패만 포함하는가? (LangChain/Pydantic/Upstage SDK)
- [ ] `_DEFAULT_GRAPH` 모듈 레벨 컴파일이 테스트 시 path override(`build_parallel_opinion_graph(custom_path)`)와 충돌하지 않는가?
