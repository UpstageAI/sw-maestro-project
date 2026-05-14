# Persona Selection Pre-Rank Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `select_personas`가 LLM 호출 전에 brief와 관련 높은 persona card를 앞쪽으로 정렬해 `farm_direct` 같은 명확한 target occupation brief에서 관련 후보 recall을 높인다.

**Architecture:** `nodes/f1_select.py`에 순수 함수 `_rank_persona_pool(brief, pool)`을 추가한다. 이 함수는 brief 텍스트와 카드 메타데이터 간 substring/keyword overlap을 계산해 높은 점수 순으로 안정 정렬하고, `select_personas`는 원본 pool 대신 ranked pool을 `_llm_select`와 fallback에 사용한다.

**Tech Stack:** Python 3.11, Pydantic v2, unittest, LangChain Upstage 호출 경로 유지.

---

## File Structure

- Modify: `nodes/f1_select.py`
  - Add `_brief_terms`
  - Add `_card_rank_text`
  - Add `_score_card_for_brief`
  - Add `_rank_persona_pool`
  - Use ranked pool inside `select_personas`
- Modify: `tests/test_f1_select.py`
  - Add tests for ranking target-relevant farm cards ahead of unrelated cards
  - Add test proving `select_personas` passes ranked pool to `_llm_select`

---

## Task 1: Add Ranking Tests

**Files:**
- Modify: `tests/test_f1_select.py`
- Test: `tests/test_f1_select.py`

- [ ] **Step 1: Import `_rank_persona_pool`**

Change the import at the top of `tests/test_f1_select.py` to include `_rank_persona_pool`:

```python
from nodes.f1_select import (
    _PROMPT,
    _format_persona_list,
    _rank_persona_pool,
    _resolve_selection,
    select_personas,
)
```

- [ ] **Step 2: Add a card helper that can vary occupation and text**

Append near `_make_card`:

```python
def _make_custom_card(
    card_id: str,
    *,
    age_group: str = "30s",
    occupation: str = "무직",
    summary: str = "일반적인 생활 맥락을 가진 사용자",
    goals: list[str] | None = None,
    pains: list[str] | None = None,
) -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid=f"source-{card_id}",
        display_name=f"사용자-{card_id}",
        age_group=age_group,
        sex="남",
        occupation=occupation,
        region="충청남",
        one_line_summary=summary,
        life_context="테스트용 생활 맥락",
        user_goals=goals or [],
        pain_points=pains or [],
        positive_triggers=[],
        negative_triggers=[],
        speaking_style="간결함",
    )
```

- [ ] **Step 3: Add failing rank behavior tests**

Append this class before `SelectPersonasTests`:

```python
class RankPersonaPoolTests(unittest.TestCase):
    def test_farm_brief_ranks_agriculture_cards_before_unrelated_cards(self) -> None:
        unrelated = _make_custom_card(
            "persona_unrelated",
            occupation="육군 부사관",
            summary="부대 행정과 가족 시간을 중시하는 사용자",
        )
        farm = _make_custom_card(
            "persona_farm",
            age_group="70plus",
            occupation="농업 단순 종사원",
            summary="농촌에서 농산물 생산과 산지 배송 부담을 겪는 고령 생산자",
            goals=["농산물 판매 채널 확대"],
            pains=["복잡한 상품 등록", "배송 책임 분쟁"],
        )

        ranked = _rank_persona_pool(_brief(), [unrelated, farm])

        self.assertEqual([card.card_id for card in ranked], ["persona_farm", "persona_unrelated"])

    def test_unmatched_cards_keep_original_order(self) -> None:
        first = _make_custom_card("persona_a")
        second = _make_custom_card("persona_b")

        ranked = _rank_persona_pool(_brief(), [first, second])

        self.assertEqual([card.card_id for card in ranked], ["persona_a", "persona_b"])
```

- [ ] **Step 4: Add failing integration test for ranked LLM pool**

Append inside `SelectPersonasTests`:

