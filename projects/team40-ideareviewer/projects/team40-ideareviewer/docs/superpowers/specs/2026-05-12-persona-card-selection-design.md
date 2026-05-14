# Persona Card Selection Design

> 100개 페르소나 카드 풀에서 사용자가 입력한 서비스 기획안에 적합한 2명을 단일 LLM 패스로 선정하고, 선정 근거를 구조화해 그래프 state에 함께 저장한다.

## Goal

`scripts/generate_user_cards.py`로 생성된 100개 카드 풀(`data/personas/persona_cards.selected.json`)을 런타임 페르소나 풀로 사용한다. `select_personas` 노드는 100개를 단일 LLM 프롬프트에 통째로 전달하고, LLM이 선정 결과(card_id 2개)와 선정 근거(각자 이유, 페어 구성 이유, 예상 리뷰 각도)를 구조화된 형식으로 반환한다. 결과는 기존 `persona_a`/`persona_b`와 함께 새 state 필드 `persona_selection_reason`에 저장되어 Streamlit UI에서 노출된다.

## Non-Goals

- 벡터 인덱스(Chroma/임베딩) 기반 retrieval — 별도 plan(`docs/superpowers/plans/2026-05-11-persona-rag-selection.md`)에 보존되며 향후 풀 확장 시 재개.
- retrieve + rerank 2단계 구조 — 100개 규모에서 정확도 향상이 비용을 정당화하지 못함.
- brief 메타데이터 기반 hard filter — 입력 기획안에 demographic 조건이 엄격히 명시되는 경우가 드물고, 텍스트 의미 기반 매칭이 더 적합함.
- raw 페르소나 샘플링/카드 생성 파이프라인 변경 — 이미 완료된 별도 작업(`scripts/generate_user_cards.py`).
- `f0_parse`, `generate_opinion`, `generate_review`, `supervisor_finalize` 노드 변경.

## Architecture

기존 파이프라인 흐름은 변경하지 않는다. `select_personas` 노드 한 곳만 갈아끼우고, 카드 풀 경로를 단일화한다.

```text
raw_input
  → f0_parse
  → select_personas       ← 본 설계 변경 지점
  → generate_opinion (×2 병렬, Send)
  → generate_review
  → supervisor_finalize
  → final_review_text
```

100개 카드 데이터는 `select_personas` 노드 함수 스코프 안에서만 로드된다. LangGraph state에는 선정된 2명(`persona_a`, `persona_b`)과 선정 근거(`persona_selection_reason`)만 올라가며, 100개 풀은 다음 노드로 전파되지 않는다.

## Data Model

`schemas.py`에 새 모델 하나를 추가한다.

```python
class PersonaSelectionReason(BaseModel):
    """LLM이 두 명의 페르소나를 고른 근거."""

    selected_card_ids: list[str]
    per_persona_reasons: dict[str, str] = Field(default_factory=dict)
    pair_reason: str
    expected_review_angles: list[str] = Field(default_factory=list)
```

필드 의미:
- `selected_card_ids`: 정확히 2개. 후보 풀에 실재하는 card_id 만. LLM이 invalid id를 반환하면 코드에서 fallback으로 보정한 뒤 이 필드도 함께 갱신.
- `per_persona_reasons`: `card_id → 한 줄 선정 이유`. UI 노출.
- `pair_reason`: 두 사람을 페어로 묶은 이유 (관점 차이 / 상호 보완성).
- `expected_review_angles`: 이 페어가 검증할 핵심 리뷰 각도 3~5개. UI 노출.

이 모델은 `docs/superpowers/plans/2026-05-11-persona-rag-selection.md`의 동명 모델과 키 호환이다. 향후 RAG plan으로 진화할 때 데이터 모델을 다시 정의하지 않아도 된다. 단 RAG plan의 `query_coverage` 필드는 본 설계에서는 사용하지 않으므로 모델에 포함하지 않는다.

`schemas.py`의 `__all__`에 `PersonaSelectionReason` 추가.

## State

`state.py`의 `ProjectState`에 한 필드 추가:

```python
class ProjectState(TypedDict, total=False):
    ...
    persona_selection_reason: PersonaSelectionReason
```

`total=False`(기존 패턴) 그대로. `select_personas` 노드만 이 키에 쓴다.

