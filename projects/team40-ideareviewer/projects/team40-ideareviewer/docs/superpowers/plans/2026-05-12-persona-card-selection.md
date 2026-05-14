# Persona Card Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 100개 페르소나 카드 풀에서 사용자가 입력한 서비스 기획안에 적합한 2명을 단일 LLM 패스로 선정하고, 선정 근거를 구조화해 그래프 state와 Streamlit UI에 노출한다.

**Architecture:** 기존 파이프라인(`raw_input → f0_parse → select_personas → ...`)을 그대로 유지하면서 `select_personas` 노드 한 곳만 갈아끼운다. 풀은 `persona_cards.selected.json`(100개)로 단일화하고, LLM에 100개 압축 카드를 통째로 전달해 `PersonaSelectionReason`(2명 + 각자 이유 + 페어 이유 + 예상 리뷰 각도)을 한 번에 받는다. invalid id / LLM 호출 실패는 풀 앞 2개로 fallback.

**Tech Stack:** Python 3.11, Pydantic v2, LangChain (`langchain-upstage`), LangGraph, Streamlit, unittest.

**Spec:** `docs/superpowers/specs/2026-05-12-persona-card-selection-design.md`

---

## File Structure

- Modify: `schemas.py` — add `PersonaSelectionReason`, update `__all__`
- Modify: `state.py` — add `persona_selection_reason` field to `ProjectState`
- Modify: `services/persona_repository.py` — switch `_SEED_PATH` to `persona_cards.selected.json`
- Rewrite: `nodes/f1_select.py` — compressed card formatter, `_resolve_selection`, LLM call, `select_personas` with fallback
- Modify: `app.py` — render selection reason card at bottom of "사용자 패널" tab
- Create: `tests/test_f1_select.py` — 4 unit tests (happy path, invalid ids, LLM exception, small pool)

Test discovery: project uses `python -m unittest discover -s tests`. Each test file is a top-level module under `tests/`.

---

## Task 1: PersonaSelectionReason 스키마 추가

**Files:**
- Modify: `schemas.py`
- Test: `tests/test_persona_selection_reason.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_persona_selection_reason.py`:

```python
import unittest

from schemas import PersonaSelectionReason


class PersonaSelectionReasonTests(unittest.TestCase):
    def test_minimum_required_fields(self) -> None:
        reason = PersonaSelectionReason(
            selected_card_ids=["persona_a", "persona_b"],
            pair_reason="핵심 타겟과 리스크 관점을 함께 본다",
        )

        self.assertEqual(reason.selected_card_ids, ["persona_a", "persona_b"])
        self.assertEqual(reason.pair_reason, "핵심 타겟과 리스크 관점을 함께 본다")
        self.assertEqual(reason.per_persona_reasons, {})
        self.assertEqual(reason.expected_review_angles, [])

    def test_all_fields_present(self) -> None:
        reason = PersonaSelectionReason(
            selected_card_ids=["persona_a", "persona_b"],
            per_persona_reasons={
                "persona_a": "핵심 타겟 적합",
                "persona_b": "디지털 접근성 리스크 검증",
            },
            pair_reason="생산자와 접근성 약자의 관점을 동시에 본다",
            expected_review_angles=["등록 난이도", "신뢰", "가격"],
        )

        self.assertEqual(reason.per_persona_reasons["persona_b"], "디지털 접근성 리스크 검증")
        self.assertEqual(len(reason.expected_review_angles), 3)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_selection_reason -v
```

Expected: FAIL with `ImportError: cannot import name 'PersonaSelectionReason' from 'schemas'`.

- [ ] **Step 3: Add the model**

In `schemas.py`, add after `class ServicePlanInput(BaseModel): ...` block:

```python
class PersonaSelectionReason(BaseModel):
    """LLM이 두 명의 페르소나를 고른 근거."""

    selected_card_ids: list[str]
    per_persona_reasons: dict[str, str] = Field(default_factory=dict)
    pair_reason: str
    expected_review_angles: list[str] = Field(default_factory=list)
```

