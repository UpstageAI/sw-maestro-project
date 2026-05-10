# Two-Person Supervisor Review Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the current two-person persona review pipeline by fixing seed persona data and adding a supervisor node that produces the final user-facing review text.

**Architecture:** Keep the current A/B fixed-slot LangGraph state because the project is already wired around `persona_a`, `persona_b`, `opinion_a`, `opinion_b`, `review_a`, and `review_b`. Add one explicit review join node, then run a neutral supervisor node after both cross reviews exist. Regenerate persona card seed data to match the current `TargetUserPersonaCard` schema instead of expanding shared schemas in this iteration.

**Tech Stack:** Python 3.11+, LangGraph 0.2.74, LangChain 0.3.19, langchain-upstage 0.5.0, Pydantic 2.11.3, stdlib `unittest`, Ruff

**Source spec:** `docs/superpowers/specs/2026-05-08-two-person-supervisor-review-flow-design.md`

---

## File Structure

| Path | Change | Responsibility |
| --- | --- | --- |
| `data/personas/persona_cards.seed.json` | Modify | Regenerated runtime persona cards that validate against `TargetUserPersonaCard`. |
| `tests/test_persona_repository.py` | Create | Verifies seed persona cards load and string-list fields match `schemas.py`. |
| `tests/test_f4_supervisor.py` | Create | Verifies supervisor prompt input formatting without calling the LLM. |
| `nodes/f4_supervisor.py` | Create | Neutral supervisor finalization node. It synthesizes brief, personas, opinions, and reviews into `final_review_text`. |
| `state.py` | Modify | Adds `final_review_text` as the final graph output key. |
| `graph.py` | Modify | Adds `collect_reviews` join and `supervisor_finalize` final node before `END`. |
| `scripts/test_pipeline.py` | Modify | Displays the new graph stage and prints `final_review_text`. Also fixes local Ruff issues in this touched file. |
| `nodes/f3_review.py` | Modify | Fixes import ordering because this file already has a Ruff import-order violation and will be checked with the changed graph flow. |

---

## Code-Line Rationale

| Location | Decision | Technical reason |
| --- | --- | --- |
| `schemas.py:66-69` | Keep `list[str]` fields for this iteration. | The shared schema currently defines `user_goals`, `pain_points`, `positive_triggers`, and `negative_triggers` as strings. Changing them to object lists would force prompt, formatter, test, and downstream node changes unrelated to the supervisor flow. |
| `data/personas/persona_cards.seed.json` | Regenerate cards to match `TargetUserPersonaCard`. | `services/persona_repository.py:11-13` directly validates JSON with `TargetUserPersonaCard(**item)`, so data must match the runtime schema before the graph can reach `select_personas`. |
| `state.py:13-21` | Add only `final_review_text: str`. | The supervisor needs one new graph output key. A full `FinalReview` Pydantic model is unnecessary until the output needs machine-readable fields. |
| `nodes/f4_supervisor.py` | Create a new node file instead of extending `nodes/f3_review.py`. | `f3_review` role-plays as a persona and writes `Review`. The supervisor is neutral, product-planner-facing, and writes final text. Splitting the file prevents role prompts and output responsibilities from mixing. |
| `graph.py:23-27` | Register `collect_reviews` and `supervisor_finalize`. | Existing graph registration is node-name based. Adding nodes here keeps the graph topology explicit and inspectable with stream updates. |
| `graph.py:45-46` | Replace direct `generate_review -> END` with `generate_review -> collect_reviews -> supervisor_finalize -> END`. | Directly ending after `generate_review` leaves no place to synthesize both reviews. The no-op join guarantees the supervisor reads both `review_a` and `review_b`. |
| `scripts/test_pipeline.py:31-37` | Add labels for `collect_reviews` and `supervisor_finalize`. | The script already streams node updates, so labels make the new flow visible without adding a separate UI. |
| `scripts/test_pipeline.py:168-173` | Print final review after cross reviews. | The final review is the user-facing result, so it should be printed after the detailed persona artifacts. |

