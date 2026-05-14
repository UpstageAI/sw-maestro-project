# Persona Selection Fit Improvements Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 본 plan(`persona-card-selection.md`) 구현 후 두 개 brief(`docs/test-briefs.md`의 senior_health, farm_direct)로 실제 LLM을 돌려 평가한 결과 드러난 적합성 결함을 좁힌다. 구체적으로 (a) 페어가 brief의 명시된 타겟 demographic을 충실히 반영하도록, (b) `pair_reason` 텍스트 안에서 카드 id-이름 hallucination이 일어나지 않도록, (c) `per_persona_reasons`와 `expected_review_angles`가 매 호출마다 안정적으로 채워지도록 만든다.

**Architecture:** 구조 변경 없음. 변화는 두 군데에 집중 — `schemas.py`의 `PersonaSelectionReason` 필드에 LLM이 읽을 JSON-schema-level 설명(`Field(description=...)`)을 추가하고, `nodes/f1_select.py`의 system 프롬프트를 강화한다. 테스트는 기존 12 케이스를 유지하고, 새 회귀 테스트 1~2개를 추가한다.

**Tech Stack:** Python 3.11, Pydantic v2, LangChain Upstage (`solar-pro3`), LangGraph, unittest.

**Origin spec:** `docs/superpowers/specs/2026-05-12-persona-card-selection-design.md`
**Parent plan:** `docs/superpowers/plans/2026-05-12-persona-card-selection.md`
**Evaluation evidence:** `scripts/run_brief_eval.py` 실행 결과 (helper 자체는 commit, 실행 결과 로그는 commit 안 함)

---

## Non-Goals

- `nodes/f3_review.py`의 `agreement` 라벨 의미 명확화 — 평가에서 발견됐지만 별 노드이며 별도 plan으로 분리.
- Opinion(`f2_opinion.py`)의 `would_use`와 Review의 `revised_would_use` 일관성 — 별 노드.
- 100개 풀의 demographic 다양성 재샘플링 — 데이터 작업이며 본 plan 범위 밖.
- `with_structured_output`을 다른 모델(Solar Mini, Solar Pro 등)로 교체하는 실험.
- Fewshot example 도입 — 토큰 비용 vs 효과 검증 후 별도 plan.

---

## File Structure

- Modify: `schemas.py` — `PersonaSelectionReason` 4개 필드에 `Field(description=...)` 추가.
- Modify: `nodes/f1_select.py` — system 프롬프트 보강 (demographic 우선 + reason 텍스트 규칙 + 필드 채움 강제).
- Modify: `tests/test_f1_select.py` — 1~2개 회귀 테스트 추가 (per_persona_reasons 채움 검증, 프롬프트 안 demographic 키워드 포함 검증).

---

## Task 1: `PersonaSelectionReason` Field 설명 보강

**Files:**
- Modify: `schemas.py`
- Test: `tests/test_persona_selection_reason.py`

`Field(description=...)`은 `with_structured_output(...)`이 LLM에 보내는 JSON schema에 그대로 포함된다. Pydantic 모델이 LLM 응답의 형식·세부 의미를 강제하는 가장 직접적 채널.

- [ ] **Step 1: Add failing test for description presence**

Append to `tests/test_persona_selection_reason.py`:

```python
    def test_fields_carry_descriptions_for_llm_schema(self) -> None:
        # Field descriptions propagate into the JSON schema sent to with_structured_output.
        # Empty/missing descriptions degrade LLM compliance.
        schema = PersonaSelectionReason.model_json_schema()
        props = schema["properties"]

        self.assertIn("description", props["selected_card_ids"])
        self.assertIn("description", props["per_persona_reasons"])
        self.assertIn("description", props["pair_reason"])
        self.assertIn("description", props["expected_review_angles"])

        # The description for selected_card_ids must enforce the "정확히 2개" invariant in prose.
        self.assertIn("2", props["selected_card_ids"]["description"])
```

- [ ] **Step 2: Run test to verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_selection_reason -v
```

Expected: 1 new test FAILS with `KeyError: 'description'` on at least one field.

- [ ] **Step 3: Add descriptions**

In `schemas.py`, replace the `PersonaSelectionReason` body with:

```python
class PersonaSelectionReason(BaseModel):
    """LLM이 두 명의 페르소나를 고른 근거."""

    selected_card_ids: list[str] = Field(
        description=(
            "후보 풀에 실재하는 card_id 정확히 2개. "
            "card_id 외 다른 식별자(이름·직업 등)는 적지 말 것. "
            "코드 측 fallback이 결과 기준으로 다시 채울 수 있음."
        ),
    )
    per_persona_reasons: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "선택한 두 card_id 각각을 키로, 그 사람을 고른 이유 한 줄을 값으로. "
            "빈 dict로 두지 말 것 — 두 card_id 모두 반드시 채울 것."
        ),
    )
    pair_reason: str = Field(
        description=(
            "두 사람을 페어로 묶은 이유. "
            "후보 풀의 카드 이름·직업·card_id를 본문에 적지 말고, "
            "두 사람이 기획안 검토에서 맡는 관점·역할만 서술."
        ),
    )
    expected_review_angles: list[str] = Field(
        default_factory=list,
        description=(
            "이 페어가 검증할 핵심 리뷰 각도 3~5개. 빈 list로 두지 말 것. "
            "각 항목은 짧은 명사구 (예: '등록 난이도', '품질 신뢰')."
        ),
    )