- [ ] **Step 4: Add to `__all__`**

In `schemas.py`, add `"PersonaSelectionReason"` to the `__all__` tuple, alphabetically near `Opinion`:

```python
__all__ = [
    "AgreementLevel",
    "DEFAULT_GUARDRAILS",
    "Opinion",
    "PersonaSelectionReason",
    "PointFeedback",
    "RawNemotronPersona",
    "ReactionPoint",
    "Review",
    "ServicePlanInput",
    "TargetUserPersonaCard",
]
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_selection_reason -v
```

Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```powershell
git add schemas.py tests/test_persona_selection_reason.py
git commit -m "feat: add PersonaSelectionReason schema"
```

---

## Task 2: ProjectState에 persona_selection_reason 필드 추가

**Files:**
- Modify: `state.py`

- [ ] **Step 1: Read current state.py to confirm pattern**

Run:

```powershell
type state.py
```

Confirm `ProjectState` is a `TypedDict` with `total=False`. (If the pattern differs, follow the existing one — do NOT change the TypedDict style.)

- [ ] **Step 2: Add the import**

In `state.py`, add `PersonaSelectionReason` to the `from schemas import` line, keeping existing imports in alphabetical order. Example after edit:

```python
from schemas import (
    Opinion,
    PersonaSelectionReason,
    Review,
    ServicePlanInput,
    TargetUserPersonaCard,
)
```

- [ ] **Step 3: Add the field**

Inside `class ProjectState(TypedDict, total=False):`, add:

```python
    persona_selection_reason: PersonaSelectionReason
```

Place it directly under `persona_b: TargetUserPersonaCard` (or wherever the persona pair fields live) to keep related fields together.

- [ ] **Step 4: Verify by import**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from state import ProjectState; print('persona_selection_reason' in ProjectState.__annotations__)"
```

Expected: prints `True`.

- [ ] **Step 5: Commit**

```powershell
git add state.py
git commit -m "feat: add persona_selection_reason to ProjectState"
```

---

## Task 3: 카드 풀 경로 단일화

**Files:**
- Modify: `services/persona_repository.py`
- Test: `tests/test_persona_repository.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_persona_repository.py`:

```python
import unittest
from pathlib import Path

from services.persona_repository import _SEED_PATH, load_personas


class PersonaRepositoryTests(unittest.TestCase):
    def test_seed_path_points_to_selected_pool(self) -> None:
        self.assertEqual(_SEED_PATH.name, "persona_cards.selected.json")

    def test_load_personas_returns_one_hundred_cards(self) -> None:
        cards = load_personas()

        self.assertEqual(len(cards), 100)
        self.assertTrue(all(card.card_id.startswith("persona_") for card in cards))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_repository -v
```

Expected: FAIL — `_SEED_PATH.name` is `persona_cards.seed.json` (or count mismatch).

- [ ] **Step 3: Switch the seed path**

In `services/persona_repository.py`, replace:

```python
_SEED_PATH = Path(__file__).parent.parent / "data" / "personas" / "persona_cards.seed.json"
```

with:

```python
_SEED_PATH = Path(__file__).parent.parent / "data" / "personas" / "persona_cards.selected.json"
```

Do NOT delete `data/personas/persona_cards.seed.json` from disk — only the code reference changes.

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_persona_repository -v
```

Expected: PASS (2 tests).

- [ ] **Step 5: Commit**

```powershell
git add services/persona_repository.py tests/test_persona_repository.py
git commit -m "feat: switch persona pool to selected 100-card set"
```

---

## Task 4: 압축 카드 표현 함수

**Files:**
- Modify: `nodes/f1_select.py`
- Test: `tests/test_f1_select.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_f1_select.py`:

```python
import unittest

from nodes.f1_select import _format_persona_list
from schemas import TargetUserPersonaCard


def _make_card(card_id: str = "persona_test1") -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid="source-test",
        display_name="김영수",
        age_group="60s",
        sex="남",
        occupation="농업",
        region="충청남",
        one_line_summary="농산물을 직접 판매하는 60대",
        life_context="가족 농장을 30년째 운영 중.",
        user_goals=["판매 채널 확대", "직거래"],
        pain_points=["복잡한 앱", "작은 글씨"],
        positive_triggers=["간단한 등록"],
        negative_triggers=["배송 책임"],
        speaking_style="현실적이고 직설적",
    )


class FormatPersonaListTests(unittest.TestCase):
    def test_includes_required_fields(self) -> None:
        text = _format_persona_list([_make_card("persona_abc")])

        self.assertIn("persona_abc", text)
        self.assertIn("김영수", text)
        self.assertIn("60s", text)
        self.assertIn("농업", text)
        self.assertIn("농산물을 직접 판매하는 60대", text)
        self.assertIn("판매 채널 확대", text)
        self.assertIn("작은 글씨", text)
        self.assertIn("간단한 등록", text)
        self.assertIn("배송 책임", text)

    def test_excludes_omitted_fields(self) -> None:
        text = _format_persona_list([_make_card()])

        self.assertNotIn("가족 농장을 30년째", text)
        self.assertNotIn("현실적이고 직설적", text)
        self.assertNotIn("source-test", text)

    def test_separates_multiple_cards_with_blank_line(self) -> None:
        text = _format_persona_list([_make_card("persona_a"), _make_card("persona_b")])

        self.assertIn("persona_a", text)
        self.assertIn("persona_b", text)
        self.assertIn("\n\n", text)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select.FormatPersonaListTests -v
```

Expected: FAIL — the current `_format_persona_list` in `nodes/f1_select.py` includes `life_context` and `speaking_style`. Tests asserting their absence will fail.

- [ ] **Step 3: Rewrite `_format_persona_list`**

In `nodes/f1_select.py`, replace the existing `_format_persona_list` function with:

```python
def _format_persona_list(pool: list[TargetUserPersonaCard]) -> str:
    """LLM 프롬프트에 들어갈 압축 카드 목록.

    선택 판단의 핵심 필드(요약, 목표, 불편함, 트리거)만 포함해 토큰을 아낀다.
    life_context/speaking_style/guardrails/source_uuid는 의도적으로 제외.
    """
    lines = []
    for card in pool:
        parts = [
            f"- card_id: {card.card_id}",
            "  이름/메타: "
            + " | ".join([
                card.display_name,
                card.age_group or "-",
                card.sex or "-",
                card.occupation or "-",
                card.region or "-",
            ]),
            f"  요약: {card.one_line_summary}",
            "  목표: " + " / ".join(card.user_goals) if card.user_goals else "  목표: -",
            "  불편함: " + " / ".join(card.pain_points) if card.pain_points else "  불편함: -",
            "  긍정 트리거: " + " / ".join(card.positive_triggers) if card.positive_triggers else "  긍정 트리거: -",
            "  부정 트리거: " + " / ".join(card.negative_triggers) if card.negative_triggers else "  부정 트리거: -",
        ]
        lines.append("\n".join(parts))
    return "\n\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select.FormatPersonaListTests -v
```

Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```powershell
git add nodes/f1_select.py tests/test_f1_select.py
git commit -m "feat: compress persona card representation for selection prompt"
```

---

## Task 5: `_resolve_selection` 헬퍼

**Files:**
- Modify: `nodes/f1_select.py`
- Test: `tests/test_f1_select.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_f1_select.py`:

```python
from nodes.f1_select import _resolve_selection


class ResolveSelectionTests(unittest.TestCase):
    def test_keeps_valid_ids_in_order(self) -> None:
        pool = [_make_card("persona_a"), _make_card("persona_b"), _make_card("persona_c")]

        selected = _resolve_selection(["persona_b", "persona_a"], pool)

        self.assertEqual([c.card_id for c in selected], ["persona_b", "persona_a"])

    def test_drops_invalid_ids_and_fills_from_pool_head(self) -> None:
        pool = [_make_card("persona_a"), _make_card("persona_b"), _make_card("persona_c")]

        selected = _resolve_selection(["missing_x", "persona_c"], pool)

        self.assertEqual([c.card_id for c in selected], ["persona_c", "persona_a"])

    def test_pads_when_llm_returns_fewer_than_two(self) -> None:
        pool = [_make_card("persona_a"), _make_card("persona_b"), _make_card("persona_c")]

        selected = _resolve_selection([], pool)

        self.assertEqual([c.card_id for c in selected], ["persona_a", "persona_b"])

    def test_dedupes_duplicates_then_fills(self) -> None:
        pool = [_make_card("persona_a"), _make_card("persona_b"), _make_card("persona_c")]

        selected = _resolve_selection(["persona_a", "persona_a"], pool)

        self.assertEqual([c.card_id for c in selected], ["persona_a", "persona_b"])
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select.ResolveSelectionTests -v
```

Expected: FAIL with `ImportError: cannot import name '_resolve_selection'`.

- [ ] **Step 3: Implement `_resolve_selection`**

In `nodes/f1_select.py`, add (above `_llm_select`):

```python
_SELECT_COUNT = 2


def _resolve_selection(
    raw_ids: list[str],
    pool: list[TargetUserPersonaCard],
) -> list[TargetUserPersonaCard]:
    """LLM이 반환한 id 목록을 풀과 매칭해 정확히 _SELECT_COUNT 개로 만든다.

    - 풀에 실재하는 id 만 순서를 유지한 채 채택
    - 중복 제거
    - 부족하면 풀 앞에서부터 채워서 _SELECT_COUNT 개 보장
    """
    by_id = {card.card_id: card for card in pool}
    selected: list[TargetUserPersonaCard] = []
    seen: set[str] = set()

    for card_id in raw_ids:
        if card_id in by_id and card_id not in seen:
            selected.append(by_id[card_id])
            seen.add(card_id)
            if len(selected) == _SELECT_COUNT:
                return selected

    for card in pool:
        if card.card_id not in seen:
            selected.append(card)
            seen.add(card.card_id)
            if len(selected) == _SELECT_COUNT:
                return selected

    return selected
```

If `_SELECT_COUNT = 2` already existed in the file, do NOT duplicate it — leave the existing assignment and only add `_resolve_selection`.

- [ ] **Step 4: Run tests to verify pass**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select.ResolveSelectionTests -v
```

Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```powershell
git add nodes/f1_select.py tests/test_f1_select.py
git commit -m "feat: add _resolve_selection helper for persona id fallback"
```

---

## Task 6: `select_personas` 노드 재작성 (LLM 호출 + fallback)

**Files:**
- Modify: `nodes/f1_select.py`
- Test: `tests/test_f1_select.py`

- [ ] **Step 1: Add failing tests**

Append to `tests/test_f1_select.py`:

```python
from unittest.mock import patch

from nodes.f1_select import select_personas
from schemas import PersonaSelectionReason, ServicePlanInput


def _brief() -> ServicePlanInput:
    return ServicePlanInput(
        raw_text="농산물 직거래",
        title="직거래 앱",
        target="고령 생산자",
        description="농촌과 도시를 연결",
        key_features=["사진 등록", "산지 배송"],
        concerns="등록 난이도",
    )


def _pool(*card_ids: str) -> list[TargetUserPersonaCard]:
    return [_make_card(cid) for cid in card_ids]