## Persona Pool

`services/persona_repository.py`의 시드 경로를 단일화한다.

- 변경 전: `_SEED_PATH = .../data/personas/persona_cards.seed.json`
- 변경 후: `_SEED_PATH = .../data/personas/persona_cards.selected.json`

함수 시그니처(`load_personas() -> list[TargetUserPersonaCard]`)와 호출부는 그대로. `persona_cards.seed.json` 파일은 디스크에서 삭제하지 않고 코드 경로에서만 떼어낸다.

## Node Logic

`nodes/f1_select.py`를 다음 구조로 재작성한다 (기존 `_Selection`, `_llm_select`, `_llm` 모듈 레벨 클라이언트 폐기).

### 압축 카드 표현

100개 × 모든 필드 출력 시 토큰 부담이 커지므로, 선택 판단에 핵심인 필드만 프롬프트에 포함한다.

```text
- card_id: persona_xxxx
  이름/메타: 김영수 | 60s | 남 | 농업 | 충청남
  요약: <one_line_summary>
  목표: <user_goals 슬래시 조인>
  불편함: <pain_points 슬래시 조인>
  긍정 트리거: <positive_triggers 슬래시 조인>
  부정 트리거: <negative_triggers 슬래시 조인>
```

제외 필드: `life_context`, `speaking_style`, `guardrails`, `source_uuid`. 카드당 약 200자 → 100개 ≈ 20K자 (약 10K 토큰). solar-pro3 컨텍스트 한도 안.

### LLM 클라이언트

```python
_llm = ChatUpstage(
    model="solar-pro3",
    timeout=120,
    max_retries=5,
).with_structured_output(PersonaSelectionReason)
```

`timeout=120`, `max_retries=5`는 `scripts/generate_user_cards.py` 100건 풀 실행에서 rate-limit 회복이 확인된 값.

### 프롬프트

`ChatPromptTemplate.from_messages`로 system/human 2개 메시지.

System:

```text
당신은 서비스 기획안 검토를 위해 서로 보완적인 관점을 가진 페르소나 패널 2명을 선정합니다.
단순 유사도가 아니라 (a) 핵심 타겟 적합성, (b) 잠재 리스크 검증,
(c) 두 사람의 관점 차이를 동시에 고려해 정확히 2명을 고르세요.
selected_card_ids 에는 반드시 아래 후보 목록에 실재하는 card_id 만 사용합니다.
per_persona_reasons 는 선택한 두 card_id 각각에 대해 한 줄로 작성합니다.
expected_review_angles 는 이 페어가 검증할 핵심 리뷰 각도 3~5개를 짧게 나열합니다.
```

Human (포맷):

```text
## 서비스 기획안
제목: {title}
타겟: {target}
설명: {description}
핵심 기능:
{key_features}
우려사항: {concerns}

## 페르소나 후보 ({pool_size}명)
{persona_list}
```

### 선택 함수

```python
def select_personas(state: ProjectState) -> dict:
    brief: ServicePlanInput = state["brief"]
    pool = load_personas()

    if len(pool) <= _SELECT_COUNT:
        selected = list(pool)
        reason = PersonaSelectionReason(
            selected_card_ids=[c.card_id for c in selected],
            pair_reason="풀 크기가 부족해 전원 선택",
        )
        return _result(selected, reason)

    reason = _llm_select(brief, pool)
    selected = _resolve_selection(reason.selected_card_ids, pool)
    normalized_reason = reason.model_copy(
        update={"selected_card_ids": [c.card_id for c in selected]}
    )
    return _result(selected, normalized_reason)
```

`_resolve_selection`은 LLM이 반환한 id 중 풀에 실재하는 것만 골라 순서를 유지하고, 부족하면 풀 앞에서부터 채워 정확히 2개를 만든다.

`_result(selected, reason)`은 `{"persona_a": selected[0], "persona_b": selected[1], "persona_selection_reason": reason}` 반환.

### Fallback