```

- [ ] **Step 4: Run test to verify pass**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_selection_reason -v
```

Expected: 3 tests PASS (2 original + 1 new).

- [ ] **Step 5: Verify downstream tests unaffected**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select -v
```

Expected: 12/12 PASS (existing test_f1_select.py tests still green — the descriptions don't change runtime validation).

- [ ] **Step 6: Commit**

```powershell
git add schemas.py tests/test_persona_selection_reason.py
git commit -m "feat: add field descriptions to PersonaSelectionReason for LLM schema"
```

---

## Task 2: `f1_select` system 프롬프트 강화

**Files:**
- Modify: `nodes/f1_select.py`
- Test: `tests/test_f1_select.py`

기존 system 프롬프트가 (a) 핵심 타겟 적합성 / (b) 잠재 리스크 / (c) 관점 차이 — 세 축을 *동등하게* 나열했더니 LLM이 (c)를 과하게 따라가 demographic을 놓침. 또 `pair_reason` 안에 카드 이름을 적는 hallucination이 발생. 프롬프트로 두 군데를 못 박는다.

- [ ] **Step 1: Add regression tests for new prompt content**

Append to `tests/test_f1_select.py`:

```python
    def test_system_prompt_emphasises_demographic_fit(self) -> None:
        # The first axis must be demographic fit so the LLM doesn't over-rotate on perspective diff.
        from nodes.f1_select import _PROMPT

        system_text = _PROMPT.messages[0].prompt.template
        self.assertIn("타겟", system_text)
        self.assertIn("demographic", system_text.lower())  # or another concrete English/Korean marker

    def test_system_prompt_forbids_names_in_pair_reason(self) -> None:
        from nodes.f1_select import _PROMPT

        system_text = _PROMPT.messages[0].prompt.template
        self.assertIn("pair_reason", system_text)
        self.assertIn("이름", system_text)  # rule must mention "이름" so LLM avoids hallucinating names
```

- [ ] **Step 2: Run tests to verify failure**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select.SelectPersonasTests -v
```

Expected: the two new tests FAIL because the current prompt does not contain `demographic` or the `이름` rule.

- [ ] **Step 3: Replace the system message**

In `nodes/f1_select.py`, replace the `("system", ...)` tuple inside `_PROMPT` with:

```python
    (
        "system",
        "당신은 서비스 기획안 검토를 위해 서로 보완적인 관점을 가진 페르소나 패널 "
        f"{_SELECT_COUNT}명을 선정합니다.\n\n"
        "선정 기준 (순서 = 우선순위):\n"
        "1) 기획안에 명시된 타겟의 demographic(연령대, 직업, 지역, 가족 관계 등) "
        "충실성. 명시된 demographic 조건을 충족하는 카드를 우선 후보로 고려한다.\n"
        "2) 잠재 리스크 검증 — 기획안의 우려사항/약점을 가장 잘 드러낼 페르소나.\n"
        "3) 두 사람의 관점 차이 — 같은 demographic 조건 안에서 서로 다른 직업·생활맥락·"
        "트리거를 가진 페어. (1)을 희생해서 (3)을 키우지 말 것.\n\n"
        "출력 규칙:\n"
        "- selected_card_ids 는 반드시 아래 후보 목록에 실재하는 card_id 정확히 2개.\n"
        "- per_persona_reasons 는 비워두지 말 것. 선택한 두 card_id 각각에 한 줄을 반드시 적는다.\n"
        "- pair_reason 본문에 카드 이름·직업·card_id 를 적지 말 것. "
        "두 사람이 맡는 관점·역할만 한국어로 서술한다. (예: '핵심 사용자 본인과 보호자 관점을 동시에 본다')\n"
        "- expected_review_angles 는 비워두지 말 것. 짧은 명사구 3~5개."
    ),
```