class SelectPersonasTests(unittest.TestCase):
    def test_happy_path_returns_two_cards_and_reason(self) -> None:
        pool = _pool("persona_a", "persona_b", "persona_c", "persona_d")
        canned = PersonaSelectionReason(
            selected_card_ids=["persona_c", "persona_a"],
            per_persona_reasons={"persona_c": "관점 A", "persona_a": "관점 B"},
            pair_reason="두 관점을 함께 본다",
            expected_review_angles=["등록", "신뢰"],
        )

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select", return_value=canned):
            result = select_personas({"brief": _brief()})

        self.assertEqual(result["persona_a"].card_id, "persona_c")
        self.assertEqual(result["persona_b"].card_id, "persona_a")
        reason = result["persona_selection_reason"]
        self.assertEqual(reason.selected_card_ids, ["persona_c", "persona_a"])
        self.assertEqual(reason.pair_reason, "두 관점을 함께 본다")

    def test_invalid_llm_ids_fall_back_and_reason_is_normalized(self) -> None:
        pool = _pool("persona_a", "persona_b", "persona_c")
        canned = PersonaSelectionReason(
            selected_card_ids=["missing_x", "missing_y"],
            pair_reason="invalid id 케이스",
        )

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select", return_value=canned):
            result = select_personas({"brief": _brief()})

        self.assertEqual(result["persona_a"].card_id, "persona_a")
        self.assertEqual(result["persona_b"].card_id, "persona_b")
        self.assertEqual(
            result["persona_selection_reason"].selected_card_ids,
            ["persona_a", "persona_b"],
        )

    def test_llm_exception_falls_back_to_pool_head(self) -> None:
        pool = _pool("persona_a", "persona_b", "persona_c")

        def _boom(*_args, **_kwargs):
            raise RuntimeError("upstream timeout")

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select", side_effect=_boom):
            result = select_personas({"brief": _brief()})

        self.assertEqual(result["persona_a"].card_id, "persona_a")
        self.assertEqual(result["persona_b"].card_id, "persona_b")
        reason = result["persona_selection_reason"]
        self.assertEqual(reason.selected_card_ids, ["persona_a", "persona_b"])
        self.assertIn("LLM", reason.pair_reason)

    def test_small_pool_skips_llm_and_returns_all(self) -> None:
        pool = _pool("persona_a", "persona_b")

        with patch("nodes.f1_select.load_personas", return_value=pool), \
             patch("nodes.f1_select._llm_select") as llm_mock:
            result = select_personas({"brief": _brief()})

        llm_mock.assert_not_called()
        self.assertEqual(result["persona_a"].card_id, "persona_a")
        self.assertEqual(result["persona_b"].card_id, "persona_b")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select.SelectPersonasTests -v
```

Expected: FAIL — current `select_personas` returns `{"persona_a", "persona_b"}` only, with no `persona_selection_reason`; `_llm_select` signature is different.

- [ ] **Step 3: Replace `nodes/f1_select.py` body**

Open `nodes/f1_select.py`. Replace the entire file with the following (keep the existing `_format_persona_list` and `_resolve_selection` from previous tasks intact within this rewrite):

```python
"""f1_select — 100개 카드 풀에서 LLM이 2명을 선정하고 근거를 함께 반환."""

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage
from langgraph.types import Send

from schemas import (
    PersonaSelectionReason,
    ServicePlanInput,
    TargetUserPersonaCard,
)
from services.persona_repository import load_personas
from state import ProjectState

load_dotenv()

_SELECT_COUNT = 2
_LLM_TIMEOUT_SECONDS = 120.0
_LLM_MAX_RETRIES = 5
_LLM_FAILURE_PAIR_REASON = "LLM 호출 실패 - 풀 앞 2개로 fallback"


_llm = ChatUpstage(
    model="solar-pro3",
    timeout=_LLM_TIMEOUT_SECONDS,
    max_retries=_LLM_MAX_RETRIES,
).with_structured_output(PersonaSelectionReason)