---

## Task 1: Add Persona Seed Contract Test

**Files:**
- Create: `tests/test_persona_repository.py`
- Read: `schemas.py:66-69`
- Read: `services/persona_repository.py:11-13`

- [ ] **Step 1: Create the failing test**

Create `tests/test_persona_repository.py`:

```python
import unittest

from services.persona_repository import load_personas


class PersonaRepositoryTests(unittest.TestCase):
    def test_seed_persona_cards_match_runtime_schema(self) -> None:
        personas = load_personas()

        self.assertGreaterEqual(len(personas), 2)
        for persona in personas:
            for field_name in (
                "user_goals",
                "pain_points",
                "positive_triggers",
                "negative_triggers",
            ):
                values = getattr(persona, field_name)
                self.assertIsInstance(values, list)
                self.assertTrue(
                    all(isinstance(item, str) for item in values),
                    f"{persona.card_id}.{field_name} must be list[str]",
                )


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify it fails on the current seed JSON**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -m unittest tests.test_persona_repository -v
```

Expected: FAIL or ERROR from Pydantic validation because the current seed file stores signal objects where `list[str]` is expected.

---

## Task 2: Regenerate Persona Cards Against Current Schema

**Files:**
- Modify: `data/personas/persona_cards.seed.json`
- Read: `scripts/generate_user_cards.py:27-37`
- Read: `scripts/generate_user_cards.py:120-138`

- [ ] **Step 1: Regenerate persona cards using the existing generator**

Run:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe scripts\generate_user_cards.py
```

Expected output includes:

```text
2개 페르소나 변환 시작
저장 완료: 2개 → persona_cards.seed.json
```

Technical reason: `scripts/generate_user_cards.py:27-37` already defines `_LLMFields.user_goals`, `_LLMFields.pain_points`, `_LLMFields.positive_triggers`, and `_LLMFields.negative_triggers` as `list[str]`, so regenerating through this script aligns the data with `schemas.py:66-69`.

- [ ] **Step 2: Re-run the persona seed contract test**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -m unittest tests.test_persona_repository -v
```

Expected: PASS.

- [ ] **Step 3: Commit the data fix and contract test**

Run:

```powershell
git add data/personas/persona_cards.seed.json tests/test_persona_repository.py
git commit -m "fix: regenerate persona cards for runtime schema"
```

---

## Task 3: Add Supervisor Formatting Test

**Files:**
- Create: `tests/test_f4_supervisor.py`
- Target create: `nodes/f4_supervisor.py`

- [ ] **Step 1: Create the failing supervisor formatting test**

Create `tests/test_f4_supervisor.py`:

```python
import unittest

from nodes.f4_supervisor import _build_supervisor_prompt_vars
from schemas import (
    Opinion,
    PointFeedback,
    ReactionPoint,
    Review,
    ServicePlanInput,
    TargetUserPersonaCard,
)


def _persona(card_id: str, name: str) -> TargetUserPersonaCard:
    return TargetUserPersonaCard(
        card_id=card_id,
        source_uuid=f"source-{card_id}",
        display_name=name,
        age_group="60s",
        sex="남자",
        occupation="테스트 직업",
        region="서울",
        one_line_summary=f"{name} 한 줄 요약",
        life_context=f"{name} 생활 맥락",
        user_goals=["목표 1"],
        pain_points=["불편 1"],
        positive_triggers=["긍정 1"],
        negative_triggers=["부정 1"],
        speaking_style="차분한 말투",
    )


def _opinion(persona_id: str, prefix: str) -> Opinion:
    return Opinion(
        persona_id=persona_id,
        positive_points=[
            ReactionPoint(
                point_id=f"{prefix}_pos_01",
                title="긍정 제목",
                detail="긍정 상세",
            )
        ],
        negative_points=[
            ReactionPoint(
                point_id=f"{prefix}_neg_01",
                title="부정 제목",
                detail="부정 상세",
            )
        ],
        would_use=True,
        would_use_description="사용 의향 설명",
    )


def _review(reviewer_id: str, target_id: str, point_id: str) -> Review:
    return Review(
        reviewer_id=reviewer_id,
        target_id=target_id,
        point_feedbacks=[
            PointFeedback(
                target_point_id=point_id,
                agreement="agree",
                comment="교차 리뷰 코멘트",
            )
        ],
        overall_comment="종합 소감",
        revised_would_use=True,
    )


class SupervisorFormattingTests(unittest.TestCase):
    def test_build_supervisor_prompt_vars_contains_all_artifacts(self) -> None:
        state = {
            "brief": ServicePlanInput(
                raw_text="원문",
                title="테스트 서비스",
                description="서비스 설명",
                target="테스트 타겟",
                key_features=["핵심 기능"],
                concerns="우려사항",
            ),
            "persona_a": _persona("persona_a", "페르소나 A"),
            "persona_b": _persona("persona_b", "페르소나 B"),
            "opinion_a": _opinion("persona_a", "a"),
            "opinion_b": _opinion("persona_b", "b"),
            "review_a": _review("persona_a", "persona_b", "b_pos_01"),
            "review_b": _review("persona_b", "persona_a", "a_pos_01"),
        }

        prompt_vars = _build_supervisor_prompt_vars(state)

        self.assertIn("테스트 서비스", prompt_vars["brief"])
        self.assertIn("페르소나 A", prompt_vars["persona_a"])
        self.assertIn("페르소나 B", prompt_vars["persona_b"])
        self.assertIn("a_pos_01", prompt_vars["opinion_a"])
        self.assertIn("b_pos_01", prompt_vars["opinion_b"])
        self.assertIn("b_pos_01", prompt_vars["review_a"])
        self.assertIn("a_pos_01", prompt_vars["review_b"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test and verify it fails because the module does not exist yet**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -m unittest tests.test_f4_supervisor -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'nodes.f4_supervisor'`.

---

## Task 4: Implement Supervisor Node

**Files:**
- Create: `nodes/f4_supervisor.py`
- Test: `tests/test_f4_supervisor.py`

- [ ] **Step 1: Create `nodes/f4_supervisor.py`**

Create `nodes/f4_supervisor.py`:

```python
"""f4_supervisor — 두 페르소나 의견과 교차 리뷰를 최종 리뷰 텍스트로 종합."""

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage

from schemas import Opinion, Review, ServicePlanInput, TargetUserPersonaCard
from state import ProjectState

load_dotenv()

_llm = ChatUpstage(model="solar-pro3")

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 서비스 기획 리뷰를 정리하는 중립적인 슈퍼바이저입니다. "
        "페르소나처럼 말하지 말고, 제품 기획자가 바로 읽을 수 있는 최종 리뷰를 작성하세요. "
        "입력에 없는 기능, 사용 맥락, 시장 사실은 만들어내지 마세요. "
        "반드시 아래 다섯 섹션을 같은 순서로 작성하세요:\n"
        "1. 종합 판단\n"
        "2. 긍정 신호\n"
        "3. 주요 우려\n"
        "4. 페르소나 간 차이\n"
        "5. 다음 검증 포인트",
    ),
    (
        "human",
        "## 서비스 기획안\n{brief}\n\n"
        "## 페르소나 A\n{persona_a}\n\n"
        "## 페르소나 B\n{persona_b}\n\n"
        "## 페르소나 A의 1차 의견\n{opinion_a}\n\n"
        "## 페르소나 B의 1차 의견\n{opinion_b}\n\n"
        "## 페르소나 A가 B 의견을 읽고 남긴 리뷰\n{review_a}\n\n"
        "## 페르소나 B가 A 의견을 읽고 남긴 리뷰\n{review_b}\n\n"
        "위 내용을 종합해 최종 리뷰를 작성하세요.",
    ),
])


def _format_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items) if items else "- 없음"


def _format_brief(brief: ServicePlanInput) -> str:
    features = _format_list(brief.key_features)
    return (
        f"제목: {brief.title or '-'}\n"
        f"설명: {brief.description or '-'}\n"
        f"타겟: {brief.target or '-'}\n"
        f"핵심 기능:\n{features}\n"
        f"우려사항: {brief.concerns or '-'}"
    )


def _format_persona(persona: TargetUserPersonaCard) -> str:
    return (
        f"ID: {persona.card_id}\n"
        f"이름: {persona.display_name}\n"
        f"연령대/성별/직업/지역: "
        f"{persona.age_group or '-'} / {persona.sex or '-'} / "
        f"{persona.occupation or '-'} / {persona.region or '-'}\n"
        f"요약: {persona.one_line_summary}\n"
        f"생활 맥락: {persona.life_context}\n"
        f"목표:\n{_format_list(persona.user_goals)}\n"
        f"불편함:\n{_format_list(persona.pain_points)}\n"
        f"긍정 트리거:\n{_format_list(persona.positive_triggers)}\n"
        f"부정 트리거:\n{_format_list(persona.negative_triggers)}\n"
        f"말투: {persona.speaking_style}"
    )


def _format_opinion(opinion: Opinion) -> str:
    positive = "\n".join(
        f"- [{point.point_id}] {point.title}: {point.detail}"
        for point in opinion.positive_points
    )
    negative = "\n".join(
        f"- [{point.point_id}] {point.title}: {point.detail}"
        for point in opinion.negative_points
    )
    would_use = "사용할 것" if opinion.would_use else "사용 안 할 것"
    return (
        f"persona_id: {opinion.persona_id}\n"
        f"긍정 포인트:\n{positive or '- 없음'}\n"
        f"부정 포인트:\n{negative or '- 없음'}\n"
        f"사용 의향: {would_use}\n"
        f"사용 의향 이유: {opinion.would_use_description or '-'}"
    )


def _format_review(review: Review) -> str:
    feedbacks = "\n".join(
        f"- [{feedback.target_point_id}] {feedback.agreement}: {feedback.comment}"
        for feedback in review.point_feedbacks
    )
    revised = "사용할 것" if review.revised_would_use else "사용 안 할 것"
    return (
        f"reviewer_id: {review.reviewer_id}\n"
        f"target_id: {review.target_id}\n"
        f"포인트별 피드백:\n{feedbacks or '- 없음'}\n"
        f"종합 소감: {review.overall_comment}\n"
        f"수정된 사용 의향: {revised}"
    )


def _build_supervisor_prompt_vars(state: ProjectState) -> dict[str, str]:
    return {
        "brief": _format_brief(state["brief"]),
        "persona_a": _format_persona(state["persona_a"]),
        "persona_b": _format_persona(state["persona_b"]),
        "opinion_a": _format_opinion(state["opinion_a"]),
        "opinion_b": _format_opinion(state["opinion_b"]),
        "review_a": _format_review(state["review_a"]),
        "review_b": _format_review(state["review_b"]),
    }


def supervisor_finalize(state: ProjectState) -> dict:
    """교차 리뷰까지 완료된 state를 읽어 최종 사용자용 리뷰 텍스트를 생성."""
    chain = _PROMPT | _llm | StrOutputParser()
    final_review_text = chain.invoke(_build_supervisor_prompt_vars(state))
    return {"final_review_text": final_review_text.strip()}
```