1. LLM이 풀에 없는 card_id 를 반환 → `_resolve_selection`이 풀 앞에서부터 채움. `selected_card_ids`는 실제 선택된 id로 갱신.
2. LLM 호출 자체가 실패 (네트워크/429 max_retries 초과 등) → 예외를 잡아 풀 앞 2개를 선택, `pair_reason="LLM 호출 실패 - 기본 페어 사용"` 으로 reason 기록. 그래프 흐름은 끊지 않는다.
3. 풀 크기 ≤ 2 → LLM 호출 생략, 전원 선택.

### `route_opinions` 변경 없음

`persona_a`/`persona_b` 만 참조하므로 그대로 동작.

## UI

`app.py` 결과 탭에 "선정 근거" 섹션을 추가한다. 새 탭은 추가하지 않는다 (단순 재설계 정신 유지).

- 기존 "사용자 패널" 탭 본문 하단에 `st.container(border=True)` 한 카드 (페르소나 카드를 먼저 보고 근거를 본다):
  - **페어 구성 이유**: `pair_reason` 한 줄
  - **각자 선정 이유**: `per_persona_reasons` 를 `card_id` 와 `display_name` 매핑해 bullet
  - **예상 리뷰 각도**: `expected_review_angles` bullet 목록

state 키는 `_get(state, "persona_selection_reason")` 패턴으로 안전 접근. reason 이 없으면 (예: 직접 그래프를 우회한 경우) 섹션 자체를 렌더링하지 않는다.

`services/pipeline_runner.py` 변경 없음.

## Testing

`tests/test_f1_select.py` 신규 (프로젝트 컨벤션인 `unittest` 기반). 4 케이스:

1. **`test_select_personas_returns_two_cards_with_reason`** — 정상 케이스. `selector` 함수를 의존성 주입으로 교체해 결정적으로 두 card_id 와 reason 을 반환시키고, state 출력에 `persona_a`, `persona_b`, `persona_selection_reason` 3개 키가 올바르게 채워지는지 검증.
2. **`test_select_personas_falls_back_when_llm_returns_invalid_ids`** — `selector` 가 풀에 없는 id 를 섞어 반환 → 앞에서부터 보정되어 정확히 2개로 만들어지고 `selected_card_ids` 가 실제 선택된 id 로 갱신되는지.
3. **`test_select_personas_handles_llm_exception`** — `selector` 가 예외를 raise → 풀 앞 2개로 fallback + `pair_reason` 에 실패 사유가 들어가는지.
4. **`test_select_personas_with_small_pool`** — `load_personas`를 풀 크기 ≤ 2 인 fixture 로 교체 → LLM 호출 없이 전원 선택.

테스트 가능성을 위해 `select_personas` 내부의 LLM 호출은 `_llm_select(brief, pool) -> PersonaSelectionReason` 함수로 캡슐화하고, 테스트는 `unittest.mock.patch`로 이 함수와 `load_personas` 를 교체한다.

기존 테스트 (`tests/test_generate_user_cards.py`, `tests/test_sample_hf_personas.py`)는 영향 없음.

## Dependencies

변경 없음. 기존 `langchain_upstage`, `pydantic`, `langgraph` 만으로 충분. Chroma/임베딩 도입 없음.

## File Changes Summary

| 파일 | 변경 |
|---|---|
| `schemas.py` | `PersonaSelectionReason` 추가, `__all__` 업데이트 |
| `state.py` | `persona_selection_reason: PersonaSelectionReason` 필드 추가 |
| `services/persona_repository.py` | `_SEED_PATH` 를 `persona_cards.selected.json` 으로 변경 |
| `nodes/f1_select.py` | 전면 재작성 (압축 포맷, 새 reason 모델, fallback 정책) |
| `app.py` | "사용자 패널" 탭에 선정 근거 카드 추가 |
| `tests/test_f1_select.py` | 신규 (4 케이스) |

## Open Risks

- LLM 응답 구조화 실패율: 100개 카드를 한 컨텍스트에 넣을 때 LLM이 `with_structured_output` 스키마를 어기는 빈도가 늘어날 수 있음. SDK 재시도(`max_retries=5`)로 대부분 흡수 예상하지만, 실패 시 fallback이 깔려 있으므로 그래프 흐름은 끊기지 않는다.
- 토큰 비용: 호출당 약 10~12K input 토큰. 데모 1회당 비용 부담은 미미하나, 동시 다수 사용 시 합산 비용은 별도 모니터링.