_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 서비스 기획안 검토를 위해 서로 보완적인 관점을 가진 페르소나 패널 "
        f"{_SELECT_COUNT}명을 선정합니다. "
        "단순 유사도가 아니라 (a) 핵심 타겟 적합성, (b) 잠재 리스크 검증, "
        "(c) 두 사람의 관점 차이를 동시에 고려해 정확히 2명을 고르세요. "
        "selected_card_ids 에는 반드시 아래 후보 목록에 실재하는 card_id 만 사용합니다. "
        "per_persona_reasons 는 선택한 두 card_id 각각에 대해 한 줄로 작성합니다. "
        "expected_review_angles 는 이 페어가 검증할 핵심 리뷰 각도 3~5개를 짧게 나열합니다.",
    ),
    (
        "human",
        "## 서비스 기획안\n"
        "제목: {title}\n"
        "타겟: {target}\n"
        "설명: {description}\n"
        "핵심 기능:\n{key_features}\n"
        "우려사항: {concerns}\n\n"
        "## 페르소나 후보 ({pool_size}명)\n{persona_list}",
    ),
])


def _format_persona_list(pool: list[TargetUserPersonaCard]) -> str:
    """LLM 프롬프트에 들어갈 압축 카드 목록.

    선택 판단의 핵심 필드(요약, 목표, 불편함, 트리거)만 포함해 토큰을 아낀다.
    life_context/speaking_style/guardrails/source_uuid는 의도적으로 제외.
    """
    lines = []
    for card in pool:
        parts = [
            f"- card_id: {card.card_id}",
            "  이름/메타: "
            + " | ".join([
                card.display_name,
                card.age_group or "-",
                card.sex or "-",
                card.occupation or "-",
                card.region or "-",
            ]),
            f"  요약: {card.one_line_summary}",
            "  목표: " + " / ".join(card.user_goals) if card.user_goals else "  목표: -",
            "  불편함: " + " / ".join(card.pain_points) if card.pain_points else "  불편함: -",
            "  긍정 트리거: " + " / ".join(card.positive_triggers) if card.positive_triggers else "  긍정 트리거: -",
            "  부정 트리거: " + " / ".join(card.negative_triggers) if card.negative_triggers else "  부정 트리거: -",
        ]
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def _resolve_selection(
    raw_ids: list[str],
    pool: list[TargetUserPersonaCard],
) -> list[TargetUserPersonaCard]:
    """LLM이 반환한 id 목록을 풀과 매칭해 정확히 _SELECT_COUNT 개로 만든다."""
    by_id = {card.card_id: card for card in pool}
    selected: list[TargetUserPersonaCard] = []
    seen: set[str] = set()

    for card_id in raw_ids:
        if card_id in by_id and card_id not in seen:
            selected.append(by_id[card_id])
            seen.add(card_id)
            if len(selected) == _SELECT_COUNT:
                return selected

    for card in pool:
        if card.card_id not in seen:
            selected.append(card)
            seen.add(card.card_id)
            if len(selected) == _SELECT_COUNT:
                return selected

    return selected


def _llm_select(
    brief: ServicePlanInput,
    pool: list[TargetUserPersonaCard],
) -> PersonaSelectionReason:
    chain = _PROMPT | _llm
    return chain.invoke({
        "title": brief.title or "",
        "target": brief.target or "",
        "description": brief.description or "",
        "key_features": "\n".join(f"- {f}" for f in brief.key_features),
        "concerns": brief.concerns or "",
        "pool_size": len(pool),
        "persona_list": _format_persona_list(pool),
    })


def _result(
    selected: list[TargetUserPersonaCard],
    reason: PersonaSelectionReason,
) -> dict:
    return {
        "persona_a": selected[0],
        "persona_b": selected[1],
        "persona_selection_reason": reason,
    }