- [ ] **Step 2: Run the supervisor formatting test**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -m unittest tests.test_f4_supervisor -v
```

Expected: PASS.

Technical reason: this test exercises prompt input assembly without calling Upstage. The LLM call remains covered by the end-to-end script because mocking LangChain runnables adds more test complexity than this iteration needs.

---

## Task 5: Wire Supervisor Into State and Graph

**Files:**
- Modify: `state.py:13-21`
- Modify: `graph.py:5-50`
- Test: `tests/test_f4_supervisor.py`

- [ ] **Step 1: Add `final_review_text` to `ProjectState`**

Modify the class in `state.py` to:

```python
class ProjectState(TypedDict, total=False):
    raw_input: str
    brief: ServicePlanInput
    persona_a: TargetUserPersonaCard
    persona_b: TargetUserPersonaCard
    opinion_a: Opinion
    opinion_b: Opinion
    review_a: Review
    review_b: Review
    final_review_text: str
```

Technical reason: every node returns a partial state dict. Adding the key here documents that `supervisor_finalize` is the owner of the final output.

- [ ] **Step 2: Import the supervisor node in `graph.py`**

Modify the import block in `graph.py` to include:

```python
from nodes.f4_supervisor import supervisor_finalize
```

- [ ] **Step 3: Make `_noop` comments generic**

Replace the opinion-specific comments above `return {}` in `graph.py` with:

```python
def _noop(state: ProjectState) -> dict:
    # 병렬 fan-out 결과가 모두 state에 반영된 뒤 다음 라우팅/종합 노드로 넘어가기 위한 join 포인트.
    # 실제 데이터 변환은 하지 않는다.
    return {}
```

Technical reason: the same no-op join function will be used for both opinion collection and review collection.

- [ ] **Step 4: Register the new graph nodes**

Modify the node registration section in `graph.py` to:

```python
builder.add_node("f0_parse", f0_parse)
builder.add_node("select_personas", select_personas)
builder.add_node("generate_opinion", generate_opinion)
builder.add_node("collect_opinions", _noop)  # opinions fan-out join 포인트
builder.add_node("generate_review", generate_review)
builder.add_node("collect_reviews", _noop)  # reviews fan-out join 포인트
builder.add_node("supervisor_finalize", supervisor_finalize)
```

- [ ] **Step 5: Replace the final edge**

Replace the current final edge:

```python
builder.add_edge("generate_review", END)
```

with:

```python
builder.add_edge("generate_review", "collect_reviews")
builder.add_edge("collect_reviews", "supervisor_finalize")
builder.add_edge("supervisor_finalize", END)
```

Technical reason: `collect_reviews` is the explicit fan-in boundary. The supervisor should not run on a partial state where only one of `review_a` or `review_b` exists.

- [ ] **Step 6: Verify graph import and supervisor test**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -c "import graph; print('import graph OK')"
$env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -m unittest tests.test_f4_supervisor -v
```

Expected:

```text
import graph OK
```

and the unit test passes.

- [ ] **Step 7: Commit the supervisor node and graph wiring**

Run:

```powershell
git add state.py graph.py nodes/f4_supervisor.py tests/test_f4_supervisor.py
git commit -m "feat: add supervisor final review node"
```

---

## Task 6: Update Pipeline Output and Lint Touched Files

**Files:**
- Modify: `scripts/test_pipeline.py:21-23`
- Modify: `scripts/test_pipeline.py:31-37`
- Modify: `scripts/test_pipeline.py:139`
- Modify: `scripts/test_pipeline.py:152`
- Modify: `scripts/test_pipeline.py:168-173`
- Modify: `nodes/f3_review.py:10`

- [ ] **Step 1: Sort local imports in `scripts/test_pipeline.py`**

Use this order after `load_dotenv()`:

```python
from generate_user_cards import generate_cards
from graph import graph
from schemas import Opinion, RawNemotronPersona, Review, TargetUserPersonaCard
```

- [ ] **Step 2: Add node labels for the final graph stages**

Modify `_NODE_LABEL` to:

```python
_NODE_LABEL = {
    "f0_parse": "f0  기획안 파싱",
    "select_personas": "f1  페르소나 선택",
    "generate_opinion": "f2  의견 생성",
    "collect_opinions": "    의견 fan-in",
    "generate_review": "f3  교차 리뷰 생성",
    "collect_reviews": "    리뷰 fan-in",
    "supervisor_finalize": "f4  최종 리뷰 생성",
}
```