```python
    def test_select_personas_passes_ranked_pool_to_llm(self) -> None:
        unrelated = _make_custom_card(
            "persona_unrelated",
            occupation="육군 부사관",
            summary="부대 행정과 가족 시간을 중시하는 사용자",
        )
        farm = _make_custom_card(
            "persona_farm",
            age_group="70plus",
            occupation="농업 단순 종사원",
            summary="농촌에서 농산물 생산과 산지 배송 부담을 겪는 고령 생산자",
            goals=["농산물 판매 채널 확대"],
            pains=["복잡한 상품 등록", "배송 책임 분쟁"],
        )
        seen_pool: list[TargetUserPersonaCard] = []

        def _select_from_seen_pool(_brief_arg, pool_arg):
            seen_pool.extend(pool_arg)
            return PersonaSelectionReason(
                selected_card_ids=["persona_farm", "persona_unrelated"],
                per_persona_reasons={
                    "persona_farm": "농산물 직거래 타겟",
                    "persona_unrelated": "비교 관점",
                },
                pair_reason="등록 난이도와 신뢰 형성을 함께 검토",
                expected_review_angles=["등록", "신뢰", "배송"],
            )

        with patch("nodes.f1_select.load_personas", return_value=[unrelated, farm]), \
             patch("nodes.f1_select._llm_select", side_effect=_select_from_seen_pool):
            select_personas({"brief": _brief()})

        self.assertEqual([card.card_id for card in seen_pool], ["persona_farm", "persona_unrelated"])
```

- [ ] **Step 5: Run tests to verify RED**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select -v
```

Expected: FAIL with `ImportError: cannot import name '_rank_persona_pool'`.

---

## Task 2: Implement Pre-Rank

**Files:**
- Modify: `nodes/f1_select.py`
- Test: `tests/test_f1_select.py`

- [ ] **Step 1: Add ranking helpers above `_llm_select`**

Add:

```python
_MIN_BRIEF_TERM_LENGTH = 2


def _brief_terms(brief: ServicePlanInput) -> set[str]:
    raw_terms: list[str] = []
    for text in [
        brief.title or "",
        brief.target or "",
        brief.description or "",
        brief.concerns or "",
        *brief.key_features,
    ]:
        raw_terms.extend(text.replace("/", " ").replace("·", " ").split())
    return {term.strip(" ,.-_()[]{}") for term in raw_terms if len(term.strip(" ,.-_()[]{}")) >= _MIN_BRIEF_TERM_LENGTH}


def _card_rank_text(card: TargetUserPersonaCard) -> str:
    return " ".join([
        card.age_group or "",
        card.sex or "",
        card.occupation or "",
        card.region or "",
        card.one_line_summary,
        " ".join(card.user_goals),
        " ".join(card.pain_points),
        " ".join(card.positive_triggers),
        " ".join(card.negative_triggers),
    ])


def _score_card_for_brief(brief: ServicePlanInput, card: TargetUserPersonaCard) -> int:
    text = _card_rank_text(card)
    score = 0
    for term in _brief_terms(brief):
        if term in text:
            score += 1
    return score


def _rank_persona_pool(
    brief: ServicePlanInput,
    pool: list[TargetUserPersonaCard],
) -> list[TargetUserPersonaCard]:
    indexed = list(enumerate(pool))
    ranked = sorted(
        indexed,
        key=lambda item: (-_score_card_for_brief(brief, item[1]), item[0]),
    )
    return [card for _, card in ranked]
```

- [ ] **Step 2: Use ranked pool inside `select_personas`**

Replace:

```python
    pool = load_personas()
```

with:

```python
    pool = _rank_persona_pool(brief, load_personas())
```

- [ ] **Step 3: Run tests to verify GREEN**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select -v
```

Expected: 17 tests PASS after adding the 3 new tests.

- [ ] **Step 4: Run schema test**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_selection_reason -v
```

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```powershell
git add nodes/f1_select.py tests/test_f1_select.py
git commit -m "feat: rank persona pool before LLM selection"
```

---

## Task 3: Verification

**Files:** No source changes unless verification reveals a bug.

- [ ] **Step 1: Run target tests**

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_selection_reason tests.test_f1_select -v
```

Expected: all target tests PASS.

- [ ] **Step 2: Run imports**

```powershell
.\.venv\Scripts\python.exe -c "import graph; import app; print('imports ok')"
```

Expected: `imports ok`.

- [ ] **Step 3: Run full unittest suite**

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all tests PASS.

- [ ] **Step 4: Optional select-only smoke**

Run a select-only `farm_direct` eval with the same temporary helper style used in the previous task. Expected: ranked prompt should put farm-related cards earlier. LLM output is non-deterministic, so do not gate commit on one live LLM sample unless the code path itself fails.

---

## Self-Review Notes

- **Spec coverage:** Implements the follow-up candidate from `docs/test-briefs.md`: keyword-based pre-rank before LLM selection.
- **Placeholder scan:** No placeholder steps; every code change and command is specified.
- **Type consistency:** New helpers use `ServicePlanInput` and `TargetUserPersonaCard`, matching existing `nodes/f1_select.py`.
- **Scope check:** No schema, graph, app, or repository changes. This keeps the fix isolated to f1 selection behavior.