def select_personas(state: ProjectState) -> dict:
    brief: ServicePlanInput = state["brief"]
    pool = load_personas()

    if len(pool) <= _SELECT_COUNT:
        selected = list(pool)[:_SELECT_COUNT]
        reason = PersonaSelectionReason(
            selected_card_ids=[c.card_id for c in selected],
            pair_reason="풀 크기가 부족해 전원 선택",
        )
        return _result(selected, reason)

    try:
        reason = _llm_select(brief, pool)
    except Exception:
        selected = list(pool[:_SELECT_COUNT])
        fallback_reason = PersonaSelectionReason(
            selected_card_ids=[c.card_id for c in selected],
            pair_reason=_LLM_FAILURE_PAIR_REASON,
        )
        return _result(selected, fallback_reason)

    selected = _resolve_selection(reason.selected_card_ids, pool)
    normalized_reason = reason.model_copy(
        update={"selected_card_ids": [c.card_id for c in selected]}
    )
    return _result(selected, normalized_reason)


def route_opinions(state: ProjectState) -> list[Send]:
    """선택된 두 페르소나에 대해 generate_opinion 노드를 병렬 파견."""
    return [
        Send("generate_opinion", {"persona": state["persona_a"], "brief": state["brief"], "slot": "a"}),
        Send("generate_opinion", {"persona": state["persona_b"], "brief": state["brief"], "slot": "b"}),
    ]
```

- [ ] **Step 4: Run all `tests/test_f1_select.py` tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_f1_select -v
```

Expected: PASS (all 11 tests: 3 format + 4 resolve + 4 select).

- [ ] **Step 5: Verify graph still imports**

Run:

```powershell
.\.venv\Scripts\python.exe -c "import graph; print('graph import ok')"
```

Expected: prints `graph import ok` with no errors.

- [ ] **Step 6: Commit**

```powershell
git add nodes/f1_select.py tests/test_f1_select.py
git commit -m "feat: rewrite select_personas with structured reason and fallback"
```

---

## Task 7: Streamlit UI에 선정 근거 카드 추가

**Files:**
- Modify: `app.py`

- [ ] **Step 1: Find the persona panel tab renderer**

Run:

```powershell
.\.venv\Scripts\python.exe -c "import re; src = open('app.py', encoding='utf-8').read(); [print(i+1, line) for i, line in enumerate(src.splitlines()) if '사용자 패널' in line or '_render_persona_tab' in line or 'persona_a' in line and 'def ' in line]"
```

Note the function name that renders the "사용자 패널" tab (typically `_render_persona_tab` or similar). Read the surrounding 30 lines to understand the helper utilities used (`_get`, `_as_list` patterns from existing code).

- [ ] **Step 2: Add the renderer function**

In `app.py`, add a new helper function near other `_render_*` functions:

```python
def _render_selection_reason(state: dict) -> None:
    reason = _get(state, "persona_selection_reason")
    if reason is None:
        return

    persona_a = _get(state, "persona_a")
    persona_b = _get(state, "persona_b")
    name_by_id = {}
    for card in (persona_a, persona_b):
        card_id = _get(card, "card_id")
        if card_id:
            name_by_id[card_id] = _get(card, "display_name", card_id)

    with st.container(border=True):
        st.markdown("#### 이 페어를 고른 이유")
        st.write(_get(reason, "pair_reason", "-"))

        per_persona = dict(_get(reason, "per_persona_reasons", {}))
        if per_persona:
            st.markdown("**각자 선정 이유**")
            for card_id, text in per_persona.items():
                label = name_by_id.get(card_id, card_id)
                st.markdown(f"- **{label}** ({card_id}): {text}")

        angles = _as_list(_get(reason, "expected_review_angles", []))
        if angles:
            st.markdown("**예상 리뷰 각도**")
            for angle in angles:
                st.markdown(f"- {angle}")
```

If `_get` or `_as_list` helpers do not yet exist in `app.py`, replace their calls with direct attribute/key access (the existing `_render_*` functions show the pattern in use).