- [ ] **Step 3: Remove f-string prefixes without interpolated values**

Change:

```python
print(f"  [종합 소감]")
```

to:

```python
print("  [종합 소감]")
```

Change:

```python
print(f"  기능  :")
```

to:

```python
print("  기능  :")
```

- [ ] **Step 4: Print the supervisor final review**

Insert this block after the cross-review block in `print_results`:

```python
    if result.get("final_review_text"):
        banner("최종 리뷰")
        print(f"\n{result['final_review_text']}")
```

Technical reason: detailed persona artifacts remain visible for debugging, while the supervisor output becomes the final user-facing result.

- [ ] **Step 5: Sort the `schemas` import in `nodes/f3_review.py`**

Change:

```python
from schemas import Opinion, PointFeedback, Review, TargetUserPersonaCard, ServicePlanInput
```

to:

```python
from schemas import Opinion, PointFeedback, Review, ServicePlanInput, TargetUserPersonaCard
```

- [ ] **Step 6: Run lint on touched files without writing Ruff cache**

Run:

```powershell
.venv\Scripts\python.exe -m ruff check graph.py state.py nodes\f3_review.py nodes\f4_supervisor.py scripts\test_pipeline.py tests\test_f4_supervisor.py tests\test_persona_repository.py --no-cache
```

Expected: `All checks passed!`

- [ ] **Step 7: Commit pipeline output and lint cleanup**

Run:

```powershell
git add scripts/test_pipeline.py nodes/f3_review.py
git commit -m "chore: show supervisor result in pipeline script"
```

---

## Task 7: Full Verification

**Files:** verification only

- [ ] **Step 1: Run all stdlib unit tests**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -m unittest discover -s tests -v
```

Expected: all discovered tests pass.

- [ ] **Step 2: Verify graph import**

Run:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe -c "import graph; print('import graph OK')"
```

Expected:

```text
import graph OK
```

- [ ] **Step 3: Run full pipeline with a valid Upstage key**

Run:

```powershell
$env:PYTHONUTF8='1'; $env:PYTHONDONTWRITEBYTECODE='1'; .venv\Scripts\python.exe scripts\test_pipeline.py
```

Expected streamed stages include:

```text
✓ f0  기획안 파싱
✓ f1  페르소나 선택
✓ f2  의견 생성
✓     의견 fan-in
✓ f3  교차 리뷰 생성
✓     리뷰 fan-in
✓ f4  최종 리뷰 생성
```

Expected final output includes the `최종 리뷰` banner.

- [ ] **Step 4: Run full lint**

Run:

```powershell
.venv\Scripts\python.exe -m ruff check . --no-cache
```

Expected: `All checks passed!`

- [ ] **Step 5: Capture final git status**

Run:

```powershell
git status --short
```

Expected: only pre-existing unrelated untracked files remain. Files changed by this plan should be committed.

---

## Task 8: Implementation Rationale Summary for Review

**Files:**
- Read: `git show --stat`
- Read: `git show --name-only --oneline -3`

- [ ] **Step 1: Collect commit evidence**

Run:

```powershell
git show --stat --oneline HEAD
git show --stat --oneline HEAD~1
git show --stat --oneline HEAD~2
```

Expected: the three implementation commits show data/test fix, supervisor node wiring, and pipeline output update.

- [ ] **Step 2: Prepare the final engineering explanation**

The final response should include:

- Why seed data was regenerated instead of changing `schemas.py`.
- Why `final_review_text` was added as a string state key.
- Why `nodes/f4_supervisor.py` is separate from `nodes/f3_review.py`.
- Why `collect_reviews` exists before `supervisor_finalize`.
- Which verification commands passed and which required API/network.

Technical reason: this gives maintainers the code-line rationale the user requested without mixing permanent implementation history into unrelated review docs.