- [ ] **Step 4: Run tests to verify pass**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select -v
```

Expected: 14/14 PASS (12 existing + 2 new).

- [ ] **Step 5: Run import sanity**

```powershell
.\.venv\Scripts\python.exe -c "import graph; print('graph import ok')"
```

Expected: `graph import ok`.

- [ ] **Step 6: Commit**

```powershell
git add nodes/f1_select.py tests/test_f1_select.py
git commit -m "feat: strengthen f1_select prompt for demographic fit and reason hygiene"
```

---

## Task 3: 동일 brief 재실행 + 평가 메모

**Files:**
- No source changes.
- Use `scripts/run_brief_eval.py` (committed in this branch as part of the fit-improvements plan).

이 task는 자동화 테스트가 아니라 **수동 평가**다. Task 1, 2 변경이 실제로 선정 적합성을 끌어올렸는지 확인.

- [ ] **Step 1: Re-run senior_health brief**

```powershell
.\.venv\Scripts\python.exe scripts/run_brief_eval.py senior_health 2>&1 | tee tmp_senior_after.log
```

체크 포인트:
- 선정된 페어 중 1명 이상이 `age_group`이 `60s` 또는 `70plus`인가?
- `pair_reason` 텍스트 안에 카드 이름(`{display_name}`)이나 `persona_<hex>` 형식의 id가 등장하는가? (등장하면 ❌)
- `per_persona_reasons`가 2개 card_id 모두에 대해 비어있지 않은가?
- `expected_review_angles`가 3~5개 채워졌는가?

- [ ] **Step 2: Re-run farm_direct brief**

```powershell
.\.venv\Scripts\python.exe scripts/run_brief_eval.py farm_direct 2>&1 | tee tmp_farm_after.log
```

체크 포인트:
- 선정된 페어 중 1명 이상이 `occupation`에 농업·생산자 관련(`농업`, `농촌`, `생산`, `재배` 등) 키워드를 가지는가? 또는 명시적으로 시골/농촌 지역(`전남`, `충청`, `경상남` 등)에 거주하는가?
- 나머지 1명은 도시 소비자 관점(가족·식료품 구매 등)을 대표하는가?
- 같은 hallucination/누락 체크 포인트 (Step 1과 동일).

- [ ] **Step 3: Record results**

`docs/test-briefs.md` 하단에 "평가 결과 — Task 1, 2 적용 후" 섹션을 추가하고 각 brief별로:
- 선정 페어(이름, age_group, occupation)
- 위 체크 포인트별 결과 (✓ / ❌)
- 비교: 적용 전 결과와 어떻게 달라졌는지 한 문단

이 섹션은 commit 하지 않는다 (test-briefs.md 자체가 untracked). 평가 기록을 보존하려면 별도 commit:

```powershell
# 선택적
git add docs/test-briefs.md
git commit -m "docs: record persona selection fit eval results"
```

또는 결과만 대화/노트에 정리하고 파일 변경 없음.

- [ ] **Step 4: Decision point**

체크 포인트가 양 brief에서 모두 ✓로 바뀌었으면 → plan 완료.

여전히 ❌가 남아있으면 → 후속 plan 후보를 적어두고 멈춘다:
- demographic 미스매치가 지속되면 → 100개 풀의 demographic 분포 점검 (별도 plan)
- hallucination이 지속되면 → fewshot example 도입 검토 (별도 plan)
- 라벨/필드 누락이 지속되면 → 모델 교체 또는 더 강한 schema 검증 (별도 plan)

---

## Self-Review Notes

- **Spec coverage:**
  - "pair_reason 안 이름 hallucination" → Task 2의 프롬프트 규칙으로 직접 금지.
  - "per_persona_reasons 누락" → Task 1의 Field description + Task 2의 프롬프트 규칙 두 층.
  - "expected_review_angles 빈 list" → Task 1의 Field description + Task 2의 프롬프트 규칙.
  - "demographic 미스매치" → Task 2의 선정 기준 우선순위 명시.
  - "선정 결과 검증" → Task 3의 수동 평가.
- **Placeholder scan:** 없음. 모든 단계에 코드/명령 명시.
- **Type consistency:** `PersonaSelectionReason`의 필드 이름·타입은 부모 plan과 동일하게 유지. 새 필드 추가 없음 — `Field(description=...)` 메타데이터만 추가.
- **Out-of-scope check:** f3_review/f2_opinion/풀 데이터/fewshot/모델 교체는 Non-Goals 섹션에서 명시적으로 분리.
- **Test impact:** 기존 14개 테스트(12 + 2 new) 모두 통과해야 한다. 이전 Task 4에서 명시한 `_format_persona_list` 동작에는 영향 없음 (LLM 프롬프트 메시지만 바뀜).
- **Risk:** 시스템 프롬프트 길이가 늘어남 → 매 호출 input 토큰 약 50~80 토큰 증가. solar-pro3 한도에 영향 없음.