- [ ] **Step 3: Call the renderer from the persona panel tab**

Locate the function body that renders the "사용자 패널" tab (e.g. `_render_persona_tab`). At the **end** of that function (after the existing persona cards), add:

```python
    _render_selection_reason(state)
```

Make sure `state` is the variable in scope inside that function. If the function only receives `persona_a, persona_b` and not `state`, also pass `state` from the call site (in `_render_results`) and update the signature.

- [ ] **Step 4: Verify app imports**

Run:

```powershell
.\.venv\Scripts\python.exe -c "import app; print('app import ok')"
```

Expected: prints `app import ok` with no errors.

- [ ] **Step 5: Commit**

```powershell
git add app.py
git commit -m "feat: show persona selection reason in panel tab"
```

---

## Task 8: 전체 검증 + 데모 스모크

**Files:** No required source changes unless verification reveals a bug.

- [ ] **Step 1: Run full unit test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all tests pass (Task 1–6 tests plus any pre-existing tests).

- [ ] **Step 2: Run Ruff (if configured)**

Run:

```powershell
.\.venv\Scripts\ruff.exe check . --no-cache
```

Expected: no lint errors. If `ruff` is not installed in the venv, skip with a note. If errors appear, fix them inline (most likely import sorting or unused imports).

- [ ] **Step 3: Verify graph and app imports**

Run:

```powershell
.\.venv\Scripts\python.exe -c "import graph; import app; print('imports ok')"
```

Expected: prints `imports ok`.

- [ ] **Step 4: Run pipeline trace demo (no LLM trace)**

Run:

```powershell
.\scripts\run_demo_trace.ps1 -NoTrace
```

Expected: pipeline runs end-to-end. Final state includes `persona_a`, `persona_b`, and `persona_selection_reason`. If the script does not exist or hits a script-level issue, fall back to:

```powershell
.\.venv\Scripts\python.exe -c "from services.pipeline_runner import run_pipeline; print('runner import ok')"
```

and confirm no import error (full demo can be deferred to Task 8 Step 5).

- [ ] **Step 5: Streamlit manual smoke (optional)**

If approved by user, run:

```powershell
.\scripts\run_demo_streamlit.ps1 -NoTrace
```

Open `http://localhost:8501`, submit the sample brief, confirm:
- Pipeline completes without error
- "사용자 패널" tab shows two persona cards
- Below the cards, the "이 페어를 고른 이유" container is rendered with `pair_reason`, per-persona reasons, and expected review angles
- Stop the server with Ctrl+C

If any of these fail, stop and create a follow-up fix task for the concrete failure.

- [ ] **Step 6: Stop on verification failure**

If any verification step fails, do NOT commit further changes. Record the failing command and output, and create a focused fix task before continuing.

---

## Self-Review Notes

- **Spec coverage:**
  - Data Model → Task 1
  - State → Task 2
  - Persona Pool → Task 3
  - Node Logic > 압축 카드 표현 → Task 4
  - Node Logic > 선택 함수 + Fallback → Task 6
  - UI → Task 7
  - Testing → Tasks 1, 3, 4, 5, 6 (4 cases of `select_personas` covered in Task 6)
  - Dependencies (변경 없음) → no task needed (verified by Task 8 imports)
  - Verification → Task 8
- **Placeholder scan:** No "TBD"/"TODO"/"handle edge cases"-style placeholders. Every code step shows the full code an engineer needs.
- **Type consistency:** `PersonaSelectionReason`, `_SELECT_COUNT`, `_resolve_selection`, `_llm_select`, `_format_persona_list`, `_LLM_FAILURE_PAIR_REASON`, `_result` are introduced in Task 1/4/5/6 and used consistently in later tasks. `load_personas` return type unchanged. State key `persona_selection_reason` matches across spec, state.py, node, and UI.
- **Out-of-scope check:** No hard filter, no rerank, no Chroma — all confirmed Non-Goals in spec.
